#!/usr/bin/env python3
"""
ingest_corpus.py — Incorpora el corpus curado de dominios (Corpus_VF) al pipeline
de datos reales, a nivel dominio.

El corpus de entrada trae una fila por dominio ya etiquetado, con el host partido
en dos columnas:

    dominio, subdominio, phishing     (phishing = 1 positivo / 0 legítimo)

Este script:
  1. Reconstruye el host completo (subdominio + dominio).
  2. Etiqueta la región (UY = marca/TLD rioplatense, BR = Brasil, otro).
  3. Lo UNE con los feeds reales que ya estaban en data/raw (phishing_real.csv,
     benign_real.csv), deduplicando por host (un host no puede ser phishing y
     legítimo a la vez: si aparece en ambas fuentes, gana la etiqueta del corpus
     curado, que es revisado a mano).
  4. Escribe phishing_all.csv / benign_all.csv (formato url,status) listos para
     build_dataset.py --host-only, y corpus_regiones.csv con la etiqueta de región.

No inventa hosts: solo normaliza y combina material ya etiquetado.

Uso:
    python3 ingest_corpus.py \
        --corpus /ruta/Corpus_VF_-_Dominios.xlsx \
        --phishing-real ../data/raw/phishing_real.csv \
        --benign-real   ../data/raw/benign_real.csv \
        --outdir ../data/raw
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

# Marcas y TLD con anclaje uruguayo / rioplatense documentado.
# Las marcas largas y distintivas se buscan como subcadena, porque el phishing
# las pega a otros tokens (ebrou, onlinebrou, msucive, sucivet...). Las marcas
# cortas/ambiguas (antel, prex, oca) exigen borde de etiqueta para no capturar
# gibberish que las contiene por casualidad (wulantel..., ...locaX...).
UY_MARCAS = re.compile(
    r"(brou|sucive|abitab|redpago|ancap|bancorepublica|midinero)"
    r"|(^|[.\-])(antel|prex|oca|bps|dgi|ute)",
    re.I,
)
UY_TLD = re.compile(r"\.uy(\.|$)|\.com\.uy", re.I)
BR_MARCAS = re.compile(
    r"brasil|americanas|bradesco|\bcaixa\b|submarino|magazine|correios|"
    r"serasa|\bitaucard\b|\bbb\b",
    re.I,
)
BR_TLD = re.compile(r"\.br(\.|$)|\.com\.br", re.I)

# "Piso ciego": phishing real alojado en infraestructura cruda (bucket S3 con
# nombre aleatorio, hostname EC2, IP inversa) SIN ninguna señal léxica que un
# detector solo-URL pueda usar. No son errores de etiqueta: son positivos
# estructuralmente indetectables por features léxicas, y se reportan aparte.
INFRA_CIEGA = re.compile(
    r"^(ec2-|ip-)"
    r"|^\d{1,3}(\.\d{1,3}){3}"
    r"|^[a-z0-9]{8,}\.s3[.-]"
    r"|\.host\.secureserver\.net$",
    re.I,
)
# Marcas cuya presencia da señal léxica aunque el host sea infraestructura.
MARCAS_SENAL = ["brou", "sucive", "antel", "itau", "mercadopago", "mercadolibre",
                "americanas", "bradesco", "prex", "oca", "santander", "bbva",
                "caixa", "correo", "scotiabank", "abitab", "redpago"]


def tiene_senal_lexica(host: str) -> bool:
    """False si el host es infraestructura cruda sin marca ni palabra reconocible."""
    h = host.lower()
    if any(m in h for m in MARCAS_SENAL):
        return True
    return not INFRA_CIEGA.search(h)


def host_de(sub: str, dom: str) -> str:
    sub = (str(sub) if pd.notna(sub) else "").strip().strip(".").lower()
    dom = (str(dom) if pd.notna(dom) else "").strip().strip(".").lower()
    return f"{sub}.{dom}" if sub else dom


def region(host: str) -> str:
    if UY_MARCAS.search(host) or UY_TLD.search(host):
        return "UY"
    if BR_MARCAS.search(host) or BR_TLD.search(host):
        return "BR"
    return "otro"


def host_de_url(url: str) -> str:
    u = url if "://" in str(url) else "http://" + str(url)
    return (urlparse(u).hostname or "").lower()


def cargar_corpus(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        xl = pd.ExcelFile(path)
        df = pd.read_excel(path, sheet_name=xl.sheet_names[0])
    else:
        df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["host"] = [host_de(s, d) for s, d in zip(df["subdominio"], df["dominio"])]
    df["label"] = df["phishing"].astype(int)
    df["region"] = df["host"].map(region)
    df["senal_lexica"] = df["host"].map(tiene_senal_lexica)
    df["fuente"] = "corpus_vf"
    # descarta hosts vacíos o claramente no-hosts (infra, sin punto)
    df = df[df["host"].str.contains(".", regex=False)].copy()
    return df[["host", "label", "region", "senal_lexica", "fuente"]].drop_duplicates("host")


def cargar_feed(path: Path, label: int) -> pd.DataFrame:
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=["host", "label", "region", "senal_lexica", "fuente"])
    x = pd.read_csv(path)
    hosts = x["host"] if "host" in x.columns else x["url"].map(host_de_url)
    out = pd.DataFrame({"host": hosts.str.lower()})
    out["label"] = label
    out["region"] = out["host"].map(region)
    out["senal_lexica"] = out["host"].map(tiene_senal_lexica)
    out["fuente"] = "feed_real"
    out = out[out["host"].astype(bool) & out["host"].str.contains(".", regex=False)]
    return out.drop_duplicates("host")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, help="Corpus_VF (.xlsx o .csv)")
    ap.add_argument("--phishing-real", default=None)
    ap.add_argument("--benign-real", default=None)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    corpus = cargar_corpus(Path(args.corpus))
    ph_feed = cargar_feed(Path(args.phishing_real), 1) if args.phishing_real else pd.DataFrame()
    be_feed = cargar_feed(Path(args.benign_real), 0) if args.benign_real else pd.DataFrame()

    todo = pd.concat([corpus, ph_feed, be_feed], ignore_index=True)
    # El corpus curado manda sobre el feed si un host aparece en ambos.
    todo["prioridad"] = (todo["fuente"] == "corpus_vf").astype(int)
    todo = (todo.sort_values("prioridad", ascending=False)
                .drop_duplicates("host", keep="first")
                .drop(columns="prioridad"))

    # Si un host quedó con etiquetas contradictorias entre fuentes ya se resolvió
    # por prioridad; reportamos cuántos hubo.
    dup_conflict = (pd.concat([corpus, ph_feed, be_feed])
                      .groupby("host")["label"].nunique())
    n_conflict = int((dup_conflict > 1).sum())

    ph = todo[todo["label"] == 1].copy()
    be = todo[todo["label"] == 0].copy()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    def escribir(df, status, nombre):
        o = pd.DataFrame({"url": "http://" + df["host"], "status": status})
        o.to_csv(outdir / nombre, index=False)

    escribir(ph, "phishing", "phishing_all.csv")
    escribir(be, "legit", "benign_all.csv")
    todo[["host", "label", "region", "senal_lexica", "fuente"]].to_csv(
        outdir / "corpus_regiones.csv", index=False)

    print(f"[ingest_corpus] phishing={len(ph)}  legit={len(be)}  "
          f"(conflictos de etiqueta resueltos por prioridad: {n_conflict})")
    print("[ingest_corpus] phishing por región:")
    print(ph["region"].value_counts().to_string())
    print("[ingest_corpus] legítimos por región:")
    print(be["region"].value_counts().to_string())


if __name__ == "__main__":
    main()
