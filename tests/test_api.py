import json

import pytest
from rest_framework.test import APIClient

BRIEF_EXAMPLE = {
    "investment_amount": 200000,
    "risk": "Moderate",
    "tenure_months": 24,
    "minimum_return": 9,
    "category": "Debt",
    "liquidity": "Medium",
}


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_brief_example_returns_sorted_results(client):
    response = client.post("/opportunities/search/", BRIEF_EXAMPLE, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["results"])
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_lowercase_risk_works(client):
    payload = {**BRIEF_EXAMPLE, "risk": "moderate"}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 200


def test_zero_investment_amount_returns_400(client):
    payload = {**BRIEF_EXAMPLE, "investment_amount": 0}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid request"


def test_invalid_risk_returns_400(client):
    payload = {**BRIEF_EXAMPLE, "risk": "extreme"}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 400


def test_missing_investment_amount_returns_400(client):
    payload = {k: v for k, v in BRIEF_EXAMPLE.items() if k != "investment_amount"}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 400


def test_malformed_json_returns_400_in_our_shape(client):
    response = client.post(
        "/opportunities/search/", data="{not valid json", content_type="application/json"
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Invalid request"
    assert "details" in body


def test_unknown_extra_field_returns_400(client):
    payload = {**BRIEF_EXAMPLE, "extra_field": "surprise"}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 400


def test_nonexistent_category_returns_zero_with_rejection_summary(client):
    payload = {**BRIEF_EXAMPLE, "category": "NonExistentCategory"}
    response = client.post("/opportunities/search/", payload, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["results"] == []
    assert "category" in body["rejection_summary"]


def test_health_and_validation_report_return_200(client):
    assert client.get("/health/").status_code == 200
    response = client.get("/validation-report/")
    assert response.status_code == 200
    assert "issues" in response.json()
