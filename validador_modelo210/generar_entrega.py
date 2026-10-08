"""Genera los informes del ejemplo y empaqueta código, pruebas y documentación."""
import json
import zipfile
from pathlib import Path

from .informe import generar_informe
from .validador import validar_fichero


def main():
    paquete = Path(__file__).resolve().parent
    destino = paquete.parent / "output" / "validador_modelo210"
    destino.mkdir(parents=True, exist_ok=True)
    resultados = validar_fichero(paquete / "ejemplos" / "declaraciones.json")
    (destino / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "informe_validacion.txt").write_text(generar_informe(resultados), encoding="utf-8")
    resumen = (
        "ENTREGA DEL VALIDADOR MODELO 210\n\n"
        "Implementado en Python 3.11+, sin dependencias externas.\n"
        "Arquitectura: detector de modelo, detector de período, reglas I/H/R,\n"
        "validador, adaptadores de entrada, informe final y CLI.\n\n"
        "Verificación ejecutada: 57 pruebas unitarias correctas (unittest),\n"
        "incluidas pruebas de ficheros y CLI, con salida UTF-8 en Windows.\n\n"
        "Resultado del conjunto de ejemplo:\n"
    )
    for i, r in enumerate(resultados, 1):
        resumen += f"  {i}. {r['tipoModelo']}: período {r['periodo']}, estado {r['estado']}; errores {len(r['errores'])}.\n"
    resumen += (
        "\nEl cuarto registro informa 4T para un alquiler individual; se detecta\n"
        "PERIODO_INCOMPATIBLE y se calcula 0A. El informe detallado contiene\n"
        "las reglas aplicadas, errores y advertencias de cada declaración.\n\n"
        "Entradas: JSON, JSONL, CSV y ASCII con descriptor versionado explícito.\n"
        "No se incluyen posiciones oficiales AEAT sin diseño verificado.\n"
        "Plazos nominales; no se incorporan ajustes de días inhábiles.\n"
        "Correcto se refiere a los controles implementados y no garantiza\n"
        "aceptación AEAT ni sustituye una validación completa del contenido.\n"
        "Ver README.txt para uso, contrato, fuentes y límites.\n"
    )
    (destino / "informe_final.txt").write_text(resumen, encoding="utf-8")
    with zipfile.ZipFile(destino / "validador_modelo210.zip", "w", zipfile.ZIP_DEFLATED) as archivo:
        for ruta in paquete.rglob("*"):
            if ruta.is_file() and "__pycache__" not in ruta.parts:
                archivo.write(ruta, Path("validador_modelo210") / ruta.relative_to(paquete))
        for nombre in ("resultados.json", "informe_validacion.txt", "informe_final.txt"):
            archivo.write(destino / nombre, Path("informes") / nombre)
    print(json.dumps({"declaraciones": len(resultados), "correctas": sum(r["estado"] == "Correcto" for r in resultados),
                      "incorrectas": sum(r["estado"] == "Incorrecto" for r in resultados),
                      "paquete": str(destino / "validador_modelo210.zip")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
