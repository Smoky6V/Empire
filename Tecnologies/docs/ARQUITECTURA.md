# Empire — Arquitectura, usuarios, autenticación, autorización y API

Este documento resume la evolución de seguridad y arquitectura aplicada al
proyecto. No sustituye a los comentarios en el propio código, que explican
el "por qué" de cada decisión puntual.

## Arquitectura

El proyecto sigue siendo un monolito Django clásico (server-side rendering
con templates), sin frontend separado ni SPA:

```
Tecnologies/
├── manage.py
├── requirements.txt
├── .env.example          # nombres de variables, sin valores reales
├── Tecnologies/
│   ├── settings/
│   │   ├── __init__.py   # elige dev.py o prod.py según DJANGO_ENV
│   │   ├── base.py       # config común, lee todo desde variables de entorno
│   │   ├── dev.py
│   │   └── prod.py
│   └── urls.py           # monta /admin/, /api/ y las rutas web existentes
├── accounts/              # Custom User Model + helpers de autorización
│   ├── models.py         # Usuario(AbstractUser)
│   ├── authz.py          # resolve_template_for_user, group_required
│   └── tests.py
├── api/                   # API REST bajo /api/, separada de la web
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
├── myapp/                 # vistas web existentes (login, registro, index...)
│   ├── views.py
│   └── tests.py
└── templates/
```

La web y la API comparten el mismo mecanismo de sesión de Django; la API no
reemplaza ni duplica la web, solo cubre los casos donde un cliente no-HTML
(app móvil futura, integraciones) necesita los mismos datos/acciones.

## Usuarios

- Modelo: `accounts.Usuario`, un Custom User Model mínimo (`AbstractUser`
  sin campos adicionales). Se introdujo ahora, con la base de datos vacía,
  para evitar una migración de usuario mucho más costosa y riesgosa más
  adelante.
- Registro (`/register`, vista `myapp.views.register`): crea el usuario con
  `create_user` (contraseña hasheada con el hasher por defecto de Django,
  PBKDF2), valida la contraseña contra `AUTH_PASSWORD_VALIDATORS` y lo
  añade automáticamente al grupo `Usuarios`.
- Login/Logout (`/login`, `/logout`): usan `authenticate()`/`login()`/
  `logout()` nativos de Django, sin cambios de comportamiento para el
  usuario final.

## Autenticación

- **Web:** sesiones y cookies nativas de Django (sin cambios respecto al
  comportamiento original). Es la opción correcta para una aplicación
  tradicional servida por el propio Django.
- **API (`/api/`):** `SessionAuthentication` de Django REST Framework —
  reutiliza la misma sesión que la web, sin introducir un segundo sistema
  de autenticación.
- **JWT:** deliberadamente no implementado. Si en el futuro se necesita una
  app móvil (que no puede depender de cookies de navegador), la
  recomendación es introducir tokens opacos y revocables (DRF
  `TokenAuthentication` o `django-rest-knox`) como una clase de
  autenticación **adicional**, sin tocar la autenticación de la web.

## Autorización

- Los grupos de Django se mantienen: `Administradores`, `Clientes`,
  `Vendedores`, `Usuarios`.
- La decisión de "qué puede ver cada rol" ya no vive dispersa en `if/elif`
  dentro de una vista: está centralizada en `accounts/authz.py`
  (`resolve_template_for_user`, `ROLE_TEMPLATES`, `group_required`), para
  que tanto vistas web futuras como la API reutilicen la misma fuente de
  verdad.
- La API nunca confía en datos enviados por el cliente para decidir
  permisos: `PATCH /api/users/me/` ignora cualquier intento de modificar
  `is_staff`/`is_superuser`/`groups` (verificado con test específico de
  intento de escalada de privilegios).
- Los endpoints de "mi perfil" operan siempre sobre `request.user`, nunca
  reciben un ID de otro usuario por URL o body, por lo que no hay
  superficie para IDOR/BOLA en la API actual.

## API

Base: `/api/`. Todos requieren `Content-Type: application/json` salvo que
se indique lo contrario.

| Método | Endpoint | Auth | Permiso | Descripción |
|---|---|---|---|---|
| POST | `/api/auth/login/` | Ninguna | Pública | Inicia sesión (misma sesión que la web) |
| POST | `/api/auth/logout/` | Sesión | Usuario autenticado | Cierra sesión |
| GET | `/api/users/me/` | Sesión | Usuario autenticado | Datos propios (sin password/hash) |
| PATCH | `/api/users/me/` | Sesión | Usuario autenticado (dueño implícito) | Edita datos propios; `groups`/`is_staff`/`is_superuser` no son editables |
| POST | `/api/auth/password/change/` | Sesión | Usuario autenticado | Cambia la contraseña propia, valida `old_password` y fortaleza de la nueva |

