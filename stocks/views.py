from rest_framework import viewsets

from reports.models import Stock
from stocks.serializer import StockSerializer


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
