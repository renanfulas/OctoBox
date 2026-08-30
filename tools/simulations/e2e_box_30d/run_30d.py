"""
ARQUIVO: simulacao E2E de 30 dias de operacao real de um box no OctoBox.

O QUE FAZ:
- 4 personas de staff (Recepcao, Coach, Manager, Owner) + 90 alunos usando o
  produto por HTTP, um dia de cada vez, durante 30 dias.
- Cada tela/acao vira uma entrada no journal, com status e latencia.

USO:
    PYTHONPATH=. DJANGO_SETTINGS_MODULE=config.settings \
      .venv/bin/python tools/simulations/e2e_box_30d/run_30d.py
"""
from __future__ import annotations

import os
import random
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from harness import Persona, JOURNAL, Call  # noqa: E402
import setup_box  # noqa: E402
from student_access import build_student_tokens  # noqa: E402

SCHEMA = 'box_crossfit-serra-norte'
START = date(2026, 8, 31)
DAYS = 30
TARGET_STUDENTS = 90
RNG = random.Random(2026)

STAFF = {
    'maria': ('Maria', 'reception', 89, 'Serra#2026'),
    'eric': ('Eric', 'coach', 95, 'Serra#2026'),
    'diego': ('Diego', 'manager', 102, 'Serra#2026'),
    'fernando': ('Fernando', 'owner', 110, 'BoxSerra#2026'),
}


def errors_in(resp):
    if resp is None:
        return ['sem resposta']
    return [e.strip() for e in re.findall(r'form-error[^>]*>([^<]{2,200})', resp.text)]


# --------------------------------------------------------------- fase 1: base
def ensure_students(maria: Persona, plan_ids, due, target):
    from django_tenants.utils import schema_context
    with schema_context(SCHEMA):
        from students.models import Student
        have = Student.objects.count()
    if have >= target:
        return have, 0
    blocked = 0
    for i in range(have, target):
        maria.get('/alunos/novo/', action='abrir cadastro de aluno')
        r = maria.post('/alunos/novo/', setup_box.student_payload(i, plan_ids[i % len(plan_ids)], due),
                       action='cadastrar aluno', expect=(200, 302, 429))
        if r is not None and r.status_code == 429:
            blocked += 1
            JOURNAL.note('Maria', 0, 'throttle',
                         f'429 no cadastro do aluno {i}: limite de 30 escritas/min trava o mutirao de cadastro')
            import time
            time.sleep(62)
    with schema_context(SCHEMA):
        from students.models import Student
        return Student.objects.count(), blocked


# ------------------------------------------------------------- rotinas diarias
def maria_day(p: Persona, day: int, d: date, students):
    p.get('/operacao/recepcao/', action='abrir painel da recepcao')
    p.get('/alunos/', action='lista de alunos')
    p.get('/entradas/', action='funil de entradas')
    # busca de aluno no balcao (o que ela mais faz)
    for _ in range(3):
        st = RNG.choice(students)
        p.get(f'/api/v1/students/autocomplete/?q={st[1].split()[0]}', action='autocomplete de aluno')
        p.get(f'/alunos/{st[0]}/drawer/profile/', action='abrir ficha do aluno', expect=(200, 404))
    # lead novo no balcao
    if day % 2 == 0:
        p.post('/entradas/', {
            'form_kind': 'quick-create',
            'entry_kind': 'lead',
            'lead-create-full_name': f'Visitante Dia {day}',
            'lead-create-phone': f'1197{day:03d}0000'[:11],
            'lead-create-email': f'visitante{day}@ex.com',
            'lead-create-source': 'manual',
            'lead-create-acquisition_channel': 'walk_in',
            'lead-create-acquisition_detail': 'entrou pela porta',
        }, action='cadastrar lead do balcao', expect=(200, 302, 429))
    # fila de pagamentos do dia: Maria da baixa nas cobrancas do balcao
    p.get('/operacao/recepcao/fragmentos/pagamentos/', action='fila de pagamentos', expect=(200, 404))
    r = p.get('/operacao/recepcao/', action='reabrir painel da recepcao')
    pay_ids = list(dict.fromkeys(re.findall(r'/operacao/recepcao/pagamento/(\d+)/acao/', r.text if r else '')))
    for pid in pay_ids[:3]:
        p.post(f'/operacao/recepcao/pagamento/{pid}/acao/', {
            'payment_id': pid, 'action': 'mark-paid', 'method': RNG.choice(['pix', 'cash', 'credit_card']),
            'due_date': d.isoformat(), 'reference': f'REC-{day:02d}-{pid}', 'notes': '',
        }, action='dar baixa em pagamento', expect=(200, 302, 429))
    p.get('/grade-aulas/', action='conferir grade do dia')


