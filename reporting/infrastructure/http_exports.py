"""
ARQUIVO: renderizadores concretos de exportacao HTTP.

POR QUE ELE EXISTE:
- Tira do catalogo historico a serializacao final de CSV/PDF em HttpResponse.

O QUE ESTE ARQUIVO FAZ:
1. Converte payloads tabulares em CSV baixavel.
2. Converte secoes textuais em PDF simples.
3. Resolve o payload para a response final conforme o formato.

PONTOS CRITICOS:
- O conteudo exportado precisa permanecer legivel e coerente com a tela filtrada.
"""

import csv
from io import BytesIO, StringIO

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def build_csv_response(*, filename, headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def build_pdf_response(*, filename, title, sections):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    current_y = page_height - 48

    def write_line(text, *, bold=False, size=10, indent=0):
        nonlocal current_y
        if current_y < 64:
            pdf.showPage()
            current_y = page_height - 48
        font_name = 'Helvetica-Bold' if bold else 'Helvetica'
        pdf.setFont(font_name, size)
        max_width = page_width - 72 - indent
        words = str(text).split()
        line = ''
        for word in words:
            candidate = f'{line} {word}'.strip()
            if stringWidth(candidate, font_name, size) <= max_width:
                line = candidate
                continue
            pdf.drawString(36 + indent, current_y, line)
            current_y -= 14
            line = word
        pdf.drawString(36 + indent, current_y, line or str(text))
        current_y -= 16

    write_line(title, bold=True, size=16)
    current_y -= 6
    for section in sections:
        write_line(section['title'], bold=True, size=12)
        for line in section['lines']:
            write_line(line, indent=10)
        current_y -= 6

    pdf.save()
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def build_report_response(report_payload):
    if report_payload['format'] == 'csv':
        return build_csv_response(
            filename=report_payload['filename'],
            headers=report_payload['headers'],
            rows=report_payload['rows'],
        )
    if report_payload['format'] == 'pdf':
        return build_pdf_response(
            filename=report_payload['filename'],
            title=report_payload['title'],
            sections=report_payload['sections'],
        )
    raise ValueError('Formato de relatorio nao suportado.')


__all__ = ['build_csv_response', 'build_pdf_response', 'build_report_response']