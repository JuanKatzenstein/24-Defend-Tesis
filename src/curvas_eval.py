#!/usr/bin/env python3
"""
curvas_eval.py — Curvas ROC y Precision-Recall (validación cruzada) + calibración
de umbral para el detector.

Usa probabilidades out-of-fold (cross_val_predict) para no inflar las métricas.
Genera dos PNG (reports/figs/) y un reporte de umbrales (reports/umbral.md) que
ayuda a elegir el punto de operación según el costo de falsos positivos/negativos
— discusión clave en la defensa.

Uso:
    python3 curvas_eval.py --data ../data/processed/dataset.csv --outdir ../reports
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (auc, precision_recall_curve, precision_score,
                             recall_score, f1_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Paleta categórica validada (dataviz, modo claro, CVD-safe).
AZUL, ROJO = "#4269d0", "#c44601"
TINTA, TINTA_SUAVE, SURF = "#2a2a28", "#6b6b68", "#fcfcfb"
MODELOS = {"Regresión Logística": AZUL, "Random Forest": ROJO}


def _estilo(ax):
    ax.set_facecolor(SURF)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_SUAVE)
    ax.tick_params(colors=TINTA_SUAVE, labelsize=9)
    ax.grid(True, color="#e8e8e6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def proba_oof(df, modelo, num, cat, k):
    pre = ColumnTransformer([("num", StandardScaler(), num),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    pipe = Pipeline([("pre", pre), ("clf", modelo)])
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    X, y = df[num + cat], df["label"].astype(int).values
    return cross_val_predict(pipe, X, y, cv=skf, method="predict_proba")[:, 1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--outdir", default="../reports")
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    y = df["label"].astype(int).values
    no = {"url", "label", "plataforma", "tld"}
    num = [c for c in df.columns if c not in no and pd.api.types.is_numeric_dtype(df[c])]
    cat = ["tld"] if "tld" in df.columns else []
    k = min(5, int(y.sum()), int((y == 0).sum()))

    modelos = {
        "Regresión Logística": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42,
                                                class_weight="balanced"),
    }
    probas = {n: proba_oof(df, m, num, cat, k) for n, m in modelos.items()}

    figs = Path(args.outdir) / "figs"; figs.mkdir(parents=True, exist_ok=True)

    # --- ROC ---
    fig, ax = plt.subplots(figsize=(5.2, 4.4), dpi=150)
    fig.patch.set_facecolor(SURF); _estilo(ax)
    ax.plot([0, 1], [0, 1], color=TINTA_SUAVE, lw=1, ls="--", zorder=1)
    for nombre, p in probas.items():
        fpr, tpr, _ = roc_curve(y, p)
        ax.plot(fpr, tpr, color=MODELOS[nombre], lw=2, zorder=3,
                label=f"{nombre} (AUC {auc(fpr, tpr):.3f})")
    ax.set_xlabel("Tasa de falsos positivos", color=TINTA, fontsize=10)
    ax.set_ylabel("Tasa de verdaderos positivos", color=TINTA, fontsize=10)
    ax.set_title("Curva ROC (validación cruzada)", color=TINTA, fontsize=12, pad=10)
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=TINTA)
    fig.tight_layout(); fig.savefig(figs / "roc.png", facecolor=SURF); plt.close(fig)

    # --- Precision-Recall ---
    base = y.mean()
    fig, ax = plt.subplots(figsize=(5.2, 4.4), dpi=150)
    fig.patch.set_facecolor(SURF); _estilo(ax)
    ax.axhline(base, color=TINTA_SUAVE, lw=1, ls="--", zorder=1,
               label=f"azar ({base:.2f})")
    for nombre, p in probas.items():
        prec, rec, _ = precision_recall_curve(y, p)
        ax.plot(rec, prec, color=MODELOS[nombre], lw=2, zorder=3,
                label=f"{nombre} (AP {auc(rec, prec):.3f})")
    ax.set_xlabel("Recall (cobertura de phishing)", color=TINTA, fontsize=10)
    ax.set_ylabel("Precisión", color=TINTA, fontsize=10)
    ax.set_title("Curva Precision-Recall (CV)", color=TINTA, fontsize=12, pad=10)
    ax.legend(loc="lower left", frameon=False, fontsize=9, labelcolor=TINTA)
    fig.tight_layout(); fig.savefig(figs / "pr.png", facecolor=SURF); plt.close(fig)

    # --- Calibración de umbral (Random Forest) ---
    p = probas["Random Forest"]
    lineas = ["# Calibración de umbral — Random Forest (CV)", "",
              "Punto de operación según el costo relativo de FP vs FN.", "",
              "| umbral | precisión | recall | F1 |", "|---|---|---|---|"]
    mejor_f1, mejor_u = -1, 0.5
    for u in np.arange(0.2, 0.81, 0.1):
        pred = (p >= u).astype(int)
        pr = precision_score(y, pred, zero_division=0)
        rc = recall_score(y, pred, zero_division=0)
        f1 = f1_score(y, pred, zero_division=0)
        if f1 > mejor_f1:
            mejor_f1, mejor_u = f1, u
        lineas.append(f"| {u:.1f} | {pr:.3f} | {rc:.3f} | {f1:.3f} |")
    lineas += ["", f"**Umbral F1-óptimo ≈ {mejor_u:.1f}** (F1 {mejor_f1:.3f}).",
               "",
               "- Subí el umbral si el costo de molestar a un usuario legítimo (FP) es alto.",
               "- Bajalo si dejar pasar phishing (FN) es lo más caro — típico en seguridad.",
               "",
               "![ROC](figs/roc.png)", "", "![PR](figs/pr.png)"]
    (Path(args.outdir) / "umbral.md").write_text("\n".join(lineas) + "\n")
    print(f"[curvas] roc.png, pr.png -> {figs}")
    print(f"[umbral] F1-óptimo ≈ {mejor_u:.1f} (F1 {mejor_f1:.3f}) -> {args.outdir}/umbral.md")


if __name__ == "__main__":
    main()
