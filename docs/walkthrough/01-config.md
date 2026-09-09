# Part 1 · Entry points and settings

Covers `manage.py` and everything in `config/`. This is the wiring: the code that
starts Django and tells it what the project consists of. None of it is domain
logic, and all of it is load-bearing.

---

## `manage.py`

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

**`#!/usr/bin/env python`** — a shebang. It lets you run `./manage.py migrate`
directly rather than `python manage.py migrate`, provided the file is executable
(it is; the scaffold ran `chmod +x`). `env python` finds whichever Python is first
on your `PATH`, which is what you want inside a virtual environment.

**`import os`** — needed only for `os.environ` on the next line.

**`import sys`** — needed only for `sys.argv`, the list of command-line arguments.
`sys.argv[0]` is the script name, so `./manage.py migrate` gives
`["manage.py", "migrate"]`.

**`def main() -> None:`** — the `-> None` is a type annotation saying this returns
nothing. Python ignores it at runtime; it exists for readers and for type
checkers.

**`os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")`** —
this is the line that matters. Django finds its configuration through an
environment variable holding a Python import path. `setdefault` writes it *only
if it is not already set*, which is deliberate: it means

```bash
DJANGO_SETTINGS_MODULE=config.settings.test ./manage.py shell
```

still works. Using `os.environ[...] = ...` instead would silently overwrite what
the caller asked for.

The default is `dev` because `manage.py` is a development tool. Production runs
through `wsgi.py`, not through this file.

**`from django.core.management import execute_from_command_line`** — imported
*inside* the function, not at the top. That is intentional and Django's own
template does it: the import triggers Django's setup, which reads
`DJANGO_SETTINGS_MODULE`. If it ran at module import time it would happen *before*
the `setdefault` line, and the default would never apply.

