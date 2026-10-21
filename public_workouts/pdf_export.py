"""
ARQUIVO: exportacao do programa publicado em PDF (Entrega 4.6 do plano de
produto, docs/plans/public-workouts-produtizacao-plan.md — "Exportar
treino em PDF": reduz atrito no cancelamento, "o treino e seu").

POR QUE ELE EXISTE:
- mesma fundacao adiantada de templates/public_workouts/workout.html: o
  payload de PublicWorkoutProgram (S1, schema.py) ja e' o contrato
  congelado desde a Onda S0 — este modulo so oferece OUTRO formato de
  saida pro MESMO dado, sem depender dos 10 programas reais (Onda A2)
  pra existir. Testado contra schema.build_example_payload(), mesmo
  padrao de public_workouts/test_workout_template.py.
- NAO reusa reporting.infrastructure.http_exports.build_pdf_response:
  aquele helper chama box_scoped_filename, que le o slug do BOX ATIVO
  (tenant) — o corredor roda no schema public, SEM tenant (D.00), e
  services.py deste app nunca pode arrastar essa dependencia (mesma
  regra de "nunca importar TENANT_APPS"). Este modulo copia o PADRAO de
  desenho do canvas (paginacao, quebra de linha) — D.00 chama isso de
  "copiar padrao": zero acoplamento, livre. Chamar aquele servico
  diretamente seria o outro tier (acoplamento de interface), que aqui
  colidiria com o isolamento tenant/public.

PONTOS CRITICOS:
- `pdf.setPageCompression(0)`: os outros exportadores de PDF do projeto
  (http_exports.py) nao setam isso, mas aqui e' deliberado — sem
  compressao o conteudo de texto fica bruto nos bytes do PDF (sequencias
  de escape octal tipo `\\347` pra acentos, ASCII puro sem escape pro
  resto), o que permite os testes deste modulo assertarem em conteudo
  (nome de movimento, "RIR", "kg") sem depender de nenhuma biblioteca de
  parsing de PDF (nenhuma esta instalada no projeto). Custo: arquivo um
  pouco maior — irrelevante pro tamanho de um PDF de treino.
- Sem view/rota ainda: get_active_program() so' teria dado real depois da
  Onda A2 (os 10 programas publicados via parser de IA). Uma rota hoje
  devolveria "sem programa" pra todos os 10 slugs reais — mesmo motivo
  de workout.html ainda nao estar ligado a URL nenhuma.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def _humanize_movement_slug(movement_slug: str) -> str:
    """Mesmo palpite de templatetags/public_workouts_extras.py — nao
    importa dali de proposito (aquele modulo existe pra registro de
    template do Django, nao pra ser biblioteca compartilhada; D.00:
    copiar um one-liner e' mais barato que acoplar camadas)."""
    if not movement_slug:
        return ''
    return movement_slug.replace('-', ' ').capitalize()


def _format_load(movement: dict) -> str:
    load_type = movement.get('load_type')
    load_value = movement.get('load_value')
    if load_type == 'percentage_of_rm':
        return f'{load_value}% RM'
    if load_type == 'fixed_kg':
        return f'{load_value} kg'
    return 'Livre'


def _build_sections(payload: dict) -> list[dict]:
    # reps_spec ("3x8-10") e rir_spec ("RIR 2") ja vem prontos pra exibir
    # no payload (mesmo contrato que workout.html renderiza cru, sem
    # prefixo/sufixo adicional) — nao reformatar aqui de novo.
    sections = []
    for day in payload.get('days', ()):
        lines = []
        for block in day.get('blocks', ()):
            for movement in block.get('movements', ()):
                label = _humanize_movement_slug(movement.get('movement_slug', ''))
                lines.append(
                    f"{label} - {movement.get('reps_spec', '')} - "
                    f"{movement.get('rir_spec', '')} - {_format_load(movement)}"
                )
        if not lines:
            lines = ['Nenhum movimento neste dia.']
        sections.append({'title': day.get('label', ''), 'lines': lines})
    return sections


def render_program_pdf(payload: dict) -> bytes:
    """Renderiza o payload de PublicWorkoutProgram (schema.py) num PDF
    simples e imprimivel: titulo, resumo (semanas/inicio) e um bloco por
    dia com movimento, reps, RIR e carga prescrita.

    Sem paginas em branco: a mesma logica de quebra de pagina de
    build_pdf_response (reporting/infrastructure/http_exports.py) —
    quando o cursor Y fica baixo demais, abre pagina nova.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setPageCompression(0)
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

    write_line(payload.get('program_label', ''), bold=True, size=16)
    weeks = payload.get('weeks')
    started_on = payload.get('started_on', '')
    if weeks:
        write_line(f'{weeks} semanas - inicio {started_on}', size=10)
    current_y -= 6

    for section in _build_sections(payload):
        write_line(section['title'], bold=True, size=12)
        for line in section['lines']:
            write_line(line, indent=10)
        current_y -= 6

    pdf.save()
    return buffer.getvalue()
