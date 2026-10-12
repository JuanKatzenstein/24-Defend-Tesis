#!/usr/bin/env python3
"""
ingest_real.py — Ingesta de datos REALES para pasar de métricas-demo a números de tesis.

Convierte feeds públicos al esquema del pipeline (CSV con columna 'url' + 'status').
Funciona de dos maneras, según lo que tengas disponible:

  (a) Descargando desde una URL (requiere red saliente habilitada en el entorno), o
  (b) Leyendo un archivo LOCAL que ya descargaste/subiste (sin red).

Fuentes sugeridas:
  - Phishing (positivos): OpenPhish community feed (openphish.com/feed.txt, una URL
    por línea) o PhishTank (CSV con columna 'url'). También datasets de Mendeley/UCI.
  - Legítimas (negativos): Tranco (tranco-list.eu, CSV 'rank,domain') o Majestic Million.

Ejemplos:
  # desde archivos locales ya descargados:
  python3 ingest_real.py --phishing-file openphish_feed.txt --tranco-file top-1m.csv \
      --n-benign 2000 --outdir ../data/raw

  # descargando (si el entorno tiene red):
  python3 ingest_real.py --phishing-url https://openphish.com/feed.txt \
      --tranco-url https://tranco-list.eu/top-1m.csv.zip --n-benign 2000 --outdir ../data/raw
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

# CA del proxy de egress (si está presente), para que la descarga valide TLS.
_CA = "/root/.ccr/ca-bundle.crt"
for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
    if os.path.exists(_CA) and not os.environ.get(var):
        os.environ[var] = _CA


def _leer_bytes(url: str) -> bytes:
    """Descarga respetando HTTPS_PROXY/CA del entorno. Lanza si la red está denegada."""
    req = urllib.request.Request(url, headers={"User-Agent": "tesis-detector/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def cargar_fuente(url: str | None, file: str | None) -> bytes:
    if file:
        return Path(file).read_bytes()
    if url:
        return _leer_bytes(url)
    raise ValueError("Falta --*-url o --*-file")


def parse_phishing(raw: bytes) -> list[str]:
    """Acepta feed de texto (una URL por línea) o CSV con columna 'url'."""
    txt = raw.decode("utf-8", errors="ignore").strip()
    if txt[:1] in "hH" and "," not in txt.splitlines()[0]:
        # texto plano: una URL por línea (OpenPhish)
        return [l.strip() for l in txt.splitlines() if l.strip().startswith("http")]
    # CSV con columna 'url'
    rows = list(csv.DictReader(io.StringIO(txt)))
    col = next((c for c in rows[0] if c.lower() == "url"), None) if rows else None
    return [r[col].strip() for r in rows if col and r.get(col, "").startswith("http")]


def parse_tranco(raw: bytes, n: int) -> list[str]:
    """Tranco: CSV 'rank,domain' (dentro de un .zip o plano). Toma los top n dominios."""
    data = raw
    if raw[:2] == b"PK":  # zip
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            data = z.read(z.namelist()[0])
    txt = data.decode("utf-8", errors="ignore")
    urls = []
    for line in txt.splitlines():
        parts = line.split(",")
        dom = parts[-1].strip() if parts else ""
        if dom and "." in dom:
            urls.append(f"https://{dom}")
        if len(urls) >= n:
            break
    return urls


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phishing-url"); ap.add_argument("--phishing-file")
    ap.add_argument("--tranco-url"); ap.add_argument("--tranco-file")
    ap.add_argument("--n-benign", type=int, default=2000)
    ap.add_argument("--n-phishing", type=int, default=0, help="0 = todas las del feed")
    ap.add_argument("--outdir", default="../data/raw")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    try:
        ph_raw = cargar_fuente(args.phishing_url, args.phishing_file)
        be_raw = cargar_fuente(args.tranco_url, args.tranco_file)
    except Exception as e:
        print(f"[ingest] ERROR al obtener las fuentes: {e}\n"
              f"  Si es un bloqueo de red (403/timeout), habilitá los hosts en el "
              f"entorno o descargá los feeds a archivos y usá --*-file.", file=sys.stderr)
        sys.exit(2)

    ph = parse_phishing(ph_raw)
    if args.n_phishing:
        ph = ph[:args.n_phishing]
    be = parse_tranco(be_raw, args.n_benign)

    # dedupe simple
    ph = list(dict.fromkeys(ph))
    be = list(dict.fromkeys(be))

    pd.DataFrame({"url": ph, "status": "phishing"}).to_csv(outdir / "phishing_real.csv", index=False)
    pd.DataFrame({"url": be, "status": "legit"}).to_csv(outdir / "benign_real.csv", index=False)
    print(f"[ingest] phishing_real.csv: {len(ph)} URLs · benign_real.csv: {len(be)} URLs -> {outdir}")
    print("  Siguiente: build_dataset.py --phishing ../data/raw/phishing_real.csv "
          "--benign ../data/raw/benign_real.csv --out ../data/processed/dataset_real.csv")


if __name__ == "__main__":
    main()
