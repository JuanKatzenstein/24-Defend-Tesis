#!/usr/bin/env python3
"""
build_dataset.py — Une la clase positiva (phishing) y la negativa (legítima) en un
único dataset etiquetado y le extrae las features léxicas.

Salida: data/processed/dataset.csv con columna 'label' (1=phishing, 0=legit) +
las features de features.py.

Uso:
    python3 build_dataset.py \
        --phishing data/raw/corpus_sintetico.csv \
        --benign   data/raw/benign_seed.csv \
        --out      data/processed/dataset.csv
"""
from __future__ import annotations

import argparse

import pandas as pd

from features import extract_frame


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phishing", required=True, help="CSV con URLs de phishing")
    ap.add_argument("--benign", required=True, help="CSV con URLs legítimas")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ph = pd.read_csv(args.phishing)
    be = pd.read_csv(args.benign)
    ph = ph[["url"]].copy(); ph["label"] = 1
    be = be[["url"]].copy(); be["label"] = 0

    df = pd.concat([ph, be], ignore_index=True)
    feats = extract_frame(df, "url")
    out = pd.concat([df[["url", "label"]], feats], axis=1)
    out.to_csv(args.out, index=False)
    print(f"[dataset] {len(out)} filas ({ph.shape[0]} phishing / {be.shape[0]} legit) "
          f"· {feats.shape[1]} features -> {args.out}")


if __name__ == "__main__":
    main()
