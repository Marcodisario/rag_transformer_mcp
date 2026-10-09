# Informe — RAG, agente, MCP y atención

## Parte 1: recuperador vectorial

### Método

Se compararon los tres encoders requeridos sobre los mismos fragmentos por secciones Markdown, con título y sección antepuestos únicamente al texto usado para embedding. El texto devuelto conserva el contenido original para que las evidencias sigan siendo subcadenas. Se midió con el evaluador de recuperación de la cátedra sobre las 20 preguntas de `dev`.

### Resultados

| Encoder | Chunking | k | Umbral | Context relevance | Recall | Precisión | MRR |
|---|---|---:|---:|---:|---:|---:|---:|
| BERT español (mean pooling) | Secciones Markdown + metadatos | 3 | 0,0 | 0,3250 | 0,6500 | 0,2167 | 0,5625 |
| multilingual-e5-small | Secciones Markdown + metadatos | 3 | 0,0 | 0,5000 | 1,0000 | 0,3333 | 0,9167 |
| paraphrase-multilingual-MiniLM-L12-v2 | Secciones Markdown + metadatos | 3 | 0,0 | 0,5000 | 1,0000 | 0,3333 | 0,9500 |
| paraphrase-multilingual-MiniLM-L12-v2 | Secciones Markdown + metadatos | 4 | 0,0 | 0,4000 | 1,0000 | 0,2500 | 0,9500 |
| **paraphrase-multilingual-MiniLM-L12-v2** | **Secciones Markdown + metadatos** | **2** | **0,0** | **0,6667** | **1,0000** | **0,5000** | **0,9500** |
| **paraphrase-multilingual-MiniLM-L12-v2** | **Secciones Markdown + metadatos** | **2** | **0,3** | **0,6667** | **1,0000** | **0,5000** | **0,9500** |

Los resultados de `k=2` con umbral 0,0 y 0,3 coinciden en `dev`. Se fija 0,3 como umbral operativo; el umbral no alteró la recuperación en estas preguntas. MiniLM gana a la línea de base BERT en context relevance por 0,3417 puntos absolutos (0,6667 frente a 0,3250), mantiene recall completo y sube la precisión de 0,2167 a 0,5. Frente a MiniLM con `k=3`, `k=2` conserva recall y mejora context relevance en 0,1667 al reducir fragmentos irrelevantes.

### Configuración entregada

`recuperar.py` usa la configuración fija de `rag/config.py`: MiniLM multilingüe, chunking por secciones con metadatos, `top_k=2` y umbral de coseno `0.3`. El CLI mantiene el contrato de entrada/salida JSONL indicado en la consigna.

### Evidencia de evaluación

Los `.eval.json` de cada experimento están en `experimentos/`. La evaluación final se basa en esas corridas guardadas y reproducibles con `experimentos/correr.py`.

## Parte 2: agente con herramientas locales

El agente usa `deepseek/deepseek-v4-flash-0731` mediante OpenRouter y el SDK de agentes de OpenAI. Expone las seis herramientas con los nombres exigidos. Las descripciones distinguen documentos estables de estado dinámico y señalan explícitamente cuándo deben combinarse ambas fuentes. Cada resultado de herramienta se conserva como texto en `contextos` y el log registra pregunta, argumentos, resultado, respuesta, tokens y costo por llamada.

### Benchmark

La corrida final se ejecutó sobre las 12 preguntas `dev` y se evaluó con el juez fijado por la cátedra:

```bash
python agente.py --preguntas datos/preguntas_agente_dev.jsonl --salida respuestas.jsonl --log experimentos/agente-dev.md
python evaluar/evaluar.py agente --preguntas datos/preguntas_agente_dev.jsonl --respuestas respuestas.jsonl
```

El resultado fue ruteo `1,0`, context relevance `4,75`, faithfulness `5,0` y answer relevance `5,0`. El agente consumió 33.237 tokens de entrada y 3.024 de salida, con costo estimado de USD 0,00326484. El juez costó USD 0,02010.

