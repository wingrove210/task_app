from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

import identity.app.main as identity_main


def test_metrics_endpoint_and_request_id_header():
    identity_main.initialize = lambda: None
    client = TestClient(identity_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers

    metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    assert "http_requests_total" in metrics_response.text
