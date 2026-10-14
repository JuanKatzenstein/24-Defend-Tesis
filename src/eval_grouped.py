#!/usr/bin/env python3
"""
eval_grouped.py — Comparación split aleatorio vs. grouped split por dominio.

El riesgo: el corpus tiene "familias" de hosts casi idénticos sobre una misma
plataforma (p. ej. itaucard00000.000webhostapp.com, itaucard011.000webhostapp.com,
itaucardbrrs.000webhostapp.com...). Un split aleatorio reparte esas familias entre
train y test, el modelo memoriza la familia y las métricas salen infladas.

Este script agrupa cada host por su dominio registrable (eTLD+1, usando solo
sufijos ICANN: así todo *.000webhostapp.com cae en un mismo grupo) y compara:
  - StratifiedKFold        (aleatorio: puede filtrar familias)
  - StratifiedGroupKFold   (grouped: la familia entera va a un solo fold)

Si las métricas caen al pasar a grouped, había fuga por familias. Los números
grouped son los defendibles.

Uso:
    python3 eval_grouped.py --data ../data/processed/dataset_combinado_host.csv \
        --report ../reports/eval_grouped.md
"""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import tldextract
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

_EXTRACT = tldextract.TLDExtract(include_psl_private_domains=False)


def dominio_registrable(url: str) -> str:
    host = urlparse(url if "://" in str(url) else "http://" + str(url)).hostname or ""
    e = _EXTRACT(host)
    return e.top_domain_under_public_suffix or host


def matriz(df: pd.DataFrame):
    num = df.select_dtypes(include=[np.number]).drop(columns=["label"])
    tld = pd.get_dummies(df["tld"], prefix="tld") if "tld" in df.columns else None
    X = num.fillna(0)
    if tld is not None:
        X = pd.concat([X, tld], axis=1)
    return X.values, df["label"].values


def evaluar(splitter, X, y, groups, modelos):
    res = {name: {"auc": [], "f1": []} for name in modelos}
    for tr, te in splitter.split(X, y, groups):
        Xtr, Xte = X[tr], X[te]
        sc = StandardScaler().fit(Xtr)
        for name, mk in modelos.items():
            m = mk()
            Xt = sc.transform(Xtr) if name == "LogReg" else Xtr
            Xv = sc.transform(Xte) if name == "LogReg" else Xte
            m.fit(Xt, y[tr])
            p = m.predict_proba(Xv)[:, 1]
            res[name]["auc"].append(roc_auc_score(y[te], p))
            res[name]["f1"].append(f1_score(y[te], (p >= 0.5).astype(int)))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    df["grupo"] = df["url"].map(dominio_registrable)
    X, y = matriz(df)
    groups = df["grupo"].values

    n_groups = df["grupo"].nunique()
    tam = df.groupby("grupo").size().sort_values(ascending=False)
    # grupos con etiquetas mixtas (mismo dominio registrable con phishing y legit)
    mixtos = df.groupby("grupo")["label"].nunique()
    n_mixtos = int((mixtos > 1).sum())

    modelos = {
        "LogReg": lambda: LogisticRegression(max_iter=1000, class_weight="balanced"),
        "RandomForest": lambda: RandomForestClassifier(
            n_estimators=300, random_state=args.seed, n_jobs=-1),
    }

    rand = evaluar(StratifiedKFold(5, shuffle=True, random_state=args.seed),
                   X, y, groups, modelos)
    grp = evaluar(StratifiedGroupKFold(5, shuffle=True, random_state=args.seed),
                  X, y, groups, modelos)

    L = ["# Split aleatorio vs. grouped por dominio registrable", ""]
    L.append(f"- Dataset: {len(df)} hosts · {n_groups} dominios registrables (grupos)")
    L.append(f"- Hosts por grupo: máx {int(tam.iloc[0])} "
             f"({tam.index[0]}), media {len(df)/n_groups:.1f}")
    L.append(f"- Grupos con etiquetas mixtas (phishing + legit en el mismo dominio): {n_mixtos}")
    L.append("")
    L.append("Familias grandes (fuente de fuga si se reparten entre train/test):")
    for g, n in tam.head(6).items():
        L.append(f"  - `{g}`: {int(n)} hosts")
    L.append("")
    L.append("| Modelo | split | ROC-AUC | F1 |")
    L.append("|--------|-------|--------:|---:|")
    for name in modelos:
        ra, rf = np.mean(rand[name]["auc"]), np.mean(rand[name]["f1"])
        ga, gf = np.mean(grp[name]["auc"]), np.mean(grp[name]["f1"])
        L.append(f"| {name} | aleatorio | {ra:.3f} | {rf:.3f} |")
        L.append(f"| {name} | **grouped** | **{ga:.3f}** | **{gf:.3f}** |")
        L.append(f"| {name} | caída | {ga-ra:+.3f} | {gf-rf:+.3f} |")
    L.append("")
    L.append("**Lectura:** la caída al pasar a grouped es la fuga por familias que "
             "el split aleatorio ocultaba. Los números grouped son los que hay que "
             "reportar en la tesis.")

    rep = "\n".join(L) + "\n"
    Path(args.report).write_text(rep)
    print(rep)
    print(f"[report] -> {args.report}")


if __name__ == "__main__":
    main()
