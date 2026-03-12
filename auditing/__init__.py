"""
ARQUIVO: app Django real de auditoria.

POR QUE ELE EXISTE:
- Separa rastreabilidade, trilha de eventos e sinais do app institucional boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace do app auditing.
2. Centraliza a fronteira real de auditoria.

PONTOS CRITICOS:
- Sinais e escrita de eventos daqui sao transversais e impactam o sistema inteiro.
"""

def log_audit_event(*args, **kwargs):
	from .services import log_audit_event as _log_audit_event

	return _log_audit_event(*args, **kwargs)


__all__ = ['log_audit_event']
