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

# HARD NEGATIVES: URLs LEGÍTIMAS reales que superficialmente parecen phishing
# (login/secure/account en el host, TLD "sospechoso", hosting de plataforma,
# subdominios, query/hash largos, guiones, dígitos). Obligan al detector a no
# apoyarse en atajos triviales. Son todas legítimas y conocidas.
HARD_NEGATIVES = [
    # Logins/portales legítimos con palabras-gancho en el host
    "https://login.microsoftonline.com/common/oauth2/authorize",
    "https://accounts.google.com/signin/v2/identifier",
    "https://secure.bancoitau.com.uy/login",
    "https://signin.aws.amazon.com/console",
    "https://auth.services.adobe.com/es_ES/index.html",
    "https://id.atlassian.com/login",
    "https://login.yahoo.com/account/personalinfo",
    "https://secure.paypal.com/myaccount/summary",
    # Empresas reales en TLDs "sospechosos"
    "https://abc.xyz/investor",            # Alphabet
    "https://vercel.com/dashboard",
    "https://brave.com",
    "https://my.webex.com",
    "https://notion.so/product",
    "https://linear.app/method",
    "https://flutter.dev/docs",
    "https://deno.land/manual",
    # Deploys/sitios legítimos en plataformas de hosting gratuito
    "https://react.dev",
    "https://nextjs-commerce.vercel.app",
    "https://pytorch.github.io/tutorials",
    "https://pages.github.com",
    "https://streamlit.app/gallery",
    # URLs legítimas largas con query/hash y dígitos
    "https://www.amazon.com/dp/B0CX1W2Y34/ref=sr_1_3?keywords=teclado&qid=1712",
    "https://www.google.com/search?q=home+banking+uruguay&hl=es&num=20",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL9a1b2c3",
    "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=a1b2c3",
    "https://docs.google.com/document/d/1A2b3C4d5E6f7G8h9I0jK/edit",
    # Dominios legítimos con guiones y/o compuestos
    "https://home-assistant.io/getting-started",
    "https://www.mercado-libre-blog.com.uy/novedades",
    "https://developer-portal.antel.com.uy",
    "https://t.co/aBcD1234",               # acortador legítimo (Twitter/X)
    "https://bit.ly/3xYzAbc",              # acortador legítimo
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60, help="cantidad de URLs legítimas 'fáciles'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-hard", action="store_true",
                    help="excluir los hard negatives (solo legítimas 'fáciles')")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    filas, vistas = [], set()

    # Hard negatives primero (URLs legítimas que parecen sospechosas).
    if not args.no_hard:
        for url in HARD_NEGATIVES:
            if url not in vistas:
                vistas.add(url)
                filas.append({"url": url, "status": "legit"})

    # Legítimas "fáciles" por muestreo hasta completar n + hard.
    objetivo = args.n + len(filas)
    intentos = 0
    while len(filas) < objetivo and intentos < objetivo * 50:
        intentos += 1
        dom = rng.choice(DOMINIOS_LEGITIMOS)
        path = rng.choice(PATHS_BENIGNOS)
        url = f"https://www.{dom}{path}" if rng.random() < 0.5 else f"https://{dom}{path}"
        if url in vistas:
            continue
        vistas.add(url)
        filas.append({"url": url, "status": "legit"})

    n_hard = 0 if args.no_hard else len(HARD_NEGATIVES)
    pd.DataFrame(filas).to_csv(args.out, index=False)
    print(f"[benign] {len(filas)} URLs legítimas ({n_hard} hard negatives) -> {args.out}")


if __name__ == "__main__":
    main()
