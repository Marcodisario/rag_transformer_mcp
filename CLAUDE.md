# Guía de trabajo del repositorio

- No modificar `evaluar/evaluar.py`, `api/`, `datos/` ni `atencion/test_atencion.py`.
- Mantener los contratos CLI y JSONL de `mission.md`.
- Toda afirmación del agente debe estar respaldada por el texto guardado en `contextos`.
- Las herramientas MCP viven en `servidor_mcp.py`; `agente_mcp.py` solo actúa como cliente.
- Antes de entregar, ejecutar los tests de atención, el benchmark de recuperación y ambos benchmarks de agente.
- No versionar `.env`, `.venv/` ni `.cache/`. Sí versionar respuestas, evaluaciones, logs y capturas finales de `experimentos/`.