**`execute_from_command_line(sys.argv)`** — hands the arguments to Django, which
finds the matching command (`migrate`, `makemigrations`, `shell`, `test`, and
anything defined in an app's `management/commands/` folder) and runs it.

**`if __name__ == "__main__":`** — standard Python. `__name__` is `"__main__"`
when the file is run directly and the module's name when it is imported. So the
guard means "only run `main()` if somebody executed this file", which keeps the
file importable without side effects.

---

## `config/settings/base.py`

The longest file in the project, and worth reading slowly, because every line is
a decision Django would otherwise make for you.

### The header

```python
"""Settings shared by every environment.

Nothing secret lives here; everything sensitive comes from the environment.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
```

**The docstring** states the invariant the file has to keep. It is worth writing
because the temptation to paste one API key "just for now" is real, and a
docstring is a small speed bump.

**`from pathlib import Path`** — the modern way to handle filesystem paths.
`Path` objects support the `/` operator (`BASE_DIR / ".env"`), which is both
readable and correct on every operating system, unlike string concatenation with
`"/"`.

**`import environ`** — `django-environ`, a third-party package that reads
configuration from environment variables with type coercion.

**`BASE_DIR = Path(__file__).resolve().parents[2]`** — the project root. Taken
apart:

- `__file__` is this file's path, possibly relative.
- `.resolve()` makes it absolute and follows symlinks.
- `.parents` is a sequence walking upward: `parents[0]` is `config/settings/`,
  `parents[1]` is `config/`, `parents[2]` is `backend/`.

So `BASE_DIR` is `backend/`. Everything else in the file builds paths from it,
which means the project works regardless of the directory you launched it from.

### Reading the environment

```python
env = environ.Env(DEBUG=(bool, False), ALLOWED_HOSTS=(list, []))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-do-not-use-in-prod")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
```

**`environ.Env(DEBUG=(bool, False), ...)`** — declares the *schema*. Each entry is
`NAME=(type, default)`. Environment variables are always strings; this is what
turns `"True"` into `True` and `"a,b,c"` into `["a", "b", "c"]`. Without it,
`if DEBUG:` would be true for the string `"False"`, which is a genuinely
dangerous bug.

**`environ.Env.read_env(BASE_DIR / ".env")`** — loads a `.env` file into
`os.environ` *if it exists*. On a laptop it does; in production it does not, and
the variables come from the process environment instead. Same code, both places.

**`SECRET_KEY`** — Django uses this to sign sessions, password-reset tokens and
CSRF tokens. Here it also keys the HMAC that hashes one-time codes. If it leaks,
sessions can be forged. The default is deliberately unusable-looking so that if
it ever escapes into production it is obvious in a traceback rather than looking
like a real key.

**`DEBUG`** — when true, Django shows full tracebacks in the browser, disables
template caching, and logs every SQL query. It must be false in production;
`DEBUG = True` on a public host leaks source code, settings names and SQL.

**`ALLOWED_HOSTS`** — a whitelist of `Host` headers Django will answer. It exists
to prevent host-header poisoning, where an attacker sends
`Host: evil.example.com` and any absolute URL your app generates (a password-reset
link, say) points at their domain. Django refuses any request whose host is not
listed.

### The application registry

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.common",
    "apps.geo",
    ...
]
```

This list is how Django discovers things. For each entry it imports the package
and looks for `models.py`, `admin.py`, a `migrations/` folder, `management/
commands/`, templates and static files.

Taking the Django ones in turn:

- **`admin`** — the automatic admin interface at `/admin/`.
- **`auth`** — users, groups, permissions, password hashing. Everything in
  `accounts/` builds on it.
- **`contenttypes`** — a registry of every model in the project, one row per
  model. `auth` uses it to attach permissions to models. It is also what
  `GenericForeignKey` would use, which this project avoids.
- **`sessions`** — server-side session storage, which is how the admin stays
  logged in.
- **`messages`** — the one-off "Saved successfully" notices in the admin.
- **`staticfiles`** — collects CSS and JS from every app into one directory for
  serving.
- **`postgres`** — Postgres-specific field and index types. Optional, and included
  because this project will never run on anything else.

Then the third-party ones:

- **`rest_framework`** — Django REST Framework: serialisers, viewsets,
  authentication, throttling.
- **`django_filters`** — turns query-string parameters into queryset filters.
- **`drf_spectacular`** — generates an OpenAPI schema from the code, which is what
  will produce typed clients for the Flutter app and the admin front end.

Order matters occasionally: apps earlier in the list win when two provide a
template with the same name. Local apps go last so they can override anything.

### Middleware

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

Middleware wraps every request. Each one runs top-to-bottom on the way in and
**bottom-to-top on the way out**, like layers of an onion — so this is not a list
of independent items, it is a nesting order, and it is why the ordering is not
arbitrary.

- **`SecurityMiddleware`** — sets security headers and, in production, redirects
  HTTP to HTTPS. First, so it applies to everything.
- **`SessionMiddleware`** — reads the session cookie and attaches
  `request.session`. Must come before anything that needs a session.
- **`CommonMiddleware`** — URL normalisation, such as appending a trailing slash.
- **`CsrfViewMiddleware`** — cross-site request forgery protection for
  cookie-authenticated writes. **Must** come after `SessionMiddleware`, because
  the CSRF check is tied to the session.
- **`AuthenticationMiddleware`** — turns the session into `request.user`. Needs
  the session, hence its position.
- **`MessageMiddleware`** — the admin's notices; needs the session too.
- **`XFrameOptionsMiddleware`** — sets `X-Frame-Options: DENY`, so the site cannot
  be embedded in an iframe on another domain and clickjacked.

### URLs and the application objects

```python
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
```

**`ROOT_URLCONF`** — the module Django starts from when matching a URL.

**`WSGI_APPLICATION`** — the callable a web server (gunicorn, uWSGI) imports to
serve the project. WSGI is the synchronous Python web standard.

### Templates

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

This project is an API, so templates are barely used — but the Django admin is a
normal Django app and will not start without this configured.

- **`BACKEND`** — which template engine. Django's own, rather than Jinja2.
- **`DIRS`** — project-wide template directories, searched first.
- **`APP_DIRS: True`** — also look in each installed app's `templates/` folder.
  This is what lets the admin find its own templates.
- **`context_processors`** — functions that add variables to every template's
  context. The three listed are the minimum the admin needs: the request object,
  the current user, and pending messages.

### The database

```python
DATABASES = {"default": env.db_url("DATABASE_URL", default="postgres://localhost:5432/edurgapuja")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

**`env.db_url(...)`** parses a connection URL into the dictionary Django wants —
`ENGINE`, `NAME`, `USER`, `PASSWORD`, `HOST`, `PORT`. One environment variable
instead of six, and it is the format every hosting provider hands you.

**`CONN_MAX_AGE = 60`** — persistent connections. Django's default is `0`, meaning
it opens a new database connection for every request and closes it afterwards.
Establishing a Postgres connection costs a few milliseconds, which is wasteful
under load. Sixty seconds means a connection is reused for a minute before being
recycled.

The caveat worth knowing: with persistent connections, each worker process holds a
connection open, so `workers × processes` must stay below Postgres's
`max_connections`. This is also exactly the setting that misbehaves behind a
transaction-mode connection pooler, which is one reason this project plans to run
on a long-lived process rather than serverless.

**`DEFAULT_AUTO_FIELD`** — the implicit primary key type for models that do not
declare one. Almost every model here inherits `BaseModel` and gets a UUID instead,
but Django's own tables (sessions, permissions) use it, and setting it silences a
startup warning.

### Redis and the cache

```python
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                      "LOCATION": REDIS_URL}}
```

`REDIS_URL` is pulled into its own name because three things use it: the cache,
the Celery broker, and the Celery result backend.

The cache matters here beyond performance: the OTP rate limits live in it. That is
why `settings/test.py` overrides it with an in-memory backend, and why the test
suite has an `autouse` fixture that clears it — cache state is *outside* the
database, so the usual transaction rollback does not undo it.

The `/0` on the end selects Redis database 0 — Redis has sixteen numbered
keyspaces by default, useful for separating environments on one server.

### Authentication

```python
AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
```

**`AUTH_USER_MODEL`** — the setting that must be correct before the first
migration ever runs, because changing it later means rewriting every foreign key
that points at the user table.

**`PASSWORD_HASHERS`** — an ordered list. The **first** is used for new passwords;
the rest are kept so existing hashes can still be verified, and Django
transparently upgrades a password to the first algorithm next time the user logs
in.

Argon2 is first because it is memory-hard: brute-forcing it needs a lot of RAM per
guess, which is what defeats GPU cracking. PBKDF2 (Django's default) is kept
second purely so that any hash created before this change still validates.

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

Run when a password is *set*, not when it is checked. Ten characters rather than
Django's default eight. `CommonPasswordValidator` rejects anything in a bundled
list of twenty thousand common passwords. `NumericPasswordValidator` rejects
all-digit passwords.

Django's fourth default validator, `UserAttributeSimilarityValidator`, is absent —
it compares the password to the username, and here the username is a phone number,
so it has nothing useful to say.

### The OTP block

```python
OTP_CODE_LENGTH = env.int("OTP_CODE_LENGTH", default=6)
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=300)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)
OTP_MAX_SENDS_PER_HOUR = env.int("OTP_MAX_SENDS_PER_HOUR", default=8)
OTP_SENDER_BACKEND = env("OTP_SENDER_BACKEND", default="apps.accounts.otp.senders.ConsoleSender")
DEFAULT_PHONE_REGION = "IN"
```

These are settings rather than constants in the code because they are the numbers
a client argues about — *"sixty seconds is too long, make it thirty"* — and none of
them should need a deployment to change.

The security-relevant relationship is between length and attempts: a six-digit
code is one in a million, and five attempts makes guessing hopeless. Shortening
the code to four digits with five attempts would be one in two thousand per
challenge, which is not enough.

**`OTP_SENDER_BACKEND`** is a dotted import path, not a class. It is looked up
with `import_string()` at call time, which is what lets the test settings swap in
a fake sender by changing one string. This is the standard Django pattern for a
pluggable implementation — the same shape as `EMAIL_BACKEND` and
`DEFAULT_FILE_STORAGE`.

**`DEFAULT_PHONE_REGION = "IN"`** — tells the phone-number parser how to interpret
a number typed without a country code, so `9876543210` becomes `+919876543210`.

### Inventory, payments, and the site

```python
CAPACITY_HOLD_TTL_SECONDS = env.int("CAPACITY_HOLD_TTL_SECONDS", default=900)
```

Fifteen minutes to complete a payment before a held place returns to the pool.
Long enough for a slow UPI approval, short enough that abandoned checkouts do not
strangle a popular slot.

```python
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")
```

Three separate secrets doing three different jobs: the key id is public and
identifies the account to the client SDK; the key secret authenticates our
server-to-server calls; the webhook secret verifies that an inbound callback
genuinely came from the provider. They default to empty strings so the project
starts without them — you cannot take a payment, but you can run the tests.

```python
SITE_DOMAIN = env("SITE_DOMAIN", default="edurgapuja.app")
RESERVED_SUBDOMAINS = {
    "www", "api", "admin", "app", "mail", "smtp", "static", "assets", "cdn",
    "staging", "dev", "test", "help", "support", "status", "blog", "docs",
}
```

`SITE_DOMAIN` is what a pandal's slug is appended to when building
`canonical_host`. `RESERVED_SUBDOMAINS` is a `set` rather than a list because the
only operation is membership testing, which is constant-time on a set. It lives in
settings so a name can be reserved without a deployment.

### REST framework

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    ...
}
```

**Authentication classes** are tried in order until one identifies the user. JWT
first because the Flutter apps are the busiest callers; session second for the
admin portal in a browser. The two coexist because they suit different clients —
a token has no cookie and therefore no CSRF problem, while a cookie survives an
app restart and is invisible to JavaScript.

**`DEFAULT_PERMISSION_CLASSES: IsAuthenticated`** — the important default. Every
endpoint requires a signed-in user *unless it explicitly says otherwise*. The
opposite default, `AllowAny`, means one forgotten line exposes an endpoint. Public
endpoints — the landing page, anonymous donation — opt out deliberately and
visibly.

```python
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"otp": "8/hour", "anon": "60/min", "user": "600/min"},
```

- **`DEFAULT_FILTER_BACKENDS`** — lets a viewset declare `filterset_fields` and get
  `?city=…` filtering for free.
- **`DEFAULT_SCHEMA_CLASS`** — hands schema generation to drf-spectacular.
- **Pagination** — every list is paginated by default, at 25. An unpaginated list
  endpoint is a denial-of-service waiting for the day the table gets big.
- **`EXCEPTION_HANDLER`** — the hook that produces the single error envelope. This
  one line is what makes `CapacityUnavailableError` come out as a 409 with a
  machine-readable code.
- **Throttle rates** — named buckets. `otp` is the strict one, applied by name on
  the OTP endpoint. `anon` and `user` are DRF's built-in scopes for unauthenticated
  and authenticated callers.

### Schema, localisation, and static files

```python
SPECTACULAR_SETTINGS = {
    "TITLE": "eDurgaPuja API",
    "DESCRIPTION": "Pandal landing pages, donations and value-added services.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
```

`SERVE_INCLUDE_SCHEMA: False` keeps the schema endpoint from documenting itself.
`COMPONENT_SPLIT_REQUEST: True` generates separate request and response types,
which matters because read-only fields (`id`, `created_at`) appear in responses
but must not appear in requests — without it, generated clients ask you to supply
an id when creating something.

```python
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("bn", "Bengali"), ("hi", "Hindi")]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
```

**`LANGUAGES`** is referenced directly by model fields —
`models.CharField(choices=settings.LANGUAGES)` — so the three supported languages
are declared once.

**`USE_TZ = True`** is the one to understand. With it, Django stores every
datetime in the database as UTC and attaches timezone information to datetimes in
Python. `TIME_ZONE` then only affects *display*. This is the correct arrangement:
UTC in storage means arithmetic across a daylight-saving boundary is not wrong,
and it is why the code always uses `django.utils.timezone.now()` rather than
`datetime.now()` — the former is timezone-aware, the latter is not, and mixing
them raises.

```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

