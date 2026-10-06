from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

_bert = {}
_st = {}


def embed(textos: list[str], encoder: str, tipo: str, es_query: bool) -> np.ndarray:
    if tipo == "bert_mean":
        return _embed_bert(textos, encoder)
    if tipo == "e5":
        prefijo = "query: " if es_query else "passage: "
        return _embed_st([prefijo + t for t in textos], encoder)
    return _embed_st(textos, encoder)


def _embed_bert(textos: list[str], encoder: str) -> np.ndarray:
    if encoder not in _bert:
        tok = AutoTokenizer.from_pretrained(encoder)
        modelo = AutoModel.from_pretrained(encoder)
        modelo.eval()
        _bert[encoder] = (tok, modelo)
    tok, modelo = _bert[encoder]
    vectores = []
    with torch.no_grad():
        for i in range(0, len(textos), 8):
            lote = textos[i : i + 8]
            enc = tok(
                lote,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            out = modelo(**enc)
            mask = enc["attention_mask"].unsqueeze(-1)
            suma = (out.last_hidden_state * mask).sum(1)
            den = mask.sum(1).clamp(min=1)
            vectores.append((suma / den).cpu().numpy())
    mat = np.vstack(vectores)
    return _l2(mat)


def _embed_st(textos: list[str], encoder: str) -> np.ndarray:
    if encoder not in _st:
        from sentence_transformers import SentenceTransformer

        _st[encoder] = SentenceTransformer(encoder, device="cpu")
    mat = np.asarray(_st[encoder].encode(textos, convert_to_numpy=True, show_progress_bar=False))
    return _l2(mat)


def _l2(mat: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(mat, axis=1, keepdims=True)
    n = np.maximum(n, 1e-12)
    return mat / n


def guardar(path: Path, vectores: np.ndarray, textos: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, vectores=vectores, textos=np.array(textos, dtype=object))


def cargar(path: Path) -> tuple[np.ndarray, list[str]] | None:
    if not path.exists():
        return None
    data = np.load(path, allow_pickle=True)
    return data["vectores"], data["textos"].tolist()
