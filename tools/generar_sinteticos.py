#!/usr/bin/env python3
"""
generar_sinteticos.py — genera hostnames sintéticos de la clase phishing = 1
llamando a un LLM por API (Claude, vía SDK oficial `anthropic`).

Flujo por lote:
  1. Calibra con el CSV combinado (solo filas phishing = 1 del split TRAIN,
     para no filtrar ejemplos del test al generador).
  2. Muestrea un plan: cuántos hosts por forma (apex / sub_ajeno / plataforma),
     qué marcas, qué TLD/plataformas, respetando las proporciones del corpus.
  3. Arma el prompt (system + user) con ejemplos reales estratificados.
  4. Pide salida estructurada (JSON validado con Pydantic).
  5. Valida y deduplica contra el dataset y contra lotes anteriores.

Solo produce cadenas de hostname (sin paths, sin contenido de páginas): es
material para entrenar/evaluar el detector, no para desplegar sitios.

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
from typing import List, Literal

import pandas as pd
from pydantic import BaseModel, Field

MODELO_DEFAULT = "claude-opus-5-5"

RE_HOST = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")


# ---------------------------------------------------------------------------
# 1. Esquema de salida (structured output)
# ---------------------------------------------------------------------------

class HostSintetico(BaseModel):
    hostname: str = Field(description="Hostname completo, en minúsculas, sin esquema ni path")
    forma: Literal["apex", "sub_ajeno", "plataforma"]
    marca: str = Field(description="Marca suplantada, o 'ninguna'")
    tld: str
    plataforma: str = Field(description="Dominio de la plataforma de hosting, o 'ninguna'")
    patron: str = Field(description="Descripción breve del patrón usado (ej. 'marca+palabra gancho', 'typosquat')")


class Lote(BaseModel):
    hosts: List[HostSintetico]


# ---------------------------------------------------------------------------
# 2. Calibración desde el CSV
# ---------------------------------------------------------------------------

def forma_de(row) -> str:
    if row.en_plataforma_hosting == 1:
        return "plataforma"
    return "apex" if row.n_subdomains == 0 else "sub_ajeno"


def cargar(csv: Path) -> tuple[pd.DataFrame, set[str]]:
    df = pd.read_csv(csv)
    todos = set(df.hostname.str.lower())
    phish = df[(df.phishing == 1) & (df.split == "train")].copy()
    phish["forma"] = phish.apply(forma_de, axis=1)
    return phish, todos


def calibracion(phish: pd.DataFrame) -> dict:
    n = len(phish)
    marcas = phish.marca_detectada.fillna("ninguna").replace("", "ninguna")
    return {
        "forma": (phish.forma.value_counts() / n).to_dict(),
        "tld": (phish[phish.forma != "plataforma"].tld.value_counts(normalize=True)).head(20).to_dict(),
        "plataforma": phish[phish.forma == "plataforma"].plataforma.value_counts(normalize=True).to_dict(),
        "marca": (marcas.value_counts(normalize=True)).head(30).to_dict(),
        "es_uy": phish.es_uy.mean(),
        "host_len_p10_p50_p90": phish.host_len.quantile([0.1, 0.5, 0.9]).round().astype(int).tolist(),
    }


def muestrear(pesos: dict, k: int, rng: random.Random) -> list:
    return rng.choices(list(pesos), weights=list(pesos.values()), k=k)


def plan_lote(cal: dict, n: int, rng: random.Random) -> list[dict]:
    """Una fila por host a generar: forma + marca + tld/plataforma."""
    filas = []
    for forma in muestrear(cal["forma"], n, rng):
        fila = {"forma": forma, "marca": muestrear(cal["marca"], 1, rng)[0]}
        if forma == "plataforma":
            fila["plataforma"] = muestrear(cal["plataforma"], 1, rng)[0]
        else:
            fila["tld"] = muestrear(cal["tld"], 1, rng)[0]
        filas.append(fila)
    return filas


def ejemplos(phish: pd.DataFrame, k_por_forma: int, rng: random.Random) -> list[str]:
    out = []
    for forma, grupo in phish.groupby("forma"):
        out += grupo.sample(min(k_por_forma, len(grupo)), random_state=rng.randint(0, 10**6)).hostname.tolist()
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------------------
# 3. Prompt
# ---------------------------------------------------------------------------

SYSTEM = """\
Sos un asistente de investigación en ciberseguridad defensiva. Ayudás a construir \
un dataset para una tesis de detección de phishing basada solo en la cadena del \
hostname (clasificación léxica antes de visitar el sitio).

Tu tarea es generar hostnames SINTÉTICOS de la clase phishing que sean \
estadísticamente indistinguibles de los del corpus real (phishing dirigido a \
Uruguay y la región: banca, fintech, e-commerce, telcos, gobierno, logística).

