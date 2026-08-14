"""Smoke tests for the integration client + emitters (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from integration.client import IntegrationAPIError, IntegrationClient
from integration.config import Config


def _config() -> Config:
  return Config(
    api_url="https://api.test",
    api_key="key-123",
    graph_id="kg_test",
    source_name="testsource",
  )


def _envelope(result: dict | None = None) -> dict:
  """A minimal but shape-complete operation envelope (camelCase wire form)."""
  return {
    "operation": "test-op",
    "operationId": "op_1",
    "status": "completed",
    "at": "2026-07-30T00:00:00Z",
    "error": None,
    "result": result or {},
  }


def _client_with(handler) -> IntegrationClient:
  """Inject an httpx.MockTransport under the SDK client.

  ``set_httpx_client`` replaces headers too, so the auth header is
  re-supplied to mirror what the SDK builds by default.
  """
  client = IntegrationClient(_config())
  client.sdk.set_httpx_client(
    httpx.Client(
      base_url="https://api.test",
      headers={"X-API-Key": "key-123"},
      transport=httpx.MockTransport(handler),
    )
  )
  return client


class TestClient:
  def test_sdk_client_carries_api_key_header(self) -> None:
    client = IntegrationClient(_config())
    headers = client.sdk.get_httpx_client().headers
    assert headers["X-API-Key"] == "key-123"
    assert "Authorization" not in headers

  def test_raw_operation_sends_idempotency_key_and_unwraps(self) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
      seen["idem"] = request.headers.get("Idempotency-Key")
      seen["path"] = request.url.path
      return httpx.Response(200, json={"error": None, "result": {"ok": True}})

    client = _client_with(handler)
    envelope = client.raw_operation(
      "/v1/graphs/kg_test/operations/x", {}, idempotency_key="k1"
    )

    assert seen["idem"] == "k1"
    assert envelope["result"] == {"ok": True}

  def test_raw_operation_envelope_error_raises(self) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
      return httpx.Response(200, json={"error": "boom", "result": None})

    client = _client_with(handler)
    with pytest.raises(IntegrationAPIError, match="boom"):
      client.raw_operation("/v1/graphs/kg_test/operations/x", {})

  def test_raw_operation_http_error_raises_with_body(self) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
      return httpx.Response(422, json={"detail": "bad source"})

    client = _client_with(handler)
    with pytest.raises(IntegrationAPIError, match="bad source"):
      client.raw_operation("/v1/graphs/kg_test/operations/x", {})


class TestEventsEmitter:
  def test_emit_event_stamps_source_and_requires_external_id(self) -> None:
    from integration.emit.events import emit_event

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
      seen["body"] = json.loads(request.content)
      seen["path"] = request.url.path
      return httpx.Response(200, json=_envelope())

    client = _client_with(handler)
    emit_event(
      client,
      {
        "event_type": "invoice_issued",
        "event_category": "sales",
        "occurred_at": "2026-07-15T12:00:00Z",
        "external_id": "inv-1",
      },
    )
    assert seen["body"]["source"] == "testsource"
    assert seen["path"] == (
      "/extensions/roboledger/kg_test/operations/create-event-block"
    )

    with pytest.raises(ValueError, match="external_id"):
      emit_event(
        client,
        {
          "event_type": "invoice_issued",
          "event_category": "sales",
          "occurred_at": "2026-07-15T12:00:00Z",
        },
      )


class TestMetricsEmitter:
  def test_assert_metrics_builds_observation_payload(self) -> None:
    from datetime import date

    from integration.emit.metrics import assert_metrics

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
      seen["body"] = json.loads(request.content)
      seen["path"] = request.url.path
      return httpx.Response(200, json=_envelope())

    client = _client_with(handler)
    assert_metrics(
      client,
      structure_id="str_growth",
      period_end=date(2026, 7, 31),
      period_start=date(2026, 7, 1),
      observations={"rsx:GithubStars": 1240.0},
    )

    assert seen["path"].endswith("/operations/assert-metrics")
    assert seen["body"]["source_system"] == "testsource"
    assert seen["body"]["observations"] == [
      {"qname": "rsx:GithubStars", "value": 1240.0}
    ]
