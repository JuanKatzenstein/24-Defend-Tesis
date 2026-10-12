#!/usr/bin/env python3
"""
ablation.py — Ablación de features para distinguir señal REAL de phishing de
atajos/fugas del armado del dataset.

Entrena el detector con distintos subconjuntos de features y compara. Si el
rendimiento se desploma al quitar el TLD one-hot, es que el modelo se apoyaba en
un atajo ("`.uy` = legítimo"), no en detección genuina. Lo que sobrevive a la
ablación es la señal defendible.

Uso:
    python3 ablation.py --data data/processed/dataset.csv --report reports/ablacion.md
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Señales interpretables de phishing que NO son artefactos de cómo se armó el
# dataset (no dependen del TLD concreto ni de largos sistemáticamente distintos).
SENALES_PHISHING = [
    "tld_sospechoso", "en_plataforma_hosting", "brand_suplantada",
    "n_palabras_gancho", "tiene_gancho", "host_entropy", "sld_entropy",
    "n_subdomains", "n_digits", "digit_ratio", "is_ip", "hex_largo", "n_hyphens",
]
LARGOS = ["url_len", "host_len", "sld_len", "path_len", "query_len"]


def numericas(df):
    no = {"url", "label", "plataforma", "tld"}
    return [c for c in df.columns
            if c not in no and pd.api.types.is_numeric_dtype(df[c])]


def pipeline(modelo, num_cols, usar_tld):
    transformers = [("num", StandardScaler(), num_cols)]
    if usar_tld:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), ["tld"]))
    return Pipeline([("pre", ColumnTransformer(transformers)), ("clf", modelo)])


def correr(nombre, df, num_cols, usar_tld, k, seed, lineas):
    cols = num_cols + (["tld"] if usar_tld else [])
    X, y = df[cols], df["label"].astype(int).values
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=seed)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)

    fila = [nombre]
    for etq, modelo in [("LogReg", LogisticRegression(max_iter=1000, class_weight="balanced")),
                        ("RF", RandomForestClassifier(n_estimators=300, random_state=seed,
                                                      class_weight="balanced"))]:
        pipe = pipeline(modelo, num_cols, usar_tld)
        cv = cross_val_score(pipe, X_tr, y_tr, cv=skf, scoring="f1")
        pipe.fit(X_tr, y_tr)
        pred = pipe.predict(X_te)
        proba = pipe.predict_proba(X_te)[:, 1]
        try:
            auc = roc_auc_score(y_te, proba)
        except ValueError:
            auc = float("nan")
        fila.append(f"{cv.mean():.3f}±{cv.std():.3f}")
        fila.append(f"{f1_score(y_te, pred, zero_division=0):.3f}")
        fila.append(f"{auc:.3f}")
    lineas.append("| " + " | ".join(fila) + " |")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    num = numericas(df)
    y = df["label"].astype(int).values
    k = min(5, int(y.sum()), int((y == 0).sum()))

    configs = [
        # (nombre, columnas numéricas, usar TLD one-hot)
        ("A. full (todo + TLD one-hot)", num, True),
        ("B. sin TLD one-hot", num, False),
        ("C. sin TLD ni largos", [c for c in num if c not in LARGOS], False),
        ("D. solo señales de phishing", [c for c in SENALES_PHISHING if c in num], False),
    ]

    lineas = ["# Ablación de features — ¿señal real o fuga?", ""]
    lineas.append(f"Dataset: {len(df)} URLs ({int(y.sum())} phishing / {int((y==0).sum())} legit) · "
                  f"CV {k}-fold · hold-out 30% · seed {args.seed}")
    lineas.append("")
    lineas.append("Cada config quita features. Si al pasar de A a B/C/D el rendimiento "
                  "cae mucho, el modelo dependía de un atajo (TLD, largos). Lo que "
                  "sobrevive es la señal defendible.")
    lineas.append("")
    lineas.append("| Config | LogReg CV-F1 | LogReg test-F1 | LogReg AUC | RF CV-F1 | RF test-F1 | RF AUC |")
    lineas.append("|--------|------|------|------|------|------|------|")
    for nombre, cols, usar_tld in configs:
        correr(nombre, df, cols, usar_tld, k, args.seed, lineas)
    lineas.append("")
    lineas.append("**Lectura:** la config D («solo señales de phishing») es la más honesta "
                  "— usa features que describen el *mecanismo* del phishing "
                  "(TLD sospechoso, hosting gratuito, marca suplantada, palabras-gancho, "
                  "entropía del dominio) y no artefactos del armado del dataset.")

    reporte = "\n".join(lineas)
    print(reporte)
    if args.report:
        with open(args.report, "w") as f:
            f.write(reporte + "\n")
        print(f"\n[report] -> {args.report}")


if __name__ == "__main__":
    main()