**Static** files are code — the admin's CSS. `collectstatic` gathers them into
`STATIC_ROOT` at deploy time. **Media** files are uploads — a pandal's logo. The
distinction matters: static files are rebuilt on every deploy, media files must
survive one, which is why media eventually belongs in object storage rather than
on a disk.

### Celery

```python
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = TIME_ZONE
```

Celery runs work outside the request: sending an SMS, generating a receipt,
reconciling a payment.

**`ACKS_LATE = True`** is the significant one. By default a worker acknowledges a
task the moment it picks it up, so if the process dies mid-task the work is lost.
With late acknowledgement the message is acknowledged only after the task
*finishes*, so a crash means the task is redelivered.

That makes redelivery normal rather than exceptional, which is why anything Celery
runs must be **idempotent** — safe to run twice. It is the same property the
payment webhook handler needs, and for the same reason.

**`REJECT_ON_WORKER_LOST = True`** completes it: if the worker is killed outright,
requeue rather than silently drop.

### Logging

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
```

**`"version": 1`** is required and is the only value Python's logging config has
ever accepted.

**`disable_existing_loggers: False`** — without it, every logger created before
this config is silenced, which includes Django's own.

Everything goes to **stdout** rather than a file. That is the container
convention: the process writes to standard output and the platform collects,
routes and rotates it. Writing to a file inside a container means logs vanish when
it restarts.

---

## `config/settings/dev.py`

```python
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
```

**`from .base import *`** — the one place a star-import is right, because the
purpose is precisely "everything from there, plus my changes". `# noqa: F403`
tells Ruff not to flag it.