No hubo fallas de ruteo ni puntuaciones menores a 4. Los casos con context relevance 4 fueron A02, A11 y A12: en A02 se recuperó toda la preparación de colonoscopía junto con un fragmento breve sobre otro estudio; en A11 apareció inicialmente ruido sobre internación y convenios, pero el agente reformuló la búsqueda y obtuvo la documentación correcta; en A12 se recuperaron los requisitos generales, aunque faltaron detalles menores de identificación. En los tres casos, la respuesta final fue completamente fiel y relevante.

## Parte 3: servidor y agente MCP

`servidor_mcp.py` concentra las seis herramientas en un `FastMCP` oficial con transporte `stdio`. `agente_mcp.py` inicia ese proceso mediante `MCPServerStdio`, ejecuta `tools/list`, entrega las herramientas descubiertas al mismo modelo de la Parte 2 y conserva exactamente el mismo esquema de salida y nivel de logging. El cliente no contiene imports del RAG, código HTTP ni rutas de la API.

### Comparación de benchmarks

| Variante | Ruteo | Context relevance | Faithfulness | Answer relevance | Costo agente | Costo juez |
|---|---:|---:|---:|---:|---:|---:|
| Herramientas locales | 1,000 | 4,750 | 5,000 | 5,000 | USD 0,00326484 | USD 0,02010 |
| Herramientas MCP | 1,000 | 4,583 | 5,000 | 4,750 | USD 0,00324352 | USD 0,01887 |

Ambas variantes alcanzaron ruteo perfecto y superaron 4 en las tres métricas. El agente MCP consumió 27.408 tokens de entrada y 3.355 de salida. Costó USD 0,00002132 menos como agente y USD 0,00123 menos en el juez, pero obtuvo 0,167 puntos menos de context relevance y 0,25 menos de answer relevance.

La diferencia no provino de herramientas faltantes: el log MCP confirma que `tools/list` descubrió las seis y el ruteo fue perfecto. Se concentró en A11 y A12. En A11, la búsqueda documental MCP devolvió normas de internación y convenios en vez de los requisitos para una primera consulta; el modelo local detectó ese ruido y realizó una segunda búsqueda, mientras que el MCP se detuvo después de la primera. En A12, la consulta documental MCP recuperó información sobre una curva de glucosa y medicamentos de alto costo, pero no los requisitos generales de retiro. El agente se mantuvo fiel a esos contextos —faithfulness permaneció en 5—, aunque respondió de manera incompleta. Esto muestra variación en los argumentos y reintentos elegidos por el modelo, no una diferencia funcional del transporte MCP.

La comprobación manual con MCP Inspector está documentada en `experimentos/inspector/README.md`. Las seis capturas deben guardarse en esa carpeta antes de entregar.

## Parte 4: atención en NumPy

La implementación final está en `atencion.py` y usa únicamente NumPy. Se verificaron `softmax`, atención escalada, autoatención con y sin máscara causal, multicabeza y layer normalization contra el archivo original de la cátedra:

```text
Ran 14 tests
OK
```

También se agregó `tests/test_entrega.py`, que comprueba sin red que el servidor declara exactamente las seis herramientas, que el cliente MCP no consulta las fuentes directamente y que los 14 tests oficiales pasan contra el archivo raíz.

## Parte 5: bloque de transformer a mano

Esta parte no se completa digitalmente: la consigna exige cálculos manuscritos, la justificación de cada operación y hojas escaneadas. Antes de entregar hay que agregar los escaneos y las respuestas a las cinco preguntas en `a_mano/`, sin reemplazar `a_mano/ejercicio.md`.

## Costo total

Las dos corridas de agente costaron en conjunto USD 0,00650836 y las dos evaluaciones con juez USD 0,03897. El costo total calculado de las partes 2 y 3 fue **USD 0,04547836**. Antes de entregar se debe contrastar ese valor con el dashboard de actividad de OpenRouter; una diferencia pequeña puede deberse al redondeo o a llamadas de prueba realizadas con la misma clave.
