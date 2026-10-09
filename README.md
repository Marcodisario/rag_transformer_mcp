# Hospital Arroyo Claro — RAG, agentes, MCP y atención

## Preparación

Se requiere Python 3.10 o posterior.

```bash
python -m venv .venv
```

En Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .envexample .env
```

En macOS o Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .envexample .env
```

Completar `OPENROUTER_API_KEY` en `.env`. En otra terminal, con el mismo entorno activado, iniciar la API:

```bash
python api/servidor.py
```

## Parte 1: recuperación

```bash
python recuperar.py --preguntas datos/preguntas_recuperacion_dev.jsonl --salida experimentos/resultados_recuperacion.jsonl
python evaluar/evaluar.py recuperacion --preguntas datos/preguntas_recuperacion_dev.jsonl --resultados experimentos/resultados_recuperacion.jsonl
```

La configuración entregada está fijada en `rag/config.py`. Los resultados comparativos ya medidos están en `experimentos/*.eval.json`.

## Parte 2: agente con herramientas locales

```bash
python agente.py --preguntas datos/preguntas_agente_dev.jsonl --salida respuestas.jsonl --log experimentos/agente-dev.md
python evaluar/evaluar.py agente --preguntas datos/preguntas_agente_dev.jsonl --respuestas respuestas.jsonl
```

## Parte 3: agente MCP

`servidor_mcp.py` publica las seis herramientas con FastMCP por `stdio`. El cliente lo inicia y descubre automáticamente:

```bash
python agente_mcp.py --preguntas datos/preguntas_agente_dev.jsonl --salida respuestas_mcp.jsonl --log experimentos/agente-mcp-dev.md
python evaluar/evaluar.py agente --preguntas datos/preguntas_agente_dev.jsonl --respuestas respuestas_mcp.jsonl
```

Para las capturas manuales:

```bash
npx @modelcontextprotocol/inspector python servidor_mcp.py
```

La lista de llamadas y nombres sugeridos está en `experimentos/inspector/README.md`.

## Parte 4: atención NumPy

```bash
python atencion/test_atencion.py atencion.py
```

## Alternativa con Docker en Windows

Si Windows Application Control bloquea las DLL de PyTorch dentro de `.venv`, no se debe desactivar esa protección. Con Docker Desktop iniciado, construir una vez la imagen Linux:

```cmd
docker build -t rag-transformer-mcp .
```

Luego se puede ejecutar cada benchmark montando el repositorio actual. El volumen `rag-hf-cache` conserva el modelo descargado entre corridas:

```cmd
docker run --rm --env-file .env -v "%cd%:/app" -v rag-hf-cache:/root/.cache/huggingface -w /app rag-transformer-mcp sh -lc "python api/servidor.py & python agente.py --preguntas datos/preguntas_agente_dev.jsonl --salida respuestas.jsonl --log experimentos/agente-dev.md"
```

El archivo `.dockerignore` permite copiar a la imagen solamente `Dockerfile` y `requirements.txt`; `.env` no forma parte de la imagen.

## Prueba rápida sin credenciales

```bash
python -m unittest tests/test_entrega.py -v
```

## Archivos que deben guardarse antes de entregar

Los benchmarks de agentes crean los JSONL y logs, y el evaluador crea los `.eval.json`. Deben versionarse junto con las capturas de Inspector. `.env`, `.venv/` y `.cache/` están excluidos por contener secretos o artefactos regenerables.
