"""Informe legible a partir de la misma salida estructurada."""
import json
import csv
import io
from html import escape
from urllib.parse import urlparse


def generar_informe(resultados):
    resultados = resultados if isinstance(resultados, list) else [resultados]
    lineas = ["INFORME DE VALIDACIÓN MODELO 210", ""]
    for indice, r in enumerate(resultados, 1):
        lineas.extend([f"Declaración {indice}: {r['estado']}",
                       f"Modelo detectado: {r['tipoModelo'] or 'Indeterminado'}",
                       f"Ejercicio: {r['ejercicio']}",
                       f"Período calculado: {r['periodo']}",
                       f"Período informado: {r['periodoInformado']}",
                       f"Fecha de devengo: {r['fechaDevengo']}",
                       "Plazo: " + json.dumps(r['plazoPresentacion'], ensure_ascii=False)])
        for nombre, clave in (("Reglas aplicadas", "reglasAplicadas"), ("Errores", "errores"),
                              ("Advertencias", "advertencias")):
            lineas.append(nombre + ":")
            lineas.extend("  " + x["codigo"] + ": " + x.get("mensaje", x.get("descripcion", "")) for x in r[clave])
            if not r[clave]:
                lineas.append("  Ninguno.")
        lineas.append("")
    lineas.append("Alcance: coherencia de modalidad, período y plazos nominales. No sustituye al validador AEAT ni valida íntegramente la declaración.")
    return "\n".join(lineas) + "\n"


def _texto(valor):
    return "—" if valor is None else str(valor)


def generar_html(resultados):
    """Informe HTML autónomo: todos los datos recibidos se escapan."""
    filas = resultados if isinstance(resultados, list) else [resultados]
    h = lambda valor: escape(_texto(valor), quote=True)
    bloqueados = sum(bool(r["errores"]) for r in filas)
    revisar = sum(not r["errores"] and bool(r["advertencias"]) for r in filas)
    contenido = []
    for indice, r in enumerate(filas, 1):
        estado = r.get("estadoQA", "Bloqueado" if r["errores"] else "Revisar" if r["advertencias"] else "Preparado")
        contenido.append(f'<section><h2>Caso {indice} · {h(r.get("idCaso") or indice)} <span>{h(estado)}</span></h2>')
        contenido.append('<table><tbody>')
        campos = (("Modelo detectado", r["tipoModelo"]), ("Tipo de renta", r.get("tipoRenta")),
                  ("Modalidad", r.get("modalidadPresentacion")), ("Ejercicio", r["ejercicio"]),
                  ("Período informado", r["periodoInformado"]), ("Período calculado", r["periodo"]),
                  ("Fecha de devengo", r["fechaDevengo"]), ("Fecha de presentación", r.get("fechaPresentacion")),
                  ("Comprobación del plazo", r.get("estadoPlazo")), ("Versión normativa", r["versionNormativa"]))
        for etiqueta, valor in campos:
            contenido.append(f'<tr><th>{h(etiqueta)}</th><td>{h(valor)}</td></tr>')
        for etiqueta, clave in (("Inicio de presentación", "inicio"), ("Fin de presentación", "fin"),
                                ("Fin de domiciliación", "finDomiciliacion")):
            contenido.append(f'<tr><th>{h(etiqueta)}</th><td>{h((r["plazoPresentacion"] or {}).get(clave))}</td></tr>')
        contenido.append('</tbody></table>')
        for titulo, clave in (("Errores funcionales", "errores"), ("Advertencias para QA", "advertencias")):
            contenido.append(f'<h3>{titulo}</h3><ul>')
            for aviso in r[clave]:
                contenido.append(f'<li><strong>{h(aviso["campo"])}: {h(aviso["mensaje"])}</strong><br>'
                                 f'Qué revisar: {h(aviso.get("accionQA", "Revisar el dato indicado."))}'
                                 f'<br><small>Código: {h(aviso["codigo"])}</small></li>')
            if not r[clave]:
                contenido.append('<li>Ninguno.</li>')
            contenido.append('</ul>')
        contenido.append('<details><summary>Reglas aplicadas y trazabilidad</summary><ul>')
        for actual in r["reglasAplicadas"]:
            fuente = str(actual.get("fuente", ""))
            try:
                fuente_enlazable = urlparse(fuente).scheme in {"http", "https"}
            except ValueError:
                fuente_enlazable = False
            enlace = (f'<a href="{h(fuente)}" rel="noreferrer">Fuente</a>'
                      if fuente_enlazable else h(fuente))
            contenido.append(f'<li>{h(actual["codigo"])}: {h(actual["descripcion"])} · {enlace}</li>')
        contenido.append('</ul><p>Módulos ejecutados: ' + h(json.dumps(r.get("reglasEjecutadas", []), ensure_ascii=False)) + '</p></details></section>')
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>QA Impresos Sage 200 · Modelo 210</title><style>'
            'body{font:16px/1.5 system-ui,sans-serif;background:#f0f5f3;color:#20342d;margin:0}'
            'main{max-width:1050px;margin:30px auto;padding:24px}h1,h2{color:#006344}'
            'section,.resumen{background:white;border:1px solid #c9dbd1;border-radius:10px;padding:24px;margin:20px 0}'
            'table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #ddd;padding:8px;overflow-wrap:anywhere}'
            'th{width:40%}li{margin:12px 0;overflow-wrap:anywhere}span{font-size:16px;color:#594200}'
            'small{color:#596861}a{color:#006344}details{overflow-wrap:anywhere}'
            '@media print{body{background:white}main{margin:0}section{break-inside:avoid}}'
            '</style></head><body><main><h1>Validación previa · Impresos Sage 200</h1>'
            '<p>Declaraciones del Modelo 210. Revisión funcional para QA.</p>'
            f'<div class="resumen">Casos: <strong>{len(filas)}</strong> · Bloqueados: <strong>{bloqueados}</strong>'
            f' · Pendientes de revisión: <strong>{revisar}</strong> · Preparados: <strong>{len(filas)-bloqueados-revisar}</strong></div>'
            + ''.join(contenido) + '<p>Validación previa de los controles implementados. Los plazos son nominales; '
            'deben contrastarse con el calendario oficial. No certifica aceptación AEAT ni sustituye las pruebas del impreso.</p>'
            '</main></body></html>')


