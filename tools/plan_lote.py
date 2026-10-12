#!/usr/bin/env python3
"""
plan_lote.py — Fase 2 del plan de ejecución (phishing sintético).

Arma la tabla de parámetros de UN lote (por defecto 20 casos) por muestreo,
usando las proporciones medidas en el corpus regional (hosts_procesados_corpus.csv).
No genera los hosts: solo arma el plan que se pega en el prompt de la Fase 1.

Uso:
    python3 plan_lote.py --n 20 --csv /ruta/hosts_procesados_corpus.csv \
        --historial historial_lotes.json --out lote_01.md --out-json lote_01.json

El --historial se lee y se actualiza en cada corrida: evita repetir la misma
combinación marca+gramática+NN+palabra entre lotes, y acumula el historial de
hosts para pasarle al validador de la Fase 3.

Dependencias: pandas (ya usado en el resto del pipeline). Sin otras libs externas.
"""
import argparse
import json
import random
import re
import string
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Calibración: proporciones medidas en el informe de patrones regional.
#    Son un primer ajuste, no una verdad fija — revisar si el validador (Fase 3)
#    muestra que el lote generado no respeta estos rangos.
# ---------------------------------------------------------------------------

# Peso de cada "forma" de host (informe, sección 1): apex 44.1 / sub-ajeno 33.1 / plataforma 22.8
PESO_FORMA = {"apex": 0.44, "sub_ajeno": 0.33, "plataforma": 0.23}

# Dentro de apex, reparto entre A1 (marca+palabra), A2 (marca+sufijo corto) y sin marca (A3a/A3b)
PESO_APEX = {"A1": 0.55, "A2": 0.25, "A3a": 0.10, "A3b": 0.10}

# Dentro de sub-ajeno, reparto entre S1 (dominante), S2 (www- + NN, 3.7% del total),
# S1b (patrón -gub, raro, solo documentado para SUCIVE) y S3 (dominio oficial incrustado, raro)
PESO_SUB_AJENO = {"S1": 0.70, "S2": 0.15, "S1b": 0.08, "S3": 0.07}

# Dentro de plataforma, reparto por popularidad de plataforma en el corpus
PESO_PLATAFORMA = {"P1": 0.20, "P2": 0.15, "P3": 0.20, "P4": 0.45}

TLD_APEX = {"com": 0.60, "gtld_barato": 0.20, "ex_gratis": 0.07, "net_org_info": 0.04, "otro": 0.09}
TLD_SUB_AJENO = {"com": 0.53, "gtld_barato": 0.10, "ex_gratis": 0.06, "net_org_info": 0.08, "otro": 0.23}

GTLD_BARATOS = ["click", "top", "xyz", "online", "site", "shop", "help", "cam", "cc", "club", "link", "icu"]
EX_GRATUITOS = ["tk", "ml", "ga", "cf", "gq"]
NET_ORG_INFO = ["net", "org", "info"]

PLATAFORMAS_P4 = ["duckdns.org", "netlify.app", "joomla.com", "000webhostapp.com",
                   "atwebpages.com", "github.io"]

PALABRAS_ES = ["soporte", "ingreso", "cliente", "seguro", "actualizar", "limites",
               "validar", "verificar", "tarjeta", "factura", "devolucion", "envios",
               "paquetes", "ofertas", "puntos", "beneficios", "premios", "enlinea",
               "logistica", "comprobante", "reclamo", "reembolso"]

# Marcas con respaldo documentado en el corpus (se usan sin aclaración) y
# extrapolaciones (se marcan igual en la tabla de salida).
MARCAS = [
    ("antel", "telco", True), ("brou", "banca", True), ("itau", "banca", True),
    ("prex", "fintech", True), ("oca", "tarjetas", True), ("sucive", "gobierno", True),
    ("santander", "banca", True), ("mercadolibre", "ecommerce", True),
    ("mercadopago", "pagos", True), ("correouruguayo", "logistica", True),
    ("abitab", "pagos", False), ("scotiabank", "banca", False),
    ("bbva", "banca", False), ("redpagos", "pagos", False),
]

