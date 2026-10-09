# Especificación de la solución

## Objetivo

Construir el asistente del Hospital Arroyo Claro con una fuente documental estable y una API dinámica, primero mediante herramientas locales y luego mediante MCP, junto con las implementaciones NumPy pedidas por la cátedra.

## Contratos verificables

- `recuperar.py` recibe preguntas JSONL y devuelve `id` más `fragmentos` ordenados.
- `agente.py` devuelve `id`, `respuesta`, `contextos` y `herramientas`, y genera un log Markdown con argumentos, resultados, tokens y costo.
- `servidor_mcp.py` publica exactamente seis herramientas por transporte `stdio`.
- `agente_mcp.py` descubre esas herramientas con MCP y no consulta directamente ni el corpus ni la API.
- `atencion.py` depende únicamente de NumPy y pasa sin cambios los 14 tests de la cátedra.

## Decisiones

- Recuperación: MiniLM multilingüe, secciones Markdown con metadatos, `top_k=2` y coseno mínimo `0.3`.
- Agentes: `deepseek/deepseek-v4-flash-0731` mediante OpenRouter y OpenAI Agents SDK.
- MCP: SDK oficial `mcp` 1.x, `FastMCP` en el servidor y `MCPServerStdio` en el cliente.
- Las herramientas devuelven texto JSON para que el mismo contenido pueda guardarse sin pérdida en `contextos` y en los logs.

## Casos de aceptación

1. La recuperación final supera claramente la línea base BERT según los `.eval.json` guardados.
2. El agente local usa la herramienta o combinación esperada en cada pregunta `dev`.
3. El cliente MCP enumera las seis herramientas y produce el mismo esquema JSONL que el agente local.
4. Las seis herramientas se pueden invocar desde MCP Inspector y quedan documentadas con capturas.
5. `python atencion/test_atencion.py atencion.py` informa 14 tests exitosos.

## Datos que requieren credenciales o intervención manual

- Los benchmarks de agentes y el juez requieren `OPENROUTER_API_KEY` con saldo.
- Las capturas de MCP Inspector requieren abrir su interfaz y guardarlas en `experimentos/inspector/`.
- La Parte 5 se entrega escrita a mano y escaneada, tal como exige la consigna.
