"""
ARQUIVO: conteudo estruturado do PAR-Q para a tela de consentimento (Onda B).

POR QUE ELE EXISTE:
- as 7 perguntas canonicas que dirigem os toggles Sim/Nao da triagem.
- o texto de registro (legal/clinico) vive no StudentConsentDocument (seed);
  esta lista dirige a UI.

PONTOS CRITICOS:
- manter em sincronia com o seed do PAR-Q (PENDENTE_REVISAO_CLINICA) ate a revisao
  clinica humana (gate B2 do plano).
- responder "sim" a qualquer pergunta sinaliza risco (flagged).
"""
from __future__ import annotations

PARQ_QUESTIONS = [
    ('q1', 'Algum medico ja disse que voce tem um problema de coracao e que so deveria fazer atividade fisica supervisionada?'),
    ('q2', 'Voce sente dor no peito quando faz atividade fisica?'),
    ('q3', 'No ultimo mes, voce sentiu dor no peito sem estar fazendo atividade fisica?'),
    ('q4', 'Voce perde o equilibrio por tontura ou ja perdeu a consciencia?'),
    ('q5', 'Voce tem algum problema osseo ou articular que pode piorar com atividade fisica?'),
    ('q6', 'Voce toma algum remedio para pressao ou para o coracao?'),
    ('q7', 'Voce sabe de qualquer outra razao para nao fazer atividade fisica?'),
]

PARQ_QUESTION_KEYS = [key for key, _ in PARQ_QUESTIONS]
