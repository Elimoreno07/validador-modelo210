"""PDF paginado con los resultados del motor, generado con ReportLab."""
import io
import json
from html import escape


def generar_pdf(resultados):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    filas = resultados if isinstance(resultados, list) else [resultados]
    buffer = io.BytesIO()
    estilos = getSampleStyleSheet()
    estilos['BodyText'].wordWrap = 'CJK'
    estilos['BodyText'].spaceAfter = 7
    p = lambda valor, estilo='BodyText': Paragraph(escape(str(valor)).replace('\n', '<br/>'), estilos[estilo])
    elementos = [p('QA Impresos Sage 200 - Modelo 210', 'Title'),
                 p(f'Declaraciones: {len(filas)} | Errores: {sum(len(r["errores"]) for r in filas)} | Avisos: {sum(len(r["advertencias"]) for r in filas)}')]
    for indice, resultado in enumerate(filas, 1):
        if indice > 1:
            elementos.append(PageBreak())
        elementos.append(p(f'Caso {indice}: {resultado.get("idCaso") or indice}', 'Heading1'))
        for campo in ('tipoModelo', 'ejercicio', 'periodo', 'periodoInformado', 'fechaDevengo',
                      'estado', 'estadoQA', 'estadoPlazo', 'plazoPresentacion', 'versionNormativa'):
            valor = resultado.get(campo)
            elementos.append(p(f'{campo}: ' + (json.dumps(valor, ensure_ascii=False) if isinstance(valor, dict) else str(valor))))
        for titulo, clave in (('Errores', 'errores'), ('Avisos', 'advertencias')):
            elementos.append(p(titulo, 'Heading2'))
            if not resultado[clave]:
                elementos.append(p('Ninguno.'))
            for aviso in resultado[clave]:
                elementos.extend([p(f'{aviso["codigo"]} | {aviso.get("campo", "")}', 'Heading3'),
                                  p(aviso['mensaje']), p('Solución: ' + aviso.get('accionQA', 'Revisar el campo indicado.'))])
        elementos.append(p('Reglas aplicadas', 'Heading2'))
        for regla in resultado['reglasAplicadas']:
            elementos.append(p(f'{regla["codigo"]}: {regla["descripcion"]}'))
        elementos.append(Spacer(1, 12))
        elementos.append(p('Validación previa de los controles implementados. Plazos nominales; no certifica aceptación AEAT.'))
    def pie(canvas, doc):
        canvas.setFillColor(colors.HexColor('#52665d'))
        canvas.setFont('Helvetica', 9)
        canvas.drawString(40, 24, 'QA Sage 200 - Modelo 210')
        canvas.drawRightString(A4[0] - 40, 24, f'Página {doc.page}')
    SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40,
                      topMargin=40, bottomMargin=45).build(elementos, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()
