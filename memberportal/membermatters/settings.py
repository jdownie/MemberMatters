"""
Django settings for membermatters project.

Generated by 'django-admin startproject' using Django 2.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ.get("PORTAL_SECRET_KEY", "l)#t68rzepzp)0l#x=9mntciapun$whl+$j&=_@nl^zl1xm3j*")

# Default config is for dev environments and is overwritten in prod
DEBUG = True
ALLOWED_HOSTS = ["*"]

if os.environ.get("PORTAL_ENV") == "Production":
    ENVIRONMENT = "Production"
    DEBUG = False
    ALLOWED_HOSTS = [os.environ.get("PORTAL_DOMAIN", "portal.example.org")]

    # Slightly hacky, but allows a direct IP while on the local network.
    # These may be required for the interlocks, doors, etc.
    for x in range(1, 255):
        ALLOWED_HOSTS.append("10.0.0." + str(x))
        ALLOWED_HOSTS.append("10.0.1." + str(x))
        ALLOWED_HOSTS.append("192.168.0." + str(x))
        ALLOWED_HOSTS.append("192.168.1." + str(x))

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "profile",
    "portal",
    "access",
    "group",
    "spacebucks",
    "spacedirectory",
    "constance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "membermatters.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "constance.context_processors.config",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "membermatters.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("PORTAL_DB_LOCATION", "/usr/src/data/db.sqlite3"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": os.environ.get("PORTAL_LOG_LOCATION", "/usr/src/logs/django.log"),
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-au"

TIME_ZONE = "Australia/Brisbane"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/signin"
MEDIA_URL = "/media/"

AUTH_USER_MODEL = "profile.User"

REQUEST_TIMEOUT = 0.05

# Django constance configuration
CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {
    "EMAIL_SYSADMIN": ("example@example.com", "The default sysadmin email that should receive errors etc."),
    "EMAIL_ADMIN": ("example@example.com", "The default admin email that should receive administrative notifications."),
    "EMAIL_DEFAULT_FROM": (
        "\"MemberMatters Portal\" <example@example.org>", "The default email that outbound messages are sent from."),
    "SITE_MAIL_ADDRESS": ("123 Example St, Nowhere", "This address is used in the footer of all emails for anti spam."),
    "SITE_NAME": ("MemberMatters Portal", "The title shown at the top of the page and as the tab title."),
    "SITE_OWNER": ("MemberMatters", "The name of the legal entity/association/club that is running this site."),
    "MEMBERBUCKS_NAME": ("Memberbucks", "You can customise the name of the portals currency."),
    "GROUP_NAME": ("Group", "You can customise what the portal calls a group.")
}
