from rest_framework import serializers
from reports.models import Stock, Analyst


class StockSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ["id", "name", "code"]


class AnalystSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analyst
        fields = ["id", "name", "company"]


class StockAnalystSerializer(serializers.Serializer):
    def to_representation(self, instance):
        stocks_queryset = instance["stocks"]
        analysts_queryset = instance["analysts"]

        stocks_data = StockSearchSerializer(stocks_queryset, many=True).data
        analysts_data = AnalystSearchSerializer(analysts_queryset, many=True).data

        return {"stocks": stocks_data, "analysts": analysts_data}
