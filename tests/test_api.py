"""Public tests for the supported local rules-mode API surface."""
import hashlib
import hmac
import json
import time

from sqlalchemy import func, select

from airr.models import AuditEvent, Delivery, Job, Request
from airr.modules.sources.service import (
    provision_source,
    rotate_source_key,
    set_source_enabled,
)
from airr.worker import process_classification_once, process_delivery_once


def _intake(client, source_headers, payload):
    response = client.post(
        "/api/v1/requests", json=payload, headers=source_headers
    )
    assert response.status_code == 202, response.text
    return response.json()["request_id"]


def test_health_probes(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_source_and_reviewer_credentials_are_distinct(
    client, payload, source_headers, reviewer_headers
):
    assert client.post("/api/v1/requests", json=payload).status_code == 401
    assert client.get("/api/v1/requests").status_code == 401
    assert client.get("/api/v1/requests", headers=source_headers).status_code == 401
    assert client.post(
        "/api/v1/requests", json=payload, headers=reviewer_headers
    ).status_code == 401


def test_intake_persists_one_request_job_and_audit_event(
    client, app, payload, source_headers
):
    request_id = _intake(client, source_headers, payload)
    with app.state.test_sf() as session:
        assert session.get(Request, request_id) is not None
        assert session.scalar(select(func.count()).select_from(Request)) == 1
        assert session.scalar(select(func.count()).select_from(Job)) == 1
        assert session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_same_payload_is_idempotent_and_mismatch_is_conflict(
    client, app, payload, source_headers
):
    request_id = _intake(client, source_headers, payload)
    replay = client.post(
        "/api/v1/requests", json=payload, headers=source_headers
    )
    assert replay.status_code == 202
    assert replay.json()["request_id"] == request_id
    conflict = client.post(
        "/api/v1/requests",
        json={**payload, "message": "different content"},
        headers=source_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    with app.state.test_sf() as session:
        assert session.scalar(select(func.count()).select_from(Request)) == 1
        assert session.scalar(select(func.count()).select_from(Job)) == 1


def test_validation_and_trace_id_on_rejection(
    client, app, source_headers, reviewer_headers
):
    invalid = client.post(
        "/api/v1/requests",
        json={"external_id": "x", "subject": "  ", "message": "hello"},
        headers=source_headers,
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_INPUT"
    assert invalid.json()["trace_id"] == invalid.headers["X-Trace-Id"]
    unsupported = client.get(
        "/api/v1/requests",
        params={"category": "finance"},
        headers=reviewer_headers,
    )
    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["code"] == "INVALID_INPUT"
    assert unsupported.json()["trace_id"] == unsupported.headers["X-Trace-Id"]
    with app.state.test_sf() as session:
        assert session.scalar(select(func.count()).select_from(Request)) == 0


def test_large_request_rejected_before_persistence(client, app, source_headers):
    oversized = client.post(
        "/api/v1/requests",
        json={"external_id": "large", "subject": "Test", "message": "x" * 70000},
        headers=source_headers,
    )
    assert oversized.status_code == 413
    assert oversized.json()["trace_id"] == oversized.headers["X-Trace-Id"]
    with app.state.test_sf() as session:
        assert session.scalar(select(func.count()).select_from(Request)) == 0


def test_approval_and_internal_delivery_complete_once(
    client, app, payload, source_headers, reviewer_headers
):
    request_id = _intake(client, source_headers, payload)
    assert process_classification_once(app.state.test_sf) is True
    detail = client.get(
        f"/api/v1/requests/{request_id}", headers=reviewer_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "PENDING_REVIEW"
    assert detail.json()["category"] == "billing"
    assert detail.json()["classifier_mode"] == "rules"
    approval = {"expected_version": 1, "category": "billing", "priority": "normal"}
    accepted = client.post(
        f"/api/v1/requests/{request_id}/approve",
        json=approval, headers=reviewer_headers,
    )
    assert accepted.status_code == 200
    duplicate = client.post(
        f"/api/v1/requests/{request_id}/approve",
        json=approval, headers=reviewer_headers,
    )
    assert duplicate.status_code == 409
    with app.state.test_sf() as session:
        assert session.scalar(select(func.count()).select_from(Delivery)) == 1
    assert process_delivery_once(app.state.test_sf) is True
    final = client.get(
        f"/api/v1/requests/{request_id}", headers=reviewer_headers
    )
    assert final.json()["status"] == "COMPLETED"


def test_rejection_leaves_no_delivery(
    client, app, payload, source_headers, reviewer_headers
):
    request_id = _intake(client, source_headers, payload)
    assert process_classification_once(app.state.test_sf)
    rejection = client.post(
        f"/api/v1/requests/{request_id}/reject",
        json={"expected_version": 1, "reason": "Not eligible"},
        headers=reviewer_headers,
    )
    assert rejection.status_code == 200
    with app.state.test_sf() as session:
        assert session.scalar(select(func.count()).select_from(Delivery)) == 0


def test_reviewer_filters_category_and_status_before_pagination(
    client, app, payload, source_headers, reviewer_headers
):
    created = []
    for index in range(3):
        rid = _intake(
            client, source_headers,
            {**payload, "external_id": f"filter-{index}"},
        )
        created.append(rid)
        assert process_classification_once(app.state.test_sf)
    for index, category in enumerate(["billing", "support", "billing"]):
        with app.state.test_sf.begin() as session:
            row = session.get(Request, created[index])
            row.category = category
    result = client.get(
        "/api/v1/requests",
        params={"category": "billing", "status": "PENDING_REVIEW", "limit": 1},
        headers=reviewer_headers,
    )
    assert result.status_code == 200
    assert len(result.json()["items"]) == 1
    assert result.json()["items"][0]["category"] == "billing"
    page_two = client.get(
        "/api/v1/requests",
        params={
            "category": "billing", "status": "PENDING_REVIEW",
            "limit": 1, "offset": 1,
        },
        headers=reviewer_headers,
    )
    assert len(page_two.json()["items"]) == 1
    assert result.json()["items"][0]["request_id"] != page_two.json()["items"][0]["request_id"]


def test_source_rotation_and_disable(
    client, app, payload
):
    token = provision_source(app.state.test_sf, "vendor_one")
    accepted = client.post(
        "/api/v1/requests", json=payload, headers={"X-Source-Key": token}
    )
    assert accepted.status_code == 202
    new_token = rotate_source_key(app.state.test_sf, "vendor_one")
    assert client.post(
        "/api/v1/requests",
        json={**payload, "external_id": "rotated"},
        headers={"X-Source-Key": token},
    ).status_code == 401
    assert client.post(
        "/api/v1/requests",
        json={**payload, "external_id": "rotated"},
        headers={"X-Source-Key": new_token},
    ).status_code == 202
    set_source_enabled(app.state.test_sf, "vendor_one", False)
    assert client.post(
        "/api/v1/requests",
        json={**payload, "external_id": "disabled"},
        headers={"X-Source-Key": new_token},
    ).status_code == 403


def test_hmac_signed_webhook_and_tampering(
    client, app, payload
):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(
        app.state.settings.source_key.encode(),
        timestamp.encode() + b"." + raw,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "X-Timestamp": timestamp,
        "X-Signature": f"sha256={digest}",
    }
    accepted = client.post(
        "/api/v1/webhooks/intake", content=raw, headers=headers
    )
    assert accepted.status_code == 202
    tampered = client.post(
        "/api/v1/webhooks/intake", content=raw + b" ", headers=headers
    )
    assert tampered.status_code == 401
