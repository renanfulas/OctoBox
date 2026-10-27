"""Holds a tenant fence lease around every tenant-routed HTTP request."""

import logging

from django.http import HttpResponse

from control.tenant_write_fence import TenantWritesFrozen, tenant_write_guard

logger = logging.getLogger('control.tenant_write_fence')


class TenantWriteFenceMiddleware:
    """Drain in-flight requests and reject traffic for a frozen tenant."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return self.get_response(request)

        schema_name = getattr(tenant, 'schema_name', '')
        try:
            with tenant_write_guard(schema_name):
                return self.get_response(request)
        except TenantWritesFrozen:
            logger.info(
                'tenant_request_write_frozen method=%s',
                request.method,
            )
            response = HttpResponse(
                'Este box está temporariamente pausado para uma operação de recuperação.',
                status=503,
                content_type='text/plain; charset=utf-8',
            )
            response['Retry-After'] = '60'
            response['Cache-Control'] = 'no-store'
            response['X-Octobox-Tenant-Frozen'] = '1'
            return response


__all__ = ['TenantWriteFenceMiddleware']
