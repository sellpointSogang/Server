from django.db.models import Min
from rest_framework import viewsets, generics
from rest_framework import filters as drf_filters
from django.db.models import Max, Q

from reports.serializers import (
    PointSerializer,
    ReportSerializer,
    StockSerializer,
    WritesSerializer,
    StockReportSerializer,  ## 종목 검색 페이지를 위한 API용 시리얼라이저
    AnalystReportSerializer,  ## 애널리스트 검색 페이지를 위한 API용 시리얼라이저
    PointContentSerializer,  ## 해당 종목리포트의 모든 부정포인트 반환 API용 시리얼라이저
)
from reports.models import Point, Report, Stock, Writes
from analysts.pagination import CustomPageNumberPagination

from django_filters import rest_framework as filters


class StockReportFilter(filters.FilterSet):
    publish_date = filters.DateFromToRangeFilter()
    min_hit_rate = filters.NumberFilter(field_name="hit_rate", lookup_expr="gte")
    min_analyst_hit_rate = filters.NumberFilter(
        method="filter_by_min_hit_rate", label="Minimum hit rate of analyst"
    )

    class Meta:
        model = Report
        fields = ["publish_date", "min_hit_rate", "min_analyst_hit_rate"]

    def filter_by_min_hit_rate(self, queryset, name, value):
        # Annotate each report with the minimum analyst hit rate
        queryset = queryset.annotate(min_hit_rate=Min("writes__analyst__hit_rate"))

        # Filter by the annotated field
        return queryset.filter(min_hit_rate__gte=value)


class CustomOrderingFilter(drf_filters.OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        # annotate analyst_max_hit_rate: the maximum hit rate of analysts who wrote the same report
        queryset = queryset.annotate(
            analyst_max_hit_rate=Max("writes__analyst__hit_rate")
        )
        return super().filter_queryset(request, queryset, view)


## http GET /stocks/:stock_ID/reports/
class StockReportsView(generics.ListAPIView):
    serializer_class = StockReportSerializer
    filter_backends = [filters.DjangoFilterBackend, CustomOrderingFilter]
    filterset_class = StockReportFilter
    ordering_fields = ["publish_date", "hit_rate", "analyst_max_hit_rate"]
    ordering = ["-hit_rate", "-publish_date"]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        stock_id = self.kwargs["pk"]
        query = self.request.query_params.get("query")

        ## 리포트 제목, 소속기관, 애널리스트명 쿼리 최적화 없이 진행
        if query is not None:
            return Report.objects.filter(
                Q(stock_id=stock_id),
                Q(title__icontains=query)
                | Q(writes__analyst__name__icontains=query)
                | Q(writes__analyst__company__icontains=query),
            )

        else:
            return Report.objects.filter(stock_id=stock_id)


class AnalystReportFilter(filters.FilterSet):
    publish_date = filters.DateFromToRangeFilter()
    sentiment = filters.ChoiceFilter(
        field_name="written_sentiment", choices=Report.SENTIMENT_CHOICES
    )
    stock_id = filters.NumberFilter()

    class Meta:
        model = Report
        fields = ["publish_date", "sentiment", "stock_id"]


## http GET /analysts/:analyst_id/reports/
class AnalystReportsView(generics.ListAPIView):
    serializer_class = AnalystReportSerializer
    filter_backends = [filters.DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = AnalystReportFilter
    ordering_fields = ["publish_date", "hit_rate"]
    ordering = ["-hit_rate", "-publish_date"]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        analyst_id = self.kwargs["pk"]
        query = self.request.query_params.get("query")

        ## 리포트 제목, 종목 쿼리 최적화 없이 진행
        if query is not None:
            return Report.objects.filter(
                Q(writes__analyst_id=analyst_id),
                Q(title__icontains=query) | Q(stock__name__icontains=query),
            )

        else:
            return Report.objects.filter(writes__analyst_id=analyst_id)


class PointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Point.objects.all()
    serializer_class = PointSerializer


## http GET /reports/:report_ID/points
class ReportPointView(generics.ListAPIView):
    serializer_class = PointContentSerializer

    def get_queryset(self):
        report_id = self.kwargs["report_id"]
        points = Point.objects.filter(report=report_id)

        return points


class WritesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Writes.objects.all()
    serializer_class = WritesSerializer
