"""Informe legible a partir de la misma salida estructurada."""
import json


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
