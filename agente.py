"""Agente con herramientas para consultar documentos y la API del hospital."""

import argparse
import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from openai import AsyncOpenAI

from rag.config import CONFIG
from rag.recuperador import Recuperador

API_BASE_URL = "http://localhost:8765"
MODEL_ID = "deepseek/deepseek-v4-flash-0731"
INPUT_PRICE_PER_MILLION = 0.04
OUTPUT_PRICE_PER_MILLION = 0.64
_recuperador: Recuperador | None = None


def cargar_env_local() -> None:
    """Carga .env sin pisar variables ya exportadas en la terminal."""
    archivo = Path(".env")
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("export "):
            linea = linea[7:].strip()
        clave, separador, valor = linea.partition("=")
        if not separador:
            continue
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if valor:
            os.environ.setdefault(clave.strip(), valor)


def _recuperador_parte_1() -> Recuperador:
    global _recuperador
    if _recuperador is None:
        _recuperador = Recuperador(CONFIG)
    return _recuperador


@function_tool
def buscar_documentos(consulta: str) -> str:
    """Busca en los documentos estables del hospital (horarios, normas, preparación, requisitos y acompañantes). Usala para preguntas respondibles desde protocolos; si la pregunta combina normas con disponibilidad actual, llamá también a la herramienta de API correspondiente. Devuelve los fragmentos originales recuperados."""
    fragmentos = _recuperador_parte_1().buscar(consulta)
    return json.dumps(fragmentos, ensure_ascii=False)


def _consultar_api(ruta: str, parametro: str | None = None, valor: str | None = None) -> str:
    query = urllib.parse.urlencode({parametro: valor}) if parametro else ""
    url = f"{API_BASE_URL}{ruta}" + (f"?{query}" if query else "")
    try:
        with urllib.request.urlopen(url, timeout=10) as respuesta:
            return respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        # La API devuelve opciones válidas en el JSON de error; se las damos al agente
        # para que pueda corregir el nombre solicitado.
        return error.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as error:
        return json.dumps({"error": f"No se pudo consultar la API del hospital: {error}"}, ensure_ascii=False)


@function_tool
def consultar_camas(sector: str) -> str:
    """Consulta las camas disponibles en tiempo real para un sector (por ejemplo, pediatría o terapia intensiva). Usala ante preguntas de disponibilidad o internación; para dudas sobre acompañantes combiná el resultado con buscar_documentos. Devuelve ocupadas, total y libres."""
    return _consultar_api("/camas", "sector", sector)


@function_tool
def consultar_guardia(especialidad: str) -> str:
    """Consulta quién está de guardia hoy y en qué horario para una especialidad. Usala para preguntas sobre profesionales de guardia; no responde turnos programados."""
    return _consultar_api("/guardia", "especialidad", especialidad)


@function_tool
def consultar_turnos(especialidad: str) -> str:
    """Consulta los próximos turnos disponibles de una especialidad. Usala para citas o disponibilidad de turnos; si también preguntan qué documentación traer, combiná con buscar_documentos."""
    return _consultar_api("/turnos", "especialidad", especialidad)


@function_tool
def consultar_farmacia(medicamento: str) -> str:
    """Consulta stock y fecha de reposición de un medicamento. Usala para disponibilidad actual de farmacia; si preguntan requisitos para retirar, combiná con buscar_documentos."""
    return _consultar_api("/farmacia", "medicamento", medicamento)


@function_tool
def consultar_espera() -> str:
    """Consulta los minutos de espera actuales de guardia por nivel de triage. Usala cuando pregunten cuánto se espera; las normas generales del triage se consultan aparte en buscar_documentos."""
    return _consultar_api("/espera")


