"""Agente cliente del servidor MCP del Hospital Arroyo Claro."""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

MODEL_ID = "deepseek/deepseek-v4-flash-0731"
INPUT_PRICE_PER_MILLION = 0.04
OUTPUT_PRICE_PER_MILLION = 0.64
ROOT = Path(__file__).resolve().parent
SERVIDOR = ROOT / "servidor_mcp.py"

INSTRUCCIONES = """Sos el asistente del Hospital Provincial Arroyo Claro. Responde siempre en espanol, de forma clara, breve y amable.

Usa las herramientas MCP como fuente obligatoria: buscar_documentos para normas y procedimientos; las consultas de API para informacion dinamica (camas, guardia, turnos, farmacia y espera). Si una pregunta pide ambas clases de datos, llama a todas las herramientas necesarias. No contestes datos del hospital desde conocimiento general ni inventes informacion. Basa cada afirmacion en los resultados; si falta un dato o una consulta da error, decilo con claridad."""


def cargar_env_local() -> None:
    """Carga el .env del proyecto sin pisar variables ya exportadas."""
    archivo = ROOT / ".env"
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


def _modelo() -> OpenAIChatCompletionsModel:
    cargar_env_local()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit(
            "Falta OPENROUTER_API_KEY. Copia .envexample a .env y completa esa variable, "
            "o exportala en el entorno."
        )
    cliente = AsyncOpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=float(os.environ.get("OPENROUTER_TIMEOUT") or "120"),
    )
    set_tracing_disabled(True)
    return OpenAIChatCompletionsModel(model=MODEL_ID, openai_client=cliente)


def _texto(valor: Any) -> str:
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
    llamadas: list[dict[str, Any]] = []
    tokens_entrada = tokens_salida = 0
    costo_total = 0.0
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
        llamadas.append(
            {
                "numero": numero,
                "input_tokens": entrada,
                "output_tokens": salida,
                "total_tokens": entrada + salida,
                "costo_usd": costo,
                "costo_tipo": (
                    "reportado por proveedor"
                    if costo_real is not None
                    else "estimado con tarifas de mission.md"
                ),
            }
        )
        tokens_entrada += entrada
        tokens_salida += salida
        costo_total += costo
    return llamadas, tokens_entrada, tokens_salida, costo_total


async def responder(
    agente: Agent, pregunta: str
) -> tuple[str, list[str], list[dict[str, str]], list[dict[str, Any]], int, int, float]:
    resultado = await Runner.run(agente, pregunta)
    llamadas_tools: list[dict[str, str]] = []
    contextos: list[str] = []
    por_call_id: dict[str, dict[str, str]] = {}

    for item in resultado.new_items:
        tipo = getattr(item, "type", "")
        if tipo == "tool_call_item":
            nombre = item.tool_name or "herramienta_desconocida"
            call_id = item.call_id or f"sin-id-{len(por_call_id)}"
            llamada = {
                "nombre": nombre,
                "argumentos": _argumentos_tool(item),
                "resultado": "",
            }
            llamadas_tools.append(llamada)
            por_call_id[call_id] = llamada
        elif tipo == "tool_call_output_item":
            salida = _texto(item.output)
            contextos.append(salida)
            info = por_call_id.get(item.call_id)
            if info is not None:
                info["resultado"] = salida

    usos, tokens_in, tokens_out, costo = _datos_modelo(resultado.raw_responses)
    return (
        str(resultado.final_output or ""),
        contextos,
        llamadas_tools,
        usos,
        tokens_in,
        tokens_out,
        costo,
    )


