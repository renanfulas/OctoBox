"""
ARQUIVO: fonte unica das perguntas canonicas do PAR-Q por versao de documento.

POR QUE ELE EXISTE:
- o corpo do StudentConsentDocument (kind=parq) semeado por seed_consent_documents
  e os toggles do formulario de consentimento (Onda B) precisam mostrar exatamente
  as mesmas perguntas. Duplicar o texto nos dois lugares e como um red-flag some
  do formulario mas continua no documento (ou vice-versa) sem ninguem notar.

O QUE ESTE ARQUIVO FAZ:
1. declara as 7 perguntas canonicas da v1 do PAR-Q.
2. monta o corpo textual do documento (usado pelo seed) a partir da mesma lista.
3. expoe um registro por versao para a view de consentimento resolver as perguntas
   certas a partir da versao do documento ATIVO (nunca hardcoded na view).

PONTOS CRITICOS:
- PENDENTE_REVISAO_CLINICA: lista provisoria (ver docs/plans/student-parq-waiver-entry-gate-corda.md,
  decisao B2). So vai a producao apos revisao humana.
- se o CONJUNTO de perguntas mudar, crie uma nova versao (nao edite a v1 in-place) —
  aceites ja gravados referenciam a versao lida na tela, nao a vigente no submit.
"""

from __future__ import annotations

PARQ_V1_VERSION = '1'

PARQ_V1_QUESTIONS = (
    'Algum medico ja disse que voce possui algum problema de coracao e que so deveria '
    'realizar atividade fisica supervisionada por profissionais de saude?',
    'Voce sente dores no peito quando pratica atividade fisica?',
    'No ultimo mes, voce sentiu dores no peito quando praticou atividade fisica?',
    'Voce apresenta desequilibrio devido a tontura e/ou perda de consciencia?',
    'Voce possui algum problema osseo ou articular que poderia ser piorado pela '
    'mudanca na sua atividade fisica?',
    'Voce toma atualmente algum medicamento para pressao arterial e/ou problema de coracao?',
    'Sabe de alguma outra razao pela qual voce nao deveria praticar atividade fisica?',
)

PARQ_QUESTIONS_BY_VERSION = {
    PARQ_V1_VERSION: PARQ_V1_QUESTIONS,
}


def build_parq_v1_body() -> str:
    intro = (
        '[PENDENTE_REVISAO_CLINICA]\n\n'
        'Questionario de Prontidao para Atividade Fisica (PAR-Q). 7 perguntas canonicas.\n'
        'Responder "sim" a qualquer uma sinaliza risco e exige liberacao por atestado no box.\n\n'
    )
    numbered_questions = '\n'.join(
        f'{index}. {question}' for index, question in enumerate(PARQ_V1_QUESTIONS, start=1)
    )
    return intro + numbered_questions
