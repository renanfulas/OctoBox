"""
ARQUIVO: formularios de autenticacao do modulo de acesso.

POR QUE ELE EXISTE:
- endurece a entrada do login com atributos consistentes de digitacao.

O QUE ESTE ARQUIVO FAZ:
1. aplica placeholders e limites ao login.
2. evita digitacao solta no campo de usuario.
3. permite criar perfis operacionais sem abrir o admin.

PONTOS CRITICOS:
- muda a experiencia da tela de login inteira.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .roles import ROLE_DEFINITIONS


class AccessAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Seu usuario interno',
            'maxlength': '150',
            'autocomplete': 'username',
            'spellcheck': 'false',
            'aria-describedby': 'login-username-note',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Sua senha',
            'autocomplete': 'current-password',
            'aria-describedby': 'login-password-note',
        })


class AccessProfileCreateForm(forms.Form):
    full_name = forms.CharField(label='Nome completo', max_length=150)
    username = forms.CharField(label='Usuario', max_length=150)
    email = forms.EmailField(label='E-mail', required=False)
    password = forms.CharField(label='Senha provisoria', widget=forms.PasswordInput(render_value=True), max_length=128)
    role = forms.ChoiceField(
        label='Papel',
        choices=[(role.slug, role.label) for role in ROLE_DEFINITIONS],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs.update({'placeholder': 'Nome da pessoa'})
        self.fields['username'].widget.attrs.update({'placeholder': 'usuario.interno', 'autocomplete': 'off'})
        self.fields['email'].widget.attrs.update({'placeholder': 'email@empresa.com'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Senha inicial segura', 'autocomplete': 'new-password'})

    def clean_username(self):
        return self.cleaned_data['username'].strip()

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()


class AccessProfileUpdateForm(forms.Form):
    full_name = forms.CharField(label='Nome completo', max_length=150)
    email = forms.EmailField(label='E-mail', required=False)
    role = forms.ChoiceField(
        label='Papel',
        choices=[(role.slug, role.label) for role in ROLE_DEFINITIONS],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs.update({'placeholder': 'Nome da pessoa'})
        self.fields['email'].widget.attrs.update({'placeholder': 'email@empresa.com'})

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()