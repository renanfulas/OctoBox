"""
ARQUIVO: mensagens operacionais da grade de aulas.

POR QUE ELE EXISTE:
- centraliza os textos exibidos pela grade de aulas para reduzir string solta na view, form e commands.

O QUE ESTE ARQUIVO FAZ:
1. define mensagens padrao de erro e sucesso da grade.
2. oferece pequenos helpers para mensagens com dados dinamicos.
3. padroniza a comunicacao operacional da tela.

PONTOS CRITICOS:
- qualquer mudanca aqui impacta feedback visual, testes e entendimento do fluxo pela equipe.
"""

ROLE_CANNOT_MANAGE_CLASSES = 'Seu papel atual pode consultar a grade, mas nao pode criar aulas por esta tela.'
SESSION_NOT_FOUND = 'A aula selecionada nao foi encontrada.'
UNKNOWN_FORM_KIND = 'O fluxo da grade de aulas nao foi reconhecido.'
UNKNOWN_SESSION_ACTION = 'A acao rapida da aula nao foi reconhecida.'
SESSION_UPDATE_INVALID = 'A aula nao foi atualizada. Revise os campos destacados.'
PLANNER_INVALID = 'A agenda nao foi criada. Revise os campos destacados do planejador.'
PLANNER_SKIPPED_ONLY = 'Nenhuma aula nova foi criada, porque todos os horarios escolhidos ja existiam.'
COMPLETED_SESSION_REOPEN_BLOCKED = 'Aulas concluidas nao podem voltar para agendada por esta edicao rapida.'
SESSION_DELETE_WITH_ATTENDANCE_BLOCKED = 'Nao exclua uma aula que ja tenha reservas ou presencas. Cancele a aula para preservar o historico.'


def session_updated_success(title):
    return f'Aula {title} atualizada com sucesso.'


def session_deleted_success(title):
    return f'Aula {title} excluida com sucesso.'


def planner_success(created_count, skipped_count):
    message = f'{created_count} aula(s) criada(s) com sucesso.'
    if skipped_count:
        message += f' {skipped_count} horario(s) ja existiam e foram pulados.'
    return message