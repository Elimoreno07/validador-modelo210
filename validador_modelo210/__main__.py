import argparse
import csv
import json
import sys
from pathlib import Path

from .entrada import cargar_fichero, leer_json
from .informe import generar_informe
from .validador import validar, validar_conjunto


def main():
    # JSON de consola estable también cuando Windows usa una página ANSI.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validación local del período del Modelo 210.")
    parser.add_argument("entrada", help="Fichero JSON, JSONL, CSV o ASCII con layout.")
    parser.add_argument("--layout", help="Descriptor JSON de posiciones, explícito y versionado.")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--salida", help="Guardar resultado JSON.")
    parser.add_argument("--informe", help="Guardar informe legible en texto.")
    parser.add_argument("--fecha-referencia", help="Comparación opcional de devengos futuros.")
    args = parser.parse_args()
    try:
        layout = leer_json(Path(args.layout).read_text(encoding="utf-8-sig")) if args.layout else None
        datos = cargar_fichero(args.entrada, layout=layout, encoding=args.encoding)
        resultado = (validar_conjunto if isinstance(datos, list) else validar)(datos, fecha_referencia=args.fecha_referencia)
        salida = json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
        if args.salida:
            Path(args.salida).write_text(salida, encoding="utf-8")
        else:
            print(salida, end="")
        if args.informe:
            Path(args.informe).write_text(generar_informe(resultado), encoding="utf-8")
        filas = resultado if isinstance(resultado, list) else [resultado]
        return 1 if any(r["errores"] for r in filas) else 0
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps({"estado": "ErrorEntrada", "errores": [{"codigo": "ENTRADA_INVALIDA", "mensaje": str(exc)}]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
