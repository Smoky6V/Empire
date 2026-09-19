"""
Punto de entrada de settings. Selecciona el módulo real según la
variable de entorno DJANGO_ENV:

    DJANGO_ENV=production  -> settings/prod.py
    (cualquier otro valor,
     o sin definir)        -> settings/dev.py   (por defecto)

Esto evita tener que tocar manage.py / wsgi.py / asgi.py: todos siguen
apuntando a 'Tecnologies.settings' como antes.
"""

import os

if os.environ.get('DJANGO_ENV') == 'production':
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
