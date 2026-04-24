"""
ARQUIVO: feriados brasileiros hardcoded para o app do aluno.

POR QUE ELE EXISTE:
- evita dependencia de API externa em runtime para marcar feriados na grade mensal.
- preserva comportamento offline e permite revisao anual controlada.

PONTO CRITICO:
- revisar esta lista todo janeiro para acrescentar anos novos e validar feriados moveis.
"""

from __future__ import annotations

from datetime import date


BRAZILIAN_HOLIDAYS = {
    2026: {
        '2026-01-01': 'Ano Novo',
        '2026-02-16': 'Carnaval',
        '2026-02-17': 'Carnaval',
        '2026-04-03': 'Sexta-feira Santa',
        '2026-04-21': 'Tiradentes',
        '2026-05-01': 'Dia do Trabalho',
        '2026-06-04': 'Corpus Christi',
        '2026-09-07': 'Independencia do Brasil',
        '2026-10-12': 'Nossa Senhora Aparecida',
        '2026-11-02': 'Finados',
        '2026-11-15': 'Proclamacao da Republica',
        '2026-12-25': 'Natal',
    },
    2027: {
        '2027-01-01': 'Ano Novo',
        '2027-02-08': 'Carnaval',
        '2027-02-09': 'Carnaval',
        '2027-03-26': 'Sexta-feira Santa',
        '2027-04-21': 'Tiradentes',
        '2027-05-01': 'Dia do Trabalho',
        '2027-05-27': 'Corpus Christi',
        '2027-09-07': 'Independencia do Brasil',
        '2027-10-12': 'Nossa Senhora Aparecida',
        '2027-11-02': 'Finados',
        '2027-11-15': 'Proclamacao da Republica',
        '2027-12-25': 'Natal',
    },
    2028: {
        '2028-01-01': 'Ano Novo',
        '2028-02-28': 'Carnaval',
        '2028-02-29': 'Carnaval',
        '2028-04-14': 'Sexta-feira Santa',
        '2028-04-21': 'Tiradentes',
        '2028-05-01': 'Dia do Trabalho',
        '2028-06-15': 'Corpus Christi',
        '2028-09-07': 'Independencia do Brasil',
        '2028-10-12': 'Nossa Senhora Aparecida',
        '2028-11-02': 'Finados',
        '2028-11-15': 'Proclamacao da Republica',
        '2028-12-25': 'Natal',
    },
    2029: {
        '2029-01-01': 'Ano Novo',
        '2029-02-12': 'Carnaval',
        '2029-02-13': 'Carnaval',
        '2029-03-30': 'Sexta-feira Santa',
        '2029-04-21': 'Tiradentes',
        '2029-05-01': 'Dia do Trabalho',
        '2029-05-31': 'Corpus Christi',
        '2029-09-07': 'Independencia do Brasil',
        '2029-10-12': 'Nossa Senhora Aparecida',
        '2029-11-02': 'Finados',
        '2029-11-15': 'Proclamacao da Republica',
        '2029-12-25': 'Natal',
    },
    2030: {
        '2030-01-01': 'Ano Novo',
        '2030-03-04': 'Carnaval',
        '2030-03-05': 'Carnaval',
        '2030-04-19': 'Sexta-feira Santa',
        '2030-04-21': 'Tiradentes',
        '2030-05-01': 'Dia do Trabalho',
        '2030-06-20': 'Corpus Christi',
        '2030-09-07': 'Independencia do Brasil',
        '2030-10-12': 'Nossa Senhora Aparecida',
        '2030-11-02': 'Finados',
        '2030-11-15': 'Proclamacao da Republica',
        '2030-12-25': 'Natal',
    },
}


def get_brazilian_holiday_name(day: date | None) -> str | None:
    if day is None:
        return None
    return BRAZILIAN_HOLIDAYS.get(day.year, {}).get(day.isoformat())
