from rest_framework.generics import ListAPIView
from reports.models import *
from search.serializers import StockAnalystSerializer
from rest_framework.response import Response


class SearchView(ListAPIView):
    def get(self, request):
        query = self.request.query_params.get("query")

        stocks_queryset = Stock.objects.filter(name__icontains=query)
        analysts_queryset = Analyst.objects.filter(name__icontains=query)

        serializer = StockAnalystSerializer(
            {"stocks": stocks_queryset, "analysts": analysts_queryset}
        )

        return Response(serializer.data)