Reglas:
- Devolvé solo hostnames: minúsculas, sin esquema (http://), sin path, sin puerto.
- Caracteres válidos: a-z, 0-9, guion y punto. Ningún label empieza ni termina en guion.
- No copies ningún ejemplo literal ni lo modifiques en un solo carácter; variá la \
  estructura, el vocabulario y la longitud.
- No uses dominios oficiales reales de las marcas (ej. itau.com.uy, antel.com.uy) \
  como dominio registrado: el dominio registrado siempre es ajeno a la marca, \
  salvo en la forma "plataforma" donde es la plataforma de hosting.
- Imitá el ruido real: no todos llevan marca, algunos usan palabras gancho \
  (soporte, verificar, actualizar, envios, reembolso...), mezclas de español y \
  portugués, números, typosquatting, subdominios aleatorios tipo gibberish.
- Respetá exactamente la forma, la marca y el TLD/plataforma pedidos en cada fila del plan.

Definición de formas:
- apex: marca/palabras directamente en el dominio registrado, sin subdominio \
  (ej. patrón <marca>-<palabra>.<tld>).
- sub_ajeno: la marca va en un subdominio de un dominio registrado ajeno \
  (ej. <marca>.<dominio-inventado>.<tld>).
- plataforma: subdominio sobre una plataforma de hosting gratuito \
  (ej. <algo>.pages.dev, <algo>.000webhostapp.com).
"""


def prompt_usuario(plan: list[dict], ejs: list[str], cal: dict) -> str:
    p10, p50, p90 = cal["host_len_p10_p50_p90"]
    lineas = [
        "Ejemplos reales del corpus (solo de referencia de estilo, NO copiar):",
        *[f"- {h}" for h in ejs],
        "",
        f"Longitud del hostname en el corpus: p10={p10}, mediana={p50}, p90={p90} caracteres.",
        "",
        f"Generá exactamente {len(plan)} hostnames siguiendo este plan (una fila = un host):",
        "",
        "| # | forma | marca | tld / plataforma |",
        "|---|-------|-------|------------------|",
    ]
    for i, f in enumerate(plan, 1):
        destino = f.get("plataforma") or "." + f["tld"]
        lineas.append(f"| {i} | {f['forma']} | {f['marca']} | {destino} |")
    lineas += [
        "",
        "Cuando la marca sea 'ninguna', generá un host de phishing sin marca reconocible "
        "(gibberish, palabras gancho o nombre de negocio genérico).",
        "Devolvé los hosts en el mismo orden del plan.",
    ]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# 4. Llamada a la API y validación
# ---------------------------------------------------------------------------

def llamar(client, modelo: str, plan: list[dict], ejs: list[str], cal: dict) -> Lote:
    resp = client.beta.messages.parse(
        model=modelo,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt_usuario(plan, ejs, cal)}],
        output_format=Lote,
        output_config={"effort": "medium"},
        # Si el clasificador de seguridad rechaza el pedido, la API lo reintenta
        # en un modelo de respaldo dentro de la misma llamada.
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Pedido rechazado por el modelo: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Respuesta truncada (max_tokens); bajar --por-lote.")
    return resp.parsed_output


def validar(lote: Lote, vistos: set[str]) -> tuple[list[HostSintetico], Counter]:
    ok, motivos = [], Counter()
    for h in lote.hosts:
        host = h.hostname.strip().lower().rstrip(".")
        if not RE_HOST.match(host):
            motivos["formato_invalido"] += 1
        elif host in vistos:
            motivos["duplicado"] += 1
        else:
            vistos.add(host)
            h.hostname = host
            ok.append(h)
    return ok, motivos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path, help="dataset combinado (con columna phishing)")
    ap.add_argument("--out", type=Path, default=Path("phishing_sintetico_llm.csv"))
    ap.add_argument("--n-lotes", type=int, default=1)
    ap.add_argument("--por-lote", type=int, default=25)
    ap.add_argument("--ejemplos-por-forma", type=int, default=6)
    ap.add_argument("--modelo", default=MODELO_DEFAULT)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="imprime el prompt del primer lote y sale")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    phish, vistos = cargar(args.csv)
    cal = calibracion(phish)

    if args.out.exists():
        previos = pd.read_csv(args.out)
        vistos |= set(previos.hostname.str.lower())
        lote_ini = int(previos.lote.max()) + 1
    else:
        previos, lote_ini = None, 1

    if args.dry_run:
        plan = plan_lote(cal, args.por_lote, rng)
        print("=== SYSTEM ===\n" + SYSTEM)
        print("=== USER ===\n" + prompt_usuario(plan, ejemplos(phish, args.ejemplos_por_forma, rng), cal))
        return

    import anthropic
    client = anthropic.Anthropic()

    filas = []
    for n_lote in range(lote_ini, lote_ini + args.n_lotes):
        plan = plan_lote(cal, args.por_lote, rng)
        ejs = ejemplos(phish, args.ejemplos_por_forma, rng)
        try:
            lote = llamar(client, args.modelo, plan, ejs, cal)
        except (anthropic.APIError, RuntimeError) as e:
            print(f"[lote {n_lote}] error: {e}", file=sys.stderr)
            continue
        ok, motivos = validar(lote, vistos)
        print(f"[lote {n_lote}] {len(ok)}/{len(plan)} válidos  descartes={dict(motivos)}")
        filas += [{**h.model_dump(), "phishing": 1, "fuente": "sintetico_llm",
                   "lote": n_lote, "modelo": args.modelo} for h in ok]

    if not filas:
        sys.exit("No se generó ningún host válido.")
    nuevo = pd.DataFrame(filas)
    if previos is not None:
        nuevo = pd.concat([previos, nuevo], ignore_index=True)
    nuevo.to_csv(args.out, index=False)
    print(f"Guardado: {args.out} ({len(nuevo)} hosts en total)")
    print("Distribución de formas generadas:", nuevo.forma.value_counts(normalize=True).round(2).to_dict())
    print("Objetivo (corpus train):         ", {k: round(v, 2) for k, v in cal["forma"].items()})


if __name__ == "__main__":
    main()
