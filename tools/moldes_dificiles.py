#!/usr/bin/env python3
"""
moldes_dificiles.py — phishing de TRAIN que el detector no detecta, para usar
como moldes de generación dirigida (generar_sinteticos.py --moldes).

Predicción out-of-fold con los folds del CSV (columna fold, 0-4): cada host se
puntúa con un modelo que no lo vio. Valid y test no se tocan, así la
generación dirigida no filtra información del test.

Mismo detector que la sección Utilidad de evaluar_sinteticos.py (Random Forest
sobre las features léxicas de src/features.py).

Uso:
    python3 moldes_dificiles.py --csv ../data/raw/dataset_combinado_v4.csv \
        --out ../data/raw/moldes_dificiles.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from evaluar_sinteticos import matriz
from generar_sinteticos import cargar, forma_de


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("moldes_dificiles.csv"))
    ap.add_argument("--umbral", type=float, default=0.5, help="phishing con p out-of-fold < umbral")
    ap.add_argument("--solo-con-marca", action="store_true",
                    help="solo los que suplantan una marca: los que tienen señal léxica que aprender")
    args = ap.parse_args()

    df, _ = cargar(args.csv)
    tr = df[df.split == "train"].reset_index(drop=True)
    X, y = matriz(tr.hostname).values, tr.phishing.values
    p = np.zeros(len(tr))
    for f in sorted(tr.fold.unique()):
        m = (tr.fold == f).values
        rf = RandomForestClassifier(300, random_state=0, n_jobs=-1, class_weight="balanced")
        p[m] = rf.fit(X[~m], y[~m]).predict_proba(X[m])[:, 1]
    tr["p_oof"] = p.round(4)

    phish = tr[tr.phishing == 1].copy()
    phish["forma"] = phish.apply(forma_de, axis=1)
    dificiles = phish[phish.p_oof < args.umbral].sort_values("p_oof")
    if args.solo_con_marca:
        dificiles = dificiles[dificiles.marca_detectada.fillna("").ne("")]
    dificiles[["hostname", "p_oof", "forma", "marca_detectada"]].to_csv(args.out, index=False)
    print(f"{len(dificiles)}/{len(phish)} phishing de train con p_oof < {args.umbral} -> {args.out}")
    print("formas:", dificiles.forma.value_counts().to_dict())


if __name__ == "__main__":
    main()
