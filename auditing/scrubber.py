"""
ARQUIVO: Filtro Forense e Sanitizador de Identificação (PIIScrubber).

POR QUE ELE EXISTE:
- Impedir Vazamento de Dados dentro do próprio banco (Audit Log Poisoning).
- Se desenvolvedores passarem request.POST inteiro pro Log, a auditoria grava dados que não deveria possuir.

O QUE ESTE ARQUIVO FAZ:
1. Inspeciona Arrays e Dicionários de forma recursiva (Deep Scan).
2. Substitui valores cuja chave contenha os termos 'password', 'cpf', 'key', 'phone', etc., pelo marcador seguro [REDACTED].
3. Retorna o Objeto esterilizado para gravação limpa.

PONTOS CRITICOS:
- Precisa ser rápido e evitar stack overflows em dicts mutantes profundamente aninhados.
"""

import copy
import re

class PIIScrubber:
    # 🕵️‍♂️ Chaves malditas que nunca devem pisar no disco legíveis:
    SENSITIVE_KEYS = {
        'cpf', 'telefone', 'phone', 'celular', 'mobile',
        'password', 'senha', 'secret', 'key', 'token',
        'cvc', 'card_number', 'authorization', 'email', 'e-mail', 'mail',
        'recipient', 'username', 'student_name', 'full_name', 'display_name',
        'subject_label', 'client_ip', 'ip_address', 'address', 'endereco',
        'date_of_birth', 'birth_date', 'dob', 'nascimento', 'height', 'altura',
        'weight', 'peso', 'note', 'notes', 'path',
    }
    
    REDACTED_MARKER = '[REDACTED]'

    @classmethod
    def sanitize(cls, data):
        """Esteriliza um dicionário ou lista de forma deep-copy, mascarando as chaves radioativas"""
        if not data:
            return data
            
        return cls._scrub_recursive(copy.deepcopy(data))

    @classmethod
    def _scrub_recursive(cls, item):
        if isinstance(item, dict):
            for k, v in item.items():
                key = k.lower() if isinstance(k, str) else ''
                is_free_text_reason = key in {
                    'reason', 'revoke_reason', 'change_reason', 'free_text_reason', 'reason_text',
                    'rejection_reason', 'approval_reason_note',
                }
                is_safe_hash = (
                    key in {'token_hash', 'ip_hash'}
                    and isinstance(v, str)
                    and re.fullmatch(r'[0-9a-fA-F]{8,128}', v) is not None
                )
                if (
                    not is_safe_hash
                    and key
                    and (is_free_text_reason or any(sk in key for sk in cls.SENSITIVE_KEYS))
                ):
                    item[k] = cls.REDACTED_MARKER
                else:
                    item[k] = cls._scrub_recursive(v)
            return item
        elif isinstance(item, list):
            return [cls._scrub_recursive(v) for v in item]
        return item
