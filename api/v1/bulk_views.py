import logging
from django.http import JsonResponse
from django.views import View
from django.db import transaction

logger = logging.getLogger(__name__)

from api.v1.views import RoleRequiredMixin, ROLE_OWNER, ROLE_MANAGER

class GenericBulkActionView(RoleRequiredMixin, View):
    """
    FIX 3: HTTP 207 Multi-Status API for Partial Commits.
    Handles bulk updates by isolating each item into its own transaction context. 
    Secured with RoleRequiredMixin (Epic 8).
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        import json
        payload = json.loads(request.body)
        
        item_ids = payload.get('item_ids', [])
        action = payload.get('action')
        
        results = {
            "success": [],
            "failed": []
        }

        for item_id in item_ids:
            try:
                # Isolamento de transação por item (Partial-Commit)
                with transaction.atomic():
                    self.perform_action(item_id, action, request.user)
                results["success"].append({"id": item_id, "status": "ok"})
            except Exception as e:
                # Falha granular não anula o lote
                logger.error(f"Bulk action failed for item {item_id}: {str(e)}")
                results["failed"].append({"id": item_id, "error": str(e)})

        # Retorna 207 Multi-Status: Parcialmente OK ou Totalmente OK
        http_status = 207 if results["failed"] else 200
        if not results["success"] and results["failed"]:
            http_status = 400  # Todos falharam
            
        return JsonResponse(results, status=http_status)

    def perform_action(self, item_id, action, user):
        """
        Hook para ser sobrescrito por classes concretas (Students, Payments, etc).
        """
        pass