def eric_day(p: Persona, day: int, d: date, session_ids):
    p.get('/operacao/coach/', action='abrir painel do coach')
    p.get('/operacao/wod/planner/', action='planner de WOD')
    p.get('/operacao/wod/editor/', action='editor de WOD')
    for sid in session_ids[:2]:
        r = p.get(f'/operacao/coach/aula/{sid}/wod/', action='abrir WOD da aula', expect=(200, 302, 404))
        if r is not None and r.status_code == 200:
            p.post(f'/operacao/coach/aula/{sid}/wod/', {
                'intent': 'save_workout',
                'title': f'WOD dia {day}',
                'coach_notes': 'Escalar conforme necessario.',
            }, action='salvar WOD da aula', expect=(200, 302, 429))
            p.post(f'/operacao/coach/aula/{sid}/wod/', {
                'intent': 'add_block', 'kind': 'metcon', 'title': 'MetCon',
                'notes': 'AMRAP 20 min', 'sort_order': '1',
            }, action='adicionar bloco ao WOD', expect=(200, 302, 429))
    p.get('/operacao/wod/aprovacoes/', action='fila de aprovacao de WOD', expect=(200, 403))
    p.get('/operacao/wod/historico/', action='historico de WOD', expect=(200, 403))
    p.get('/operacao/wod/templates/', action='biblioteca de templates', expect=(200, 403))


def diego_day(p: Persona, day: int, d: date, students):
    p.get('/dashboard/', action='dashboard')
    p.get('/financeiro/', action='financeiro')
    p.get('/financeiro/?payment_status=overdue', action='financeiro filtrado por inadimplencia')
    p.get('/alunos/?status=active', action='alunos ativos')
    p.get('/operacao/relatorios/', action='hub de relatorios')
    p.get('/operacao/resumo-executivo/', action='resumo executivo')
    p.get('/operacao/whatsapp/', action='painel de whatsapp')
    p.get('/operacao/manager/', action='workspace do manager', expect=(200, 404))
    if day % 7 == 3:
        p.get('/financeiro/exportar/csv/', action='exportar financeiro', expect=(200, 302, 429, 403))


def fernando_day(p: Persona, day: int, d: date):
    p.get('/operacao/owner/', action='workspace do owner')
    p.get('/dashboard/', action='dashboard do dono')
    p.get('/operacao/resumo-executivo/', action='resumo executivo')
    if day % 7 == 0:
        p.get('/operacao/relatorios/', action='relatorios semanais')
        p.get('/alunos/exportar/csv/', action='exportar base de alunos', expect=(200, 302, 429, 403))
        p.get('/integrations/webhooks/', action='observabilidade de webhooks', expect=(200, 403))
        p.get('/acessos/', action='conferir acessos da equipe')


