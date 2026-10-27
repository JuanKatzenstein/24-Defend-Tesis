#!/usr/bin/env python3
"""
generar_sinteticos.py — genera hostnames sintéticos de la clase phishing = 1
llamando a un LLM por API (Claude, vía SDK oficial `anthropic`).

Flujo por lote:
  1. Calibra con el CSV combinado (solo filas phishing = 1 del split TRAIN,
     para no filtrar ejemplos del test al generador).
  2. Muestrea un plan: forma (apex / sub_ajeno / plataforma), marca y sufijo
     (com, com.br, ...) o plataforma, respetando las proporciones del corpus.
  3. Arma el prompt (system + user) con ejemplos reales estratificados y la
     lista de hosts ya generados (para que no repita patrones entre lotes).
  4. Pide salida estructurada (JSON validado con Pydantic).
  5. Valida cada host contra su fila del plan, descarta casi-copias del corpus
     y duplicados, y registra qué modelo sirvió cada lote.

Solo produce cadenas de hostname (sin paths, sin contenido de páginas): es
material para entrenar/evaluar el detector, no para desplegar sitios.

Parámetros de la API (ver docs de Claude Opus 5.5, effort, structured outputs
y refusals-and-fallback):
  - Sin temperature/top_p: Claude Opus 5.5 los rechaza (400). La diversidad sale
    del plan muestreado, de los ejemplos rotados y de la lista de ya generados.
  - Thinking adaptativo siempre activo; el control es output_config.effort
    (default de la API: medium). Se fija explícito con --effort.
  - max_tokens incluye el thinking: 16000 alcanza de sobra para 25-40 hosts.
  - System prompt cacheado (cache_control): es idéntico en todos los lotes.
  - fallbacks="default": si el clasificador de seguridad rechaza el pedido, la
    API lo reintenta en el modelo recomendado; el modelo que sirvió queda en
    la columna modelo_servido.

Uso:
    pip install anthropic pydantic pandas
    export ANTHROPIC_API_KEY=...
    python3 generar_sinteticos.py --csv ../data/raw/dataset_combinado_v4.csv \
        --n-lotes 10 --por-lote 25 --out ../data/raw/phishing_sintetico_llm.csv
    python3 generar_sinteticos.py --csv ... --dry-run   # imprime el prompt, no llama a la API

Las columnas de features se recalculan después con src/features.py; acá solo
se generan hostname + metadatos (fuente = "sintetico_llm").
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import List

import pandas as pd
from pydantic import BaseModel, Field

MODELO_DEFAULT = "claude-opus-5-5"
FORMAS = ("apex", "sub_ajeno", "plataforma")
MAX_YA_GENERADOS = 60  # cuántos hosts previos se muestran en el prompt

RE_HOST = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")


# ---------------------------------------------------------------------------
# 1. Esquema de salida (structured output)
# ---------------------------------------------------------------------------

class HostSintetico(BaseModel):
    id: int = Field(description="Número de fila del plan")
    hostname: str = Field(description="Hostname completo, en minúsculas, sin esquema ni path")
    # str en vez de Literal: la doc avisa que el modelo puede cambiar mayúsculas
    # de un enum; se normaliza y valida en validar().
    forma: str = Field(description="apex, sub_ajeno o plataforma")
    marca: str = Field(description="Marca suplantada, o 'ninguna'")
    patron: str = Field(description="Etiqueta corta del patrón, máx. 6 palabras (ej. 'marca+palabra gancho')")


class Lote(BaseModel):
    hosts: List[HostSintetico]


# ---------------------------------------------------------------------------
# 2. Calibración desde el CSV
# ---------------------------------------------------------------------------

def forma_de(row) -> str:
    if row.en_plataforma_hosting == 1:
        return "plataforma"
    return "apex" if row.n_subdomains == 0 else "sub_ajeno"


def cargar(csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv)
    df["hostname"] = df.hostname.str.lower()
    # sufijo público tal como lo calculó el CSV (dominio menos su primer label: com, com.br, ...)
    df["sufijo"] = df.dominio.str.lower().str.split(".", n=1).str[1]
    phish = df[(df.phishing == 1) & (df.split == "train")].copy()
    phish["forma"] = phish.apply(forma_de, axis=1)
    return df, phish


def calibracion(df: pd.DataFrame, phish: pd.DataFrame) -> dict:
    no_plat = phish[phish.forma != "plataforma"]
    marcas = phish.marca_detectada.fillna("ninguna").replace("", "ninguna")
    return {
        "forma": phish.forma.value_counts(normalize=True).to_dict(),
        "sufijo": no_plat.sufijo.value_counts(normalize=True).head(25).to_dict(),
        "plataforma": phish[phish.forma == "plataforma"].plataforma.value_counts(normalize=True).to_dict(),
        "marca": marcas.value_counts(normalize=True).head(30).to_dict(),
        "host_len_p10_p50_p90": phish.host_len.quantile([0.1, 0.5, 0.9]).round().astype(int).tolist(),
        "host_len_min_max": phish.host_len.quantile([0.01, 0.99]).round().astype(int).tolist(),
        # sufijos de dos niveles vistos en todo el corpus (com.br, com.uy, ...)
        "sufijos_2n": {s for s in df.sufijo.dropna().unique() if "." in s},
        "plataformas": set(df.plataforma.dropna().unique()),
    }


def muestrear(pesos: dict, k: int, rng: random.Random) -> list:
    return rng.choices(list(pesos), weights=list(pesos.values()), k=k)


def plan_lote(cal: dict, n: int, rng: random.Random) -> list[dict]:
    """Una fila por host a generar: forma + marca + sufijo/plataforma."""
    filas = []
    for i, forma in enumerate(muestrear(cal["forma"], n, rng), 1):
        fila = {"id": i, "forma": forma, "marca": muestrear(cal["marca"], 1, rng)[0]}
        if forma == "plataforma":
            fila["plataforma"] = muestrear(cal["plataforma"], 1, rng)[0]
        else:
            fila["sufijo"] = muestrear(cal["sufijo"], 1, rng)[0]
        filas.append(fila)
    return filas


def ejemplos(phish: pd.DataFrame, k_por_forma: int, rng: random.Random) -> list[str]:
    out = []
    for _, grupo in phish.groupby("forma"):
        out += grupo.sample(min(k_por_forma, len(grupo)), random_state=rng.randint(0, 10**6)).hostname.tolist()
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------------------
# 3. Prompt
# ---------------------------------------------------------------------------

SYSTEM = """\
Sos un asistente de investigación en ciberseguridad defensiva. Ayudás a construir \
un dataset para una tesis de detección de phishing basada solo en la cadena del \
hostname (clasificación léxica antes de visitar el sitio). Los hostnames que \
generes se usan únicamente como ejemplos de entrenamiento de un clasificador: \
nunca se registran ni se resuelven.

