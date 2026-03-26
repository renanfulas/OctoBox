from django.db import models
from django.conf import settings

class IdempotencyKey(models.Model):
    """
    Guarda chaves de requisições para evitar que a mesma ação ocorra duas vezes.
    
    É como um 'ticket' de cinema: uma vez usado, ele fica carimbado e não pode 
    ser usado de novo para entrar na mesma sessão.
    """
    key = models.CharField(max_length=255, unique=True, help_text="A chave única enviada pelo cliente (ex: UUID)")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="O usuário que fez a requisição"
    )
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True, help_text="A resposta salva para ser retornada se houver repetição")
    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField(null=True, blank=True, help_text="Usado como trava para evitar processamento simultâneo")

    class Meta:
        db_table = 'idempotency_keys'
        indexes = [
            models.Index(fields=['key']),
        ]

    def __str__(self):
        return f"{self.key} ({self.user})"
