"""Adaptación de archivos subidos; no modifica las reglas fiscales."""
import csv
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from .entrada import leer_json, leer_registro_fijo

MAX_BYTES = 10 * 1024 * 1024


def leer_xml(texto):
    if '<!DOCTYPE' in texto.upper() or '<!ENTITY' in texto.upper():
        raise ValueError('XML con DTD o entidades no permitido.')
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as exc:
        raise ValueError('XML no válido: revise las etiquetas.') from exc
    nombre = lambda nodo: nodo.tag.rsplit('}', 1)[-1]
    if nombre(raiz) == 'declaracion':
        nodos = [raiz]
    elif nombre(raiz) == 'declaraciones' and all(nombre(n) == 'declaracion' for n in raiz):
        nodos = list(raiz)
    else:
        raise ValueError('XML esperado: declaracion o declaraciones con hijos declaracion.')
    def convertir(nodo, profundidad=0):
        if profundidad > 8 or nodo.attrib:
            raise ValueError('XML demasiado profundo o con atributos no admitidos.')
        if not len(nodo):
            return (nodo.text or '').strip() or None
        if (nodo.text or '').strip() or any((n.tail or '').strip() for n in nodo):
            raise ValueError('XML con contenido mixto no admitido.')
        # Las listas explícitas representan fechas/claves de rentas agrupadas.
        if nombre(nodo) in {'fechasDevengo', 'clavesRenta'}:
            return [convertir(n, profundidad + 1) for n in nodo]
        datos = {}
        for hijo in nodo:
            clave = nombre(hijo)
            if clave in datos:
                raise ValueError(f'Campo XML duplicado: {clave}.')
            datos[clave] = convertir(hijo, profundidad + 1)
        return datos
    filas = [convertir(n) for n in nodos]
    if not filas or any(not isinstance(n, dict) for n in filas):
        raise ValueError('XML sin declaraciones con campos.')
    for fila in filas:
        if str(fila.get('domiciliacion', '')).lower() in {'true', 'false'}:
            fila['domiciliacion'] = fila['domiciliacion'].lower() == 'true'
    return filas


def cargar_subida(contenido, nombre, *, layout=None, encoding='utf-8-sig'):
    if not contenido or len(contenido) > MAX_BYTES:
        raise ValueError('Seleccione un fichero no vacío de hasta 10 MB.')
    try:
        texto = contenido.decode(encoding)
    except UnicodeError as exc:
        raise ValueError('Codificación incorrecta. Pruebe Windows-1252 en las opciones.') from exc
    extension = Path(nombre).suffix.lower()
    if layout is not None:
        filas = [leer_registro_fijo(linea, layout) for linea in texto.splitlines()]
    elif extension == '.xml' or (extension == '.txt' and texto.lstrip().startswith('<')):
        filas = leer_xml(texto)
    elif extension in {'.json', '.txt'} and texto.lstrip().startswith(('{', '[')):
        # TXT admite JSON completo o un objeto JSON por línea.
        try:
            filas = leer_json(texto)
        except ValueError:
            if extension != '.txt':
                raise
            filas = [leer_json(l) for l in texto.splitlines() if l.strip()]
    elif extension in {'.jsonl', '.ndjson'}:
        filas = [leer_json(l) for l in texto.splitlines() if l.strip()]
    elif extension == '.csv':
        dialecto = csv.Sniffer().sniff(texto[:8192], delimiters=',;\t')
        lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
        if not lector.fieldnames or len(set(lector.fieldnames)) != len(lector.fieldnames):
            raise ValueError('Cabeceras CSV ausentes o duplicadas.')
        filas = list(lector)
        if any(None in f for f in filas):
            raise ValueError('CSV con columnas adicionales.')
        for fila in filas:
            if str(fila.get('domiciliacion', '')).lower() in {'true', 'false'}:
                fila['domiciliacion'] = fila['domiciliacion'].lower() == 'true'
    else:
        raise ValueError('Para TXT fijo, ASCII o .210 seleccione su layout JSON versionado.')
    filas = filas if isinstance(filas, list) else [filas]
    if not filas or any(not isinstance(f, dict) for f in filas):
        raise ValueError('El fichero debe contener una o varias declaraciones con campos.')
    return filas
