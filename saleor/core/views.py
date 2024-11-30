import os

from django.http import JsonResponse, HttpResponse
from django.template.response import TemplateResponse

from .jwt_manager import get_jwt_manager


def home(request):
    storefront_url = os.environ.get("STOREFRONT_URL", "")
    dashboard_url = os.environ.get("DASHBOARD_URL", "")
    return TemplateResponse(
        request,
        "home/index.html",
        {"storefront_url": storefront_url, "dashboard_url": dashboard_url},
    )


def jwks(request):
    return JsonResponse(get_jwt_manager().get_jwks())


def test_view(request):
    return HttpResponse("11zzz11 Testing auto reload now!")
