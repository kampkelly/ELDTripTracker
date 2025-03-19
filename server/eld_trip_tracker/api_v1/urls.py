from api_v1.views.health import health_check
from django.urls import path
from rest_framework import routers

app_name = "api_v1"

router = routers.SimpleRouter()

urlpatterns = [
    path("healthz/", health_check, name="health_check"),
]
urlpatterns += router.urls
