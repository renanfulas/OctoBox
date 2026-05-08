"""
ARQUIVO: form de captura Early Adopter da landing.

POR QUE ELE EXISTE:
- Mantem o checkout publico com o minimo de friccao: 4 campos essenciais.
- Centraliza validacoes e mascara de telefone fora do template.

O QUE ESTE ARQUIVO FAZ:
1. Coleta email, nome do dono, nome do box e telefone.
2. Normaliza o email em lowercase para evitar duplicacao silenciosa.
3. Limita tamanho de campo para impedir payloads abusivos.

PONTOS CRITICOS:
- Nao pede CPF/CNPJ aqui: dado fiscal entra no Stripe Checkout (Tax ID collection).
- Nao pede senha: a senha sera criada apenas pos-pagamento via magic link.
"""
from __future__ import annotations

import re

from django import forms


_PHONE_DIGITS_RE = re.compile(r'\D+')


class CheckoutForm(forms.Form):
    """Form minimo do checkout publico Early Adopter."""

    email = forms.EmailField(
        label='Seu melhor e-mail',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'inputmode': 'email',
            'placeholder': 'voce@seubox.com.br',
            'autofocus': 'autofocus',
        }),
    )
    full_name = forms.CharField(
        label='Seu nome',
        max_length=120,
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'placeholder': 'Como voce quer ser chamado',
        }),
    )
    box_name = forms.CharField(
        label='Nome do box',
        max_length=120,
        widget=forms.TextInput(attrs={
            'autocomplete': 'organization',
            'placeholder': 'CrossFit ABC, Box do Joao, etc.',
        }),
    )
    phone = forms.CharField(
        label='WhatsApp',
        max_length=32,
        widget=forms.TextInput(attrs={
            'autocomplete': 'tel',
            'inputmode': 'tel',
            'placeholder': '(11) 99999-9999',
        }),
        help_text='Vamos chamar voce em ate 12h para guiar o setup.',
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()

    def clean_box_name(self):
        return self.cleaned_data['box_name'].strip()

    def clean_phone(self):
        raw = self.cleaned_data['phone']
        digits = _PHONE_DIGITS_RE.sub('', raw)
        if len(digits) < 10:
            raise forms.ValidationError('Informe um telefone com DDD valido.')
        return digits


_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.-]{3,32}$')


class OnboardingForm(forms.Form):
    """Define username e senha do Owner apos pagamento confirmado.

    O email ja esta confirmado pelo Stripe; nao pedimos novamente.
    """

    username = forms.CharField(
        label='Nome de usuário',
        max_length=32,
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'placeholder': 'ex: joao.crossfitsul',
            'autofocus': 'autofocus',
        }),
        help_text='Apenas letras, números, ponto, hífen e underscore. De 3 a 32 caracteres.',
    )
    password = forms.CharField(
        label='Crie uma senha',
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Mínimo 10 caracteres',
        }),
        min_length=10,
        max_length=128,
    )
    password_confirm = forms.CharField(
        label='Confirme a senha',
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Repita a mesma senha',
        }),
        min_length=10,
        max_length=128,
    )

    def clean_username(self):
        value = self.cleaned_data['username'].strip()
        if not _USERNAME_RE.match(value):
            raise forms.ValidationError(
                'Use apenas letras, números, ponto, hífen e underscore (3 a 32 caracteres).'
            )
        return value.lower()

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'As senhas não conferem.')
        return cleaned
