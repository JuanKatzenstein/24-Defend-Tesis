#!/usr/bin/env python3
"""
features.py — Extracción de features léxicas de URL/host para detección de phishing.

No descarga ni resuelve nada: trabaja solo sobre el string de la URL/host, que es
el escenario realista de un detector que clasifica ANTES de visitar el sitio.

Cada feature está pensada para ser interpretable (importante para defender la tesis):
largos, conteos de caracteres, entropía del dominio, uso de marca, palabras-gancho,
TLD sospechoso, etc. Todas derivan únicamente de la cadena.

Uso:
    from features import extract_features
    row = extract_features("https://brou-ingreso.top/login.php")

    # o en lote, sobre un CSV con columna 'url':
    python3 features.py --in data/raw/corpus_sintetico.csv --out data/processed/feats.csv
"""
from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from urllib.parse import urlparse

import pandas as pd

# ---------------------------------------------------------------------------
# Listas de apoyo (interpretables, documentables en la tesis)
# ---------------------------------------------------------------------------

# TLDs/sufijos baratos o gratuitos frecuentemente abusados en phishing.
TLDS_SOSPECHOSOS = {
    "tk", "ml", "ga", "cf", "gq", "top", "xyz", "click", "online", "site",
    "shop", "help", "cam", "cc", "club", "link", "icu", "work", "live",
    "fit", "rest", "country", "kim", "loan", "men", "download",
}

# Plataformas de hosting gratuito que aparecen como dominio registrable en phishing.
PLATAFORMAS_HOSTING = {
    "repl.co", "vercel.app", "netlify.app", "pantheonsite.io", "github.io",
    "joomla.com", "000webhostapp.com", "atwebpages.com", "duckdns.org",
    "glitch.me", "herokuapp.com", "web.app", "firebaseapp.com", "pages.dev",
    "r2.dev", "weeblysite.com", "blogspot.com",
}

# Palabras-gancho típicas (es + en). Señal fuerte en el path/host de phishing.
PALABRAS_GANCHO = {
    "login", "signin", "ingreso", "acceso", "verificar", "verificacion",
    "validar", "confirmar", "actualizar", "seguro", "secure", "account",
    "cuenta", "tarjeta", "card", "clave", "password", "banco", "bank",
    "pago", "pagos", "factura", "cobro", "soporte", "cliente", "premio",
    "beneficio", "oferta", "reembolso", "devolucion", "limite", "update",
    "webscr", "wp-includes", "wp-admin", "admin",
}

# Marcas regionales de referencia (para el flag has_brand del escenario rioplatense).
MARCAS = {
    "antel", "brou", "itau", "prex", "oca", "sucive", "santander",
    "mercadolibre", "mercadopago", "correouruguayo", "abitab", "scotiabank",
    "bbva", "redpagos", "brou", "bcu", "midinero",
}

_IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_HEX_RUN = re.compile(r"[0-9a-f]{8,}")


def _shannon_entropy(s: str) -> float:
    """Entropía de Shannon de la cadena (bits/caracter). Alta = string aleatorio."""
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _ensure_scheme(url: str) -> str:
    """urlparse necesita un esquema para separar host de path de forma confiable."""
    if "://" not in url:
        return "http://" + url
    return url


def extract_features(url: str) -> dict:
    """Devuelve un dict de features léxicas para una URL o host."""
    url = (url or "").strip()
    parsed = urlparse(_ensure_scheme(url))
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""
    full = url.lower()

    labels = host.split(".") if host else []
    tld = labels[-1] if len(labels) >= 1 else ""
    # dominio registrable aproximado (sld.tld); suficiente para features léxicas
    sld = labels[-2] if len(labels) >= 2 else (labels[0] if labels else "")

    n_digits = sum(c.isdigit() for c in full)
    n_letters = sum(c.isalpha() for c in full)
    n_hyphen = full.count("-")
    n_dot = host.count(".")
    n_sub = max(len(labels) - 2, 0) if len(labels) >= 2 else 0

    has_brand = any(m in host for m in MARCAS)
    # marca presente pero NO como dominio registrable propio (señal de suplantación)
    brand_not_registrable = has_brand and not any(sld == m for m in MARCAS)

    tokens = re.split(r"[^a-z]+", full)
    n_gancho = sum(1 for t in tokens if t in PALABRAS_GANCHO)

    is_ip = 1 if _IPV4.match(host or "") else 0
    plataforma = next((p for p in PLATAFORMAS_HOSTING if host.endswith(p)), "")

    feats = {
        "url_len": len(url),
        "host_len": len(host),
        "path_len": len(path),
        "query_len": len(query),
        "n_dots": n_dot,
        "n_hyphens": n_hyphen,
        "n_subdomains": n_sub,
        "n_digits": n_digits,
        "digit_ratio": round(n_digits / len(full), 4) if full else 0.0,
        "letter_ratio": round(n_letters / len(full), 4) if full else 0.0,
        "n_at": full.count("@"),
        "n_slash": full.count("/"),
        "n_pct": full.count("%"),
        "n_params": full.count("="),
        "host_entropy": round(_shannon_entropy(host), 4),
        "sld_entropy": round(_shannon_entropy(sld), 4),
        "sld_len": len(sld),
        "tld": tld,
        "tld_sospechoso": 1 if tld in TLDS_SOSPECHOSOS else 0,
        "is_ip": is_ip,
        "en_plataforma_hosting": 1 if plataforma else 0,
        "plataforma": plataforma,
        "has_brand": 1 if has_brand else 0,
        "brand_suplantada": 1 if brand_not_registrable else 0,
        "n_palabras_gancho": n_gancho,
        "tiene_gancho": 1 if n_gancho > 0 else 0,
        "hex_largo": 1 if _HEX_RUN.search(host.replace(".", "")) else 0,
        "https": 1 if parsed.scheme == "https" else 0,
    }
    return feats


def extract_frame(df: pd.DataFrame, url_col: str = "url") -> pd.DataFrame:
    """Aplica extract_features a cada fila y devuelve el frame de features."""
    feats = df[url_col].map(extract_features).apply(pd.Series)
    return feats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True, help="CSV con columna 'url'")
    ap.add_argument("--out", required=True, help="CSV de salida con features")
    ap.add_argument("--url-col", default="url")
    ap.add_argument("--keep", nargs="*", default=["status", "marca", "sector"],
                    help="columnas del original a conservar si existen")
    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    feats = extract_frame(df, args.url_col)

    keep = [c for c in args.keep if c in df.columns]
    out = pd.concat([df[[args.url_col] + keep].reset_index(drop=True), feats], axis=1)
    out.to_csv(args.out, index=False)
    print(f"[features] {len(out)} filas · {feats.shape[1]} features -> {args.out}")


if __name__ == "__main__":
    main()
