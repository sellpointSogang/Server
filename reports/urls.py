from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register(r"point", PointViewSet)
router.register(r"writes", WritesViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("<int:report_id>/points", ReportPointView.as_view(), name="report-points"),
]
