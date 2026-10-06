"""Configuración ganadora del recuperador. La cátedra corre recuperar.py sin flags extra."""

CORPUS_DIR = "datos/corpus"
CACHE_DIR = ".cache/rag"

# Ganador en dev: MiniLM, secciones Markdown, k=2 y umbral 0.3.
CONFIG = {
    "encoder": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "tipo": "st",
    "top_k": 2,
    "umbral": 0.3,
    "metadatos": True,
}
