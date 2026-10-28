#!/usr/bin/env python3
"""
evaluar_sinteticos.py — control de calidad de un lote de hostnames sintéticos
de phishing antes de usarlo para entrenar el detector.

Cinco chequeos, todos contra el CSV combinado (dataset_combinado_v4.csv):

  1. Integridad    formato válido, sin duplicados, sin hosts del dataset y sin
                   casi-copias (distancia de edición <= 1) de hosts de valid/test.
  2. Fidelidad     distribución de features léxicas (src/features.py) y de formas
                   frente al phishing real de TRAIN (estadístico KS por feature).
  3. Diversidad    casi-duplicados dentro del lote y memorización de hosts reales
                   (similitud coseno de n-gramas de caracteres >= 0.9).
  4. Firma         ¿un clasificador separa sintético de real? AUC cercano a 0.5 =
                   indistinguibles; cercano a 1 = el generador deja una firma.
  5. Utilidad      detector entrenado con real vs. real + sintético, evaluado en
                   el TEST real. Control: real + sobremuestreo (repetir phishing
                   real), para ver si el sintético aporta más que repetir datos.
                   Dos detectores: Random Forest sobre las features léxicas y
                   regresión logística sobre n-gramas de caracteres (ve el texto).

Las features se recalculan con src/features.py para TODOS los hosts (reales y
sintéticos), así ambos grupos pasan por el mismo pipeline.

Uso:
    pip install pandas scikit-learn
    python3 evaluar_sinteticos.py --csv ../data/raw/dataset_combinado_v4.csv \
        --sint ../data/raw/phishing_sintetico_llm.csv \
        --report ../reports/eval_sinteticos.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from features import _levenshtein, extract_features  # noqa: E402

from generar_sinteticos import RE_HOST, calibracion, cargar, esqueleto, forma_host  # noqa: E402

# Features numéricas de host (las de path/query son 0 para hostnames pelados).
FEATS = ["host_len", "n_dots", "n_hyphens", "n_subdomains", "n_digits", "digit_ratio",
         "letter_ratio", "host_entropy", "sld_entropy", "sld_len", "tld_sospechoso",
         "en_plataforma_hosting", "has_brand", "brand_suplantada", "n_palabras_gancho",
         "hex_largo", "dist_marca_min", "typosquat", "ratio_consonantes", "max_run_consonantes"]

UMBRAL_SIMILITUD = 0.9
SEMILLAS = [0, 1, 2, 3, 4]


def matriz(hosts) -> pd.DataFrame:
    return pd.DataFrame([extract_features(h) for h in hosts])[FEATS].astype(float)


def vecino_mas_cercano(consulta, base, excluir_mismo=False):
    """Similitud coseno (n-gramas de caracteres 2-4) al host más parecido de `base`."""
    vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4)).fit(list(base) + list(consulta))
    nn = NearestNeighbors(n_neighbors=2 if excluir_mismo else 1, metric="cosine").fit(vec.transform(base))
    dist, idx = nn.kneighbors(vec.transform(consulta))
    col = 1 if excluir_mismo else 0
    return 1 - dist[:, col], np.asarray(base)[idx[:, col]]


# ---------------------------------------------------------------------------
# 1-3. Integridad, fidelidad, diversidad
# ---------------------------------------------------------------------------

def integridad(sint: pd.DataFrame, df: pd.DataFrame) -> dict:
    hosts = sint.hostname
    heldout = df[df.split != "train"].hostname.tolist()
    sim, cercano = vecino_mas_cercano(hosts, heldout)
    fuga = sum(_levenshtein(h, c) <= 1 for h, c in zip(hosts, cercano))
    esq_dataset = {esqueleto(h) for h in df.hostname}
    return {
        "n": len(hosts),
        "formato_invalido": int((~hosts.map(lambda h: bool(RE_HOST.match(h)))).sum()),
        "duplicados_internos": int(hosts.duplicated().sum()),
        "en_dataset": int(hosts.isin(set(df.hostname)).sum()),
        "casi_copia_dataset": int(hosts.map(esqueleto).isin(esq_dataset).sum()),
        "fuga_lev1_valid_test": int(fuga),
    }


def fidelidad(F_sint: pd.DataFrame, F_real: pd.DataFrame, formas_sint, formas_real) -> tuple[pd.DataFrame, dict]:
    filas = []
    for c in FEATS:
        ks = ks_2samp(F_real[c], F_sint[c]).statistic
        filas.append({"feature": c, "real": F_real[c].mean(), "sintetico": F_sint[c].mean(), "ks": ks})
    tabla = pd.DataFrame(filas).sort_values("ks", ascending=False)
    formas = {"real": formas_real.value_counts(normalize=True).round(3).to_dict(),
              "sintetico": formas_sint.value_counts(normalize=True).round(3).to_dict()}
    return tabla, formas


def diversidad(sint_hosts, train_phish_hosts) -> dict:
    sim_self, _ = vecino_mas_cercano(sint_hosts, sint_hosts, excluir_mismo=True)
    sim_real, _ = vecino_mas_cercano(sint_hosts, train_phish_hosts)
    return {
        "casi_duplicados_internos": float((sim_self >= UMBRAL_SIMILITUD).mean()),
        "memorizacion_train": float((sim_real >= UMBRAL_SIMILITUD).mean()),
        "similitud_media_al_real_mas_cercano": float(sim_real.mean()),
    }


# ---------------------------------------------------------------------------
# 4. Firma: ¿se distingue sintético de real?
# ---------------------------------------------------------------------------

def firma(sint_hosts, real_hosts, F_sint, F_real) -> dict:
    n = min(len(sint_hosts), len(real_hosts))
    rng = np.random.default_rng(0)
    i_s = rng.choice(len(sint_hosts), n, replace=False)
    i_r = rng.choice(len(real_hosts), n, replace=False)
    hosts = np.concatenate([np.asarray(sint_hosts)[i_s], np.asarray(real_hosts)[i_r]])
    y = np.r_[np.ones(n), np.zeros(n)]
    skf = StratifiedKFold(5, shuffle=True, random_state=0)

    vec = TfidfVectorizer(analyzer="char", ngram_range=(1, 4), sublinear_tf=True)
    X_txt = vec.fit_transform(hosts)
    lr = LogisticRegression(max_iter=2000, C=1.0)
    p_txt = cross_val_predict(lr, X_txt, y, cv=skf, method="predict_proba")[:, 1]
    lr.fit(X_txt, y)
    vocab = np.array(vec.get_feature_names_out())
    orden = np.argsort(lr.coef_[0])
    marcadores_sint = [v.strip() or repr(v) for v in vocab[orden[::-1][:15]]]

    X_num = pd.concat([F_sint.iloc[i_s], F_real.iloc[i_r]]).values
    rf = RandomForestClassifier(300, random_state=0, n_jobs=-1)
    p_num = cross_val_predict(rf, X_num, y, cv=skf, method="predict_proba")[:, 1]
    return {"auc_ngramas": roc_auc_score(y, p_txt), "auc_features": roc_auc_score(y, p_num),
            "n_por_clase": n, "ngramas_tipicos_del_sintetico": marcadores_sint}


# ---------------------------------------------------------------------------
# 5. Utilidad para el detector
# ---------------------------------------------------------------------------

def recall_a_fpr(y, p, fpr_max=0.01) -> float:
    fpr, tpr, _ = roc_curve(y, p)
    return float(tpr[fpr <= fpr_max].max())


def utilidad(df: pd.DataFrame, F_df: pd.DataFrame, F_sint: pd.DataFrame,
             F_moldes: pd.DataFrame | None = None) -> pd.DataFrame:
    tr = (df.split == "train").values
    te = (df.split == "test").values
    legit_extra = df.split.isin(["valid_uy", "test_hosting"]).values  # solo legítimos
    X_tr, y_tr = F_df[tr].values, df.phishing[tr].values
    X_te, y_te = F_df[te].values, df.phishing[te].values
    X_leg = F_df[legit_extra].values
    pos_tr = X_tr[y_tr == 1]

    def correr(X_add, nombre):
        res = []
        for s in SEMILLAS:
            X = np.vstack([X_tr, X_add]) if len(X_add) else X_tr
            y = np.r_[y_tr, np.ones(len(X_add))]
            rf = RandomForestClassifier(300, random_state=s, n_jobs=-1, class_weight="balanced").fit(X, y)
            p = rf.predict_proba(X_te)[:, 1]
            res.append({"pr_auc": average_precision_score(y_te, p), "roc_auc": roc_auc_score(y_te, p),
                        "recall_fpr1": recall_a_fpr(y_te, p),
                        "fpr_legit_extra": float((rf.predict_proba(X_leg)[:, 1] >= 0.5).mean())})
        r = pd.DataFrame(res)
        return {"experimento": nombre, **{f"{c}": r[c].mean() for c in r}, "pr_auc_sd": r.pr_auc.std()}

    rng = np.random.default_rng(0)
    sobremuestreo = pos_tr[rng.choice(len(pos_tr), len(F_sint), replace=True)]
    filas = [
        correr(np.empty((0, X_tr.shape[1])), "A: solo real"),
        correr(sobremuestreo, f"B: real + {len(F_sint)} repetidos (control)"),
        correr(F_sint.values, f"C: real + {len(F_sint)} sintéticos"),
    ]
    if F_moldes is not None:
        # Control de la generación dirigida: repetir los mismos moldes difíciles.
        rep_moldes = F_moldes.values[rng.choice(len(F_moldes), len(F_sint), replace=True)]
        filas.append(correr(rep_moldes, f"D: real + {len(F_sint)} moldes difíciles repetidos (control)"))
    return pd.DataFrame(filas)


def utilidad_ngramas(df: pd.DataFrame, sint_hosts, moldes_hosts=None) -> pd.DataFrame:
    """Mismos experimentos que utilidad(), con un detector que ve el texto del host:
    TF-IDF de n-gramas de caracteres (1-4) + regresión logística."""
    tr = (df.split == "train").values
    te = (df.split == "test").values
    legit_extra = df.split.isin(["valid_uy", "test_hosting"]).values
    h_tr, y_tr = df.hostname[tr].tolist(), df.phishing[tr].values
    h_te, y_te = df.hostname[te].tolist(), df.phishing[te].values
    h_leg = df.hostname[legit_extra].tolist()
    pos_tr = np.asarray(h_tr)[y_tr == 1]
    n = len(sint_hosts)

    def correr(agregar, nombre):
        res = []
        for s in SEMILLAS:
            extra = agregar(np.random.default_rng(s))
            hosts, y = h_tr + list(extra), np.r_[y_tr, np.ones(len(extra))]
            vec = TfidfVectorizer(analyzer="char", ngram_range=(1, 4), sublinear_tf=True, min_df=2)
            lr = LogisticRegression(max_iter=3000, C=3.0, class_weight="balanced").fit(vec.fit_transform(hosts), y)
            p = lr.predict_proba(vec.transform(h_te))[:, 1]
            res.append({"pr_auc": average_precision_score(y_te, p), "roc_auc": roc_auc_score(y_te, p),
                        "recall_fpr1": recall_a_fpr(y_te, p),
                        "fpr_legit_extra": float((lr.predict_proba(vec.transform(h_leg))[:, 1] >= 0.5).mean())})
        r = pd.DataFrame(res)
        return {"experimento": nombre, **{c: r[c].mean() for c in r}, "pr_auc_sd": r.pr_auc.std()}

    filas = [
        correr(lambda rng: [], "A: solo real"),
        correr(lambda rng: pos_tr[rng.choice(len(pos_tr), n, replace=True)], f"B: real + {n} repetidos (control)"),
        correr(lambda rng: list(sint_hosts), f"C: real + {n} sintéticos"),
    ]
    if moldes_hosts is not None:
        m = np.asarray(moldes_hosts)
        filas.append(correr(lambda rng: m[rng.choice(len(m), n, replace=True)],
                            f"D: real + {n} moldes difíciles repetidos (control)"))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Veredicto y reporte
# ---------------------------------------------------------------------------

def veredicto(integ, tabla_ks, div, fir, util) -> list[tuple[str, str, str]]:
    a, b, c = util.pr_auc.values[:3]
    d = util.pr_auc.values[3] if len(util) > 3 else -1
    chequeos = [
        ("Integridad", "OK" if integ["formato_invalido"] == integ["en_dataset"] == integ["fuga_lev1_valid_test"] == 0
         else "FALLA", "sin formato inválido, sin hosts del dataset, sin fuga a valid/test"),
        ("Fidelidad", "OK" if tabla_ks.ks.median() <= 0.15 else "REVISAR",
         f"KS mediano {tabla_ks.ks.median():.2f} (objetivo <= 0.15)"),
        ("Diversidad", "OK" if div["casi_duplicados_internos"] <= 0.05 and div["memorizacion_train"] <= 0.05
         else "REVISAR", "<= 5% casi-duplicados internos y <= 5% memorización de train"),
        ("Firma", "OK" if fir["auc_ngramas"] <= 0.75 else "REVISAR" if fir["auc_ngramas"] <= 0.9 else "FALLA",
         f"AUC n-gramas {fir['auc_ngramas']:.2f} (<= 0.75 OK, > 0.9 el generador deja firma)"),
        ("Utilidad", "OK" if c >= max(a, b, d) else "NO MEJORA",
         f"PR-AUC test: real {a:.4f} | control {b:.4f} | sintético {c:.4f}"
         + (f" | moldes repetidos {d:.4f}" if d >= 0 else "")),
    ]
    return chequeos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--sint", required=True, type=Path, help="CSV con columna hostname")
    ap.add_argument("--report", type=Path, default=None, help="reporte markdown de salida")
    ap.add_argument("--moldes", type=Path, default=None,
                    help="moldes de la generación dirigida (CSV con hostname): agrega el control D")
    args = ap.parse_args()

    df, phish = cargar(args.csv)
    cal = calibracion(df, phish)
    sint = pd.read_csv(args.sint, keep_default_na=False)
    sint["hostname"] = sint.hostname.astype(str).str.strip().str.lower()

    print("Calculando features...", file=sys.stderr)
    F_df = matriz(df.hostname)
    F_sint = matriz(sint.hostname)
    F_real = F_df[((df.split == "train") & (df.phishing == 1)).values].reset_index(drop=True)

    integ = integridad(sint, df)
    tabla_ks, formas = fidelidad(F_sint, F_real, sint.hostname.map(lambda h: forma_host(h, cal)), phish.forma)
    div = diversidad(sint.hostname, phish.hostname)
    fir = firma(sint.hostname, phish.hostname, F_sint, F_real)
    print("Entrenando detectores (5 semillas x 3 experimentos)...", file=sys.stderr)
    moldes_hosts = pd.read_csv(args.moldes).hostname.str.lower() if args.moldes else None
    F_moldes = matriz(moldes_hosts) if args.moldes else None
    util = utilidad(df, F_df, F_sint, F_moldes)
    util_ng = utilidad_ngramas(df, sint.hostname, moldes_hosts)
    chequeos = veredicto(integ, tabla_ks, div, fir, util)

    L = [f"# Evaluación de sintéticos — `{args.sint.name}`", ""]
    L += ["## Veredicto", "", "| chequeo | estado | criterio |", "|---|:-:|---|"]
    L += [f"| {n} | **{e}** | {c} |" for n, e, c in chequeos]
    L += ["", "## 1. Integridad", "", *[f"- {k}: {v}" for k, v in integ.items()]]
    L += ["", "## 2. Fidelidad (vs. phishing real de train)", "",
          f"Formas — real: {formas['real']} · sintético: {formas['sintetico']}", "",
          "| feature | media real | media sintético | KS |", "|---|--:|--:|--:|"]
    L += [f"| {r.feature} | {r.real:.3f} | {r.sintetico:.3f} | {r.ks:.2f} |" for r in tabla_ks.itertuples()]
    L += ["", "## 3. Diversidad", "", *[f"- {k}: {v:.3f}" for k, v in div.items()]]
    L += ["", "## 4. Firma (sintético vs. real)", "",
          f"- AUC n-gramas de caracteres: {fir['auc_ngramas']:.3f}",
          f"- AUC features léxicas: {fir['auc_features']:.3f}",
          f"- n por clase: {fir['n_por_clase']}",
          f"- n-gramas que más delatan al sintético: {', '.join(fir['ngramas_tipicos_del_sintetico'])}"]
    L += ["", "## 5. Utilidad (Random Forest, test real, media de 5 semillas)", "",
          "| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |",
          "|---|--:|--:|--:|--:|--:|"]
    L += [f"| {r.experimento} | {r.pr_auc:.4f} | {r.pr_auc_sd:.4f} | {r.roc_auc:.4f} | "
          f"{r.recall_fpr1:.3f} | {r.fpr_legit_extra:.3f} |" for r in util.itertuples()]
    L += ["", "## 6. Utilidad con detector de n-gramas (TF-IDF 1-4 + regresión logística, test real)", "",
          "| experimento | PR-AUC | ±sd | ROC-AUC | recall @ FPR 1% | FPR en legítimos extra |",
          "|---|--:|--:|--:|--:|--:|"]
    L += [f"| {r.experimento} | {r.pr_auc:.4f} | {r.pr_auc_sd:.4f} | {r.roc_auc:.4f} | "
          f"{r.recall_fpr1:.3f} | {r.fpr_legit_extra:.3f} |" for r in util_ng.itertuples()]
    L += ["", "FPR en legítimos extra = proporción de hosts de valid_uy y test_hosting (todos legítimos) "
          "marcados como phishing con umbral 0.5."]
    texto = "\n".join(L) + "\n"
    print(texto)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(texto, encoding="utf-8")
        print(f"Reporte: {args.report}", file=sys.stderr)


if __name__ == "__main__":
    main()
