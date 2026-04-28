from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from operations.class_session_types import infer_class_type_from_session_title
from operations.models import ClassSession, ClassType


class ClassSessionClassTypeTests(TestCase):
    def test_infer_class_type_from_session_title_uses_conservative_keywords(self):
        self.assertEqual(infer_class_type_from_session_title('Cross 07h'), ClassType.CROSS)
        self.assertEqual(infer_class_type_from_session_title('Mobilidade 18h'), ClassType.MOBILITY)
        self.assertEqual(infer_class_type_from_session_title('Halterofilia tecnica'), ClassType.OLY)
        self.assertEqual(infer_class_type_from_session_title('Forca base'), ClassType.STRENGTH)
        self.assertEqual(infer_class_type_from_session_title('Open Gym domingo'), ClassType.OPEN_GYM)
        self.assertEqual(infer_class_type_from_session_title('Turma especial'), ClassType.OTHER)

    def test_class_session_defaults_to_other_until_typed_explicitly(self):
        session = ClassSession.objects.create(
            title='Turma especial',
            scheduled_at=timezone.make_aware(datetime(2026, 4, 24, 12, 0)),
            duration_minutes=60,
            capacity=12,
        )

        self.assertEqual(session.class_type, ClassType.OTHER)
