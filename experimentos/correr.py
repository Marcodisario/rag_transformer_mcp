"""Corre una configuración, evalúa y copia el .eval.json a experimentos/."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os

os.chdir(ROOT)

from rag.config import CONFIG
from recuperar import recuperar

PREGUNTAS = "datos/preguntas_recuperacion_dev.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--encoder", default=CONFIG["encoder"])
    ap.add_argument("--tipo", default=CONFIG["tipo"])
    ap.add_argument("--top-k", type=int, default=CONFIG["top_k"])
    ap.add_argument("--umbral", type=float, default=CONFIG["umbral"])
    ap.add_argument("--metadatos", action=argparse.BooleanOptionalAction, default=True)
    args = ap.parse_args()

    config = {
        "encoder": args.encoder,
        "tipo": args.tipo,
        "top_k": args.top_k,
        "umbral": args.umbral,
        "metadatos": args.metadatos,
    }
    out_dir = Path("experimentos")
    out_dir.mkdir(exist_ok=True)
    jsonl = out_dir / f"{args.nombre}.jsonl"
    recuperar(PREGUNTAS, str(jsonl), config)

    subprocess.check_call(
        [
            sys.executable,
            "evaluar/evaluar.py",
            "recuperacion",
            "--preguntas",
            PREGUNTAS,
            "--resultados",
            str(jsonl),
        ]
    )
    bruto = Path(str(jsonl) + ".eval.json")
    destino = out_dir / f"{args.nombre}.eval.json"
    shutil.copyfile(bruto, destino)
    data = json.loads(destino.read_text(encoding="utf-8"))
    print(json.dumps({"nombre": args.nombre, "config": config, "resumen": data["resumen"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
