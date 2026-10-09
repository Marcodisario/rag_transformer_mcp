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

La corrida final debe ejecutarse con una clave de OpenRouter con saldo:

```bash
python agente.py --preguntas datos/preguntas_agente_dev.jsonl --salida respuestas.jsonl --log experimentos/agente-dev.md
python evaluar/evaluar.py agente --preguntas datos/preguntas_agente_dev.jsonl --respuestas respuestas.jsonl
```

Al cerrar esta versión no había una `OPENROUTER_API_KEY` configurada, por lo que no se inventan resultados del juez ni costos. Después de la corrida, copiar aquí el resumen de `respuestas.jsonl.eval.json` y analizar en particular cualquier pregunta cuyo ruteo o puntaje sea menor al objetivo.

## Parte 3: servidor y agente MCP

`servidor_mcp.py` concentra las seis herramientas en un `FastMCP` oficial con transporte `stdio`. `agente_mcp.py` inicia ese proceso mediante `MCPServerStdio`, ejecuta `tools/list`, entrega las herramientas descubiertas al mismo modelo de la Parte 2 y conserva exactamente el mismo esquema de salida y nivel de logging. El cliente no contiene imports del RAG, código HTTP ni rutas de la API.

### Comparación de benchmarks

| Variante | Ruteo | Context relevance | Faithfulness | Answer relevance | Costo agente | Costo juez |
|---|---:|---:|---:|---:|---:|---:|
| Herramientas locales | pendiente de corrida | pendiente | pendiente | pendiente | pendiente | pendiente |
| Herramientas MCP | pendiente de corrida | pendiente | pendiente | pendiente | pendiente | pendiente |

Completar la tabla únicamente a partir de los dos `.eval.json` y de los totales de los logs. Si los resultados difieren, comparar por pregunta los nombres y argumentos de las herramientas, sus contextos y la cantidad de llamadas al modelo; el transporte por sí solo no cambia los datos del hospital.

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

Pendiente de las dos corridas de agente y sus evaluaciones. El total debe ser la suma del costo informado en ambos logs más el costo del juez de ambos `.eval.json`, contrastada con el dashboard de OpenRouter. No se informa `USD 0` porque todavía no se ejecutaron esas llamadas.
