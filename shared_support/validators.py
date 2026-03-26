import os
import logging
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_security(file_path: str, max_size_mb: int = 15, allowed_mimes: list[str] = None):
    """
    🚀 Verificador de Segurança de Arquivos (Fintech Hardening)
    
    O que faz:
    1. Verifica o tamanho no disco (rápido).
    2. Verifica o MIME TYPE real (lendo os 'magic numbers' do arquivo).
    3. Protege o sistema contra executáveis disfarçados de CSV/PNG.
    """
    # 1. Checagem de Tamanho
    file_size = os.path.getsize(file_path)
    if file_size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _("Arquivo muito grande. Limite máximo é de %(limit)s MB."),
            params={'limit': max_size_mb}
        )

    # 2. Checagem de MIME Type (Magic Numbers)
    if allowed_mimes:
        try:
            import magic
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_file(file_path)
        except ImportError:
            import mimetypes
            detected_mime, _ = mimetypes.guess_type(file_path)
            logging.getLogger('octobox.security').warning(
                "python-magic não instalado. Usando mimetypes (menos seguro). Instale libmagic para proteção real."
            )
        
        if detected_mime not in allowed_mimes:
            raise ValidationError(
                _("Tipo de arquivo não permitido (%(mime)s). Envie um arquivo válido."),
                params={'mime': detected_mime}
            )
    
    return True
