"""membermatters URL Configuration
"""
import os
import sqlite3

import django.db.utils
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from constance import config
import json


try:
    if (
        config.SENTRY_DSN_BACKEND
        and os.environ.get("PORTAL_ENV")
        and os.environ.get("PORTAL_ENV") != "Development"
    ):
        version = None
        with open("../package.json") as f:
            d = json.load(f)

        sentry_sdk.init(
            release=d.get("version"),
            dsn=config.SENTRY_DSN_BACKEND,
            integrations=[DjangoIntegration()],
        )
except django.db.utils.OperationalError as e:
    pass

urlpatterns = [
    path("", include("access.urls")),
    path("", include("memberbucks.urls")),
    path("", include("api_spacedirectory.urls")),
    path("", include("api_general.urls")),
    path("", include("api_access.urls")),
    path("", include("api_member_tools.urls")),
    path("", include("api_meeting.urls")),
    path("", include("api_member_bucks.urls")),
    path("", include("api_billing.urls")),
    path("api/admin/", include("api_admin_tools.urls")),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root="")
