from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import admin
from app.database import get_session
from app.main import app
from app.services.article_review import ArticleReviewService


@pytest.fixture
def client():
    app.router.on_startup.clear()

    def _override_get_session():
        yield object()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "error_code,message",
    [
        ("missing_v4_ast", "Review v4 mode requires meta.v4_ast, but it is missing."),
        ("invalid_v4_ast_blocks", "meta.v4_ast.forms[0].blocks must be an array."),
    ],
)
def test_admin_article_review_returns_parse_error_and_review_diagnostic_without_500(
    client,
    monkeypatch,
    error_code,
    message,
):
    diagnostic = {
        "code": error_code,
        "message": message,
        "hint": "reparse",
    }

    class StubService:
        def __init__(self, session):
            self.session = session

        def load_article(self, lang, art_id):
            return {
                "art_id": art_id,
                "lang": lang,
                "headword": "test",
                "template": "headword",
                "success": False,
                "parse_error": error_code,
                "review_diagnostic": diagnostic,
                "parsing_status": "needs_review",
                "groups": [],
                "auto_candidates": [],
                "resolved_translations": {},
                "notes": [],
                "review_notes": [],
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.get("/admin/articles/eo/42")

    assert response.status_code == 200
    body = response.json()
    assert body["parse_error"] == error_code
    assert body["review_diagnostic"] == diagnostic


def test_admin_reparse_endpoint_returns_parse_error_and_review_diagnostic_without_500(
    client,
    monkeypatch,
):
    diagnostic = {
        "code": "missing_v4_ast",
        "message": "Review v4 mode requires meta.v4_ast, but it is missing.",
        "hint": "Enable parser v4 payload generation before opening review.",
    }

    class StubService:
        def __init__(self, session):
            self.session = session

        def reparse_article(self, lang, art_id):
            return {}, SimpleNamespace(
                success=False,
                error="missing_v4_ast",
                review_diagnostic=diagnostic,
            )

        def load_article(self, lang, art_id):
            return {
                "art_id": art_id,
                "lang": lang,
                "headword": "test",
                "template": "headword",
                "success": False,
                "parse_error": "missing_v4_ast",
                "review_diagnostic": diagnostic,
                "parsing_status": "needs_review",
                "groups": [],
                "auto_candidates": [],
                "resolved_translations": {},
                "notes": [],
                "review_notes": [],
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.post("/admin/articles/eo/77/reparse")

    assert response.status_code == 200
    body = response.json()
    assert body["parse_error"] == "missing_v4_ast"
    assert body["review_diagnostic"] == diagnostic
    assert body["article"]["review_diagnostic"] == diagnostic


@pytest.mark.parametrize(
    "error_code,message",
    [
        ("missing_v4_ast", "Review v4 mode requires meta.v4_ast, but it is missing."),
        ("invalid_v4_ast_blocks", "meta.v4_ast.forms[0].blocks must be an array."),
    ],
)
def test_admin_v4_ast_endpoint_fail_fast_payload_contains_diagnostic(
    client,
    monkeypatch,
    error_code,
    message,
):
    diagnostic = {"code": error_code, "message": message, "hint": "reparse"}

    class StubService:
        def __init__(self, session):
            self.session = session

        def load_article_ast(self, lang, art_id):
            return {
                "headword": "test-headword",
                "lang": lang,
                "art_id": art_id,
                "parse_error": error_code,
                "review_diagnostic": diagnostic,
                "v4_ast": None,
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.get("/admin/v4/articles/eo/99/ast")

    assert response.status_code == 200
    body = response.json()
    assert body["headword"] == "test-headword"
    assert body["lang"] == "eo"
    assert body["art_id"] == 99
    assert body["v4_ast"] is None
    assert body["parse_error"] == error_code
    assert body["review_diagnostic"] == diagnostic


def test_admin_v4_ast_endpoint_happy_path_contract(client, monkeypatch):
    expected_ast = {
        "forms": [
            {
                "raw": "abio",
                "blocks": [
                    {
                        "type": "text_raw",
                        "raw": "пихта",
                    }
                ],
            }
        ]
    }

    class StubService:
        def __init__(self, session):
            self.session = session

        def load_article_ast(self, lang, art_id):
            return {
                "headword": "abio",
                "lang": lang,
                "art_id": art_id,
                "parse_error": None,
                "review_diagnostic": None,
                "v4_ast": expected_ast,
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.get("/admin/v4/articles/eo/77/ast")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "headword": "abio",
        "lang": "eo",
        "art_id": 77,
        "parse_error": None,
        "review_diagnostic": None,
        "v4_ast": expected_ast,
    }


def test_admin_v4_resolve_block_happy_path(client, monkeypatch):
    class StubService:
        def __init__(self, session):
            self.session = session

        def resolve_block_draft(self, lang, art_id, form_id, block_id, context):
            assert lang == "eo"
            assert art_id == 77
            assert form_id == "form_0"
            assert block_id == "block_1"
            assert context == {"items": ["бета"]}
            return {
                "provider": "gemma-assist-stub",
                "candidates": ["бета", "бетта"],
                "confidence": 0.42,
                "rationale_short": "stub rationale",
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.post(
        "/admin/v4/resolve-block",
        json={
            "article_id": 77,
            "lang": "eo",
            "form_id": "form_0",
            "block_id": "block_1",
            "context": {"items": ["бета"]},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "gemma-assist-stub",
        "candidates": ["бета", "бетта"],
        "confidence": 0.42,
        "rationale_short": "stub rationale",
    }


def test_admin_v4_resolve_block_validation_error(client):
    response = client.post(
        "/admin/v4/resolve-block",
        json={
            "article_id": 77,
            "lang": "eo",
            "form_id": "form_0",
            "context": {},
        },
    )

    assert response.status_code == 422


def test_admin_v4_apply_resolution_happy_path(client, monkeypatch):
    class StubService:
        def __init__(self, session):
            self.session = session

        def apply_resolution_action(self, lang, art_id, form_id, block_id, operator_action):
            assert lang == "eo"
            assert art_id == 77
            assert form_id == "form_0"
            assert block_id == "block_1"
            assert operator_action == {
                "action": "edit",
                "selected_candidate_id": "c2",
                "value": "бета",
                "comment": "ок",
            }
            return {
                "status": "ok",
                "article_id": art_id,
                "lang": lang,
                "form_id": form_id,
                "block_id": block_id,
                "operator_action": operator_action,
            }

    monkeypatch.setattr(admin, "ArticleReviewService", StubService)

    response = client.post(
        "/admin/v4/apply-resolution",
        json={
            "article_id": 77,
            "lang": "eo",
            "form_id": "form_0",
            "block_id": "block_1",
            "operator_action": {
                "action": "edit",
                "selected_candidate_id": "c2",
                "value": "бета",
                "comment": "ок",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_v4_apply_resolution_validation_error(client):
    response = client.post(
        "/admin/v4/apply-resolution",
        json={
            "article_id": 77,
            "lang": "eo",
            "form_id": "form_0",
            "block_id": "block_1",
            "operator_action": {
                "action": "merge",
            },
        },
    )

    assert response.status_code == 422



def test_article_review_service_apply_resolution_persists_operator_action_to_groups_list():
    class FakeSession:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

    service = ArticleReviewService.__new__(ArticleReviewService)
    service.session = FakeSession()
    state = SimpleNamespace(resolved_translations={"groups": []})
    service._ensure_state = lambda lang, art_id: state

    result = service.apply_resolution_action(
        "eo",
        55,
        "form_0",
        "block_2",
        {"action": "accept", "selected_candidate_id": "c1"},
    )

    assert result["status"] == "ok"
    assert service.session.commits == 1
    groups = state.resolved_translations["groups"]
    assert isinstance(groups, list)
    assert groups[0]["form_id"] == "form_0"
    assert groups[0]["block_id"] == "block_2"
    assert groups[0]["operator_action"] == {"action": "accept", "selected_candidate_id": "c1"}