# Ejemplos reales raros (S1b, S3): el corpus trae muy pocos casos, se curaron a mano
# a partir del análisis de hosts con dominio incrustado y del patrón -gub de SUCIVE.
EJEMPLOS_S1B = ["sucive-gub.txmhj.cn", "sucive-gub.txmtb.help", "sucive-gub.fldbr.cn"]
EJEMPLOS_S3 = [
    "acessoseguro.itau.com.br.mbarquiteturabrandao.com.br",
    "pix.bb.com.br.appsegu.com",
    "bradescori.com.br.admin-mcas-df.ms",
]

VOCALES = "aeiou"
CONSONANTES = "bcdfghjklmnpqrstvwxyz"


# ---------------------------------------------------------------------------
# 2. Utilidades de muestreo
# ---------------------------------------------------------------------------

def elegir(pesos: dict, rng: random.Random):
    claves = list(pesos.keys())
    pesos_v = list(pesos.values())
    return rng.choices(claves, weights=pesos_v, k=1)[0]


def elegir_tld(bucket: str, rng: random.Random) -> str:
    if bucket == "com":
        return "com"
    if bucket == "gtld_barato":
        return rng.choice(GTLD_BARATOS)
    if bucket == "ex_gratis":
        return rng.choice(EX_GRATUITOS)
    if bucket == "net_org_info":
        return rng.choice(NET_ORG_INFO)
    return rng.choice(["co", "info", "es", "me", "cam"])


class Historial:
    """Evita repetir combinaciones marca+gramática+NN+palabra entre lotes,
    y acumula todos los hosts descriptos (para pasarle al validador de Fase 3)."""

    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            self.data = json.loads(path.read_text())
        else:
            self.data = {"combos_usadas": [], "nn_usados": [], "palabras_contador": {}}

    def combo_libre(self, marca, gram):
        return [marca, gram] not in self.data["combos_usadas"]

    def registrar_combo(self, marca, gram):
        self.data["combos_usadas"].append([marca, gram])

    def nn_libre(self, nn):
        return nn not in self.data["nn_usados"]

    def registrar_nn(self, nn):
        self.data["nn_usados"].append(nn)

    def palabra_menos_usada(self, candidatas, rng):
        cont = self.data["palabras_contador"]
        candidatas = sorted(candidatas, key=lambda w: cont.get(w, 0))
        minimo = cont.get(candidatas[0], 0)
        empatadas = [w for w in candidatas if cont.get(w, 0) == minimo]
        return rng.choice(empatadas)

    def registrar_palabra(self, palabra):
        if palabra:
            self.data["palabras_contador"][palabra] = self.data["palabras_contador"].get(palabra, 0) + 1

    def guardar(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))


def nn_nuevo(hist: Historial, rng: random.Random) -> str:
    redondos = {"00", "01", "02", "07", "10", "12", "99"}
    for _ in range(200):
        n = f"{rng.randint(13, 98):02d}"
        if n not in redondos and hist.nn_libre(n):
            return n
    raise RuntimeError("No quedan NN libres; revisar el historial o ampliar el rango.")


# ---------------------------------------------------------------------------
# 3. Ejemplos reales por gramática, muestreados en vivo del CSV regional
# ---------------------------------------------------------------------------

def clasificar_regional(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df.status == "phishing"].copy()
    df["hasbrand"] = df.H2.fillna(False) | df.H3.fillna(False) | df.H4.fillna(False)

    def forma(r):
        if r.plat_cualquiera:
            return "plataforma"
        if r.n_sub == 0:
            return "apex"
        return "sub_ajeno"

    df["forma"] = df.apply(forma, axis=1)
    return df


