import random

def get_cache_ttl_with_jitter(base_ttl: int, jitter_percentage: float = 0.1) -> int:
    """
    🚀 Performance de Elite (Ghost Hardening): Cache Jitter.
    Adiciona um ruido aleatorio ao tempo de expiração do cache (TTL).
    Isso evita o "Cache Stampede" (Efeito Manada), onde milhares de chaves
    expiram no mesmo milissegundo, sobrecarregando o banco de dados.
    """
    if base_ttl <= 0:
        return base_ttl
        
    variation = int(base_ttl * jitter_percentage)
    return base_ttl + random.randint(-variation, variation)
