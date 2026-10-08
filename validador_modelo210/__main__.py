import argparse
import csv
import json
import sys
from pathlib import Path

from .entrada import cargar_fichero, leer_json
from .informe import generar_csv, generar_html, generar_informe
from .motor_reglas import crear_registro
from .validador import validar, validar_conjunto


def main():
    # JSON de consola estable también cuando Windows usa una página ANSI.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validación previa para QA de Impresos Sage 200: Modelo 210.")
    parser.add_argument("entrada", help="Fichero JSON, JSONL, CSV o ASCII con layout.")
    parser.add_argument("--layout", help="Descriptor JSON de posiciones, explícito y versionado.")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--salida", help="Guardar resultado JSON.")
    parser.add_argument("--informe", help="Guardar informe legible en texto.")
    parser.add_argument("--informe-html", help="Guardar informe funcional HTML.")
    parser.add_argument("--informe-csv", help="Guardar informe CSV para QA.")
    parser.add_argument("--directorio-informes", help="Generar resultados.json, informe.html e informe.csv en una carpeta.")
    parser.add_argument("--reglas", action="append", default=[], metavar="MODULO:REGISTRAR",
                        help="Cargar un módulo Python de reglas de confianza; opción repetible.")
    parser.add_argument("--estricto-qa", action="store_true", help="Código de salida 1 también si hay advertencias.")
    parser.add_argument("--fecha-referencia", help="Comparación opcional de devengos futuros.")
    args = parser.parse_args()
    try:
        layout = leer_json(Path(args.layout).read_text(encoding="utf-8-sig")) if args.layout else None
        datos = cargar_fichero(args.entrada, layout=layout, encoding=args.encoding)
        motor = crear_registro(modulos=args.reglas)
        resultado = (validar_conjunto if isinstance(datos, list) else validar)(datos,
            fecha_referencia=args.fecha_referencia, registro_reglas=motor)
        salida = json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
        archivos = {}
        if args.directorio_informes:
            destino = Path(args.directorio_informes)
            archivos.update({destino / "resultados.json": salida,
                             destino / "informe.html": generar_html(resultado),
                             destino / "informe.csv": generar_csv(resultado)})
        if args.salida:
            archivos[Path(args.salida)] = salida
        if args.informe:
            extension = Path(args.informe).suffix.lower()
            formato = {".html": generar_html, ".csv": generar_csv}.get(extension, generar_informe)
            archivos[Path(args.informe)] = formato(resultado)
        if args.informe_html:
            archivos[Path(args.informe_html)] = generar_html(resultado)
        if args.informe_csv:
            archivos[Path(args.informe_csv)] = generar_csv(resultado)
        protegidos = {Path(args.entrada).resolve()}
        if args.layout:
            protegidos.add(Path(args.layout).resolve())
        if any(ruta.resolve() in protegidos for ruta in archivos):
            raise ValueError("Los informes no pueden sobrescribir el fichero de entrada ni su layout.")
        for ruta, contenido in archivos.items():
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido, encoding="utf-8", newline="")
        if not args.salida:
            print(salida, end="")
        filas = resultado if isinstance(resultado, list) else [resultado]
        return 1 if any(r["errores"] or (args.estricto_qa and r["advertencias"]) for r in filas) else 0
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps({"estado": "ErrorEntrada", "errores": [{"codigo": "ENTRADA_INVALIDA", "mensaje": str(exc)}]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
