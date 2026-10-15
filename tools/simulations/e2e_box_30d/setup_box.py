"""
ARQUIVO: fase de montagem do box na simulacao E2E de 30 dias.

O QUE FAZ:
1. Fernando (Owner) cria planos de mensalidade em /financeiro/.
2. Fernando monta a grade semanal de aulas em /grade-aulas/ (form_kind=planner).
3. Maria (Recepcao) cadastra alunos em /alunos/novo/ e no balcao rapido.
4. Fernando emite convites do app do aluno.

PONTOS CRITICOS:
- Tudo por HTTP, com CSRF, como um humano faria. Falha vira incidente no journal.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from harness import Persona, JOURNAL

WEEK_SLOTS = [
    ('CrossFit 06h', '06:00', 18, '0,1,2,3,4'),
    ('CrossFit 07h', '07:00', 18, '0,1,2,3,4'),
    ('CrossFit 12h', '12:00', 14, '0,1,2,3,4'),
    ('CrossFit 18h', '18:00', 20, '0,1,2,3,4'),
    ('CrossFit 19h', '19:00', 20, '0,1,2,3,4'),
    ('Sabado Team WOD', '09:00', 24, '5'),
]

PLANS = [
    ('Ilimitado', '289.90', 'monthly', 7, 'Acesso livre a todas as aulas.'),
    ('3x na semana', '219.90', 'monthly', 3, 'Tres aulas por semana.'),
    ('2x na semana', '179.90', 'monthly', 2, 'Duas aulas por semana.'),
    ('Anual Ilimitado', '2790.00', 'yearly', 7, 'Plano anual com desconto.'),
]


def create_plans(owner: Persona):
    owner.get('/financeiro/', action='abrir financeiro')
    created = 0
    for name, price, cycle, spw, desc in PLANS:
        r = owner.post('/financeiro/', {
            'name': name, 'price': price, 'billing_cycle': cycle,
            'sessions_per_week': str(spw), 'description': desc, 'active': 'True',
        }, action='criar plano')
        if r is not None and r.status_code in (200, 302):
            created += 1
    return created


def build_class_grid(owner: Persona, start: date, weeks: int = 6):
    owner.get('/grade-aulas/', action='abrir grade de aulas')
    made = 0
    end = start + timedelta(weeks=weeks)
    for title, hhmm, capacity, weekdays in WEEK_SLOTS:
        data = {
            'form_kind': 'planner',
            'title': title,
            'coach': '',
            'start_time': hhmm,
            'duration_minutes': '60',
            'capacity': str(capacity),
            'status': 'scheduled',
            'notes': '',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'sequence_count': '0',
            'skip_existing': 'on',
            'return_query': '',
            'weekdays': weekdays.split(','),
        }
        # 'anchor_date' (rodizio) so vale para sabado/domingo — mandar em aula
        # de dia util faz o form recusar tudo com erro escondido no campo.
        # rodizio (anchor_date + interval_days) so existe no modal de fim de
        # semana; em dia util o planner nao manda esses campos.
        if set(weekdays.split(',')) <= {'5', '6'}:
            data['anchor_date'] = start.isoformat()
            data['interval_days'] = '7'
        r = owner.post('/grade-aulas/', data, action='criar grade semanal')
        if r is not None and r.status_code in (200, 302):
            made += 1
    return made


FIRST = ['Ana', 'Bruno', 'Carla', 'Diego', 'Elisa', 'Felipe', 'Gabi', 'Henrique', 'Isa', 'Joao',
         'Karla', 'Lucas', 'Marina', 'Nathan', 'Olivia', 'Pedro', 'Queila', 'Rafa', 'Sofia', 'Tiago',
         'Ursula', 'Vitor', 'Wesley', 'Xenia', 'Yuri', 'Zoe', 'Aline', 'Caio', 'Dani', 'Eduardo']
LAST = ['Silva', 'Souza', 'Oliveira', 'Costa', 'Ferreira', 'Rocha', 'Almeida', 'Barbosa', 'Ramos', 'Pinto']
SOURCES = ['referral', 'instagram', 'walk_in', 'google', 'whatsapp', 'website', 'meta_ads', 'event']


def student_payload(i: int, plan_id: str, due: str):
    first = FIRST[i % len(FIRST)]
    last = LAST[(i // len(FIRST)) % len(LAST)]
    return {
        'full_name': f'{first} {last} {i:03d}',
        'phone': f'119{80000000 + i:08d}'[:11],
        'email': f'aluno{i:03d}@serranorte.test',
        'cpf': '', 'birth_date': '', 'gender': ['', 'male', 'female'][i % 3],
        'status': 'active', 'enrollment_status': 'active',
        'selected_plan': plan_id,
        'billing_strategy': 'recurring',
        'payment_method': ['pix', 'credit_card', 'cash', 'bank_slip'][i % 4],
        'payment_due_date': due,
        'initial_payment_amount': '',
        'installment_total': '1',
        'recurrence_cycles': '12',
        'acquisition_source': SOURCES[i % len(SOURCES)],
        'acquisition_source_detail': '',
        'health_issue_status': 'no',
        'notes': '',
        'intake_record': '',
        'confirm_payment_now': 'False',
    }


def enroll_students(reception: Persona, count: int, plan_ids: list[str], due: str):
    """Maria cadastra a base inicial pelo formulario completo de /alunos/novo/."""
    ok, failed = 0, []
    for i in range(count):
        reception.get('/alunos/novo/', action='abrir cadastro de aluno')
        payload = student_payload(i, plan_ids[i % len(plan_ids)], due)
        r = reception.post('/alunos/novo/', payload, action='cadastrar aluno')
        if r is None:
            failed.append((i, 'sem resposta'))
            continue
        errs = re.findall(r'form-error[^>]*>([^<]{2,160})', r.text)
        if errs:
            failed.append((i, errs[:2]))
        else:
            ok += 1
    return ok, failed
