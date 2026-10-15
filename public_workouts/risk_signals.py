"""
ARQUIVO: sinais deterministicos de risco do aluno (Curva) -- cockpit do
treinador (achado do Renan, profissional real: "aluno que nao vai
geralmente nao renova; que nao progride, que nao esta tendo resultado").

POR QUE ELE EXISTE:
- os dois sinais ja existiam soltos -- CoachStudentRosterView ja calculava
  dias sem treinar, build_weekly_review ja calcula platô/declínio -- mas
  nunca viravam UMA leitura de "precisa agir aqui" pro treinador. Este
  modulo junta os dois (+ pagamento/renovacao) numa classificacao so.
- Deterministico de proposito, mesmo espirito de build_weekly_review
  (services.py): regra explicavel, nunca IA/score misterioso -- todo
  aluno classificado como risco vem com os MOTIVOS em texto, nunca so um
  numero.

PONTOS CRITICOS:
- Thresholds (STALE/FADING/RENEWAL_SOON) sao *palpite inicial*, nao lei --
  ficam soltos aqui de proposito (constantes no topo do modulo) pra
  ajustar em 1 lugar sem caçar magic number espalhado.
- `high` nunca é rebaixado por um sinal `medium` que apareça depois (ver
  ordem das checagens) -- pagamento com problema ou sumiço prolongado
  sempre vencem "so' renovando em breve".
"""

from __future__ import annotations

from dataclasses import dataclass, field

STALE_TRAINING_DAYS = 10
FADING_TRAINING_DAYS = 5
RENEWAL_SOON_DAYS = 7

_PROBLEM_SUBSCRIPTION_STATUSES = ('past_due', 'suspended')

_LEVEL_ORDER = {'high': 0, 'medium': 1, 'healthy': 2}


@dataclass(frozen=True)
class StudentRiskSignal:
    level: str  # 'high' | 'medium' | 'healthy'
    reasons: list = field(default_factory=list)

    @property
    def sort_key(self) -> int:
        return _LEVEL_ORDER[self.level]


def compute_student_risk(
    *,
    days_since_last_workout: int | None,
    declining_movements: list,
    plateaued_movements: list,
    tracked_movement_count: int,
    subscription_status: str,
    days_until_renewal: int | None,
) -> StudentRiskSignal:
    """Classifica UM aluno. Todo argumento já vem calculado por quem chama
    (build_weekly_review, roster) -- esta função só decide o que os
    números SIGNIFICAM, nunca consulta o banco."""
    reasons: list[str] = []
    high = False
    medium = False

    if days_since_last_workout is None:
        reasons.append('nunca registrou treino')
        high = True
    elif days_since_last_workout >= STALE_TRAINING_DAYS:
        reasons.append(f'{days_since_last_workout} dias sem treinar')
        high = True
    elif days_since_last_workout >= FADING_TRAINING_DAYS:
        reasons.append(f'{days_since_last_workout} dias sem treinar')
        medium = True

    stalled_count = len(declining_movements) + len(plateaued_movements)
    if tracked_movement_count > 0 and stalled_count > 0:
        if declining_movements:
            reasons.append(f'{len(declining_movements)} movimento(s) em queda')
        if plateaued_movements:
            reasons.append(f'{len(plateaued_movements)} movimento(s) em platô')
        # Queda concentrada (metade ou mais dos movimentos acompanhados)
        # pesa mais que um platô isolado -- mas nunca sozinha decide
        # "high" quando so' 1 de muitos movimentos estagnou.
        if declining_movements and stalled_count / tracked_movement_count >= 0.5:
            high = True
        else:
            medium = True

    if subscription_status in _PROBLEM_SUBSCRIPTION_STATUSES:
        reasons.append('pagamento com problema')
        high = True

    if days_until_renewal is not None and 0 <= days_until_renewal <= RENEWAL_SOON_DAYS:
        reasons.append(f'renovação em {days_until_renewal} dia(s)')
        medium = True  # nunca sobrescreve high, ver docstring do modulo

    level = 'high' if high else ('medium' if medium else 'healthy')
    return StudentRiskSignal(level=level, reasons=reasons)


__all__ = ['STALE_TRAINING_DAYS', 'FADING_TRAINING_DAYS', 'RENEWAL_SOON_DAYS', 'StudentRiskSignal', 'compute_student_risk']
