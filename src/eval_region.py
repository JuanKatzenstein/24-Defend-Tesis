#!/usr/bin/env python3
"""
eval_region.py — Evaluación del detector por región (UY / BR / otro).

Responde la pregunta de la tesis: ¿el detector entrenado sobre el corpus amplio
generaliza a los casos uruguayos/rioplatenses? Mide el recall sobre cada región
con predicción out-of-fold (cada host se predice con un modelo que NO lo vio en
entrenamiento, vía StratifiedKFold), así el número no está inflado.

Uso:
    python3 eval_region.py \
        --data ../data/processed/dataset_combinado_host.csv \
        --regiones ../data/raw/corpus_regiones.csv \
        --report ../reports/eval_region.md
"""
from __future__ import annotations

import argparse
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--regiones", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    d = pd.read_csv(args.data)
    reg = pd.read_csv(args.regiones)[["host", "region"]]
    d["host"] = d["url"].map(lambda u: urlparse(u).hostname or "")
    d = d.merge(reg, on="host", how="left")
    d["region"] = d["region"].fillna("otro")

    num = d.select_dtypes(include=[np.number]).drop(columns=["label"])
    X = num.fillna(0).values
    y = d["label"].values
    reg_arr = d["region"].values

    skf = StratifiedKFold(5, shuffle=True, random_state=args.seed)
    pred = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        m = RandomForestClassifier(n_estimators=300, random_state=args.seed, n_jobs=-1)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])

    lines = ["# Evaluación por región — ¿generaliza a los casos uruguayos?", ""]
    lines.append("Recall out-of-fold (5-fold, seed %d): cada host se predice con un "
                 "modelo que no lo vio en entrenamiento." % args.seed)
    lines.append("")
    lines.append("| región | phishing | detectados | recall |")
    lines.append("|--------|---------:|-----------:|-------:|")
    for r in ["UY", "BR", "otro"]:
        mk = (reg_arr == r) & (y == 1)
        if mk.sum():
            lines.append(f"| {r} | {int(mk.sum())} | {int(pred[mk].sum())} | "
                         f"{pred[mk].mean():.3f} |")
    gp = pred[y == 1].mean()
    fp = pred[y == 0].mean()
    lines.append("")
    lines.append(f"**Global:** recall phishing {gp:.3f} · tasa de falsos positivos "
                 f"(legítimos marcados phishing) {fp:.3f}")

    miss = d[(reg_arr == "UY") & (y == 1) & (pred == 0)]["host"].tolist()
    lines.append("")
    lines.append("## Casos UY no detectados")
    if miss:
        lines.append("Apex minimalistas sin señal léxica (necesitan señales externas: "
                     "edad del dominio, certificado, reputación DNS):")
        for h in miss:
            lines.append(f"- `{h}`")
    else:
        lines.append("Ninguno.")

    report = "\n".join(lines) + "\n"
    Path = __import__("pathlib").Path
    Path(args.report).write_text(report)
    print(report)
    print(f"[report] -> {args.report}")


if __name__ == "__main__":
    main()
