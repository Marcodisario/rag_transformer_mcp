# softmax(M) softmax por fila (ultimo eje)
import numpy as np

def softmax(M):
    m_max= np.max(M,axis=-1,keepdims=True)
    e_m = np.exp(M-m_max)
    return e_m/ np.sum(e_m, axis=-1, keepdims=True)

def atencion(Q, K, V, mascara=False):
    """
    Atención escalada por producto punto.

    Parámetros:
        Q : Queries  (n_q, d_k)
        K : Keys     (n_k, d_k)
        V : Values   (n_k, d_v)
        mascara : si True aplica máscara causal

    Retorna:
        salida : A @ V
        A      : matriz de atención

    Fórmula:
        A = softmax(Q K^T / sqrt(d_k))
        salida = A V
    """

    d_k = K.shape[-1]

    # Similaridad entre queries y keys
    scores = Q @ K.T / np.sqrt(d_k)

    if mascara:
        # Máscara causal:
        # impide mirar posiciones futuras.
        n = scores.shape[0]
        mask = np.triu(np.ones((n, n)), k=1)
        scores = np.where(mask, -1e9, scores)

    # Pesos de atención
    A = softmax(scores)

    # Combinación ponderada de los valores
    salida = A @ V

    return salida, A


def autoatencion(X, Wq, Wk, Wv, mascara=False):
    """
    Self-Attention.

    A partir de la misma entrada X genera:
        Q = X Wq
        K = X Wk
        V = X Wv

    Luego aplica atención estándar.
    """

    Q = X @ Wq
    K = X @ Wk
    V = X @ Wv

    return atencion(Q, K, V, mascara)


def multicabeza(X, cabezas, Wo, mascara=False):
    """
    Multi-Head Attention.

    Parámetros:
        X : entrada (n, d_model)

        cabezas :
            lista de tuplas (Wq, Wk, Wv)

        Wo :
            matriz de proyección final

    Proceso:
        1. Cada cabeza calcula su propia atención.
        2. Se concatenan las salidas.
        3. Se proyectan con Wo.

    Retorna:
        salida final
    """

    salidas = []

    for Wq, Wk, Wv in cabezas:
        salida_cabeza, _ = autoatencion(
            X, Wq, Wk, Wv, mascara
        )
        salidas.append(salida_cabeza)

    # Concatenar por columnas
    H = np.concatenate(salidas, axis=-1)

    # Proyección final
    salida = H @ Wo

    return salida


def layer_norm(x, eps=1e-5):
    """
    Layer Normalization.

    Normaliza cada fila independientemente:
        media = 0
        varianza = 1

    Parámetros:
        x : (n, d)

    Retorna:
        tensor normalizado
    """

    media = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)

    return (x - media) / np.sqrt(var + eps)