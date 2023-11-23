from django.urls import path, include
from rest_framework import routers
from reports.views import StockReportsView
from stocks.views import StockViewSet

app_name = "stocks"

router = routers.DefaultRouter()
router.register("", StockViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("<int:pk>/reports/", StockReportsView.as_view(), name="stock-reports"),
]
