#!/usr/bin/env python3
"""
train_baseline.py — Baseline del detector de phishing en URLs.

Entrena y evalúa dos modelos interpretables (Regresión Logística y Random Forest)
con validación cruzada estratificada + un hold-out de test. Reporta accuracy,
precision, recall, F1 y ROC-AUC, la matriz de confusión y la importancia de
features. Todo pensado para ser defendible en la tesis.

ADVERTENCIA METODOLÓGICA (va en el informe): con un dataset chico y en parte
sintético, estas métricas son optimistas. Sirven para validar el pipeline, no
como resultado final. Reemplazar/ampliar con feeds reales (PhishTank/OpenPhish)
y ranking legítimo (Tranco) antes de reportar números definitivos.

Uso:
    python3 train_baseline.py --data data/processed/dataset.csv --report reports/baseline.md
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NO_FEATURES = {"url", "label", "plataforma", "tld"}  # 'tld' se one-hot-encodea aparte


def construir_matrices(df: pd.DataFrame):
    y = df["label"].astype(int).values
    num_cols = [c for c in df.columns
                if c not in NO_FEATURES and pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = ["tld"] if "tld" in df.columns else []
    X = df[num_cols + cat_cols].copy()
    return X, y, num_cols, cat_cols


def hacer_pipeline(modelo, num_cols, cat_cols):
    pre = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
    return Pipeline([("pre", pre), ("clf", modelo)])


def evaluar(nombre, pipe, X_tr, y_tr, X_te, y_te, k, lineas):
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(pipe, X_tr, y_tr, cv=skf, scoring="f1")
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    proba = pipe.predict_proba(X_te)[:, 1]

    acc = accuracy_score(y_te, pred)
    prec = precision_score(y_te, pred, zero_division=0)
    rec = recall_score(y_te, pred, zero_division=0)
    f1 = f1_score(y_te, pred, zero_division=0)
    try:
        auc = roc_auc_score(y_te, proba)
    except ValueError:
        auc = float("nan")
    cm = confusion_matrix(y_te, pred)

    lineas.append(f"### {nombre}")
    lineas.append("")
    lineas.append(f"- CV F1 (train, {k}-fold): {cv_f1.mean():.3f} ± {cv_f1.std():.3f}")
    lineas.append(f"- Test — accuracy {acc:.3f} · precision {prec:.3f} · "
                  f"recall {rec:.3f} · F1 {f1:.3f} · ROC-AUC {auc:.3f}")
    lineas.append("")
    lineas.append("Matriz de confusión (test) — filas=real, cols=pred [legit, phishing]:")
    lineas.append("```")
    lineas.append(f"            pred_legit  pred_phish")
    lineas.append(f"real_legit   {cm[0,0]:>9}  {cm[0,1]:>10}")
    lineas.append(f"real_phish   {cm[1,0]:>9}  {cm[1,1]:>10}")
    lineas.append("```")
    lineas.append("")
    return pipe, {"nombre": nombre, "f1": f1, "auc": auc}


def importancia_rf(pipe, lineas, top=15):
    pre = pipe.named_steps["pre"]
    clf = pipe.named_steps["clf"]
    nombres = pre.get_feature_names_out()
    imp = clf.feature_importances_
    orden = np.argsort(imp)[::-1][:top]
    lineas.append(f"### Importancia de features (Random Forest, top {top})")
    lineas.append("")
    for i in orden:
        nombre = nombres[i].split("__", 1)[-1]
        lineas.append(f"- {nombre}: {imp[i]:.4f}")
    lineas.append("")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--test-size", type=float, default=0.3)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    X, y, num_cols, cat_cols = construir_matrices(df)
    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    k = min(args.folds, n_pos, n_neg)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=args.seed)

    lineas = ["# Baseline — Detector de phishing en URLs", ""]
    lineas.append(f"- Dataset: {len(df)} URLs ({n_pos} phishing / {n_neg} legit) · "
                  f"{len(num_cols)} features numéricas + TLD (one-hot)")
    lineas.append(f"- Split: {int((1-args.test_size)*100)}% train / "
                  f"{int(args.test_size*100)}% test (estratificado, seed {args.seed})")
    lineas.append(f"- CV: {k}-fold estratificado sobre el train")
    lineas.append("")
    lineas.append("> **Nota metodológica:** revisar siempre las *importancias* de features "
                  "para descartar fugas por el armado del dataset (p. ej. formato de la "
                  "clase negativa). Si la clase legítima son dominios pelados (Tranco), "
                  "evaluar a nivel dominio (`--host-only`) para evitar que `path_len`/"
                  "`n_slash` separen por formato en vez de por phishing. Contrastar con "
                  "`ablation.py`: si el rendimiento no cae al quitar largos/TLD, la señal "
                  "es real.")
    lineas.append("")

    logreg = LogisticRegression(max_iter=1000, class_weight="balanced")
    rf = RandomForestClassifier(n_estimators=300, random_state=args.seed,
                                class_weight="balanced")

    evaluar("Regresión Logística", hacer_pipeline(logreg, num_cols, cat_cols),
            X_tr, y_tr, X_te, y_te, k, lineas)
    pipe_rf, _ = evaluar("Random Forest", hacer_pipeline(rf, num_cols, cat_cols),
                         X_tr, y_tr, X_te, y_te, k, lineas)
    importancia_rf(pipe_rf, lineas)

    reporte = "\n".join(lineas)
    print(reporte)
    if args.report:
        with open(args.report, "w") as f:
            f.write(reporte + "\n")
        print(f"\n[report] -> {args.report}")


if __name__ == "__main__":
    main()
