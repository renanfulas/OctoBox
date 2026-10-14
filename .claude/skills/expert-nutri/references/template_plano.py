# -*- coding: utf-8 -*-
"""
Template reportlab para gerar plano alimentar em PDF, no padrao visual usado
pela skill expert-nutri (faixas verdes por refeicao, opcoes em bullet, tabela
de legumes/proteina/salada no almoco, resumo de ajuste calorico no fim).

Como usar: copie este arquivo, ajuste OUT_PATH e o conteudo de cada secao
(CAPA, CAFE DA MANHA, COLACAO, ALMOCO, LANCHE DA TARDE, JANTAR, ORIENTACOES,
RESUMO). As funcoes meal_header() e option_block() sao genericas, reuse sem
modificar. Nao copie logo/fotos de um nutricionista terceiro num plano
derivado -- e um documento adaptado, nao uma falsificacao do original.

Instalar dependencia se faltar: pip install reportlab
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

OUT_PATH = r"C:\caminho\para\Plano alimentar - Nome do Cliente.pdf"

GREEN = colors.HexColor("#AFCB99")
GREEN_LIGHT = colors.HexColor("#E9F2E2")
GREY_HEADER = colors.HexColor("#C9C9C9")
TEXT_DARK = colors.HexColor("#333333")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=22, textColor=TEXT_DARK, spaceAfter=4)
subtitle_style = ParagraphStyle("SubtitleCustom", parent=styles["Normal"], fontSize=12, textColor=TEXT_DARK, spaceAfter=2)
section_header_style = ParagraphStyle(
    "SectionHeader", parent=styles["Heading2"], fontSize=15, textColor=TEXT_DARK,
    alignment=TA_CENTER, spaceBefore=0, spaceAfter=0
)
meal_time_style = ParagraphStyle(
    "MealTime", parent=styles["Normal"], fontSize=9, textColor=TEXT_DARK,
    alignment=TA_CENTER, spaceAfter=0
)
option_title_style = ParagraphStyle(
    "OptionTitle", parent=styles["Normal"], fontSize=11, textColor=TEXT_DARK,
    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2
)
item_style = ParagraphStyle(
    "Item", parent=styles["Normal"], fontSize=10.5, textColor=TEXT_DARK,
    leftIndent=14, spaceAfter=1, leading=14
)
note_style = ParagraphStyle(
    "Note", parent=styles["Normal"], fontSize=9.5, textColor=TEXT_DARK,
    leftIndent=0, spaceAfter=1, leading=13, fontName="Helvetica-Oblique"
)
disclaimer_style = ParagraphStyle(
    "Disclaimer", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#666666"),
    alignment=TA_LEFT, leading=12
)
footer_small = ParagraphStyle(
    "FooterSmall", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#888888"), leading=11
)


def meal_header(title, time_note):
    """Faixa verde com o nome da refeicao + horario/observacao opcional."""
    t = Table(
        [[Paragraph(title, section_header_style)],
         [Paragraph(time_note, meal_time_style)] if time_note else [""]],
        colWidths=[17 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    return t


def option_block(title, lines):
    """Bloco 'Opcao N: ...' com itens em bullet."""
    flow = [Paragraph(title, option_title_style)]
    for line in lines:
        flow.append(Paragraph(f"• {line}", item_style))
    return flow


def resumo_ajuste_table(rows):
    """
    rows: lista de tuplas (refeicao, antes_kcal, depois_kcal, reducao) com a
    ultima linha sendo o TOTAL. Gera a tabela de registro interno no fim do
    documento -- nao mostrar essa tabela nas paginas de uso diario.
    """
    data = [["Refeição (combinação de referência)", "Antes (kcal aprox.)", "Depois (kcal aprox.)", "Redução"]]
    data.extend(rows)
    t = Table(data, colWidths=[7.5 * cm, 3.2 * cm, 3.2 * cm, 3.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), GREEN_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


# ---------------- MONTAGEM DO DOCUMENTO (exemplo minimo) ----------------
if __name__ == "__main__":
    story = []

    # CAPA
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Plano alimentar", title_style))
    story.append(Paragraph("Nome do Cliente — versão ajustada", subtitle_style))
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "Descreva aqui a origem do plano (nutricionista responsavel, se houver) e a "
        "estrategia de ajuste aplicada (deficit/superavit em kcal, o que foi cortado/adicionado).",
        disclaimer_style,
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Este é um ajuste mecânico de quantidades, não uma nova prescrição clínica. "
        "Recomenda-se validar com o(a) nutricionista responsável antes de adotar de forma continuada.",
        disclaimer_style,
    ))
    story.append(PageBreak())

    # REFEICAO (repita este padrao pra cada refeicao do dia)
    story.append(meal_header("Café da manhã", "06:00 ou 09:00"))
    story.append(Spacer(1, 10))
    story.extend(option_block("Opção 1: ...", ["Item – medida caseira (Xg)"]))
    story.append(Spacer(1, 18))
    story.append(PageBreak())

    # ORIENTACOES + RESUMO (ultima pagina)
    story.append(meal_header("Orientações", ""))
    story.append(Spacer(1, 12))
    for o in ["Orientação 1", "Orientação 2"]:
        story.append(Paragraph(f"• {o}", item_style))
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.75, color=GREY_HEADER))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Resumo do ajuste calórico (referência interna)", ParagraphStyle(
        "ResumoTitle", parent=styles["Heading3"], fontSize=12, textColor=TEXT_DARK)))
    story.append(Spacer(1, 6))
    story.append(resumo_ajuste_table([
        ["Refeição X", "000", "000", "-00"],
        ["TOTAL DO DIA", "0000", "0000", "-000"],
    ]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Valores estimados a partir de tabela TACO/TBCA para os itens listados no plano; não incluem "
        "azeite/óleo de preparo eventualmente usado e não listado no documento original.",
        footer_small,
    ))

    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title="Plano alimentar (ajustado)",
    )
    doc.build(story)
    print("OK:", OUT_PATH)
