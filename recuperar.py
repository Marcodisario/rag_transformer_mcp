"""Recuperador vectorial. Contrato de la Parte 1."""
import argparse
import json
from pathlib import Path

from rag.config import CONFIG
from rag.recuperador import Recuperador


def leer_jsonl(path: str) -> list[dict]:
    lineas = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lineas if l.strip()]


def escribir_jsonl(path: str, filas: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def recuperar(preguntas: str, salida: str, config: dict | None = None) -> None:
    rec = Recuperador(config or CONFIG)
    filas = []
    for p in leer_jsonl(preguntas):
        filas.append({"id": p["id"], "fragmentos": rec.buscar(p["pregunta"])})
    escribir_jsonl(salida, filas)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preguntas", required=True)
    ap.add_argument("--salida", required=True)
    args = ap.parse_args()
    recuperar(args.preguntas, args.salida)


if __name__ == "__main__":
    main()
