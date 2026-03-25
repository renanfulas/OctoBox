from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role

class AdvisorDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    View exclusiva para o painel do Conselheiro (Manager/Owner).
    Fornece o contexto narrativo, micro-tendências e radar de fuga.
    """
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
    template_name = 'dashboard/conselheiro.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_role = get_user_role(self.request.user)
        context['current_role'] = current_role
        context['page_title'] = 'O Conselheiro'
        context['current_page_assets'] = {'css': [], 'js': []}
        
        # O contexto real interativo (Frase-mestra, Radar) seria alimentado por 
        # queries consolidadas aqui. No momento, o template assumirá o layout Base.
        
        return context
