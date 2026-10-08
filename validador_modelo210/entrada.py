"""Adaptadores JSON, JSONL, CSV y registros de longitud fija con layout explícito."""
import csv
import io
import json
from pathlib import Path

from .comun import entero


def _objeto(pares):
    salida = {}
    for clave, valor in pares:
        if clave in salida:
            raise ValueError(f"Clave JSON duplicada: {clave}.")
        salida[clave] = valor
    return salida


def leer_json(texto):
    def constante(valor):
        raise ValueError(f"Constante JSON no válida: {valor}.")
    return json.loads(texto, object_pairs_hook=_objeto, parse_constant=constante)


def leer_registro_fijo(texto, layout):
    if not isinstance(layout, dict) or not layout.get("version"):
        raise ValueError("El layout necesita una versión explícita.")
    longitud = entero(layout.get("longitudRegistro"))
    if longitud <= 0 or len(texto) != longitud:
        raise ValueError("Longitud de registro distinta del layout seleccionado.")
    campos = layout.get("campos")
    if not isinstance(campos, dict) or not campos:
        raise ValueError("El layout debe definir campos.")
    usados, datos = set(), {}
    for campo, especificacion in campos.items():
        if not isinstance(especificacion, dict):
            raise ValueError("Descripción de campo inválida.")
        inicio, tamano = entero(especificacion.get("inicio")), entero(especificacion.get("longitud"))
        if inicio < 1 or tamano < 1 or inicio + tamano - 1 > longitud:
            raise ValueError("Campos fuera del registro.")
        posiciones = set(range(inicio - 1, inicio - 1 + tamano))
        if usados & posiciones:
            raise ValueError("Campos solapados o fuera del registro.")
        usados |= posiciones
        valor = texto[inicio - 1:inicio - 1 + tamano].strip()
        vacios = especificacion.get("valoresVacios", [])
        if not isinstance(vacios, list) or any(not isinstance(x, str) for x in vacios):
            raise ValueError("valoresVacios debe ser una lista de cadenas.")
        datos[campo] = None if valor in vacios else valor
    return datos


def cargar_fichero(ruta, *, layout=None, encoding="utf-8-sig"):
    ruta = Path(ruta)
    texto = ruta.read_text(encoding=encoding)
    if layout is not None:
        lineas = texto.splitlines()
        if not lineas:
            raise ValueError("Fichero vacío.")
        return [leer_registro_fijo(linea, layout) for linea in lineas]
    extension = ruta.suffix.lower()
    if extension == ".json":
        datos = leer_json(texto)
        if not isinstance(datos, (dict, list)):
            raise ValueError("JSON debe contener un registro o una lista de registros.")
        return datos
    if extension in {".jsonl", ".ndjson"}:
        filas = [leer_json(linea) for linea in texto.splitlines() if linea.strip()]
        if not filas:
            raise ValueError("Fichero vacío.")
        return filas
    if extension == ".csv":
        dialecto = csv.Sniffer().sniff(texto[:8192], delimiters=",;\t")
        lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
        if not lector.fieldnames or len(set(lector.fieldnames)) != len(lector.fieldnames):
            raise ValueError("Cabeceras CSV ausentes o duplicadas.")
        filas = list(lector)
        if any(None in fila for fila in filas):
            raise ValueError("Filas CSV con columnas adicionales.")
        if not filas:
            raise ValueError("CSV sin declaraciones.")
        for fila in filas:
            if "domiciliacion" in fila:
                valor = str(fila["domiciliacion"]).strip().lower()
                if valor in {"true", "false"}:
                    fila["domiciliacion"] = valor == "true"
        return filas
    raise ValueError("Use JSON/JSONL/CSV, o un layout versionado para ASCII/.210.")
