from rest_framework import serializers
from reports.models import *
from analysts.serializers import *
from stocks.serializer import StockSerializer


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"


class PointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Point
        fields = "__all__"


class WritesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Writes
        fields = "__all__"


class PointContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Point
        fields = ["content"]

    def to_representation(self, instance):
        return str(instance.content)


class PointsMixin:
    # Provide functionality: Retreive list of "content" of points related to a report(obj)

    def get_points(self, obj, max_count=3):
        points = Point.objects.filter(report=obj)[:max_count]
        serializer = PointContentSerializer(points, many=True)
        return serializer.data


class StockReportSerializer(serializers.ModelSerializer, PointsMixin):
    points = serializers.SerializerMethodField()
    analyst_data = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "points",
            "target_price",
            "publish_date",
            "hit_rate",
            "days_to_first_hit",
            "days_to_first_miss",
            "analyst_data",
        ]

    class BasicAnalystSerializer(AnalystSerializer):
        history = serializers.SerializerMethodField()

        class Meta:
            model = Analyst
            fields = ["id", "name", "history"]

        def get_history(self, analyst):
            return {
                "avg_days_hit": analyst.avg_days_hit,
                "avg_days_to_first_hit": analyst.avg_days_to_first_hit,
                "avg_days_to_first_miss": analyst.avg_days_to_first_miss,
            }

    ## 리포트를 쓴 애널리스트 정보
    def get_analyst_data(self, report):
        writes = Writes.objects.filter(report=report)
        analyst = Analyst.objects.filter(writes__in=writes).first()

        if analyst is not None:
            return self.BasicAnalystSerializer(analyst).data
        else:
            return None  # 해당하는 analyst가 없을 경우 None 반환


class AnalystReportSerializer(serializers.ModelSerializer, PointsMixin):
    class BasicStockSerializer(StockSerializer):
        class Meta:
            model = Stock
            fields = ["id", "name"]

    points = serializers.SerializerMethodField()
    stock = BasicStockSerializer()

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "points",
            "target_price",
            "publish_date",
            "stock",
            "hidden_sentiment",
            "hit_rate",
            "days_to_first_hit",
            "days_to_first_miss",
        ]
