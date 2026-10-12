#!/usr/bin/env python3
"""
make_benign.py — Construye la CLASE NEGATIVA (URLs legítimas) para el detector.

Usa dominios oficiales REALES (los mismos que el phishing suplanta, más sitios
conocidos) combinados con paths benignos realistas. Son URLs legítimas: no hay
suplantación ni material ofensivo.

Esto es solo una SEMILLA reproducible para tener un detector funcional de punta a
punta. Para la tesis, lo ideal es reemplazar/ampliar con un ranking real
(Tranco / Majestic Million) — el formato de salida es el mismo (columna 'url').

Uso:
    python3 make_benign.py --n 60 --out data/raw/benign_seed.csv --seed 42
"""
from __future__ import annotations

import argparse
import random

import pandas as pd

# Dominios oficiales reales de las entidades del escenario rioplatense + globales.
DOMINIOS_LEGITIMOS = [
    # Uruguay — banca / pagos / estado / telco / ecommerce
    "brou.com.uy", "bancoitau.com.uy", "santander.com.uy", "bbva.com.uy",
    "scotiabank.com.uy", "prex.com.uy", "oca.com.uy", "abitab.com.uy",
    "redpagos.com.uy", "mercadolibre.com.uy", "mercadopago.com.uy",
    "correo.com.uy", "antel.com.uy", "sucive.gub.uy", "bcu.gub.uy",
    "gub.uy", "dgi.gub.uy", "ancap.com.uy", "ute.com.uy", "ose.com.uy",
    # Globales de uso cotidiano
    "google.com", "youtube.com", "wikipedia.org", "github.com",
    "amazon.com", "microsoft.com", "apple.com", "cloudflare.com",
    "stackoverflow.com", "linkedin.com", "reddit.com", "whatsapp.com",
]

# Paths benignos realistas (navegación normal de sitios legítimos).
PATHS_BENIGNOS = [
    "", "/", "/home", "/index.html", "/about", "/contacto", "/ayuda",
    "/personas", "/empresas", "/sucursales", "/productos", "/tarjetas",
    "/prestamos", "/institucional", "/noticias", "/faq", "/terminos",
    "/es/inicio", "/buscar?q=cuenta", "/blog/2025/articulo", "/soporte/tickets",
    "/wiki/Uruguay", "/watch?v=abc123", "/user/settings", "/docs/intro",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60, help="cantidad de URLs legítimas")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    filas, vistas = [], set()
    intentos = 0
    while len(filas) < args.n and intentos < args.n * 50:
        intentos += 1
        dom = rng.choice(DOMINIOS_LEGITIMOS)
        path = rng.choice(PATHS_BENIGNOS)
        url = f"https://www.{dom}{path}" if rng.random() < 0.5 else f"https://{dom}{path}"
        if url in vistas:
            continue
        vistas.add(url)
        filas.append({"url": url, "status": "legit"})

    pd.DataFrame(filas).to_csv(args.out, index=False)
    print(f"[benign] {len(filas)} URLs legítimas -> {args.out}")


if __name__ == "__main__":
    main()
