"""Servidor MCP stdio con las seis herramientas del Hospital Arroyo Claro."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

from rag.config import CONFIG
from rag.recuperador import Recuperador

API_BASE_URL = os.environ.get("HOSPITAL_API_URL", "http://localhost:8765")

mcp = FastMCP("Hospital Arroyo Claro")
_recuperador: Recuperador | None = None


def _recuperador_parte_1() -> Recuperador:
    global _recuperador
    if _recuperador is None:
        _recuperador = Recuperador(CONFIG)
    return _recuperador


def _consultar_api(ruta: str, parametro: str | None = None, valor: str | None = None) -> str:
    query = urllib.parse.urlencode({parametro: valor}) if parametro else ""
    url = f"{API_BASE_URL}{ruta}" + (f"?{query}" if query else "")
    try:
        with urllib.request.urlopen(url, timeout=10) as respuesta:
            return respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        # La API incluye las opciones validas en el cuerpo del error. El agente puede
        # usar ese dato para explicar el problema sin inventar una respuesta.
        return error.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as error:
        return json.dumps(
            {"error": f"No se pudo consultar la API del hospital: {error}"},
            ensure_ascii=False,
        )


@mcp.tool()
def buscar_documentos(consulta: str) -> str:
    """Busca normas, horarios, preparaciones, requisitos y reglas de acompanamiento en los documentos estables del hospital. Usala tambien junto con una consulta dinamica cuando la pregunta combine ambos tipos de informacion."""
    fragmentos = _recuperador_parte_1().buscar(consulta)
    return json.dumps(fragmentos, ensure_ascii=False)


@mcp.tool()
def consultar_camas(sector: str) -> str:
    """Consulta las camas disponibles ahora en un sector. Usala para disponibilidad o internacion; si preguntan por acompanantes, llama tambien a buscar_documentos."""
    return _consultar_api("/camas", "sector", sector)


@mcp.tool()
def consultar_guardia(especialidad: str) -> str:
    """Consulta quien esta de guardia hoy y su horario para una especialidad. No devuelve turnos programados."""
    return _consultar_api("/guardia", "especialidad", especialidad)


@mcp.tool()
def consultar_turnos(especialidad: str) -> str:
    """Consulta los proximos turnos disponibles para una especialidad. Si preguntan que documentacion llevar, llama tambien a buscar_documentos."""
    return _consultar_api("/turnos", "especialidad", especialidad)


@mcp.tool()
def consultar_farmacia(medicamento: str) -> str:
    """Consulta stock actual y fecha de reposicion de un medicamento. Si preguntan requisitos para retirarlo, llama tambien a buscar_documentos."""
    return _consultar_api("/farmacia", "medicamento", medicamento)


@mcp.tool()
def consultar_espera() -> str:
    """Consulta los minutos de espera actuales de guardia para cada nivel de triage."""
    return _consultar_api("/espera")


if __name__ == "__main__":
    # En stdio no se debe imprimir nada en stdout: ese canal pertenece al protocolo.
    mcp.run(transport="stdio")
