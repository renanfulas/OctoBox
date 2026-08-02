"""
ARQUIVO: atribuicao de holdout controlado para casos high_signal do churn financeiro.

POR QUE ELE EXISTE:
- sem grupo de controle, o historical_score so mede correlacao: a acao que mais
  aparece "bem sucedida" no historico pode so estar ligada a casos que a
  equipe escolheu agir primeiro (selecao por indicacao), nao a um efeito real
  da intervencao.
- atribuicao por hash estavel do student_id independe do risco do aluno,
  entao aproxima uma amostragem aleatoria sem precisar de infraestrutura de
  experimento formal.

PONTOS CRITICOS:
- atribuicao e permanente por aluno (nao rotaciona por episodio de risco);
  simples de auditar, mas nao e um RCT formal com janela fixa nem tem
  avaliacao longitudinal de resultado ainda — isso fica para uma proxima
  rodada, quando houver captura fora do limite de preview da fila.
- so se aplica a signal_bucket == high_signal com aluno ainda ativo; nao
  aplicar a aluno ja inativo (churn ja aconteceu, nao ha o que comparar).
"""

import hashlib

HOLDOUT_SALT = 'finance-churn-holdout-v1'
HIGH_SIGNAL_HOLDOUT_FRACTION = 0.1


def resolve_high_signal_holdout(*, student_id, holdout_fraction=HIGH_SIGNAL_HOLDOUT_FRACTION):
    if not student_id or holdout_fraction <= 0:
        return False
    digest = hashlib.sha256(f'{HOLDOUT_SALT}:{student_id}'.encode()).hexdigest()
    bucket = int(digest[:8], 16) % 1000
    return bucket < round(holdout_fraction * 1000)


__all__ = ['HIGH_SIGNAL_HOLDOUT_FRACTION', 'HOLDOUT_SALT', 'resolve_high_signal_holdout']
