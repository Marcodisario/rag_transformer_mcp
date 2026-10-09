"""Pruebas rápidas que no requieren red, modelos descargados ni una API key."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "buscar_documentos",
    "consultar_camas",
    "consultar_guardia",
    "consultar_turnos",
    "consultar_farmacia",
    "consultar_espera",
}


class TestEntrega(unittest.TestCase):
    def test_servidor_publica_las_seis_herramientas(self):
        arbol = ast.parse((ROOT / "servidor_mcp.py").read_text(encoding="utf-8"))
        publicadas = set()
        for nodo in arbol.body:
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorador in nodo.decorator_list:
                if (
                    isinstance(decorador, ast.Call)
                    and isinstance(decorador.func, ast.Attribute)
                    and isinstance(decorador.func.value, ast.Name)
                    and decorador.func.value.id == "mcp"
                    and decorador.func.attr == "tool"
                ):
                    publicadas.add(nodo.name)
        self.assertEqual(publicadas, TOOLS)

    def test_cliente_mcp_no_accede_directamente_a_las_fuentes(self):
        fuente = (ROOT / "agente_mcp.py").read_text(encoding="utf-8")
        self.assertNotIn("from rag", fuente)
        self.assertNotIn("import urllib", fuente)
        for endpoint in ("/camas", "/guardia", "/turnos", "/farmacia", "/espera"):
            self.assertNotIn(endpoint, fuente)

    def test_atencion_de_la_entrega_pasa_tests_de_catedra(self):
        resultado = subprocess.run(
            [sys.executable, str(ROOT / "atencion" / "test_atencion.py"), str(ROOT / "atencion.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
