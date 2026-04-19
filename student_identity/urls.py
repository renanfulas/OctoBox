from django.urls import path

from .views import (
    StudentBoxInviteLandingView,
    StudentInviteLandingView,
    StudentOAuthCallbackView,
    StudentOAuthStartView,
    StudentSignInView,
    StudentSignOutView,
)


urlpatterns = [
    path('login/', StudentSignInView.as_view(), name='student-identity-login'),
    path('logout/', StudentSignOutView.as_view(), name='student-identity-logout'),
    path('invite/<uuid:token>/', StudentInviteLandingView.as_view(), name='student-identity-invite'),
    path('box-invite/<uuid:token>/', StudentBoxInviteLandingView.as_view(), name='student-identity-box-invite'),
    path('oauth/<slug:provider>/start/', StudentOAuthStartView.as_view(), name='student-identity-oauth-start'),
    path('oauth/<slug:provider>/callback/', StudentOAuthCallbackView.as_view(), name='student-identity-oauth-callback'),
]