Tu tarea es generar hostnames SINTÉTICOS de la clase phishing que sean \
estadísticamente indistinguibles de los del corpus real (phishing dirigido a \
Uruguay y la región: banca, fintech, e-commerce, telcos, gobierno, logística). \
El objetivo es realismo, no creatividad: un analista no debería poder separar \
tus hosts de los reales.

Reglas:
- Devolvé solo hostnames: minúsculas, sin esquema (http://), sin path, sin puerto.
- Caracteres válidos: a-z, 0-9, guion y punto. Ningún label empieza ni termina en guion.
- No copies ningún ejemplo ni lo cambies solo en números o guiones; variá la \
  estructura, el vocabulario y la longitud.
- No repitas el patrón de los hosts ya generados en lotes anteriores.
- No uses dominios oficiales reales de las marcas (ej. itau.com.uy, antel.com.uy) \
  como dominio registrado: el dominio registrado siempre es ajeno a la marca, \
  salvo en la forma "plataforma" donde es la plataforma de hosting.
- Imitá el ruido real: no todos llevan marca, algunos usan palabras gancho \
  (soporte, verificar, actualizar, envios, reembolso...), mezclas de español y \
  portugués, números, typosquatting, subdominios aleatorios tipo gibberish.
- Respetá exactamente la forma, la marca y el sufijo o la plataforma de cada fila del plan.

Definición de formas (el sufijo es la parte final que se registra: com, com.br, com.uy, top...):
- apex: <nombre>.<sufijo>, sin ningún subdominio (ej. patrón <marca>-<palabra>.<sufijo>).
- sub_ajeno: uno o más subdominios sobre un dominio registrado ajeno a la marca \
  (ej. <marca>.<dominio-inventado>.<sufijo>).
- plataforma: subdominio sobre una plataforma de hosting gratuito \
  (ej. <algo>.pages.dev, <algo>.000webhostapp.com).

En el campo "patron" poné solo una etiqueta corta, no expliques tu razonamiento.
"""


def prompt_usuario(plan: list[dict], ejs: list[str], cal: dict, ya_generados: list[str]) -> str:
    p10, p50, p90 = cal["host_len_p10_p50_p90"]
    lineas = [
        "Ejemplos reales del corpus (solo de referencia de estilo, NO copiar):",
        *[f"- {h}" for h in ejs],
        "",
        f"Longitud del hostname en el corpus: p10={p10}, mediana={p50}, p90={p90} caracteres.",
        "",
    ]
    if ya_generados:
        lineas += [
            "Hosts ya generados en lotes anteriores (no repitas estos patrones):",
            ", ".join(ya_generados),
            "",
        ]
    lineas += [
        f"Generá exactamente {len(plan)} hostnames siguiendo este plan (una fila = un host, mismo id):",
        "",
        "| id | forma | marca | sufijo / plataforma |",
        "|----|-------|-------|---------------------|",
    ]
    for f in plan:
        destino = f.get("plataforma") or "." + f["sufijo"]
        lineas.append(f"| {f['id']} | {f['forma']} | {f['marca']} | {destino} |")
    lineas += [
        "",
        "Cuando la marca sea 'ninguna', generá un host de phishing sin marca reconocible "
        "(gibberish, palabras gancho o nombre de negocio genérico).",
    ]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# 4. Llamada a la API
# ---------------------------------------------------------------------------

def llamar(client, args, prompt: str) -> tuple[Lote, str, bool]:
    resp = client.beta.messages.parse(
        model=args.modelo,
        max_tokens=16000,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
        output_format=Lote,
        output_config={"effort": args.effort},
        # Si el clasificador de seguridad rechaza el pedido, la API lo reintenta
        # en el modelo de respaldo recomendado dentro de la misma llamada.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Pedido rechazado (también por el fallback): {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Respuesta truncada (max_tokens); bajar --por-lote.")
    hubo_fallback = any(it.type == "fallback_message" for it in (resp.usage.iterations or []))
    return resp.parsed_output, resp.model, hubo_fallback


# ---------------------------------------------------------------------------
# 5. Validación
# ---------------------------------------------------------------------------

def esqueleto(host: str) -> str:
    """Host sin dígitos ni guiones: detecta casi-copias tipo americanas-loja34 -> americanas-loja35."""
    return re.sub(r"[0-9-]", "", host)


def dominio_registrado(host: str, cal: dict) -> tuple[str, str]:
    """(dominio registrado, sufijo) usando los sufijos de dos niveles del corpus."""
    labels = host.split(".")
    n = 2 if len(labels) >= 3 and ".".join(labels[-2:]) in cal["sufijos_2n"] else 1
    sufijo = ".".join(labels[-n:])
    return ".".join(labels[-(n + 1):]), sufijo


def motivo_rechazo(h: HostSintetico, fila: dict | None, cal: dict,
                   vistos: set[str], esqueletos: set[str]) -> str | None:
    host = h.hostname
    if not RE_HOST.match(host):
        return "formato_invalido"
    if host in vistos:
        return "duplicado"
    if esqueleto(host) in esqueletos:
        return "casi_copia"
    lo, hi = cal["host_len_min_max"]
    if not lo <= len(host) <= hi:
        return "largo_fuera_de_rango"
    if fila is None or h.forma != fila["forma"]:
        return "no_respeta_plan"
    plataforma = next((p for p in cal["plataformas"] if host.endswith("." + p)), None)
    if fila["forma"] == "plataforma":
        return None if plataforma == fila["plataforma"] else "no_respeta_plan"
    if plataforma:
        return "no_respeta_plan"
    registrado, sufijo = dominio_registrado(host, cal)
    if sufijo != fila["sufijo"]:
        return "no_respeta_plan"
    es_apex = registrado == host
    if es_apex != (fila["forma"] == "apex"):
        return "no_respeta_plan"
    return None


def validar(lote: Lote, plan: list[dict], cal: dict,
            vistos: set[str], esqueletos: set[str]) -> tuple[list[HostSintetico], Counter]:
    por_id = {f["id"]: f for f in plan}
    ok, motivos = [], Counter()
    for h in lote.hosts:
        h.hostname = h.hostname.strip().lower().rstrip(".")
        h.forma = h.forma.strip().lower()
        motivo = motivo_rechazo(h, por_id.get(h.id), cal, vistos, esqueletos)
        if motivo:
            motivos[motivo] += 1
            continue
        vistos.add(h.hostname)
        esqueletos.add(esqueleto(h.hostname))
        ok.append(h)
    if len(lote.hosts) != len(plan):
        motivos["cantidad_distinta_al_plan"] += abs(len(plan) - len(lote.hosts))
    return ok, motivos


def resumen(nuevo: pd.DataFrame, phish: pd.DataFrame, cal: dict) -> None:
    largos = nuevo.hostname.str.len().quantile([0.1, 0.5, 0.9]).round().astype(int).tolist()
    print("Formas  sintético:", nuevo.forma.value_counts(normalize=True).round(2).to_dict())
    print("        corpus:   ", {k: round(v, 2) for k, v in cal["forma"].items()})
    print(f"Largo p10/p50/p90 sintético: {largos}  corpus: {cal['host_len_p10_p50_p90']}")
    print("Modelos que sirvieron:", nuevo.modelo_servido.value_counts().to_dict())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path, help="dataset combinado (con columna phishing)")
    ap.add_argument("--out", type=Path, default=Path("phishing_sintetico_llm.csv"))
    ap.add_argument("--n-lotes", type=int, default=1)
    ap.add_argument("--por-lote", type=int, default=25)
    ap.add_argument("--ejemplos-por-forma", type=int, default=6)
    ap.add_argument("--modelo", default=MODELO_DEFAULT)
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="imprime el prompt del primer lote y sale")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    df, phish = cargar(args.csv)
    cal = calibracion(df, phish)
    vistos = set(df.hostname)
    esqueletos = {esqueleto(h) for h in df.hostname}

    if args.out.exists():
        previos = pd.read_csv(args.out)
        vistos |= set(previos.hostname)
        esqueletos |= {esqueleto(h) for h in previos.hostname}
        ya_generados = previos.hostname.tolist()
        lote_ini = int(previos.lote.max()) + 1
    else:
        previos, ya_generados, lote_ini = None, [], 1

    if args.dry_run:
        plan = plan_lote(cal, args.por_lote, rng)
        prompt = prompt_usuario(plan, ejemplos(phish, args.ejemplos_por_forma, rng), cal,
                                ya_generados[-MAX_YA_GENERADOS:])
        print("=== SYSTEM ===\n" + SYSTEM)
        print("=== USER ===\n" + prompt)
        return

    import anthropic
    client = anthropic.Anthropic(max_retries=4)  # reintenta 429/5xx con backoff

    filas = []
    for n_lote in range(lote_ini, lote_ini + args.n_lotes):
        plan = plan_lote(cal, args.por_lote, rng)
        prompt = prompt_usuario(plan, ejemplos(phish, args.ejemplos_por_forma, rng), cal,
                                ya_generados[-MAX_YA_GENERADOS:])
        try:
            lote, modelo_servido, hubo_fallback = llamar(client, args, prompt)
        except (anthropic.APIError, RuntimeError) as e:
            print(f"[lote {n_lote}] error: {e}", file=sys.stderr)
            continue
        ok, motivos = validar(lote, plan, cal, vistos, esqueletos)
        aviso = f"  (fallback a {modelo_servido})" if hubo_fallback else ""
        print(f"[lote {n_lote}] {len(ok)}/{len(plan)} válidos  descartes={dict(motivos)}{aviso}")
        ya_generados += [h.hostname for h in ok]
        filas += [{**h.model_dump(exclude={"id"}), "phishing": 1, "fuente": "sintetico_llm",
                   "lote": n_lote, "modelo_pedido": args.modelo, "modelo_servido": modelo_servido,
                   "effort": args.effort} for h in ok]

    if not filas:
        sys.exit("No se generó ningún host válido.")
    nuevo = pd.DataFrame(filas)
    if previos is not None:
        nuevo = pd.concat([previos, nuevo], ignore_index=True)
    nuevo.to_csv(args.out, index=False)
    print(f"Guardado: {args.out} ({len(nuevo)} hosts en total)")
    resumen(nuevo, phish, cal)


if __name__ == "__main__":
    main()
