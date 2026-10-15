"""
ARQUIVO: varredura funcional ampla apos os 30 dias de operacao.

POR QUE ELE EXISTE:
- O loop diario cobre a rotina. Esta varredura cobre o resto do produto:
  financeiro avancado, importacao, exportacao, WOD (templates/aprovacao/
  planner), app do aluno (pagamento, congelamento, consentimento, PWA) e
  observabilidade.

PONTOS CRITICOS:
- Cada acao registra no journal com o status esperado declarado. Divergencia
  vira incidente.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from harness import Persona, JOURNAL  # noqa: E402
from student_access import build_student_tokens  # noqa: E402

SCHEMA = 'box_crossfit-serra-norte'
OUT = '/tmp/claude-0/-home-user-OctoBox/8e3945d9-7925-5252-bda4-e18bcfc79f0f/scratchpad/journal_sweep.json'


def show(tag, r, extra=''):
    st = r.status_code if r is not None else 'ERR'
    errs = re.findall(r'form-error[^>]*>([^<]{2,140})', r.text) if r is not None else []
    msgs = [m.strip() for m in re.findall(r'class="message[^"]*"[^>]*>\s*([^<]{4,160})', r.text)] if r is not None else []
    msgs = [m for m in msgs if m]
    print(f'{str(st):>5} | {tag:<46} {extra} {("ERR:"+str(errs[:2])) if errs else ""} {("MSG:"+str(msgs[:2])) if msgs else ""}')
    return r


def main():
    import django
    django.setup()
    from django_tenants.utils import schema_context

    with schema_context(SCHEMA):
        from students.models import Student
        from boxcore.models import Payment
        from operations.models import ClassSession
        sid = Student.objects.order_by('id').first().id
        sid2 = Student.objects.order_by('id')[1].id
        pay = Payment.objects.order_by('id').first()
        pay_id = pay.id if pay else None
        sess_id = ClassSession.objects.order_by('scheduled_at').first().id
        n_pay = Payment.objects.count()
    print(f'# aluno={sid} pagamento={pay_id} (total {n_pay}) aula={sess_id}\n')

    ow = Persona('Fernando', 'owner', 110); ow.login_staff('fernando', 'BoxSerra#2026')
    mg = Persona('Diego', 'manager', 102); mg.login_staff('diego', 'Serra#2026')
    co = Persona('Eric', 'coach', 95); co.login_staff('eric', 'Serra#2026')
    rc = Persona('Maria', 'reception', 89); rc.login_staff('maria', 'Serra#2026')

    print('--- FICHA / EDICAO DE ALUNO (Maria) ---')
    show('POST drawer/profile', rc.post(f'/alunos/{sid}/drawer/profile/', {}, action='drawer do aluno (POST)', expect=(200, 405)))
    show('GET  drawer/fragments', rc.get(f'/alunos/{sid}/drawer/fragments/', action='fragmentos do drawer', expect=(200, 405)))
    show('GET  snapshot', rc.get(f'/alunos/{sid}/snapshot/', action='snapshot do aluno', expect=(200, 405)))
    show('GET  editar', rc.get(f'/alunos/{sid}/editar/', action='abrir edicao do aluno', expect=(200, 403)))
    show('POST sessao/iniciar', rc.post(f'/alunos/{sid}/editar/sessao/iniciar/', {}, action='iniciar sessao de edicao', expect=(200, 302, 405)))
    show('GET  lock/status', rc.get(f'/alunos/{sid}/editar/lock/status/', action='status do lock de edicao', expect=(200, 405)))
    show('POST lock/heartbeat', rc.post(f'/alunos/{sid}/editar/lock/heartbeat/', {}, action='heartbeat do lock', expect=(200, 405)))
    show('POST sessao/liberar', rc.post(f'/alunos/{sid}/editar/sessao/liberar/', {}, action='liberar sessao de edicao', expect=(200, 302, 405)))

    print('\n--- FINANCEIRO (Maria / Diego) ---')
    show('GET  cobranca/drawer', rc.get(f'/alunos/{sid}/financeiro/cobranca/drawer/', action='drawer de cobranca', expect=(200, 403, 405)))
    show('GET  cobranca/avulsa', rc.get(f'/alunos/{sid}/financeiro/cobranca/avulsa/drawer/', action='drawer de cobranca avulsa', expect=(200, 403, 405)))
    show('GET  pag.rapidos/drawer', rc.get(f'/alunos/{sid}/pagamentos-rapidos/drawer/', action='drawer de pagamento rapido', expect=(200, 403, 405)))
    show('GET  pag.rapidos/sugestoes', rc.get(f'/alunos/{sid}/pagamentos-rapidos/sugestoes/', action='sugestoes de pagamento rapido', expect=(200, 403, 405)))
    if pay_id:
        show('POST recepcao mark-paid', rc.post(f'/operacao/recepcao/pagamento/{pay_id}/acao/',
             {'action': 'mark-paid', 'payment_method': 'pix'}, action='baixar pagamento na recepcao', expect=(200, 302, 403, 404)))
        show('GET  payment-link', mg.get(f'/api/v1/finance/payment-link/{pay_id}/', action='gerar link de pagamento', expect=(200, 400, 403, 405, 502)))
    show('POST bulk-action', mg.post('/api/v1/finance/payments/bulk-action/',
         {'action': 'mark-paid', 'payment_ids': str(pay_id)}, action='acao em lote de pagamentos', expect=(200, 400, 403, 405)))
    show('POST freeze-student', mg.post('/api/v1/finance/freeze-student/', {'student_id': str(sid2)},
         action='congelar aluno', expect=(200, 400, 403, 405)))
    show('POST comunicacao/acao', mg.post('/financeiro/comunicacao/acao/', {'student_id': str(sid), 'action': 'whatsapp'},
         action='acao de comunicacao financeira', expect=(200, 302, 400, 403, 404, 405)))

    print('\n--- IMPORT / EXPORT ---')
    csv_body = ('nome,telefone,email\n'
                'Importado Um,11970000001,imp1@ex.com\n'
                'Importado Dois,11970000002,imp2@ex.com\n')
    show('GET  alunos/importar', ow.get('/alunos/importar/', action='tela de importacao de alunos', expect=(200, 403)))
    r = ow.post('/alunos/importar/', {}, action='importar CSV de alunos', expect=(200, 302, 400, 403),
                files={'import_file': ('alunos.csv', csv_body, 'text/csv')})
    show('POST alunos/importar', r)
    for fmt in ('csv', 'xlsx', 'pdf'):
        show(f'GET  alunos/exportar/{fmt}', ow.get(f'/alunos/exportar/{fmt}/', action=f'exportar alunos {fmt}', expect=(200, 302, 403, 404, 429)))
        show(f'GET  financeiro/exportar/{fmt}', mg.get(f'/financeiro/exportar/{fmt}/', action=f'exportar financeiro {fmt}', expect=(200, 302, 403, 404, 429)))

    print('\n--- WOD (Eric / Fernando) ---')
    show('GET  wod/paste', co.get('/operacao/wod/paste/', action='colar WOD (smart paste)', expect=(200, 403)))
    show('POST wod/paste', co.post('/operacao/wod/paste/', {'source_text': 'AMRAP 20\n10 Pull-ups\n15 Push-ups\n20 Air Squats'},
         action='processar WOD colado', expect=(200, 302, 400, 403)))
    show('GET  wod/aprovacoes', ow.get('/operacao/wod/aprovacoes/', action='fila de aprovacao', expect=(200, 403)))
    show('GET  wod/aprov/checkpoint', ow.get('/operacao/wod/aprovacoes/checkpoint-semanal/', action='checkpoint semanal de WOD', expect=(200, 403, 405)))
    show('GET  wod/templates', co.get('/operacao/wod/templates/', action='templates de WOD', expect=(200, 403)))
    show('GET  wod/historico', co.get('/operacao/wod/historico/', action='historico de WOD', expect=(200, 403)))
    show('GET  wod/planner', co.get('/operacao/wod/planner/', action='planner de WOD', expect=(200, 403)))
    show('GET  prescription-preview', co.get(f'/operacao/coach/aula/{sess_id}/wod/prescription-preview/',
         action='previa de prescricao por 1RM', expect=(200, 403, 404, 405)))
    show('POST ocorrencia tecnica', co.post(f'/operacao/aluno/{sid}/ocorrencia-tecnica/',
         {'category': 'technique', 'description': 'Joelho valgo no agachamento; regredir carga.'},
         action='registrar ocorrencia tecnica', expect=(200, 302, 400, 403, 404)))

    print('\n--- OBSERVABILIDADE / RELATORIOS ---')
    show('GET  relatorios', ow.get('/operacao/relatorios/', action='hub de relatorios', expect=(200, 403)))
    show('GET  resumo-executivo', ow.get('/operacao/resumo-executivo/', action='resumo executivo', expect=(200, 403)))
    show('GET  webhooks panel', ow.get('/integrations/webhooks/', action='painel de webhooks', expect=(200, 403)))
    show('GET  whatsapp', mg.get('/operacao/whatsapp/', action='painel whatsapp', expect=(200, 403)))
    show('GET  mapa-sistema', ow.get('/mapa-sistema/', action='mapa do sistema', expect=(200, 403)))
    show('GET  health', ow.get('/api/v1/health/', action='healthcheck', expect=(200,)))
    show('GET  health/tenant', ow.get('/api/v1/health/tenant/', action='healthcheck do tenant', expect=(200, 403)))
    show('GET  metrics', ow.get('/metrics/', action='metricas prometheus', expect=(200, 403, 404)))

    print('\n--- APP DO ALUNO ---')
    tok = build_student_tokens(SCHEMA, limit=1)[0]
    st = Persona(tok[1], 'student', 93)
    st.get(f'/aluno/auth/dev-login/?token={tok[2]}', action='entrar no app', expect=(200, 302))
    for path, exp in [('/aluno/', (200,)), ('/aluno/configuracoes/', (200,)), ('/aluno/consentimento/', (200, 302)),
                      ('/aluno/rm/', (200,)), ('/aluno/treino/', (200,)), ('/aluno/manifest.webmanifest', (200,)),
                      ('/aluno/sw.js', (200,)), ('/aluno/offline/', (200,)), ('/aluno/box/switch/', (200, 302, 405)),
                      ('/aluno/matricula/congelar/', (200, 302, 405)), ('/aluno/sem-box/', (200, 302)),
                      ('/aluno/suspenso-financeiro/', (200, 302)), ('/aluno/liberacao-pendente/', (200, 302)),
                      ('/aluno/aguardando-aprovacao/', (200, 302)), ('/aluno/onboarding/', (200, 302)),
                      ('/aluno/entrar-com-convite/', (200, 302))]:
        show(f'GET  {path}', st.get(path, action=f'aluno {path}', expect=exp))
    show('POST push/subscribe', st.post('/aluno/push/subscribe/', {'subscription': '{}'},
         action='assinar push', expect=(200, 400, 405)))
    if pay_id:
        show('GET  aluno pagar', st.get(f'/aluno/pagamentos/{pay_id}/pagar/', action='pagar mensalidade no app',
             expect=(200, 302, 403, 404, 502)))
    show('POST congelar matricula', st.post('/aluno/matricula/congelar/', {'reason': 'viagem'},
         action='congelar matricula pelo app', expect=(200, 302, 400, 403, 405)))

    print('\n--- SEGURANCA / BORDAS ---')
    anon = Persona('Anonimo', 'anon', 0)
    show('GET  /financeiro/ sem login', anon.get('/financeiro/', action='financeiro sem login', expect=(200, 302, 403)))
    show('GET  rota inexistente', anon.get('/rota-que-nao-existe-xyz/', action='rota inexistente', expect=(404,)))
    show('GET  /.env (honeypot)', anon.get('/.env', action='varredura /.env', expect=(200, 302, 403, 404)))
    show('GET  admin', anon.get('/painel-interno-privado/', action='admin sem login', expect=(200, 302, 403, 404)))

    JOURNAL.dump(OUT)
    print('\njournal da varredura:', len(JOURNAL.calls), 'chamadas ->', OUT)


if __name__ == '__main__':
    main()
