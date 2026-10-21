"""Detalhe operacional de treino, isolado do funil de aquisição."""

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from public_workouts.models import PublicWorkoutTrainingSession
from .public_workout_views import PublicWorkoutAnalyticsAccessMixin


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutTrainingSessionDetailView(PublicWorkoutAnalyticsAccessMixin, TemplateView):
    template_name = 'public_workouts/training_session_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = get_object_or_404(
            PublicWorkoutTrainingSession.objects.select_related('account', 'program').prefetch_related('sets'),
            pk=self.kwargs['session_id'],
        )
        context['session'] = session
        context['sets'] = list(session.sets.all())
        context['analytics_username'] = self.request.analytics_username
        return context
