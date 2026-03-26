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

class PIIScrubber:
    # 🕵️‍♂️ Chaves malditas que nunca devem pisar no disco legíveis:
    SENSITIVE_KEYS = {
        'cpf', 'telefone', 'phone', 'celular', 'mobile',
        'password', 'senha', 'secret', 'key', 'token',
        'cvc', 'card_number', 'authorization'
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
                if isinstance(k, str) and any(sk in k.lower() for sk in cls.SENSITIVE_KEYS):
                    item[k] = cls.REDACTED_MARKER
                else:
                    item[k] = cls._scrub_recursive(v)
            return item
        elif isinstance(item, list):
            return [cls._scrub_recursive(v) for v in item]
        return item
