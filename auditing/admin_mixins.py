"""
ARQUIVO: mixins de auditoria para o Django admin.

POR QUE ELE EXISTE:
- Evita repetir a mesma logica de auditoria em cada ModelAdmin sem acoplar o admin de outros apps ao pacote boxcore.admin.

O QUE ESTE ARQUIVO FAZ:
1. Audita criacao e edicao feitas no admin.
2. Audita exclusao individual e em massa.
3. Marca eventos financeiros como mais sensiveis para investigacao futura.

PONTOS CRITICOS:
- O mixin depende de request.user estar disponivel no ciclo padrao do admin.
- Alteracoes aqui afetam a rastreabilidade do backoffice inteiro.
"""

from auditing import log_audit_event


class AuditedAdminMixin:
    financial_model_names = {'membershipplan', 'enrollment', 'payment'}

    def _build_metadata(self, obj, *, changed_fields=None, bulk_count=None):
        model_name = obj._meta.model_name
        metadata = {
            'changed_fields': changed_fields or [],
            'is_financial': model_name in self.financial_model_names,
        }
        if bulk_count is not None:
            metadata['bulk_count'] = bulk_count
        return metadata

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        action = f'admin_change_{obj._meta.model_name}' if change else f'admin_add_{obj._meta.model_name}'
        description = 'Alteracao realizada pelo Django admin.' if change else 'Criacao realizada pelo Django admin.'
        log_audit_event(
            actor=request.user,
            action=action,
            target=obj,
            description=description,
            metadata=self._build_metadata(obj, changed_fields=list(getattr(form, 'changed_data', []))),
        )

    def delete_model(self, request, obj):
        cached_obj = obj
        super().delete_model(request, obj)
        log_audit_event(
            actor=request.user,
            action=f'admin_delete_{cached_obj._meta.model_name}',
            target=cached_obj,
            description='Exclusao individual realizada pelo Django admin.',
            metadata=self._build_metadata(cached_obj),
        )

    def delete_queryset(self, request, queryset):
        cached_objects = list(queryset)
        super().delete_queryset(request, queryset)

        for obj in cached_objects:
            log_audit_event(
                actor=request.user,
                action=f'admin_bulk_delete_{obj._meta.model_name}',
                target=obj,
                description='Exclusao em massa realizada pelo Django admin.',
                metadata=self._build_metadata(obj, bulk_count=len(cached_objects)),
            )
