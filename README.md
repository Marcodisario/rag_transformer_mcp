# Hospital Arroyo Claro — Parte 2

## Preparación

1. Instalar las dependencias del proyecto con `pip install -r requirements.txt`.
2. Copiar `.envexample` a `.env` y completar `OPENROUTER_API_KEY`. El modelo requerido queda fijado en el código. `OPENROUTER_BASE_URL` y `OPENROUTER_TIMEOUT` son opcionales.
3. En una terminal, iniciar la API: `python api/servidor.py`.

## Correr el agente y evaluar

En otra terminal, desde la raíz del repositorio:

```bash
python agente.py --preguntas datos/preguntas_agente_dev.jsonl --salida experimentos/respuestas_agente_dev.jsonl
python evaluar/evaluar.py agente --preguntas datos/preguntas_agente_dev.jsonl --respuestas experimentos/respuestas_agente_dev.jsonl
```

El primer comando guarda respuestas JSONL y crea automáticamente un log `.md` en `experimentos/` con las herramientas, argumentos, resultados, respuestas y usage/costo estimado de cada llamada al modelo. También se puede pasar una ubicación explícita con `--log ruta/al/log.md`.

El segundo comando crea el `.eval.json` con ruteo y métricas del juez. El costo del juez se reporta ahí; el log del agente estima el costo de OpenRouter con las tarifas que figuran en `mission.md`.
