from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from communications.models import WhatsAppMessageLog
import logging

logger = logging.getLogger('octobox.security.gc')

class Command(BaseCommand):
    help = 'OctoBox Garbage Collector: Extermina Mensagens de WhatsApp defasadas (>7 dias) p/ evitar Database Bloat (Skin Changer Epic).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=================================================="))
        self.stdout.write(self.style.WARNING("INICIANDO OPERACAO SKIN CHANGER - GARBAGE COLLECTOR"))
        self.stdout.write(self.style.WARNING("=================================================="))
        
        # O Limite rigoroso (Rolling Log) de 7 dias aprovado pelo C-Level Architect
        cutoff_date = timezone.now() - timedelta(days=7)
        
        olds = WhatsAppMessageLog.objects.filter(created_at__lt=cutoff_date)
        total_olds = olds.count()
        
        if total_olds == 0:
            self.stdout.write(self.style.SUCCESS("[✔️] O Banco de Dados ja esta cristalino. Zero Webhooks pesados encontrados."))
            return
        
        self.stdout.write(f"[*] Triturando {total_olds} logs pesados de WhatsApp excedentes...")
        
        deleted, details = olds.delete()
        
        # Loga silenciosamente o Evento p/ possiveis analises de I/O futuras
        logger.info(f"Garbage Collector limpou {total_olds} logs antigos do sistema.")
        
        self.stdout.write(self.style.SUCCESS(f"[💣] KABUM! Operacao concluida. {total_olds} linhas apagadas do Postgres."))
        self.stdout.write(self.style.SUCCESS("O Banco de Dados agora respira como um Motor V8 limpo."))