INSTRUCCIONES = """Sos el asistente del Hospital Provincial Arroyo Claro. Respondé siempre en español, de forma clara, breve y amable.

Usá las herramientas como fuente obligatoria: buscar_documentos para normas y procedimientos; las consultas de API para información dinámica (camas, guardia, turnos, farmacia y espera). Si una pregunta pide las dos clases de datos, llamá a ambas herramientas necesarias. No contestes datos del hospital desde conocimiento general ni inventes información. Basá cada afirmación en los resultados; si falta un dato o una consulta da error, decilo con claridad y no lo adivines. No incluyas afirmaciones médicas que no estén respaldadas por los resultados."""


def _modelo_y_agente() -> Agent:
    cargar_env_local()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit(
            "Falta OPENROUTER_API_KEY. Copiá .envexample a .env y completá esa variable, "
            "o exportala en el entorno."
        )
    cliente = AsyncOpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=float(os.environ.get("OPENROUTER_TIMEOUT") or "120"),
    )
    modelo = OpenAIChatCompletionsModel(
        model=MODEL_ID,
        openai_client=cliente,
    )
    set_tracing_disabled(True)
    return Agent(
        name="Asistente Hospital Arroyo Claro",
        instructions=INSTRUCCIONES,
        model=modelo,
        tools=[
            buscar_documentos,
            consultar_camas,
            consultar_guardia,
            consultar_turnos,
            consultar_farmacia,
            consultar_espera,
        ],
    )


