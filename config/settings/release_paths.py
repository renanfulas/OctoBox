"""Filesystem settings that must follow the immutable application release."""

import os
from pathlib import Path


def build_release_path_settings(base_dir):
    return {
        'STATIC_ROOT': Path(os.getenv('OCTOBOX_STATIC_ROOT', str(base_dir / 'staticfiles'))),
        'STATICFILES_DIRS': [path for path in [base_dir / 'static'] if path.exists()],
        'MEDIA_ROOT': Path(os.getenv('OCTOBOX_MEDIA_ROOT', str(base_dir / 'media'))),
        'MEDIA_URL': '/media/',
    }


__all__ = ['build_release_path_settings']
