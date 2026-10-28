#!/usr/bin/env python3
"""
test_generar_sinteticos.py — prueba de punta a punta del generador sin gastar API.

Levanta un servidor HTTP local que imita la Messages API: lee el plan del prompt
y devuelve un host por fila (más algunos errores a propósito), y corre main()
contra él. Verifica el request enviado (modelo, effort, fallbacks, caché,
structured output), la validación contra el plan, la reanudación sin repetir
planes y el reporte de trazabilidad.

Uso:
    python3 test_generar_sinteticos.py --csv ../data/raw/dataset_combinado_v4.csv
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pandas as pd

import generar_sinteticos as g

FILA = re.compile(r"^\| (\d+) \| (\S+) \| (.+?) \| (\S+) \|$", re.M)
PEDIDOS: list[dict] = []
PRIMER_LOTE: list[str] = []


def host_para(fila_id: int, forma: str, destino: str, lote: int) -> str:
    # Solo letras: el filtro de casi-copias ignora dígitos y guiones.
    base = "zqx" + "abcdefghij"[lote] + "klmnopqrstuvwxyz"[fila_id] + "vrent"
    if forma == "plataforma":
        return f"{base}.{destino}"
    sufijo = destino.lstrip(".")
    return f"{base}.{sufijo}" if forma == "apex" else f"acceso.{base}.{sufijo}"


class FalsaAPI(BaseHTTPRequestHandler):
    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
        PEDIDOS.append({"body": cuerpo, "beta": self.headers.get("anthropic-beta")})
        prompt = cuerpo["messages"][0]["content"]
        lote = len(PEDIDOS)
        filas = FILA.findall(prompt)
        hosts = [{"id": int(i), "hostname": host_para(int(i), f, d, lote), "forma": f.upper(),
                  "marca": m, "patron": "prueba"} for i, f, m, d in filas]
        # Errores a propósito: forma cambiada, host con formato inválido y copia de un host previo.
        hosts[0]["forma"] = "apex" if hosts[0]["forma"].lower() != "apex" else "sub_ajeno"
        hosts[1]["hostname"] = "-invalido-.com"
        if lote == 1:
            PRIMER_LOTE.extend(h["hostname"] for h in hosts)
        else:
            hosts[2]["hostname"] = PRIMER_LOTE[2]
        datos = json.dumps({
            "id": f"msg_{lote}", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": json.dumps({"hosts": hosts})}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 500,
                      "iterations": [{"type": "message", "input_tokens": 1000, "output_tokens": 500}]},
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *a):
        pass


def correr_main(argv: list[str]):
    sys.argv = ["generar_sinteticos.py", *argv]
    g.main()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()

    srv = HTTPServer(("127.0.0.1", 0), FalsaAPI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update(ANTHROPIC_API_KEY="test", ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}",
                      NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sint.csv"
        correr_main(["--csv", args.csv, "--out", str(out), "--n-lotes", "2", "--por-lote", "10"])
        correr_main(["--csv", args.csv, "--out", str(out), "--n-lotes", "1", "--por-lote", "10"])
        res = pd.read_csv(out)
        reportes = sorted(Path(tmp).glob("sint.reporte_lotes_*.json"))
        rep2 = json.loads(reportes[-1].read_text())

    b = PEDIDOS[0]["body"]
    planes = [FILA.findall(p["body"]["messages"][0]["content"]) for p in PEDIDOS]
    chequeos = {
        "modelo claude-opus-5-5": b["model"] == "claude-opus-5-5",
        "effort explícito": b["output_config"].get("effort") == "medium",
        "salida estructurada (json_schema)": b["output_config"].get("format", {}).get("type") == "json_schema",
        "fallbacks=default + beta": b.get("fallbacks") == "default"
                                    and PEDIDOS[0]["beta"] == "server-side-fallback-2026-07-01",
        "system prompt cacheado": b["system"][0].get("cache_control") == {"type": "ephemeral"},
        "sin temperature": "temperature" not in b,
        "3 lotes llamados": len(PEDIDOS) == 3,
        "reanudar no repite el plan": planes[2] != planes[0],
        "lote 3 ve los hosts ya generados": "Hosts ya generados" in PEDIDOS[2]["body"]["messages"][0]["content"],
        # 10 por lote - forma cambiada - formato inválido (- copia del lote 1 en lotes 2 y 3)
        "aceptados = 8 + 7 + 7": len(res) == 22,
        "sin duplicados": res.hostname.is_unique,
        "lotes 1..3 numerados": sorted(res.lote.unique()) == [1, 2, 3],
        "trazabilidad (config_hash, split, grupo)": res.config_hash.nunique() == 1
                                                     and (res.split == "train").all()
                                                     and (res.grupo_split == res.hostname).all(),
        "reporte por corrida": len(reportes) == 2 and rep2["descartes"].get("no_respeta_plan") == 1
                               and rep2["descartes"].get("formato_invalido") == 1
                               and rep2["descartes"].get("duplicado") == 1,
    }
    for nombre, ok in chequeos.items():
        print(f"[{'OK' if ok else 'FALLA'}] {nombre}")
    srv.shutdown()
    sys.exit(0 if all(chequeos.values()) else 1)


if __name__ == "__main__":
    main()
