"""
URL configuration for eld_trip_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.schemas import get_schema_view
from rest_framework.urlpatterns import format_suffix_patterns

schema_url_patterns = [
    path("api_v1/", include("api_v1.urls")),
]

schema_view = get_schema_view(
    title="Sku App",
    description="API to manage SKUs",
    version="1.0.0",
    patterns=schema_url_patterns,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api_v1.urls", namespace="api_v1")),
    path("api/v1/openapi", schema_view),
]

urlpatterns = format_suffix_patterns(
    urlpatterns, suffix_required=False, allowed=["json"]
)
