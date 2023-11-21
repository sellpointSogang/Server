from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *
from reports.views import AnalystReportsView

router = DefaultRouter()

router.register(r"analyst", AnalystViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("<int:pk>/reports", AnalystReportsView.as_view(), name="analyst-reports"),
]
