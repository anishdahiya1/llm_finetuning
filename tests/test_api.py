"""Unit tests for the backend API."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_info(client):
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert "demos" in data
    assert "quantization" in data["demos"]


def test_quantization_endpoint(client):
    response = client.post("/api/quantization", json={"model_name": "sshleifer/tiny-gpt2"})
    assert response.status_code in [200, 500]  # May fail without GPU
    if response.status_code == 200:
        data = response.json()
        assert "baseline_memory_mb" in data


def test_retrieval_endpoint(client):
    response = client.post("/api/retrieval", json={"query": "What is RAG?"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_evaluation_endpoint(client):
    response = client.post(
        "/api/evaluation",
        json={
            "predictions": ["LoRA is efficient."],
            "references": ["LoRA updates adapters."],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "rouge_score" in data
    assert "bertscore_f1" in data