def student_day(p: Persona, day: int):
    p.get('/aluno/', action='home do app')
    r = p.get('/aluno/grade/', action='grade de aulas no app')
    sessions = re.findall(r'name="session_id"[^>]*value="(\d+)"', r.text) if r else []
    booked = False
    # o aluno tenta ate 3 horarios diferentes antes de desistir, como faria
    # alguem procurando vaga na grade.
    for sid in RNG.sample(sessions, min(3, len(sessions))) if sessions else []:
        rr = p.post('/aluno/presenca/confirmar/', {'session_id': sid},
                    action='confirmar presenca', expect=(200, 302, 429))
        if rr is None:
            break
        plain = rr.text.replace('á', 'a').replace('í', 'i').replace('ê', 'e').replace('ç', 'c')
        if 'foi confirmada' in plain:
            booked = True
            break
        if 'ja tem uma reserva ativa' in plain:
            JOURNAL.note(p.name, day, 'friction',
                         'app recusa reservar outra aula: so 1 reserva ativa por vez')
            break
        if 'vagas preenchidas' in plain:
            JOURNAL.note(p.name, day, 'friction', 'aula lotada; aluno tenta outro horario')
    p.get('/aluno/wod/', action='ver WOD do dia')
    if day % 5 == 0:
        p.get('/aluno/rm/', action='abrir meus RMs')
        p.post('/aluno/rm/adicionar/', {
            'exercise_label': RNG.choice(['Back Squat', 'Deadlift', 'Snatch', 'Clean and Jerk', 'Bench Press']),
            'one_rep_max_kg': str(RNG.randint(40, 150)),
            'notes': '',
        }, action='registrar RM', expect=(200, 302, 429))
    return booked


# ------------------------------------------------------------------- principal
def main():
    import django
    django.setup()
    from django_tenants.utils import schema_context

    staff = {}
    for user, (name, role, iq, pwd) in STAFF.items():
        p = Persona(name, role, iq)
        if not p.login_staff(user, pwd):
            print(f'!! login falhou: {user}')
        staff[user] = p

    with schema_context(SCHEMA):
        from boxcore.models import MembershipPlan
        plan_ids = [str(pk) for pk in MembershipPlan.objects.filter(active=True).values_list('id', flat=True)[:4]]
    total, blocked = ensure_students(staff['maria'], plan_ids or ['1'], '10/09/26', TARGET_STUDENTS)
    print(f'alunos na base: {total} (bloqueios por rate limit: {blocked})')

    tokens = build_student_tokens(SCHEMA)
    students_meta = [(sid, nm) for sid, nm, _ in tokens]
    student_personas = []
    for sid, nm, tok in tokens:
        sp = Persona(nm, 'student', 93)
        sp.get(f'/aluno/auth/dev-login/?token={tok}', action='entrar no app do aluno', expect=(200, 302))
        student_personas.append(sp)
    print(f'alunos com app ativo: {len(student_personas)}')

    for day in range(1, DAYS + 1):
        d = START + timedelta(days=day - 1)
        for p in staff.values():
            p.day = day
        for sp in student_personas:
            sp.day = day

        with schema_context(SCHEMA):
            from operations.models import ClassSession
            day_sessions = list(
                ClassSession.objects.filter(scheduled_at__date=d).order_by('scheduled_at').values_list('id', flat=True)
            )

        maria_day(staff['maria'], day, d, students_meta)
        eric_day(staff['eric'], day, d, day_sessions)
        diego_day(staff['diego'], day, d, students_meta)
        fernando_day(staff['fernando'], day, d)

        # alunos: fim de semana tem menos gente
        share = 0.35 if d.weekday() >= 5 else 0.62
        actives = RNG.sample(student_personas, int(len(student_personas) * share))
        for sp in actives:
            student_day(sp, day)

        print(f'dia {day:02d} ({d.isoformat()}) aulas={len(day_sessions)} alunos_ativos={len(actives)} '
              f'chamadas={len(JOURNAL.calls)}', flush=True)

    JOURNAL.dump('/tmp/claude-0/-home-user-OctoBox/8e3945d9-7925-5252-bda4-e18bcfc79f0f/scratchpad/journal.json')
    print('journal salvo:', len(JOURNAL.calls), 'chamadas')


if __name__ == '__main__':
    main()
