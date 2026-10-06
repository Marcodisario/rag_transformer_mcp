# Informe: recuperador vectorial (Parte 1)

## Método

Se compararon los tres encoders requeridos sobre los mismos fragmentos por secciones Markdown, con título y sección antepuestos únicamente al texto usado para embedding. El texto devuelto conserva el contenido original para que las evidencias sigan siendo subcadenas. Se midió con el evaluador de recuperación de la cátedra sobre las 20 preguntas de `dev`.

## Resultados

| Encoder | Chunking | k | Umbral | Context relevance | Recall | Precisión | MRR |
|---|---|---:|---:|---:|---:|---:|---:|
| BERT español (mean pooling) | Secciones Markdown + metadatos | 3 | 0,0 | 0,3250 | 0,6500 | 0,2167 | 0,5625 |
| multilingual-e5-small | Secciones Markdown + metadatos | 3 | 0,0 | 0,5000 | 1,0000 | 0,3333 | 0,9167 |
| paraphrase-multilingual-MiniLM-L12-v2 | Secciones Markdown + metadatos | 3 | 0,0 | 0,5000 | 1,0000 | 0,3333 | 0,9500 |
| paraphrase-multilingual-MiniLM-L12-v2 | Secciones Markdown + metadatos | 4 | 0,0 | 0,4000 | 1,0000 | 0,2500 | 0,9500 |
| **paraphrase-multilingual-MiniLM-L12-v2** | **Secciones Markdown + metadatos** | **2** | **0,0** | **0,6667** | **1,0000** | **0,5000** | **0,9500** |
| **paraphrase-multilingual-MiniLM-L12-v2** | **Secciones Markdown + metadatos** | **2** | **0,3** | **0,6667** | **1,0000** | **0,5000** | **0,9500** |

Los resultados de `k=2` con umbral 0,0 y 0,3 coinciden en `dev`. Se fija 0,3 como umbral operativo; el umbral no alteró la recuperación en estas preguntas. MiniLM gana a la línea de base BERT en context relevance por 0,3417 puntos absolutos (0,6667 frente a 0,3250), mantiene recall completo y sube la precisión de 0,2167 a 0,5. Frente a MiniLM con `k=3`, `k=2` conserva recall y mejora context relevance en 0,1667 al reducir fragmentos irrelevantes.

## Configuración entregada

`recuperar.py` usa la configuración fija de `rag/config.py`: MiniLM multilingüe, chunking por secciones con metadatos, `top_k=2` y umbral de coseno `0.3`. El CLI mantiene el contrato de entrada/salida JSONL indicado en la consigna.

## Evidencia de evaluación

Los `.eval.json` de cada experimento están en `experimentos/`. La evaluación final se basa en las corridas ya guardadas. Se intentó repetir la corrida desde este entorno, pero Windows bloqueó el inicio de `python.exe`; por eso no se generó una nueva corrida durante el cierre.
