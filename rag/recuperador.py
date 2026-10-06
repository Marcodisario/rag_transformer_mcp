from pathlib import Path

import numpy as np

from rag.chunking import cargar_corpus
from rag.config import CACHE_DIR, CORPUS_DIR
from rag.embeddings import cargar, embed, guardar


class Recuperador:
    def __init__(self, config: dict, corpus_dir: str = CORPUS_DIR):
        self.config = config
        self.fragmentos = cargar_corpus(corpus_dir)
        self.vectores = self._indice()

    def _clave_cache(self) -> Path:
        nombre = self.config["encoder"].replace("/", "_")
        meta = "meta" if self.config.get("metadatos", True) else "nuda"
        return Path(CACHE_DIR) / f"{nombre}_{meta}.npz"

    def _indice(self) -> np.ndarray:
        textos_dev = [f["texto"] for f in self.fragmentos]
        cache = cargar(self._clave_cache())
        if cache is not None:
            vectores, textos = cache
            if textos == textos_dev:
                return vectores
        campos = "para_embed" if self.config.get("metadatos", True) else "texto"
        textos_emb = [f[campos] for f in self.fragmentos]
        vectores = embed(
            textos_emb,
            self.config["encoder"],
            self.config["tipo"],
            es_query=False,
        )
        guardar(self._clave_cache(), vectores, textos_dev)
        return vectores

    def buscar(self, pregunta: str) -> list[str]:
        q = embed(
            [pregunta],
            self.config["encoder"],
            self.config["tipo"],
            es_query=True,
        )[0]
        scores = self.vectores @ q
        k = self.config["top_k"]
        umbral = self.config["umbral"]
        orden = np.argsort(-scores)
        chosen = []
        for i in orden:
            if scores[i] < umbral:
                continue
            chosen.append(self.fragmentos[int(i)]["texto"])
            if len(chosen) >= k:
                break
        return chosen