def _celda_csv(valor):
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")) else texto


def generar_csv(resultados):
    """Una fila por caso; BOM UTF-8 y separador ; para Excel en español."""
    filas = resultados if isinstance(resultados, list) else [resultados]
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow(("caso", "id_caso", "modelo", "tipo_renta", "modalidad", "ejercicio",
        "periodo_informado", "periodo_calculado", "fecha_devengo", "fecha_presentacion",
        "estado", "estado_qa", "estado_plazo", "inicio_plazo", "fin_plazo", "fin_domiciliacion",
        "errores", "advertencias", "acciones_qa", "reglas_aplicadas", "reglas_ejecutadas", "version_normativa"))
    for indice, r in enumerate(filas, 1):
        limites = r["plazoPresentacion"] or {}
        incidencias = r["errores"] + r["advertencias"]
        mensajes = lambda grupo: '\n'.join(f'{x["codigo"]} ({x["campo"]}): {x["mensaje"]}' for x in grupo)
        valores = (indice, r.get("idCaso"), r["tipoModelo"], r.get("tipoRenta"), r.get("modalidadPresentacion"),
            r["ejercicio"], r["periodoInformado"], r["periodo"], r["fechaDevengo"], r.get("fechaPresentacion"),
            r["estado"], r.get("estadoQA"), r.get("estadoPlazo"), limites.get("inicio"), limites.get("fin"),
            limites.get("finDomiciliacion"), mensajes(r["errores"]), mensajes(r["advertencias"]),
            '\n'.join(x.get("accionQA", "Revisar el dato indicado.") for x in incidencias),
            json.dumps(r["reglasAplicadas"], ensure_ascii=False),
            json.dumps(r.get("reglasEjecutadas", []), ensure_ascii=False), r["versionNormativa"])
        escritor.writerow([_celda_csv(x) for x in valores])
    return '\ufeff' + buffer.getvalue()
