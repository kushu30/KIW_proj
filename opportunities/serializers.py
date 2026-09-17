from rest_framework import serializers

from core.domain import LiquidityLevel, RiskLevel, SearchQuery


class SearchRequestSerializer(serializers.Serializer):
    investment_amount = serializers.FloatField()
    risk = serializers.CharField()
    tenure_months = serializers.IntegerField(min_value=1, max_value=600)
    minimum_return = serializers.FloatField(required=False, allow_null=True, min_value=0)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=False)
    liquidity = serializers.CharField(required=False, allow_null=True)

    def validate_investment_amount(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError("must be greater than 0")
        return value

    def validate_risk(self, value: str) -> RiskLevel:
        try:
            return RiskLevel.from_label(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_liquidity(self, value: str | None) -> LiquidityLevel | None:
        if value is None:
            return None
        try:
            return LiquidityLevel.from_label(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs: dict) -> dict:
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(f"unknown field(s): {', '.join(sorted(unknown))}")
        return attrs

    def to_search_query(self) -> SearchQuery:
        data = self.validated_data
        return SearchQuery(
            investment_amount=data["investment_amount"],
            risk=data["risk"],
            tenure_months=data["tenure_months"],
            minimum_return=data.get("minimum_return"),
            category=data.get("category"),
            liquidity=data.get("liquidity"),
        )
