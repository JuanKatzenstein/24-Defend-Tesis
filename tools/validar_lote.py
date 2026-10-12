#!/usr/bin/env python3
"""
validar_lote.py — Fase 3: valida el PLAN de un lote (salida de plan_lote.py).

Chequea que el plan muestreado respete la calibración del corpus y las reglas de
no-repetición. Opera sobre el JSON del plan (lote_XX.json), NO sobre hostnames
generados: es control de calidad del muestreo, puramente analítico/defensivo.

Validaciones:
  1. Distribución por FORMA (apex / sub_ajeno / plataforma) vs. PESO_FORMA objetivo.
  2. Sin combinaciones (marca, gramática) repetidas dentro del lote.
  3. NN únicos entre las filas que usan NN.
  4. Balance de palabras-gancho (ninguna domina el lote).

Uso:
    python3 validar_lote.py --lote lote_01.json --report ../reports/validacion_lote.md
    python3 validar_lote.py --lote lote_01.json --tol 0.15   # tolerancia de proporción
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Mapa gramática -> forma, y pesos objetivo (misma calibración que plan_lote.py).
GRAM_A_FORMA = {
    "A1": "apex", "A2": "apex", "A3a": "apex", "A3b": "apex",
    "S1": "sub_ajeno", "S1b": "sub_ajeno", "S2": "sub_ajeno", "S3": "sub_ajeno",
    "P1": "plataforma", "P2": "plataforma", "P3": "plataforma", "P4": "plataforma",
}
PESO_FORMA = {"apex": 0.44, "sub_ajeno": 0.33, "plataforma": 0.23}


def validar(filas: list[dict], tol: float) -> tuple[list[str], bool]:
    lineas, ok = [], True
    n = len(filas)

    # 1. Distribución por forma
    formas = Counter(GRAM_A_FORMA.get(f["gramatica"], "?") for f in filas)
    lineas.append("## 1. Distribución por forma (vs. objetivo)")
    lineas.append("")
    lineas.append("| forma | objetivo | observado | n | desvío | estado |")
    lineas.append("|-------|---------:|----------:|--:|-------:|:------:|")
    for forma, objetivo in PESO_FORMA.items():
        obs = formas.get(forma, 0) / n if n else 0
        desvio = obs - objetivo
        estado = "OK" if abs(desvio) <= tol else "FUERA"
        if estado == "FUERA":
            ok = False
        lineas.append(f"| {forma} | {objetivo:.2f} | {obs:.2f} | "
                      f"{formas.get(forma,0)} | {desvio:+.2f} | {estado} |")
    lineas.append("")
    lineas.append(f"Tolerancia: ±{tol:.2f} sobre la proporción. "
                  f"(Con n={n} chico, un desvío aislado es ruido de muestreo esperable.)")
    lineas.append("")

    # 2. Combinaciones marca+gramática repetidas
    combos = Counter((f.get("marca"), f["gramatica"]) for f in filas)
    reps = {k: v for k, v in combos.items() if v > 1}
    lineas.append("## 2. Combinaciones (marca, gramática) repetidas")
    lineas.append("")
    if reps:
        ok = False
        for (m, g), v in reps.items():
            lineas.append(f"- ⚠️ ({m}, {g}) aparece {v} veces")
    else:
        lineas.append("- OK: sin repeticiones dentro del lote.")
    lineas.append("")

    # 3. NN únicos
    nns = [f["nn"] for f in filas if f.get("nn")]
    dup_nn = [k for k, v in Counter(nns).items() if v > 1]
    lineas.append("## 3. Unicidad de NN")
    lineas.append("")
    if dup_nn:
        ok = False
        lineas.append(f"- ⚠️ NN repetidos: {', '.join(dup_nn)}")
    else:
        lineas.append(f"- OK: {len(nns)} NN, todos únicos.")
    lineas.append("")

    # 4. Balance de palabras-gancho
    palabras = Counter(f["palabra_es"] for f in filas if f.get("palabra_es"))
    lineas.append("## 4. Balance de palabras-gancho")
    lineas.append("")
    if palabras:
        top, cnt = palabras.most_common(1)[0]
        max_frac = cnt / sum(palabras.values())
        estado = "OK" if max_frac <= 0.4 else "CONCENTRADO"
        if estado != "OK":
            ok = False
        lineas.append(f"- {len(palabras)} palabras distintas; la más usada «{top}» "
                      f"= {max_frac:.0%} del total → {estado}")
    else:
        lineas.append("- (sin palabras-gancho en este lote)")
    lineas.append("")

    return lineas, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lote", required=True, help="lote_XX.json (salida de plan_lote.py)")
    ap.add_argument("--tol", type=float, default=0.15, help="tolerancia de proporción")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    filas = json.loads(Path(args.lote).read_text())
    cab = [f"# Validación de lote — {Path(args.lote).name}", "",
           f"Casos: {len(filas)} · tolerancia ±{args.tol:.2f}", ""]
    cuerpo, ok = validar(filas, args.tol)
    cab.append(f"**Resultado global: {'✅ PASA' if ok else '❌ REVISAR'}**")
    cab.append("")
    reporte = "\n".join(cab + cuerpo)
    print(reporte)
    if args.report:
        Path(args.report).write_text(reporte + "\n")
        print(f"[report] -> {args.report}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