def _agregar_pregunta_log(
    lineas: list[str],
    pregunta: dict[str, Any],
    respuesta: str,
    herramientas: list[dict[str, str]],
    usos: list[dict[str, Any]],
) -> None:
    lineas.extend([f"## {pregunta['id']}", "", f"**Pregunta:** {pregunta['pregunta']}", ""])
    lineas.extend(["### Llamadas a herramientas MCP", ""])
    if not herramientas:
        lineas.extend(["El modelo no llamo herramientas.", ""])
    for llamada in herramientas:
        lineas.extend(
            [
                f"- **{llamada['nombre']}**",
                f"  - Argumentos: `{llamada['argumentos']}`",
                f"  - Resultado: `{llamada['resultado']}`",
                "",
            ]
        )
    lineas.extend(["### Llamadas al modelo", ""])
    if not usos:
        lineas.extend(["No se recibio detalle de usage del proveedor.", ""])
    for uso in usos:
        lineas.append(
            f"- Llamada {uso['numero']}: {uso['input_tokens']} tokens de entrada, "
            f"{uso['output_tokens']} de salida, {uso['total_tokens']} total; "
            f"costo USD {uso['costo_usd']:.8f} ({uso['costo_tipo']})."
        )
    lineas.extend(["", "### Respuesta", "", respuesta, ""])


async def ejecutar(preguntas_path: str, salida_path: str, log_path: str) -> dict[str, Any]:
    preguntas = [
        json.loads(linea)
        for linea in Path(preguntas_path).read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
    servidor = MCPServerStdio(
        name="Hospital Arroyo Claro",
        params={"command": sys.executable, "args": [str(SERVIDOR)], "cwd": str(ROOT)},
        cache_tools_list=True,
        client_session_timeout_seconds=120,
    )
    filas: list[dict[str, Any]] = []
    logs = [
        "# Log de benchmark — agente MCP (Parte 3)",
        "",
        f"- Fecha UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Modelo: {MODEL_ID}",
        "- Transporte MCP: stdio",
        "",
    ]
    total_entrada = total_salida = 0
    costo_total = 0.0

    async with servidor:
        descubiertas = [tool.name for tool in await servidor.list_tools()]
        logs.extend([f"- Herramientas descubiertas con tools/list: {', '.join(descubiertas)}", ""])
        agente = Agent(
            name="Asistente Hospital Arroyo Claro MCP",
            instructions=INSTRUCCIONES,
            model=_modelo(),
            mcp_servers=[servidor],
        )
        for pregunta in preguntas:
            respuesta, contextos, llamadas, usos, tokens_in, tokens_out, costo = await responder(
                agente, pregunta["pregunta"]
            )
            filas.append(
                {
                    "id": pregunta["id"],
                    "respuesta": respuesta,
                    "contextos": contextos,
                    "herramientas": [llamada["nombre"] for llamada in llamadas],
                }
            )
            _agregar_pregunta_log(logs, pregunta, respuesta, llamadas, usos)
            total_entrada += tokens_in
            total_salida += tokens_out
            costo_total += costo

    destino = Path(salida_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        "".join(json.dumps(fila, ensure_ascii=False) + "\n" for fila in filas),
        encoding="utf-8",
    )
    logs.extend(
        [
            "## Totales",
            "",
            f"- Preguntas: {len(filas)}",
            f"- Tokens de entrada: {total_entrada}",
            f"- Tokens de salida: {total_salida}",
            f"- Costo estimado del agente: USD {costo_total:.8f}",
            "",
        ]
    )
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(logs), encoding="utf-8")
    return {
        "preguntas": len(filas),
        "herramientas_descubiertas": descubiertas,
        "tokens_entrada": total_entrada,
        "tokens_salida": total_salida,
        "costo_estimado_usd": round(costo_total, 8),
        "salida": str(destino),
        "log": str(log),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preguntas", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument(
        "--log",
        help="Ruta del log Markdown. Por defecto crea experimentos/agente-mcp-<fecha>.md.",
    )
    args = parser.parse_args()
    log_path = args.log or f"experimentos/agente-mcp-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    print(
        json.dumps(
            asyncio.run(ejecutar(args.preguntas, args.salida, log_path)),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
