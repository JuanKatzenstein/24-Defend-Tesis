#!/usr/bin/env python3
"""
scrape_certuy.py — Monitor de avisos de CERTuy en busca de indicadores (dominios
de phishing) citados públicamente.

Recorre las noticias de CERTuy (gub.uy), se queda con los artículos cuyo título
o cuerpo mencionan phishing/fraude/suplantación/estafa, y extrae dominios/URLs,
incluidos los "defanged" (hxxp://, dominio[.]com). Deduplica contra el corpus
existente y escribe los candidatos a un CSV para revisión manual.

NOTA: al día de hoy CERTuy casi no publica IoCs crudos en sus noticias (sus
avisos suelen ser de vulnerabilidades), así que el rinde esperado es bajo. El
valor es como *monitor* para correr periódicamente: si publican una campaña con
dominios, esto los captura.

Uso:
    python3 scrape_certuy.py --paginas 10 --out ../data/raw/certuy_candidatos.csv \
        [--corpus ../data/raw/corpus_regiones.csv]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://www.gub.uy"
LISTADO = (BASE + "/centro-nacional-respuesta-incidentes-seguridad-informatica"
           "/comunicacion/noticias")
REL = re.compile(r"/centro-nacional-respuesta-incidentes-seguridad-informatica"
                 r"/comunicacion/noticias/[a-z0-9-]+")
RELEVANTE = re.compile(r"phishing|fraude|suplant|estafa|smishing|campa[nñ]a|"
                       r"credencial|robo de datos", re.I)
RUIDO = re.compile(r"gub\.uy|cert\.uy|w3\.org|schema\.org|fortinet|microsoft|"
                   r"google|cloudflare|adobe|joomla|wordpress|zimbra|linux|"
                   r"facebook|twitter|linkedin|youtube|\.gov\b", re.I)


def get(url: str) -> str:
    req = Request(url, headers={"User-Agent": "tesis-phishing-monitor/1.0"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def refang(s: str) -> str:
    return (s.replace("hxxp", "http").replace("[.]", ".")
             .replace("(.)", ".").replace("[:]", ":"))


def indicadores(txt: str) -> set[str]:
    txt = refang(txt)
    urls = set(re.findall(r"https?://[^\s\"<)]+", txt))
    hosts = {re.sub(r"^https?://", "", u).split("/")[0].lower() for u in urls}
    sueltos = set(re.findall(
        r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+\.(?:uy|com|net|org|info|xyz|top|click|"
        r"app|site|online|shop)\b", txt, re.I))
    cand = {h for h in (hosts | {s.lower() for s in sueltos}) if not RUIDO.search(h)}
    return cand


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paginas", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--corpus", default=None, help="CSV para deduplicar (col host)")
    ap.add_argument("--pausa", type=float, default=0.5, help="segundos entre requests")
    args = ap.parse_args()

    conocidos = set()
    if args.corpus and Path(args.corpus).exists():
        import csv
        with open(args.corpus) as f:
            for row in csv.DictReader(f):
                if row.get("host"):
                    conocidos.add(row["host"].lower())

    arts = set()
    for p in range(args.paginas):
        try:
            html = get(f"{LISTADO}?page={p}")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] página {p}: {e}", file=sys.stderr)
            continue
        nuevos = set(REL.findall(html))
        arts |= nuevos
        time.sleep(args.pausa)
    print(f"[certuy] {len(arts)} artículos encontrados", file=sys.stderr)

    filas = []
    for rel in sorted(arts):
        try:
            html = get(BASE + rel)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {rel}: {e}", file=sys.stderr)
            continue
        txt = texto(html)
        if not RELEVANTE.search(txt):
            continue
        for h in indicadores(txt):
            if h not in conocidos:
                filas.append((h, BASE + rel))
        time.sleep(args.pausa)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write("host,fuente_aviso\n")
        for h, u in sorted(set(filas)):
            f.write(f"{h},{u}\n")
    print(f"[certuy] {len(set(filas))} candidatos nuevos -> {out}")
    if not filas:
        print("[certuy] (sin indicadores crudos en los avisos actuales; "
              "correr periódicamente)")


if __name__ == "__main__":
    main()
