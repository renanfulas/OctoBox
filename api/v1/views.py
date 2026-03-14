"""
ARQUIVO: views iniciais da API v1.

POR QUE ELE EXISTE:
- Fornece endpoints minimos de saude e manifesto para preparar clientes externos e app mobile.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da versao v1.
2. Publica um endpoint de saude estavel.
3. Publica o autocomplete de busca global de alunos.

PONTOS CRITICOS:
- Endpoints versionados devem permanecer previsiveis e pequenos.
- O autocomplete limita resultados a 10 e exige autenticacao.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.views import View

from students.models import Student


class ApiV1ManifestView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'version': 'v1',
                'status': 'active',
                'resources': {
                    'health': '/api/v1/health/',
                    'student_autocomplete': '/api/v1/students/autocomplete/',
                },
                'scope': [
                    'foundation',
                    'mobile-ready-boundary',
                    'integration-ready-boundary',
                ],
            }
        )


class ApiV1HealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'status': 'ok',
                'version': 'v1',
                'product': 'OctoBox Control',
                'api_boundary': 'stable-entrypoint',
            }
        )


class StudentAutocompleteView(LoginRequiredMixin, View):
    """Retorna ate 10 alunos cujo nome, telefone ou CPF contem o termo digitado."""

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if len(query) < 1:
            return JsonResponse({'results': []})

        students = (
            Student.objects
            .filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(cpf__icontains=query)
            )
            .order_by('full_name')[:10]
        )

        results = [
            {
                'id': s.id,
                'name': s.full_name,
                'phone': s.phone,
                'status': s.get_status_display(),
                'status_raw': s.status,
                'url': f'/alunos/{s.id}/editar/',
            }
            for s in students
        ]

        return JsonResponse({'results': results})