def ejemplos_por_gramatica(df: pd.DataFrame, k: int, rng_seed: int):
    rng = random.Random(rng_seed)
    out = {}

    apex = df[df.forma == "apex"]
    out["A1"] = apex[apex.hasbrand & apex.H4].host.tolist()
    out["A2"] = apex[apex.hasbrand & ~apex.H4 & apex.sufijo.isin(GTLD_BARATOS + EX_GRATUITOS)].host.tolist()
    out["A3a"] = apex[~apex.hasbrand].host.tolist()
    out["A3b"] = out["A3a"]  # mismo pool; en A3b se insiste en que no sea nombre de negocio real

    sub = df[df.forma == "sub_ajeno"]
    out["S1"] = sub[sub.hasbrand & ~sub.host.str.startswith("www-")].host.tolist()
    out["S2"] = sub[sub.host.str.match(r"^www-")].host.tolist()
    out["S1b"] = EJEMPLOS_S1B
    out["S3"] = EJEMPLOS_S3

    plat = df[df.forma == "plataforma"]
    out["P1"] = plat[plat.dominio_reg == "pantheonsite.io"].host.tolist()
    out["P2"] = plat[plat.dominio_reg == "repl.co"].host.tolist()
    out["P3"] = plat[plat.dominio_reg == "vercel.app"].host.tolist()
    out["P4"] = plat[plat.dominio_reg.isin(PLATAFORMAS_P4)].host.tolist()

    muestra = {}
    for gram, pool in out.items():
        pool = [h for h in pool if isinstance(h, str)]
        if not pool:
            muestra[gram] = []
            continue
        k_efectivo = min(k, len(pool))
        muestra[gram] = rng.sample(pool, k_efectivo)
    return muestra


def tokens_vedados(ejemplos_usados: dict, marcas: set) -> list:
    vedados = set()
    for hosts in ejemplos_usados.values():
        for h in hosts:
            for tok in re.split(r"[.\-]", h):
                tok = tok.lower()
                if len(tok) >= 3 and tok not in marcas and not tok.isdigit():
                    vedados.add(tok)
    return sorted(vedados)


# ---------------------------------------------------------------------------
# 4. Armado de una fila del plan
# ---------------------------------------------------------------------------

LARGO_DEFAULT = "<=27"
LARGO_MEDIO = "33-41"
LARGO_LARGO = "44-52"

PATHS_GENERICOS = ["sin", "/login.php", "/index.php", "/acceso/", "/ingreso/", "/verificar/",
                    "/signin", "/login", "/index.html"]


