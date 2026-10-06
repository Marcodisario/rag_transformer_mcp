"""Comprueba que cada evidencia de dev cabe entera en al menos un fragmento."""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os

os.chdir(ROOT)

from rag.chunking import cargar_corpus
from rag.config import CORPUS_DIR


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    return re.sub(r"\s+", " ", t)


def main() -> None:
    frags = [norm(f["texto"]) for f in cargar_corpus(CORPUS_DIR)]
    preguntas = [
        json.loads(l)
        for l in Path("datos/preguntas_recuperacion_dev.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    faltan = []
    for p in preguntas:
        for e in p["evidencia"]:
            if not any(norm(e) in f for f in frags):
                faltan.append((p["id"], e))
    print(f"fragmentos: {len(frags)}")
    if faltan:
        print("evidencias partidas:")
        for pid, e in faltan:
            print(f"  {pid}: {e}")
        sys.exit(1)
    print("todas las evidencias de dev están enteras en algún fragmento")


if __name__ == "__main__":
    main()
