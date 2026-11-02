#!/usr/bin/env python3
"""
gen_sinteticos.py — Fase 1 del plan de generación (phishing sintético regional).

Toma el PLAN muestreado por `plan_lote.py` (Fase 2) y lo *realiza*: convierte cada
fila de parámetros en un hostname concreto usando un modelo de Anthropic. La salida
es un CSV en el MISMO esquema que `data/raw/corpus_sintetico.csv`, listo para:

  - entrenar/evaluar el detector (`build_dataset.py` solo usa la columna `url`), y
  - volver a usarse como corpus de ejemplos de `plan_lote.py` (Fase 2).

Alcance / ética (importante para la tesis):
  Esto produce ETIQUETAS de entrenamiento (strings de hostnames con estilo phishing)
  para un DETECTOR defensivo. No registra dominios, no levanta sitios, no genera
  páginas ni credenciales: la salida es un dataset de texto que consume el pipeline
  de detección. Elegir un nombre de dominio plausible no es la parte difícil ni
  escasa del phishing, así que el artefacto no da ventaja operativa a un atacante;
  sí da a la tesis una clase positiva regional etiquetada que no existe lista para
  bajar. El hosting/payload queda deliberadamente fuera de alcance.

Diseño (según `plan_lote.py`):
  Fase 2 (plan_lote)  -> tabla de parámetros por muestreo (forma/gramática/TLD/marca/
                         palabra/NN/estilo/path/largo), calibrada con proporciones del
                         corpus regional.
  Fase 1 (este script)-> el modelo redacta UN host por fila imitando la FORMA de los
                         ejemplos reales (nunca copiándolos), respetando la gramática.
  Fase 3 (validar_lote)-> control de calidad del plan (distribución, no-repetición).

Uso:
    export TESIS_ANTHROPIC_API_KEY=sk-ant-...   # (o HESIS_... / ANTHROPIC_API_KEY)
    python3 gen_sinteticos.py --n 125 \
        --csv ../data/raw/corpus_sintetico.csv \
        --out ../data/raw/sinteticos_lote.csv \
        --out-plan ../data/processed/plan_lote_125.json \
        --seed 20251102

    # sin consumir API (arma plan + prompts y sale):
    python3 gen_sinteticos.py --n 125 --dry-run --out-prompts /tmp/prompts.md

Dependencias: pandas, tldextract, anthropic.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import pandas as pd
import tldextract

# Reutilizamos TODA la calibración y el muestreo de la Fase 2 (no se duplica diseño).
import plan_lote as f2

# tldextract sin red: usamos el snapshot de PSL que trae el paquete (no refresca online).
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())

# Nombres candidatos de la variable de entorno con la API key (tolera el typo "HESIS").
ENV_KEYS = ["TESIS_ANTHROPIC_API_KEY", "HESIS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"]

MARCAS_SET = {m[0] for m in f2.MARCAS}


# ---------------------------------------------------------------------------
# 1. Clave y cliente
# ---------------------------------------------------------------------------

def resolver_key() -> tuple[str, str]:
    for name in ENV_KEYS:
        v = os.environ.get(name)
        if v:
            return v, name
    sys.exit(f"[error] no encontré la API key. Definí una de: {', '.join(ENV_KEYS)}")


# ---------------------------------------------------------------------------
# 2. Construcción del plan (Fase 2) hasta exactamente n filas
# ---------------------------------------------------------------------------

def construir_plan(n: int, csv: Path, historial: Path, seed: int):
    rng = random.Random(seed)
    df = f2.clasificar_regional(pd.read_csv(csv))
    hist = f2.Historial(historial)

    filas: list[dict] = []
    # armar_lote respeta la no-repetición (marca, gramática); las gramáticas que
    # fuerzan marca o que no llevan marca (A3a/A3b/S1b/S3) rellenan sin tope, así
    # que iterando se alcanza exactamente n sin tocar la lógica de Fase 2.
    for _ in range(200):
        if len(filas) >= n:
            break
        filas += f2.armar_lote(n - len(filas), hist, rng)
    filas = filas[:n]
    for i, fila in enumerate(filas, 1):
        fila["id"] = i

    ejemplos = f2.ejemplos_por_gramatica(df, k=4, rng_seed=seed)
    vedados = f2.tokens_vedados(ejemplos, MARCAS_SET | {"card"})
    hist.guardar()
    return filas, ejemplos, vedados


# ---------------------------------------------------------------------------
# 3. Prompt (la "explicación del modelo" vive también en reports/)
# ---------------------------------------------------------------------------

SYSTEM = (
    "Sos un asistente que ayuda a construir un DATASET DE ENTRENAMIENTO ETIQUETADO "
    "para un DETECTOR DEFENSIVO de phishing (tesis de grado). Tu tarea es puramente "
    "de generación de texto: redactar hostnames de estilo phishing que sirvan como "
    "clase positiva para que un clasificador aprenda a RECONOCERLOS y proteger a los "
    "usuarios. No registrás dominios ni construís sitios; solo producís strings.\n\n"
    "Trabajás a partir de un PLAN de parámetros muestreado de proporciones reales del "
    "corpus regional rioplatense. Para cada fila del plan generás UN hostname que "
    "IMITA LA FORMA de los ejemplos reales dados, pero sin copiarlos y sin reutilizar "
    "los tokens vedados. Seguí exactamente: la marca indicada (si hay), el TLD o la "
    "plataforma, la palabra-gancho (si hay), el NN (si hay), el estilo y el largo "
    "objetivo. Todo en minúsculas y con etiquetas DNS válidas (solo a-z, 0-9 y guion; "
    "sin guion al inicio/fin de etiqueta).\n\n"
    "Respondé ÚNICAMENTE con un array JSON válido, sin texto alrededor, sin markdown. "
    'Cada elemento: {"id": <int>, "host": "<hostname>", "path": "<path o cadena vacía>"}. '
    "El path: si el plan dice 'sin', devolvé \"\"; si trae un placeholder como "
    "'/?id=<hash de 6>', resolvelo a un valor concreto."
)


def fila_a_linea(fila: dict) -> str:
    marca = fila["marca"] or "(sin marca)"
    palabra = fila["palabra_es"] or "—"
    estilo = fila["estilo_inventar"]
    if fila["nn"]:
        estilo = f"NN={fila['nn']}; " + estilo
    return (f'id={fila["id"]} | marca={marca} | gramatica={fila["gramatica"]} | '
            f'tld_o_plataforma={fila["tld_o_plataforma"]} | palabra={palabra} | '
            f'estilo={estilo} | path={fila["path"]} | largo={fila["largo_objetivo"]}')


def construir_prompt(filas: list[dict], ejemplos: dict, vedados: list[str]) -> str:
    out = ["# PLAN DEL LOTE (una fila = un host a generar)", ""]
    out += [fila_a_linea(f) for f in filas]
    out += ["", "# EJEMPLOS REALES por gramática (imitá la forma, NUNCA copies)"]
    usados = {f["gramatica"] for f in filas}
    for gram, hosts in ejemplos.items():
        if gram in usados and hosts:
            out.append(f"{gram}: " + " · ".join(hosts))
    out += ["", "# TOKENS VEDADOS (no los uses ni los modifiques):",
            ", ".join(vedados[:60]), "",
            "Devolvé el array JSON con exactamente "
            f"{len(filas)} objetos, uno por id."]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 4. Llamada al modelo + parseo robusto
# ---------------------------------------------------------------------------

def _parse_json_array(texto: str) -> list[dict]:
    t = texto.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.MULTILINE).strip()
    ini, fin = t.find("["), t.rfind("]")
    if ini == -1 or fin == -1:
        raise ValueError("la respuesta no contiene un array JSON")
    return json.loads(t[ini:fin + 1])


class RefusalError(RuntimeError):
    """El modelo declinó la generación (stop_reason=refusal o sin texto).

    Es una respuesta de política de seguridad del modelo, no un error transitorio:
    NO se reintenta ni se reescribe el prompt para esquivarla. El plan se realiza
    por la vía determinista."""


def realizar(client, model: str, filas: list[dict], ejemplos, vedados,
             temperature: float, max_tokens: int) -> dict[int, dict]:
    prompt = construir_prompt(filas, ejemplos, vedados)
    # El gateway de esta sesión no admite `temperature` (ni named ni extra_body):
    # responde 400 "Extra inputs are not permitted". La variabilidad entre hosts la
    # da el muestreo del plan (Fase 2, con --seed); la realización no es determinista.
    _ = temperature  # conservado por compatibilidad de CLI; ignorado aquí
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=SYSTEM, messages=[{"role": "user", "content": prompt}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    if getattr(resp, "stop_reason", None) == "refusal" or not texto.strip():
        raise RefusalError(f"stop_reason={getattr(resp, 'stop_reason', None)}")
    datos = _parse_json_array(texto)
    return {int(d["id"]): d for d in datos if "id" in d and "host" in d}


# ---------------------------------------------------------------------------
# 5. Validación de un host realizado contra su fila del plan
# ---------------------------------------------------------------------------

_LABEL_OK = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def _largo_ok(host: str, largo: str) -> bool:
    n = len(host)
    m = re.match(r"<=(\d+)$", largo)
    if m:
        return n <= int(m.group(1)) + 6          # tolerancia blanda
    m = re.match(r"(\d+)-(\d+)$", largo)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return lo - 6 <= n <= hi + 6
    return True


def validar_host(host: str, fila: dict, ejemplos_set: set, vedados: set) -> str | None:
    """Devuelve None si OK, o un string con el motivo del rechazo."""
    if not host or host != host.lower():
        return "vacío o con mayúsculas"
    if len(host) > 253:
        return "excede 253 chars"
    labels = host.split(".")
    if any(not _LABEL_OK.match(l) for l in labels):
        return "etiqueta DNS inválida"
    suf = fila["tld_o_plataforma"]
    objetivo = suf[1:] if suf.startswith(".") else suf
    if not host.endswith(objetivo):
        return f"no termina en {objetivo}"
    if fila["marca"] and fila["marca"] not in host:
        return f"no contiene la marca {fila['marca']}"
    if fila["palabra_es"] and fila["palabra_es"][:4] not in host:
        return f"no refleja la palabra {fila['palabra_es']}"
    if fila["nn"] and fila["nn"] not in host:
        return f"no contiene NN={fila['nn']}"
    if host in ejemplos_set:
        return "copia un ejemplo real"
    if not _largo_ok(host, fila["largo_objetivo"]):
        return f"largo fuera de {fila['largo_objetivo']} (={len(host)})"
    return None


# ---------------------------------------------------------------------------
# 6. Fallback determinista (garantiza lote completo; se marca como tal)
# ---------------------------------------------------------------------------

def fallback_host(fila: dict, rng: random.Random) -> str:
    def pseudo(n):
        s = "".join(rng.choice(f2.CONSONANTES if i % 2 else f2.VOCALES) for i in range(n))
        return s
    marca = fila["marca"]
    pal = fila["palabra_es"]
    nn = fila["nn"]
    suf = fila["tld_o_plataforma"]
    g = fila["gramatica"]
    if g == "A1":
        sep = "-" if "guion" in fila["estilo_inventar"] else ""
        return f"{marca}{sep}{pal}{suf}"
    if g == "A2":
        return f"{marca}{pseudo(rng.choice([2, 3]))}{suf}"
    if g == "A3a":
        return f"{pseudo(rng.randint(8, 12))}{suf}"
    if g == "A3b":
        return f"{pseudo(rng.randint(7, 10))}{suf}"
    if g == "S1":
        return f"{marca}.{pseudo(rng.randint(5, 8))}{suf}"
    if g == "S1b":
        return f"{marca}-gub.{pseudo(5)}{suf}"
    if g == "S2":
        return f"www-{marca}{nn}.{pseudo(6)}{suf}"
    if g == "S3":
        return f"{marca}.com.{pseudo(rng.randint(7, 11))}{suf}"
    if g in {"P1", "P2", "P3", "P4"}:
        pieces = [p for p in [marca, pal, nn] if p]
        sub = "-".join(pieces) if g != "P2" else f"{marca}card.{pal}v2"
        return f"{sub}.{suf}"
    return f"{marca or pseudo(8)}{suf}"


# ---------------------------------------------------------------------------
# 7. host -> fila del esquema corpus_sintetico.csv (vía tldextract)
# ---------------------------------------------------------------------------

# Mapa gramática -> (H1,H2,H3,H4) para round-trip con clasificar_regional de Fase 2.
H_POR_GRAM = {
    "A1": (0, 0, 0, 1), "A2": (0, 0, 1, 0),      # apex con marca
    "A3a": (0, 0, 0, 0), "A3b": (0, 0, 0, 0),    # apex sin marca
    "S1": (0, 1, 0, 0), "S2": (0, 1, 0, 0),      # sub-ajeno con marca
    "S1b": (0, 0, 1, 0), "S3": (0, 0, 1, 0),     # sub-ajeno, patrón raro
    "P1": (0, 1, 0, 0), "P2": (0, 1, 0, 0),      # plataforma con marca
    "P3": (0, 1, 0, 0), "P4": (0, 1, 0, 0),
}
PLATAFORMA_GRAMS = {"P1", "P2", "P3", "P4"}


def fila_corpus(host: str, path: str, fila: dict, fuente: str) -> dict:
    ext = _EXTRACT(host)
    dominio_reg = ".".join(p for p in [ext.domain, ext.suffix] if p)
    subdominio = ext.subdomain
    n_sub = len(subdominio.split(".")) if subdominio else 0
    url = f"https://{host}" + (path if path and path != "sin" else "")
    h1, h2, h3, h4 = H_POR_GRAM.get(fila["gramatica"], (0, 0, 0, 0))
    return {
        "url": url, "host": host, "status": "phishing",
        "subdominio": subdominio, "dominio_reg": dominio_reg, "sufijo": ext.suffix,
        "sld": ext.domain, "n_sub": n_sub, "ip_kind": "",
        "marca": fila["marca"] or "", "sector": fila["sector"] or "",
        "H1": bool(h1), "H2": bool(h2), "H3": bool(h3), "H4": bool(h4),
        "plat_cualquiera": fila["gramatica"] in PLATAFORMA_GRAMS,
        "gramatica": fila["gramatica"], "fuente": fuente,
    }


# ---------------------------------------------------------------------------
# 8. Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=125)
    ap.add_argument("--csv", default="../data/raw/corpus_sintetico.csv",
                    help="corpus regional (ejemplos + calibración de Fase 2)")
    ap.add_argument("--historial", default="historial_lotes.json")
    ap.add_argument("--seed", type=int, default=20251102)
    ap.add_argument("--out", default="../data/raw/sinteticos_lote.csv")
    ap.add_argument("--out-plan", default=None, help="JSON del plan (Fase 2)")
    ap.add_argument("--out-prompts", default=None, help="vuelca el prompt enviado")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--batch-size", type=int, default=25)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--dry-run", action="store_true",
                    help="arma plan y prompts, no llama a la API")
    args = ap.parse_args()

    filas, ejemplos, vedados = construir_plan(args.n, Path(args.csv),
                                              Path(args.historial), args.seed)
    print(f"[plan] {len(filas)} filas · seed={args.seed}")

    if args.out_plan:
        Path(args.out_plan).write_text(json.dumps(filas, ensure_ascii=False, indent=2))
        print(f"[plan] -> {args.out_plan}")

    if args.out_prompts:
        Path(args.out_prompts).write_text(construir_prompt(filas, ejemplos, vedados))
        print(f"[prompt] -> {args.out_prompts}")

    if args.dry_run:
        print("[dry-run] no se llamó a la API."); return

    key, keyname = resolver_key()
    print(f"[api] usando {keyname} · modelo {args.model}")
    import anthropic
    client = anthropic.Anthropic(api_key=key)

    ejemplos_set = {h for hs in ejemplos.values() for h in hs}
    vedados_set = set(vedados)
    por_id = {f["id"]: f for f in filas}
    realizados: dict[int, tuple[str, str, str]] = {}   # id -> (host, path, fuente)

    pendientes = list(filas)       # a reintentar vía modelo (solo errores transitorios)
    a_fallback: list[dict] = []    # el modelo declinó o no validó -> vía determinista
    refusal_global = False
    for intento in range(1, 3):                 # 1 pase + 1 reintento (solo transitorios)
        if not pendientes or refusal_global:
            break
        print(f"[modelo] pase {intento}: {len(pendientes)} filas pendientes")
        nuevos_pendientes = []
        for i in range(0, len(pendientes), args.batch_size):
            lote = pendientes[i:i + args.batch_size]
            try:
                res = realizar(client, args.model, lote, ejemplos, vedados,
                               args.temperature, args.max_tokens)
            except RefusalError as e:
                # Política de seguridad del modelo: no se reintenta ni se reescribe.
                print(f"  [refusal] el modelo declinó ({e}); realización determinista")
                refusal_global = True
                a_fallback += list(pendientes)   # todo lo que quede va por fallback
                nuevos_pendientes = []
                break
            except Exception as e:
                print(f"  [warn] batch transitorio ({type(e).__name__}: {str(e)[:120]}); reintento")
                nuevos_pendientes += lote
                time.sleep(2)
                continue
            for fila in lote:
                d = res.get(fila["id"])
                host = (d or {}).get("host", "").strip().lower()
                path = (d or {}).get("path", "")
                motivo = validar_host(host, fila, ejemplos_set, vedados_set) if host else "sin respuesta"
                if motivo is None:
                    realizados[fila["id"]] = (host, path, "modelo")
                else:
                    a_fallback.append(fila)
        pendientes = nuevos_pendientes
    a_fallback += pendientes       # transitorios que no se resolvieron

    # Realización determinista para lo que el modelo declinó o no validó.
    if a_fallback:
        print(f"[fallback] {len(a_fallback)} filas por realización determinista")
        rng = random.Random(args.seed)
        for fila in a_fallback:
            host = fallback_host(fila, rng).lower()
            path = "" if fila["path"] == "sin" else fila["path"]
            realizados.setdefault(fila["id"], (host, path, "determinista"))

    # Dedup de hosts (si dos filas colisionaron, la segunda al fallback)
    vistos = set()
    registros = []
    rng = random.Random(args.seed + 1)
    for fid in sorted(realizados):
        host, path, fuente = realizados[fid]
        if host in vistos:
            host = fallback_host(por_id[fid], rng).lower(); fuente = "determinista"
        vistos.add(host)
        registros.append(fila_corpus(host, path if path != "sin" else "", por_id[fid], fuente))

    cols = ["url", "host", "status", "subdominio", "dominio_reg", "sufijo", "sld",
            "n_sub", "ip_kind", "marca", "sector", "H1", "H2", "H3", "H4",
            "plat_cualquiera", "gramatica", "fuente"]
    out_df = pd.DataFrame(registros)[cols]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)

    n_modelo = int((out_df.fuente == "modelo").sum())
    print(f"[ok] {len(out_df)} hosts -> {args.out}  "
          f"({n_modelo} del modelo / {len(out_df) - n_modelo} deterministas)")


if __name__ == "__main__":
    main()