def fila(idx, marca_info, gram, hist: Historial, rng: random.Random):
    marca, sector, respaldo = marca_info
    palabra = None
    tld_o_plat = None
    estilo = ""
    path = rng.choice(PATHS_GENERICOS)
    largo = LARGO_DEFAULT

    if gram == "A1":
        tld_o_plat = "." + elegir_tld(elegir(TLD_APEX, rng), rng)
        palabra = hist.palabra_menos_usada(PALABRAS_ES, rng)
        estilo = "guion" if rng.random() < 0.5 else "pegada"
        path = rng.choice(["sin", "/login.php", "/signin", "/index.php"])
    elif gram == "A2":
        tld_o_plat = "." + elegir_tld(rng.choice(["gtld_barato", "ex_gratis"]), rng)
        estilo = rng.choice(["sufijo de 2 letras sin sentido", "sufijo de 3 letras sin sentido",
                               "prefijo e + sufijo de 2 letras sin sentido"])
        path = "sin"
    elif gram == "A3a":
        marca = None
        tld_o_plat = "." + elegir_tld(elegir(TLD_APEX, rng), rng)
        estilo = "nombre NEGOCIO rioplatense de hasta 23 caracteres"
        # A3a no tiene marca: el path no debe traer <marca> (quedaría doble barra)
        path = rng.choice(["/wp-includes/css/login.php",
                             "/wp-includes/images/login.php",
                             "/includes/modules/index.php"])
    elif gram == "A3b":
        marca = None
        tld_o_plat = "." + elegir_tld(rng.choice(["gtld_barato", "com"]), rng)
        estilo = "pseudo-palabra pronunciable de 7-10 letras, sin significado"
        path = rng.choice(["/index.html", "sin"])
    elif gram == "S1":
        tld_o_plat = "." + elegir_tld(elegir(TLD_SUB_AJENO, rng), rng)
        estilo = rng.choice(["ajeno PSEUDO de 5-8 letras", "ajeno NEGOCIO de hasta 17 letras",
                               "ajeno CONSONANTES de 6-8 letras"])
        path = rng.choice(["sin", "/login", "/acceso/"])
    elif gram == "S1b":
        marca = "sucive"  # único caso documentado en el corpus para este patrón
        tld_o_plat = "." + elegir_tld(rng.choice(["ex_gratis", "otro"]), rng)
        estilo = "etiqueta de 5 letras al azar, con al menos 4 consonantes"
        path = "sin"
    elif gram == "S2":
        tld_o_plat = "." + elegir_tld(rng.choice(["com", "net_org_info"]), rng)
        estilo = "ajeno COMPUESTO de 13-21 caracteres (letra+2 dígitos+palabras pegadas)"
        largo = LARGO_MEDIO
        path = "sin"
    elif gram == "S3":
        marca = "brou"  # único patrón documentado con dominio oficial incrustado completo
        tld_o_plat = ".com"
        estilo = "ajeno de una pseudo-palabra o compuesto, hasta 11 letras (nunca palabra común real)"
        path = "/verificar/"
    elif gram == "P1":
        tld_o_plat = "pantheonsite.io"
        palabra = hist.palabra_menos_usada(PALABRAS_ES, rng)
        estilo = "typo de letra repetida en la palabra; bloque -uy- fijo entre la palabra y el NN"
        largo = LARGO_MEDIO
        path = "sin"
    elif gram == "P2":
        tld_o_plat = "repl.co"
        palabra = hist.palabra_menos_usada(["validar", "verificar", "confirmar", "activar"], rng)
        estilo = "acción + v2 (el ejemplo real usa 'verificationv2'; no lo copies)"
        # <marca>card.<palabra>v2.repl.co: el largo lo fija la estructura
        largo = "<=41"
        path = "/index.php"
    elif gram == "P3":
        tld_o_plat = "vercel.app"
        palabra = rng.choice(["demo", "clon", "test", "preview"])
        estilo = "hash de 9 caracteres y usuario (nombre propio rioplatense, minúsculas, 6-12 letras)"
        # con palabras cortas (demo/clon/test) no se llega al piso de 44; acotamos por arriba
        largo = "<=52"
        path = "/?id=<hash de 6>"
    elif gram == "P4":
        tld_o_plat = rng.choice(PLATAFORMAS_P4)
        palabra = hist.palabra_menos_usada(PALABRAS_ES, rng)
        estilo = "guion, NN"
        # marca-palabra-NN + plataforma: con plataformas cortas no se llega a 33
        largo = "<=46"
        path = "sin"

    nn_necesita = gram in {"S2", "P1", "P4"}
    nn = nn_nuevo(hist, rng) if nn_necesita else None
    if nn:
        hist.registrar_nn(nn)
    if palabra:
        hist.registrar_palabra(palabra)
    hist.registrar_combo(marca, gram)

    return {
        "id": idx,
        "marca": marca,
        "sector": sector if marca else None,
        "respaldo_corpus": respaldo if marca else None,
        "gramatica": gram,
        "tld_o_plataforma": tld_o_plat,
        "palabra_es": palabra,
        "nn": nn,
        "estilo_inventar": estilo,
        "path": path,
        "largo_objetivo": largo,
    }


# ---------------------------------------------------------------------------
# 5. Armado del lote completo
# ---------------------------------------------------------------------------

