"""
ARQUIVO: formularios de autenticacao do modulo de acesso.

POR QUE ELE EXISTE:
- endurece a entrada do login com atributos consistentes de digitacao.

O QUE ESTE ARQUIVO FAZ:
1. aplica placeholders e limites ao login.
2. evita digitacao solta no campo de usuario.

PONTOS CRITICOS:
- muda a experiencia da tela de login inteira.
"""

from django.contrib.auth.forms import AuthenticationForm


class AccessAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Seu usuario interno',
            'maxlength': '150',
            'autocomplete': 'username',
            'spellcheck': 'false',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Sua senha',
            'autocomplete': 'current-password',
        })