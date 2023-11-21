from django.urls import path, include
from rest_framework.routers import DefaultRouter
from reports.views import StockReportsView, StockViewSet, PointViewSet

urlpatterns = [
    path("<int:pk>/reports", StockReportsView.as_view(), name="stock-reports"),
]
