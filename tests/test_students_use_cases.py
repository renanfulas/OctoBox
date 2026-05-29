"""
ARQUIVO: testes de students.application.use_cases e domain.enrollment_lifecycle.

POR QUE EXISTE:
- execute_create/update_student_quick_use_case orquestra criação/atualização
  de alunos + sync de matrícula + sync de intake + auditoria. Antes deste
  arquivo: 0 testes — rollback de falha parcial nunca exercitado.
- resolve_enrollment_sync_defaults define defaults comerciais
  (base_amount, billing_strategy, etc.). Sem teste, mudanças nesses defaults
  podem cobrar 0 sem alerta.
- Cobre Sprint 7 do plano de hardening.

CAMADA: L1 (unit) — sem banco, sem ORM. Use cases recebem ports injetados,
domain functions são puras.

SOURCE-UNDER-TEST:
- students/application/use_cases.py:48 (execute_create_student_quick_use_case)
- students/application/use_cases.py:73 (execute_update_student_quick_use_case)
- students/domain/enrollment_lifecycle.py:60 (resolve_enrollment_sync_defaults)

CONTRATO DE MOCK:
- Todos os ports via create_autospec do Protocol — refactor na assinatura
  do port quebra o teste imediatamente (AP6 evitado).
- UnitOfWorkPort.run executa op() diretamente (sem transação).
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call, create_autospec

from students.application.commands import StudentQuickCommand
from students.application.ports import (
    StudentEnrollmentSyncPort,
    StudentIntakeSyncPort,
    StudentQuickAuditPort,
    StudentWriterPort,
    UnitOfWorkPort,
)
from students.application.results import (
    EnrollmentSyncRecord,
    StudentQuickResult,
    StudentRecord,
)
from students.application.use_cases import (
    execute_create_student_quick_use_case,
    execute_update_student_quick_use_case,
)
from students.domain.enrollment_lifecycle import (
    EnrollmentSyncDefaults,
    resolve_enrollment_sync_defaults,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _command(**overrides) -> StudentQuickCommand:
    defaults = dict(
        actor_id=1,
        full_name='João Aluno',
        phone='11999990000',
        status='active',
    )
    defaults.update(overrides)
    return StudentQuickCommand(**defaults)


def _student_record(id_: int = 42, name: str = 'João Aluno') -> StudentRecord:
    return StudentRecord(id=id_, full_name=name)


def _enrollment_record(**overrides) -> EnrollmentSyncRecord:
    defaults = dict(enrollment_id=1, payment_id=2, movement='created')
    defaults.update(overrides)
    return EnrollmentSyncRecord(**defaults)


def _ports():
    """Mocks de TODOS os ports usados pelos use cases, via create_autospec."""
    uow = create_autospec(UnitOfWorkPort, instance=True)
    # Por padrão, executa a operation diretamente (sem transação)
    uow.run.side_effect = lambda op: op()

    writer = create_autospec(StudentWriterPort, instance=True)
    writer.create.return_value = _student_record()
    writer.update.return_value = _student_record()

    enrollment = create_autospec(StudentEnrollmentSyncPort, instance=True)
    enrollment.sync.return_value = _enrollment_record()

    intake = create_autospec(StudentIntakeSyncPort, instance=True)
    intake.sync.return_value = 99

    audit = create_autospec(StudentQuickAuditPort, instance=True)

    return uow, writer, enrollment, intake, audit


# ===========================================================================
# execute_create_student_quick_use_case
# ===========================================================================

class ExecuteCreateStudentQuickUseCaseTest(unittest.TestCase):
    """L1: execute_create_student_quick_use_case — use_cases.py:48."""

    def test_success_calls_all_ports_in_correct_order(self):
        """student_writer.create → enrollment_sync.sync → intake_sync.sync → audit.record_created."""
        uow, writer, enrollment, intake, audit = _ports()
        cmd = _command()

        result = execute_create_student_quick_use_case(
            cmd,
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        writer.create.assert_called_once_with(cmd)
        enrollment.sync.assert_called_once()
        intake.sync.assert_called_once()
        audit.record_created.assert_called_once()
        self.assertIsInstance(result, StudentQuickResult)

    def test_result_contains_student_intake_id_and_enrollment(self):
        uow, writer, enrollment, intake, audit = _ports()
        writer.create.return_value = _student_record(id_=777, name='Carlos')
        intake.sync.return_value = 555
        enrollment_rec = _enrollment_record(enrollment_id=42, payment_id=88, movement='created')
        enrollment.sync.return_value = enrollment_rec

        result = execute_create_student_quick_use_case(
            _command(),
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        self.assertEqual(result.student.id, 777)
        self.assertEqual(result.student.full_name, 'Carlos')
        self.assertEqual(result.intake_id, 555)
        self.assertEqual(result.enrollment_sync, enrollment_rec)

    def test_changed_fields_forwarded_from_command_to_result(self):
        uow, writer, enrollment, intake, audit = _ports()
        cmd = _command(changed_fields=('phone', 'email'))

        result = execute_create_student_quick_use_case(
            cmd,
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        self.assertEqual(result.changed_fields, ('phone', 'email'))

    def test_command_forwarded_intact_to_student_writer(self):
        uow, writer, enrollment, intake, audit = _ports()
        cmd = _command(
            full_name='Ana Carolina',
            phone='11888887777',
            email='ana@x.com',
            selected_plan_id=15,
        )

        execute_create_student_quick_use_case(
            cmd,
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        # writer.create recebeu o command inteiro, sem alterações
        called_with = writer.create.call_args.args[0]
        self.assertEqual(called_with, cmd)

    def test_intake_sync_receives_intake_record_id_from_command(self):
        uow, writer, enrollment, intake, audit = _ports()
        writer.create.return_value = _student_record(id_=100)
        cmd = _command(intake_record_id=7777)

        execute_create_student_quick_use_case(
            cmd,
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        intake.sync.assert_called_once_with(student_id=100, intake_record_id=7777)

    def test_enrollment_sync_failure_prevents_audit_record_created(self):
        """FINDING POTENCIAL: se enrollment_sync.sync levanta, audit NÃO deve ser chamado."""
        uow, writer, enrollment, intake, audit = _ports()
        enrollment.sync.side_effect = RuntimeError('enrollment service down')

        with self.assertRaises(RuntimeError):
            execute_create_student_quick_use_case(
                _command(),
                unit_of_work=uow,
                student_writer=writer,
                enrollment_sync=enrollment,
                intake_sync=intake,
                audit=audit,
            )

        # student_writer.create rodou (não há savepoint aqui — só transaction.atomic via UoW)
        writer.create.assert_called_once()
        # MAS audit NÃO deve ter sido chamado
        audit.record_created.assert_not_called()
        # E intake nunca rodou (enrollment falhou antes)
        intake.sync.assert_not_called()

    def test_intake_sync_failure_prevents_audit_record_created(self):
        uow, writer, enrollment, intake, audit = _ports()
        intake.sync.side_effect = RuntimeError('intake service down')

        with self.assertRaises(RuntimeError):
            execute_create_student_quick_use_case(
                _command(),
                unit_of_work=uow,
                student_writer=writer,
                enrollment_sync=enrollment,
                intake_sync=intake,
                audit=audit,
            )

        writer.create.assert_called_once()
        enrollment.sync.assert_called_once()
        audit.record_created.assert_not_called()

    def test_unit_of_work_run_is_invoked_with_callable(self):
        """UoW.run recebe a operação como callable — não é executada antes."""
        uow, writer, enrollment, intake, audit = _ports()
        # Override side_effect: NÃO executa op imediatamente, apenas guarda
        uow.run.side_effect = None
        uow.run.return_value = MagicMock()

        execute_create_student_quick_use_case(
            _command(),
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        uow.run.assert_called_once()
        # O argumento passado é callable
        op_arg = uow.run.call_args.args[0]
        self.assertTrue(callable(op_arg))


# ===========================================================================
# execute_update_student_quick_use_case
# ===========================================================================

class ExecuteUpdateStudentQuickUseCaseTest(unittest.TestCase):
    """L1: execute_update_student_quick_use_case — use_cases.py:73."""

    def test_calls_student_writer_update_not_create(self):
        uow, writer, enrollment, intake, audit = _ports()

        execute_update_student_quick_use_case(
            _command(),
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        writer.update.assert_called_once()
        writer.create.assert_not_called()

    def test_calls_audit_record_updated_not_record_created(self):
        uow, writer, enrollment, intake, audit = _ports()

        execute_update_student_quick_use_case(
            _command(),
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        audit.record_updated.assert_called_once()
        audit.record_created.assert_not_called()

    def test_changed_fields_audited_in_update_flow(self):
        """O campo changed_fields chega ao record_updated via result."""
        uow, writer, enrollment, intake, audit = _ports()
        cmd = _command(changed_fields=('phone', 'health_issue_status'))

        execute_update_student_quick_use_case(
            cmd,
            unit_of_work=uow,
            student_writer=writer,
            enrollment_sync=enrollment,
            intake_sync=intake,
            audit=audit,
        )

        call_kwargs = audit.record_updated.call_args.kwargs
        self.assertEqual(call_kwargs['command'], cmd)
        self.assertEqual(call_kwargs['result'].changed_fields, ('phone', 'health_issue_status'))


# ===========================================================================
# resolve_enrollment_sync_defaults — defaults comerciais
# ===========================================================================

class ResolveEnrollmentSyncDefaultsTest(unittest.TestCase):
    """L1: resolve_enrollment_sync_defaults — enrollment_lifecycle.py:60.

    Função PURA, sem banco, sem ORM. Cada teste cobre 1 default.
    """

    TODAY = date(2026, 6, 1)

    def _resolve(self, **overrides) -> EnrollmentSyncDefaults:
        params = dict(
            enrollment_status='',
            due_date=None,
            payment_method='',
            billing_strategy='',
            installment_total=0,
            recurrence_cycles=0,
            initial_payment_amount=None,
            selected_plan_price=None,
            today=self.TODAY,
        )
        params.update(overrides)
        return resolve_enrollment_sync_defaults(**params)

    def test_enrollment_status_defaults_to_pending(self):
        defaults = self._resolve(enrollment_status='')
        self.assertEqual(defaults.enrollment_status, 'pending')

    def test_enrollment_status_preserved_when_provided(self):
        defaults = self._resolve(enrollment_status='active')
        self.assertEqual(defaults.enrollment_status, 'active')

    def test_due_date_defaults_to_today_when_none(self):
        defaults = self._resolve(due_date=None)
        self.assertEqual(defaults.due_date, self.TODAY)

    def test_due_date_preserved_when_provided(self):
        custom = date(2026, 12, 31)
        defaults = self._resolve(due_date=custom)
        self.assertEqual(defaults.due_date, custom)

    def test_payment_method_defaults_to_pix(self):
        defaults = self._resolve(payment_method='')
        self.assertEqual(defaults.payment_method, 'pix')

    def test_payment_method_preserved_when_provided(self):
        defaults = self._resolve(payment_method='credit_card')
        self.assertEqual(defaults.payment_method, 'credit_card')

    def test_billing_strategy_defaults_to_single(self):
        defaults = self._resolve(billing_strategy='')
        self.assertEqual(defaults.billing_strategy, 'single')

    def test_installment_total_defaults_to_one_when_zero(self):
        defaults = self._resolve(installment_total=0)
        self.assertEqual(defaults.installment_total, 1)

    def test_installment_total_preserved_when_positive(self):
        defaults = self._resolve(installment_total=12)
        self.assertEqual(defaults.installment_total, 12)

    def test_recurrence_cycles_defaults_to_one_when_zero(self):
        defaults = self._resolve(recurrence_cycles=0)
        self.assertEqual(defaults.recurrence_cycles, 1)

    def test_base_amount_uses_initial_payment_when_provided(self):
        defaults = self._resolve(
            initial_payment_amount=Decimal('150.00'),
            selected_plan_price=Decimal('99.00'),
        )
        self.assertEqual(defaults.base_amount, Decimal('150.00'))

    def test_base_amount_falls_back_to_plan_price_when_no_initial(self):
        defaults = self._resolve(
            initial_payment_amount=None,
            selected_plan_price=Decimal('250.00'),
        )
        self.assertEqual(defaults.base_amount, Decimal('250.00'))

    def test_base_amount_is_zero_when_no_initial_and_no_plan_price(self):
        """FINDING ALTO: cobrança zerada silenciosa.

        Quando initial_payment_amount=None E selected_plan_price=None,
        base_amount cai para Decimal('0.00') sem alerta.

        Isso significa que matrículas podem ser criadas com cobrança 0,00 se
        a UI permitir submeter sem plano e sem amount custom. Recomendação:
        validar base_amount > 0 explicitamente ou levantar ValueError no domain.
        """
        defaults = self._resolve(
            initial_payment_amount=None,
            selected_plan_price=None,
        )
        self.assertEqual(defaults.base_amount, Decimal('0.00'))
        # FINDING: ver tests/sprint-5-8-findings.md FIND-001

    def test_initial_payment_zero_decimal_is_treated_as_falsy(self):
        """Decimal('0.00') é falsy em Python — cai no fallback selected_plan_price.

        Isso confirma: se UI envia explicitamente 0,00, o sistema usa o plano.
        Comportamento intencional ou bug? Documentado para revisão.
        """
        defaults = self._resolve(
            initial_payment_amount=Decimal('0.00'),
            selected_plan_price=Decimal('99.00'),
        )
        # FINDING: 0.00 é coalescido como falsy → vai para o plano
        self.assertEqual(defaults.base_amount, Decimal('99.00'))