**`ALLOWED_HOSTS = ["*"]`** accepts any host. Fine on a laptop, where you might
reach the server as `localhost`, as `127.0.0.1`, or as a `*.localhost` subdomain
while testing pandal routing. Never in production.

---

## `config/settings/test.py`

```python
from .base import *  # noqa: F403

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True
OTP_SENDER_BACKEND = "apps.accounts.otp.senders.MemorySender"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
```

**`DEBUG = False`** — tests should exercise the production code path. With
`DEBUG=True` Django behaves differently in small ways, and a test that only passes
in debug mode is worse than no test.

**`CELERY_TASK_ALWAYS_EAGER = True`** — `task.delay()` runs the task immediately,
in-process, instead of queueing it. So tests need no broker and no worker.

**`OTP_SENDER_BACKEND = MemorySender`** — the pluggable-backend setting paying off.
Tests read the generated code out of the fake sender rather than intercepting an
SMS.

**`PASSWORD_HASHERS = [MD5PasswordHasher]`** — MD5 is cryptographically broken and
that is exactly why it is here: Argon2 is deliberately slow, and a suite that
creates hundreds of users would spend most of its time hashing. This setting is
the reason the whole suite runs in under two seconds. It is safe **only** because
this file is never used to serve anything.

**`CACHES` → `LocMemCache`** — an in-process dictionary, so tests need no Redis.
Note that it is per-process, which is another reason the rate-limit tests clear it
explicitly between tests.