def _texto_salida(valor: Any) -> str:
    if isinstance(valor, str):
        return valor
    try:
        return json.dumps(valor, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(valor)


def _argumentos_tool(item: Any) -> str:
    raw = item.raw_item
    if isinstance(raw, dict):
        return str(raw.get("arguments", "{}"))
    return str(getattr(raw, "arguments", "{}"))


def _datos_modelo(respuestas: list[Any]) -> tuple[list[dict[str, Any]], int, int, float]:
    llamadas = []
    tokens_entrada = 0
    tokens_salida = 0
    costo_estimado = 0.0
    for numero, respuesta in enumerate(respuestas, start=1):
        usage = respuesta.usage
        entrada = int(getattr(usage, "input_tokens", 0) or 0)
        salida = int(getattr(usage, "output_tokens", 0) or 0)
        raw_usage = getattr(respuesta, "raw_usage", None) or {}
        costo_real = raw_usage.get("cost") if isinstance(raw_usage, dict) else None
        costo = (
            float(costo_real)
            if costo_real is not None
            else entrada * INPUT_PRICE_PER_MILLION / 1_000_000
            + salida * OUTPUT_PRICE_PER_MILLION / 1_000_000
        )
        llamadas.append({
            "numero": numero,
            "input_tokens": entrada,
            "output_tokens": salida,
            "total_tokens": entrada + salida,
            "costo_usd": costo,
            "costo_tipo": "reportado por proveedor" if costo_real is not None else "estimado con tarifas de mission.md",
        })
        tokens_entrada += entrada
        tokens_salida += salida
        costo_estimado += costo
    return llamadas, tokens_entrada, tokens_salida, costo_estimado


async def responder(agente: Agent, pregunta: str) -> tuple[str, list[str], list[dict[str, str]], list[dict[str, Any]], int, int, float]:
    resultado = await Runner.run(agente, pregunta)
    llamadas_tools: list[dict[str, str]] = []
    contextos: list[str] = []
    por_call_id: dict[str, dict[str, str]] = {}

    for item in resultado.new_items:
        tipo = getattr(item, "type", "")
        if tipo == "tool_call_item":
            nombre = item.tool_name or "herramienta_desconocida"
            call_id = item.call_id or f"sin-id-{len(por_call_id)}"
            llamada = {"nombre": nombre, "argumentos": _argumentos_tool(item), "resultado": ""}
            llamadas_tools.append(llamada)
            por_call_id[call_id] = llamada
        elif tipo == "tool_call_output_item":
            call_id = item.call_id
            info = por_call_id.get(call_id, {"nombre": "herramienta_desconocida", "argumentos": "{}", "resultado": ""})
            salida = _texto_salida(item.output)
            contextos.append(salida)
            info["resultado"] = salida

    usos, tokens_in, tokens_out, costo = _datos_modelo(resultado.raw_responses)
    return str(resultado.final_output or ""), contextos, llamadas_tools, usos, tokens_in, tokens_out, costo


def _agregar_pregunta_log(
    lineas: list[str], pregunta: dict[str, Any], respuesta: str,
    herramientas: list[dict[str, str]], usos: list[dict[str, Any]],
) -> None:
    lineas.extend([f"## {pregunta['id']}", "", f"**Pregunta:** {pregunta['pregunta']}", ""])
    lineas.append("### Llamadas a herramientas")
    if not herramientas:
        lineas.extend(["", "El modelo no llamó herramientas.", ""])
    else:
        for llamada in herramientas:
            lineas.extend([
                "",
                f"- **{llamada['nombre']}**",
                f"  - Argumentos: `{llamada['argumentos']}`",
                f"  - Resultado: `{llamada['resultado']}`",
            ])
        lineas.append("")
    lineas.extend(["### Llamadas al modelo", ""])
    if not usos:
        lineas.extend(["No se recibió detalle de usage del proveedor.", ""])
    else:
        for uso in usos:
            lineas.append(
                f"- Llamada {uso['numero']}: {uso['input_tokens']} tokens de entrada, "
                f"{uso['output_tokens']} de salida, {uso['total_tokens']} total; "
                f"costo USD {uso['costo_usd']:.8f} ({uso['costo_tipo']})."
            )
        lineas.append("")
    lineas.extend(["### Respuesta", "", respuesta, ""])


async def ejecutar(preguntas_path: str, salida_path: str, log_path: str) -> dict[str, Any]:
    agente = _modelo_y_agente()
    preguntas = [
        json.loads(linea)
        for linea in Path(preguntas_path).read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
    filas = []
    logs = [
        "# Log de benchmark — agente (Parte 2)",
        "",
        f"- Fecha UTC: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        f"- Modelo: {MODEL_ID}",
        f"- API hospital: {API_BASE_URL}",
        "- Tarifas estimadas del agente: USD 0,04 / millón de tokens de entrada y USD 0,64 / millón de salida, según mission.md.",
        "- El costo del juez de evaluar.py se informa aparte en su `.eval.json`.",
        "",
    ]
    total_entrada = total_salida = 0
    costo_total = 0.0

    for pregunta in preguntas:
        respuesta, contextos, llamadas_tools, usos, tokens_in, tokens_out, costo = await responder(
            agente, pregunta["pregunta"]
        )
        filas.append({
            "id": pregunta["id"],
            "respuesta": respuesta,
            "contextos": contextos,
            "herramientas": [llamada["nombre"] for llamada in llamadas_tools],
        })
        _agregar_pregunta_log(logs, pregunta, respuesta, llamadas_tools, usos)
        total_entrada += tokens_in
        total_salida += tokens_out
        costo_total += costo

    destino = Path(salida_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        "".join(json.dumps(fila, ensure_ascii=False) + "\n" for fila in filas),
        encoding="utf-8",
    )
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    logs.extend([
        "## Totales", "",
        f"- Preguntas: {len(filas)}",
        f"- Tokens de entrada: {total_entrada}",
        f"- Tokens de salida: {total_salida}",
        f"- Costo estimado del agente: USD {costo_total:.8f}",
        "",
    ])
    log.write_text("\n".join(logs), encoding="utf-8")
    return {"preguntas": len(filas), "tokens_entrada": total_entrada,
            "tokens_salida": total_salida, "costo_estimado_usd": round(costo_total, 8),
            "salida": str(destino), "log": str(log)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preguntas", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument(
        "--log",
        help="Ruta del log Markdown. Por defecto crea experimentos/agente-<fecha>.md.",
    )
    args = parser.parse_args()
    log_path = args.log or f"experimentos/agente-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    print(json.dumps(asyncio.run(ejecutar(args.preguntas, args.salida, log_path)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
