"""
ARQUIVO: adapter Django de resolucao de coach da grade.

POR QUE ELE EXISTE:
- tira do writer principal a responsabilidade de reidratar usuarios Django para a grade.

O QUE ESTE ARQUIVO FAZ:
1. resolve o coach por id quando informado.
2. devolve nulo quando o planner nao vincula coach.

PONTOS CRITICOS:
- esta camada e puramente de infraestrutura; a aplicacao continua falando apenas por ids.
"""


class DjangoClassGridCoachResolver:
    def resolve(self, coach_id: int | None):
        if coach_id is None:
            return None
        from django.contrib.auth import get_user_model

        return get_user_model().objects.filter(pk=coach_id).first()


__all__ = ['DjangoClassGridCoachResolver']