from pathlib import Path


def cortar_markdown(texto: str, ruta: str) -> list[dict]:
    lineas = texto.replace("\r\n", "\n").split("\n")
    titulo = Path(ruta).stem
    cuerpo = list(lineas)
    if cuerpo and cuerpo[0].startswith("# "):
        titulo = cuerpo[0][2:].strip()
        cuerpo = cuerpo[1:]

    hay_h2 = any(l.startswith("## ") for l in cuerpo)
    if hay_h2:
        return _por_secciones(titulo, cuerpo)
    return _por_parrafos(titulo, "\n".join(cuerpo).strip())


def _por_secciones(titulo: str, lineas: list[str]) -> list[dict]:
    fragmentos = []
    seccion = None
    bloque: list[str] = []

    def flush():
        texto = "\n".join(bloque).strip()
        if not texto:
            return
        fragmentos.append(_item(titulo, seccion, texto))

    for linea in lineas:
        if linea.startswith("## "):
            flush()
            seccion = linea[3:].strip()
            bloque = [linea]
        else:
            bloque.append(linea)
    flush()
    return fragmentos


def _por_parrafos(titulo: str, texto: str) -> list[dict]:
    if not texto:
        return []
    partes = [p.strip() for p in texto.split("\n\n") if p.strip()]
    return [_item(titulo, None, p) for p in partes]


def _item(titulo: str, seccion: str | None, texto: str) -> dict:
    partes_meta = [titulo]
    if seccion:
        partes_meta.append(seccion)
    para_embed = " | ".join(partes_meta) + "\n" + texto
    return {
        "titulo": titulo,
        "seccion": seccion,
        "texto": texto,
        "para_embed": para_embed,
    }


def cargar_corpus(directorio: str) -> list[dict]:
    raiz = Path(directorio)
    fragmentos = []
    for path in sorted(raiz.glob("*.md")):
        texto = path.read_text(encoding="utf-8")
        fragmentos.extend(cortar_markdown(texto, str(path)))
    return fragmentos
