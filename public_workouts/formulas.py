"""
ARQUIVO: formulas e tabelas de classificacao da avaliacao fisica.

POR QUE ELE EXISTE:
- centraliza as constantes cientificas (formula US Navy, faixas de RCQ/IMC/BF%)
  num unico lugar, testavel isoladamente, sem depender de request/template.

PONTOS CRITICOS:
- BF% por fita (US Navy) e uma ESTIMATIVA (margem tipica +-3 a 5 pontos vs.
  DEXA) — todo consumidor deste modulo deve rotular o valor como estimado,
  nunca como medida exata.
- de proposito NAO existe funcao de "% gordura localizada" (braco/coxa) —
  isso nao e defensavel a partir de circunferencia sem bioimpedancia
  segmentar real. Regioes de membro expõem so a circunferencia e o delta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class Sex:
    MALE = 'M'
    FEMALE = 'F'


@dataclass(frozen=True)
class Classification:
    label: str
    level: str  # 'good' | 'warning' | 'risk' — usado pra cor do badge no front


def estimate_body_fat_navy(
    *, sex: str, height_cm: float, waist_cm: float, neck_cm: float, hip_cm: float | None = None
) -> float | None:
    """Estimativa de %BF pelo metodo de circunferencias da Marinha dos EUA.

    Requer neck < waist (homem) ou neck < waist+hip (mulher, que tambem
    precisa de hip_cm). Retorna None se faltar dado ou a formula degenerar
    (log de numero <= 0).
    """
    if not height_cm or not waist_cm or not neck_cm:
        return None
    try:
        if sex == Sex.FEMALE:
            if not hip_cm:
                return None
            diff = waist_cm + hip_cm - neck_cm
            if diff <= 0:
                return None
            bf = 495 / (1.29579 - 0.35004 * math.log10(diff) + 0.22100 * math.log10(height_cm)) - 450
        else:
            diff = waist_cm - neck_cm
            if diff <= 0:
                return None
            bf = 495 / (1.0324 - 0.19077 * math.log10(diff) + 0.15456 * math.log10(height_cm)) - 450
    except ValueError:
        return None
    if bf <= 0 or bf >= 70:
        return None
    return round(bf, 1)


def compute_whr(*, waist_cm: float | None, hip_cm: float | None) -> float | None:
    if not waist_cm or not hip_cm:
        return None
    return round(waist_cm / hip_cm, 2)


def classify_whr(*, sex: str, whr: float) -> Classification:
    if sex == Sex.FEMALE:
        if whr < 0.80:
            return Classification('Risco baixo', 'good')
        if whr < 0.85:
            return Classification('Risco moderado', 'warning')
        return Classification('Risco alto', 'risk')
    if whr < 0.90:
        return Classification('Risco baixo', 'good')
    if whr < 1.0:
        return Classification('Risco moderado', 'warning')
    return Classification('Risco alto', 'risk')


def compute_bmi(*, weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def classify_bmi(bmi: float) -> Classification:
    if bmi < 18.5:
        return Classification('Abaixo do peso', 'warning')
    if bmi < 25.0:
        return Classification('Normal', 'good')
    if bmi < 30.0:
        return Classification('Sobrepeso', 'warning')
    if bmi < 35.0:
        return Classification('Obesidade grau I', 'risk')
    if bmi < 40.0:
        return Classification('Obesidade grau II', 'risk')
    return Classification('Obesidade grau III', 'risk')


# American Council on Exercise — faixas de referencia por sexo.
_BF_CATEGORIES_MALE = (
    (5.0, 'Gordura essencial', 'warning'),
    (13.0, 'Atleta', 'good'),
    (17.0, 'Fitness', 'good'),
    (24.0, 'Aceitavel', 'warning'),
    (float('inf'), 'Obesidade', 'risk'),
)
_BF_CATEGORIES_FEMALE = (
    (13.0, 'Gordura essencial', 'warning'),
    (20.0, 'Atleta', 'good'),
    (24.0, 'Fitness', 'good'),
    (31.0, 'Aceitavel', 'warning'),
    (float('inf'), 'Obesidade', 'risk'),
)


def classify_body_fat(*, sex: str, bf_percent: float) -> Classification:
    table = _BF_CATEGORIES_FEMALE if sex == Sex.FEMALE else _BF_CATEGORIES_MALE
    for ceiling, label, level in table:
        if bf_percent <= ceiling:
            return Classification(label, level)
    return Classification('Obesidade', 'risk')


def estimate_body_fat_jackson_pollock_3site(
    *, sex: str, age: float, fold_a_mm: float, fold_b_mm: float, fold_c_mm: float
) -> float | None:
    """Protocolo de 3 dobras de Jackson & Pollock (1978), via equacao de Siri.

    Dobras esperadas (soma em mm, ordem nao importa pro calculo):
    - Homem: peitoral, abdominal, coxa.
    - Mulher: triceps, suprailiaca (iliaca), coxa.

    Mais preciso que a estimativa por fita (US Navy) quando ha adipometro
    disponivel, mas ainda e uma ESTIMATIVA — erro tipico de +-3% mesmo com
    boa tecnica de pinca.
    """
    if not age or fold_a_mm is None or fold_b_mm is None or fold_c_mm is None:
        return None
    sum3 = fold_a_mm + fold_b_mm + fold_c_mm
    if sum3 <= 0:
        return None

    if sex == Sex.FEMALE:
        density = 1.0994921 - 0.0009929 * sum3 + 0.0000023 * (sum3**2) - 0.0001392 * age
    else:
        density = 1.10938 - 0.0008267 * sum3 + 0.0000016 * (sum3**2) - 0.0002574 * age

    if density <= 0:
        return None
    bf = (495 / density) - 450
    if bf <= 0 or bf >= 70:
        return None
    return round(bf, 1)


def estimate_body_fat_jackson_pollock_7site(
    *,
    sex: str,
    age: float,
    chest_mm: float,
    midaxillary_mm: float,
    triceps_mm: float,
    subscapular_mm: float,
    abdomen_mm: float,
    suprailiac_mm: float,
    thigh_mm: float,
) -> float | None:
    """Protocolo de 7 dobras de Jackson & Pollock (1978), via equacao de Siri.

    Mesmas 7 dobras pros dois sexos (peitoral, axilar media, triceps,
    subescapular, abdominal, suprailiaca, coxa) — so a equacao de densidade
    muda por sexo. Mais preciso que o protocolo de 3 dobras por usar mais
    pontos de medida; ainda uma ESTIMATIVA (erro tipico de +-3%).
    """
    folds = (chest_mm, midaxillary_mm, triceps_mm, subscapular_mm, abdomen_mm, suprailiac_mm, thigh_mm)
    if not age or any(v is None for v in folds):
        return None
    sum7 = sum(folds)
    if sum7 <= 0:
        return None

    if sex == Sex.FEMALE:
        density = 1.097 - 0.00046971 * sum7 + 0.00000056 * (sum7**2) - 0.00012828 * age
    else:
        density = 1.112 - 0.00043499 * sum7 + 0.00000055 * (sum7**2) - 0.00028826 * age

    if density <= 0:
        return None
    bf = (495 / density) - 450
    if bf <= 0 or bf >= 70:
        return None
    return round(bf, 1)
