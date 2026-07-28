from pathlib import Path

from .base import *  # noqa: F403,F401

DEBUG = False
SECRET_KEY = "teste-seguro-apenas-suite-comprimento-superior-a-32-bytes-2026"
ALLOWED_HOSTS = ["testserver", "localhost"]
CSRF_TRUSTED_ORIGINS = ["http://testserver"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",  # noqa: F405
    }
}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MEDIA_ROOT = Path(BASE_DIR) / "test_media"  # noqa: F405
STATICFILES_DIRS = []
STORAGES = {
    **globals().get("STORAGES", {}),
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