def armar_lote(n: int, hist: Historial, rng: random.Random):
    filas = []
    marcas_ciclo = MARCAS[:]
    rng.shuffle(marcas_ciclo)
    i = 0
    intentos = 0
    while len(filas) < n and intentos < n * 20:
        intentos += 1
        forma = elegir(PESO_FORMA, rng)
        if forma == "apex":
            gram = elegir(PESO_APEX, rng)
        elif forma == "sub_ajeno":
            gram = elegir(PESO_SUB_AJENO, rng)
        else:
            gram = elegir(PESO_PLATAFORMA, rng)

        marca_info = marcas_ciclo[i % len(marcas_ciclo)]
        i += 1
        # evitar repetir la misma combinación marca+gramática ya usada en lotes previos
        if not hist.combo_libre(marca_info[0], gram):
            continue
        filas.append(fila(len(filas) + 1, marca_info, gram, hist, rng))
    return filas


# ---------------------------------------------------------------------------
# 6. Salida: tabla markdown lista para pegar en el prompt + JSON
# ---------------------------------------------------------------------------

def a_markdown(filas, ejemplos, vedados) -> str:
    out = []
    out.append("| id | marca | gram | TLD / plataforma | palabra ES | lo que inventás | path | largo |")
    out.append("|----|-------|------|-------------------|-----------|------------------|------|-------|")
    for f in filas:
        marca = f["marca"] if f["marca"] else "(sin marca)"
        palabra = f["palabra_es"] or "—"
        estilo = f["estilo_inventar"]
        if f["nn"]:
            estilo = f"NN={f['nn']}; " + estilo
        out.append(f"| {f['id']} | {marca} | {f['gramatica']} | {f['tld_o_plataforma']} | "
                    f"{palabra} | {estilo} | {f['path']} | {f['largo_objetivo']} |")

    out.append("")
    out.append("Respaldo en el corpus: " + ", ".join(
        sorted({f["marca"] for f in filas if f["marca"] and f["respaldo_corpus"]})))
    extrapoladas = sorted({f["marca"] for f in filas if f["marca"] and not f["respaldo_corpus"]})
    if extrapoladas:
        out.append("Extrapolaciones (decilo en la justificación): " + ", ".join(extrapoladas))

    out.append("")
    out.append("## Ejemplos reales de este lote (para imitar la forma, nunca para copiar)")
    for gram, hosts in ejemplos.items():
        usados = {f["gramatica"] for f in filas}
        if gram not in usados or not hosts:
            continue
        out.append(f"{gram}: " + " · ".join(hosts))

    out.append("")
    out.append("Tokens vedados de este lote (no los uses ni los modifiques): " + ", ".join(vedados[:40]))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=20, help="casos en el lote")
    ap.add_argument("--csv", default="hosts_procesados_corpus.csv",
                     help="CSV regional (hosts_procesados_corpus.csv)")
    ap.add_argument("--historial", default="historial_lotes.json",
                     help="archivo de historial, se lee y se actualiza")
    ap.add_argument("--seed", type=int, default=None, help="semilla (default: aleatoria)")
    ap.add_argument("--out", default=None, help="archivo .md de salida (tabla para el prompt)")
    ap.add_argument("--out-json", default=None, help="archivo .json de salida (plan crudo)")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.SystemRandom().randint(0, 10**9)
    rng = random.Random(seed)

    df = pd.read_csv(args.csv)
    df = clasificar_regional(df)

    hist = Historial(Path(args.historial))
    filas = armar_lote(args.n, hist, rng)

    ejemplos = ejemplos_por_gramatica(df, k=4, rng_seed=seed)
    marcas_set = {m[0] for m in MARCAS} | {"card"}
    vedados = tokens_vedados(ejemplos, marcas_set)

    md = a_markdown(filas, ejemplos, vedados)

    if args.out:
        Path(args.out).write_text(md)
    else:
        print(md)

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(filas, ensure_ascii=False, indent=2))

    hist.guardar()
    print(f"\n# seed usada: {seed} (pasala con --seed para reproducir este lote)", file=sys.stderr)


if __name__ == "__main__":
    main()
