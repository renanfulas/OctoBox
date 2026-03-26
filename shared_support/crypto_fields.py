"""
ARQUIVO: Engine de Criptografia Simétrica do Sistema.

POR QUE ELE EXISTE:
- Prevenir que backups vazados exponham PII (Personal Identifiable Information).
- Atender a requisitos severos da LGPD/PCI-DSS para aplicacoes financeiras.

O QUE ESTE ARQUIVO FAZ:
1. Define um Campo de Banco de Dados (`EncryptedCharField`) que intercepta dados indo para o Banco e os criptografa (Fernet).
2. Intercepta dados voltando do Banco e os descriptografa na memoria do Python de forma transparente.
3. Possui um "Modo Fallback" para nao quebrar o sistema ao ler CPFs e Telefones antigos (plain text) que ainda nao foram re-salvos com a chave nova.

PONTOS CRITICOS:
- Se a SECRET_KEY mudar, todos os dados cifrados ficam inacessíveis. Em producao, a chave base deve ser guardada em cofre (KMS/Vault).
"""

import base64
import logging
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models
from django.utils.encoding import force_bytes, force_str

logger = logging.getLogger(__name__)

# Derivamos uma chave de 32 bytes validos em base64 a partir do SECRET_KEY do Django
# Se não for de 32 bytes o Fernet crasha, entao fazemos um pad/slice deterministico
_raw_key = force_bytes(settings.SECRET_KEY)[:32].ljust(32, b'O')
CRYPTO_KEY = base64.urlsafe_b64encode(_raw_key)

try:
    cipher_suite = Fernet(CRYPTO_KEY)
except Exception as e:
    logger.critical(f"Falha gravíssima ao instanciar Suite Criptográfica. Database será Plain-Text. Erro: {e}")
    cipher_suite = None

class EncryptedCharField(models.CharField):
    """
    Campo que mascara dados PII de forma transparente.
    No banco de dados: gAAAAABkO_Pqxyz... (Criptografado AES-128)
    No Python/Views: 123.456.789-00 (Decifrado)
    """
    description = "String PII criptografada com AES/Fernet"

    def get_internal_type(self):
        # Para o ORM, é apenas um CharField (que aceita base64 longo)
        return "CharField"

    def get_prep_value(self, value):
        # Python -> Database (Cifrador)
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value

        if not cipher_suite:
            return value  # Fallback de desespero se engine cripto quebrar

        try:
            # Se já está criptografado (tem cabeçalho padrão Fernet gAAAAA...), nao cifra de novo.
            str_val = force_str(value)
            if str_val.startswith("gAAAAA"):
                return value
                
            encrypted = cipher_suite.encrypt(force_bytes(value))
            return force_str(encrypted)
        except Exception as e:
            logger.error(f"Erro ao criptografar PII: {e}")
            return value

    def from_db_value(self, value, expression, connection):
        # Database -> Python (Decifrador)
        if value is None or value == '':
            return value

        if not cipher_suite:
            return value
            
        try:
            str_val = force_str(value)
            # Se não parece ter o header do Fernet, assume que é legacy/plain-text (ex: telefones antigos) e retorna puro.
            if not str_val.startswith("gAAAAA"):
                return value
                
            decrypted = cipher_suite.decrypt(force_bytes(value))
            return force_str(decrypted)
        except InvalidToken:
            # Token criptográfico rasgado ou migração parcial, assumimos que sobrou lixo ou é legado
            return value
        except Exception as e:
            logger.error(f"Falha de decifragem PII em load: {e}")
            return value

    def to_python(self, value):
        # Inputs e forms convertendo pra obj
        if getattr(self, '_is_db_value', False):
            # Se veio do DB, foi tratado no from_db_value. Aqui tratamos input sujo normal.
            pass
        return super().to_python(value)

class EncryptedTextField(models.TextField):
    """
    Campo de texto longo (Notas, Corpos de Mensagem) criptografado.
    """
    description = "Texto longo PII criptografado com AES/Fernet"

    def get_internal_type(self):
        return "TextField"

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        if not cipher_suite:
            return value
        try:
            str_val = force_str(value)
            if str_val.startswith("gAAAAA"):
                return value
            encrypted = cipher_suite.encrypt(force_bytes(value))
            return force_str(encrypted)
        except Exception as e:
            logger.error(f"Erro ao criptografar PII (Text): {e}")
            return value

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        if not cipher_suite:
            return value
        try:
            str_val = force_str(value)
            if not str_val.startswith("gAAAAA"):
                return value
            decrypted = cipher_suite.decrypt(force_bytes(value))
            return force_str(decrypted)
        except InvalidToken:
            return value
        except Exception as e:
            logger.error(f"Falha de decifragem PII em load (Text): {e}")
            return value
