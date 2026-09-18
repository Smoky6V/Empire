from django.db import models

# El antiguo modelo `Usuario` (nombre/email/edad) definido aqui no se
# utilizaba en ninguna vista ni formulario del proyecto (verificado por
# busqueda en todo el codigo) y entraba en conflicto de nombre con el nuevo
# Custom User Model (accounts.Usuario). Se retira por ser codigo muerto.
# No existian migraciones previas para este modelo, por lo que no se pierde
# historial de migraciones al eliminarlo.
