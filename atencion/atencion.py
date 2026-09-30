# softmax(M) softmax por fila (ultimo eje)
import numpy as np

def softmax(M):
    m_max= np.max(M,axis=-1,keepdims=True)
    e_m = np.exp(M-m_max)
    return e_m/ np.sum(e_m, axis=-1, keepdims=True)