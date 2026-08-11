import pytest

from app.rag.index_manager import index_is_ready

pytestmark = pytest.mark.skipif(
    not index_is_ready(), reason="Knowledge base index not built — run scripts/ingest_documents.py first."
)


def test_emergency_message_short_circuits_conversation(registered_client):
    resp = registered_client.post(
        "/api/chat",
        json={"message": "I have severe chest pain radiating to my arm with cold sweat"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_emergency"] is True
    assert data["response_type"] == "emergency"
    assert "911" in data["message"] or "emergency" in data["message"].lower()


def test_factual_question_answers_directly_without_follow_up(registered_client):
    resp = registered_client.post("/api/chat", json={"message": "What causes migraines?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_type"] == "text"
    assert data["question"] is None


def test_symptom_report_triggers_follow_up_question(registered_client):
    resp = registered_client.post("/api/chat", json={"message": "I have had a headache since this morning"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_type"] == "question"
    assert data["question"] is not None


def test_conversation_persists_and_appears_in_history(registered_client):
    resp = registered_client.post("/api/chat", json={"message": "I have a sore throat"})
    conversation_id = resp.json()["conversation_id"]

    history = registered_client.get("/api/conversations")
    assert history.status_code == 200
    assert any(c["id"] == conversation_id for c in history.json())

    detail = registered_client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) >= 2


def test_conversation_delete(registered_client):
    resp = registered_client.post("/api/chat", json={"message": "I have a mild cough"})
    conversation_id = resp.json()["conversation_id"]
    delete_resp = registered_client.delete(f"/api/conversations/{conversation_id}")
    assert delete_resp.status_code == 204
    get_resp = registered_client.get(f"/api/conversations/{conversation_id}")
    assert get_resp.status_code == 404