Todos los endpoints sensibles (`login`, `password/change`) usan
`throttle_scope = "auth"` (10 peticiones/minuto por defecto, configurable en
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`).

No se crearon endpoints de administración (listar/gestionar usuarios de
otros) porque hoy no hay un caso de uso real para ellos; añadirlos sin
necesidad solo aumentaría la superficie de ataque.

## Variables de entorno

Ver `.env.example` para la lista completa. Resumen (sin valores):

- `DJANGO_ENV` — `development` o `production`
- `DJANGO_SECRET_KEY` — obligatoria, sin valor por defecto
- `DJANGO_ALLOWED_HOSTS` — obligatoria en producción
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `DJANGO_HSTS_SECONDS` — opcional, solo producción

## Seguridad implementada

- `SECRET_KEY` y credenciales de MySQL: ya no están en el código, se leen
  de variables de entorno. **Los valores anteriores (encontrados durante la
  auditoría) deben tratarse como comprometidos y rotarse** antes de
  desplegar; no se han reutilizado en ningún archivo de este proyecto.
- `myapp/db.py` (script suelto con una tercera credencial MySQL hardcodeada
  y sin uso real) fue eliminado.
- `DEBUG=False` por defecto en producción; solo `True` en desarrollo.
- `ALLOWED_HOSTS` obligatorio y sin default en producción.
- HTTPS/HSTS, cookies `Secure`/`HttpOnly`/`SameSite`, `X-Content-Type-
  Options`, `Referrer-Policy`, `X-Frame-Options: DENY` configurados en
  `settings/prod.py` (verificado con `manage.py check --deploy`, sin
  advertencias salvo la propia de la SECRET_KEY de prueba usada en la
  verificación).
- Rate limiting con `django-ratelimit` (login/registro web) y con el
  throttling nativo de DRF (`scope="auth"`) en los endpoints de API
  equivalentes.
- Validación de fortaleza de contraseña (`AUTH_PASSWORD_VALIDATORS`) tanto
  en el registro web como en el cambio de contraseña por API.
- La API nunca devuelve `password`, hashes, ni permite auto-escalar
  `is_staff`/`is_superuser`/`groups`.
- CORS: no instalado (no hace falta con el mismo origen); queda documentado
  para cuándo y cómo añadirlo si un frontend externo empieza a consumir la
  API.

## Tests ejecutados

`python manage.py test` — **26 tests, todos en verde**:

- `accounts`: creación de usuario y hashing de contraseña, confirmación de
  que el modelo activo es el Custom User.
- `myapp`: registro (éxito, contraseña débil, username/email duplicado),
  login (correcto, incorrecto, rate limiting), logout, autorización por rol
  en `index` (anónimo, usuario normal, administrador, y que un usuario sin
  el grupo correcto **no** vea el panel de admin).
- `api`: login (éxito, credenciales inválidas, datos inválidos, rate
  limiting), `me` (requiere autenticación, no expone campos sensibles,
  **no permite escalar privilegios**), cambio de contraseña (old_password
  incorrecto, contraseña débil rechazada, éxito manteniendo la sesión),
  logout.

## Pendientes / riesgos que todavía existen

- **Bug preexistente, no corregido por no ser parte del alcance de
  seguridad:** `myapp.views.index` (a través de `accounts.authz`) referencia
  las plantillas `cliente_dashboard.html` y `vendedor_dashboard.html`, que
  **no existen** en `templates/`. Un usuario en el grupo `Clientes` o
  `Vendedores` obtendrá un error 500 (`TemplateDoesNotExist`) al visitar
  `/`. Habría que crear esas plantillas o decidir qué deben mostrar esos
  roles.
- Confirmar que la base de datos MySQL de destino esté realmente vacía
  antes de aplicar `migrate` en un entorno que no sea este sandbox de
  pruebas.
- Si en el futuro se expone la API a un origen distinto (frontend
  separado, app móvil web), añadir `django-cors-headers` con whitelist
  explícita.
- Si se añade una app móvil nativa, evaluar `django-rest-knox` (o
  `TokenAuthentication`) en vez de JWT, según lo razonado en este
  documento.
- Rotar `SECRET_KEY` y credenciales MySQL antes de cualquier despliegue,
  ya que las anteriores quedaron expuestas durante la auditoría.
- El `.gitignore` ya excluye `.env`; verificar que ningún `.env` real haya
  quedado versionado en el historial de git si el proyecto ya tenía commits
  previos con las credenciales antiguas.
