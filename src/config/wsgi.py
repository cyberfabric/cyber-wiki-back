"""
WSGI config for CyberWiki backend.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_path))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
