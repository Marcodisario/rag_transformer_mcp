"""Implementacion NumPy de atencion escalada para la Parte 4."""

import numpy as np


def softmax(M):
    """Calcula softmax estable sobre el ultimo eje."""
    desplazada = M - np.max(M, axis=-1, keepdims=True)
    exponenciales = np.exp(desplazada)
    return exponenciales / np.sum(exponenciales, axis=-1, keepdims=True)


def atencion(Q, K, V, mascara=False):
    """Devuelve (salida, pesos) de la atencion escalada por producto punto."""
    puntajes = Q @ K.T / np.sqrt(K.shape[-1])
    if mascara:
        causal = np.triu(np.ones(puntajes.shape, dtype=bool), k=1)
        puntajes = np.where(causal, -np.inf, puntajes)
    pesos = softmax(puntajes)
    return pesos @ V, pesos


def autoatencion(X, Wq, Wk, Wv, mascara=False):
    """Proyecta una entrada a Q, K y V y aplica atencion."""
    return atencion(X @ Wq, X @ Wk, X @ Wv, mascara=mascara)


def multicabeza(X, cabezas, Wo, mascara=False):
    """Concatena las salidas de las cabezas y aplica la proyeccion final."""
    salidas = [autoatencion(X, Wq, Wk, Wv, mascara)[0] for Wq, Wk, Wv in cabezas]
    return np.concatenate(salidas, axis=-1) @ Wo


def layer_norm(x, eps=1e-5):
    """Normaliza cada fila de forma independiente."""
    media = np.mean(x, axis=-1, keepdims=True)
    varianza = np.var(x, axis=-1, keepdims=True)
    return (x - media) / np.sqrt(varianza + eps)