---

## `config/celery.py`

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("edurgapuja")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

**`os.environ.setdefault(...)`** — a Celery worker is started by the `celery`
command, not by `manage.py`, so it needs its own way to find Django's settings.

**`app = Celery("edurgapuja")`** — the application instance. The name appears in
worker logs and in monitoring.

**`config_from_object("django.conf:settings", namespace="CELERY")`** — read
configuration from Django's settings, taking only names beginning `CELERY_` and
stripping that prefix. So `CELERY_TASK_ACKS_LATE` becomes Celery's `task_acks_late`.
One settings file for the whole project.

**`autodiscover_tasks()`** — walk every entry in `INSTALLED_APPS` looking for a
`tasks.py`, and register what it finds. Without it, every task module would have
to be imported by hand.

### And in `config/__init__.py`

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

This runs when the `config` package is imported, which happens whenever Django
starts — so the Celery app is created and its `@shared_task` decorators are wired
up even in the web process. Without it, calling `task.delay()` from a view would
fail because no Celery app existed.

**`__all__`** declares the module's public names, which is what stops a linter
deciding the import is unused.

---

## `config/urls.py`

```python
from django.contrib import admin
from django.urls import path

from apps.common.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", health, name="health"),
]
```

**`urlpatterns`** — the list Django matches against, in order, first match wins.

**`path("admin/", admin.site.urls)`** — mounts the entire admin. `admin.site.urls`
is not a view but a nested URL configuration, so everything under `/admin/` is
handled by it.

**`path("healthz", health, name="health")`** — note the missing trailing slash.
That is deliberate: `CommonMiddleware` would redirect `/healthz` to `/healthz/`,
and a load balancer following a 301 on every check is noise. `healthz` is a
Kubernetes convention.

**`name="health"`** — a reverse name, so code and tests can write
`reverse("health")` instead of hard-coding the path. Change the URL and nothing
else breaks.

The API routes are not here yet; this file grows when the endpoints from the
contract are built.

---

## `config/wsgi.py`

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
application = get_wsgi_application()
```

The production entry point. A server is pointed at `config.wsgi:application` and
calls that object for every request.

**`get_wsgi_application()`** initialises Django — loads settings, populates the app
registry, imports every model — and returns the WSGI callable. It runs once per
worker process at startup, which is why a slow import at module level shows up as
slow boot rather than a slow request.

The default settings module here should become `config.settings.prod` when a
production settings file exists; for now the environment variable is set
explicitly wherever it runs.
