"""Asistente RAG: solo fuentes publicadas, abstención, advertencia y citas.

La recuperación queda congelada en las coincidencias `LIKE` de `v0.1.0`. Cada
prueba usa un término inventado y único para no depender de los datos que otras
pruebas hayan dejado publicados.
"""

import random
import string
import uuid

import pytest
from conftest import requires_database

pytestmark = requires_database


def _unique_term() -> str:
    """Palabra alfabética irrepetible, apta para el filtro `[a-záéíóúñ]+`."""
    return "".join(random.choices(string.ascii_lowercase, k=20))


@pytest.fixture
def publisher() -> str:
    from app.database import SessionLocal
    from app.models.rag import SourcePublisher

    with SessionLocal() as db:
        row = SourcePublisher(
            code=f"T{uuid.uuid4().hex[:12]}",
            name="Instituto de Prueba",
            official_domain="ejemplo.test",
            country_code="BO",
        )
        db.add(row)
        db.commit()
        return row.id


@pytest.fixture
def publish_source(client, curator, publisher):
    """Publica una fuente con un fragmento que contiene el texto indicado."""

    def factory(content: str) -> dict[str, str]:
        source = client.post(
            "/sources",
            headers=curator.headers,
            json={
                "publisher_id": publisher,
                "title": "Guía oficial de prueba",
                "canonical_url": f"https://ejemplo.test/{uuid.uuid4().hex}",
                "topic": "formalización",
                "jurisdiction": "Bolivia",
            },
        )
        assert source.status_code == 201, source.text

        version = client.post(
            "/source-versions",
            headers=curator.headers,
            json={
                "source_id": source.json()["id"],
                "version_label": "2026-01",
                "content_hash": uuid.uuid4().hex + uuid.uuid4().hex,
                "storage_key": f"sources/{uuid.uuid4().hex}.pdf",
            },
        )
        assert version.status_code == 201, version.text

        chunk = client.post(
            "/source-chunks",
            headers=curator.headers,
            json={
                "source_version_id": version.json()["id"],
                "chunk_number": 1,
                "heading": "Requisitos",
                "content": content,
                "token_count": 40,
            },
        )
        assert chunk.status_code == 201, chunk.text

        published = client.post(
            f"/source-versions/{version.json()['id']}/publish", headers=curator.headers
        )
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "PUBLISHED"
        return {"source_id": source.json()["id"], "version_id": version.json()["id"]}

    return factory


def test_abstains_without_evidence(client, account) -> None:
    response = client.post(
        "/assistant/query", headers=account.headers, json={"message": f"consulta sobre {_unique_term()}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["abstained"] is True
    assert body["citations"] == []
    assert "se abstuvo" in body["warning"]
    assert "No encontré evidencia suficiente" in body["answer"]
    assert body["trace_id"]


def test_answers_with_citations_from_published_sources(client, account, publish_source) -> None:
    term = _unique_term()
    publish_source(f"Para registrar una {term} se requiere la documentación vigente del titular.")

    response = client.post(
        "/assistant/query", headers=account.headers, json={"message": f"cómo funciona una {term}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["abstained"] is False
    assert len(body["citations"]) >= 1
    citation = body["citations"][0]
    assert citation["institution"] == "Instituto de Prueba"
    assert citation["title"] == "Guía oficial de prueba"
    assert citation["url"].startswith("https://ejemplo.test/")
    assert citation["version_or_date"] == "2026-01"
    assert term in body["answer"]


def test_normative_answer_carries_a_warning_and_citations(client, account, publish_source) -> None:
    term = _unique_term()
    publish_source(f"El impuesto aplicable a una {term} depende del régimen elegido por la titular.")

    response = client.post(
        "/assistant/query",
        headers=account.headers,
        json={"message": f"qué impuesto paga una {term}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["abstained"] is False
    assert body["warning"] is not None
    assert "sujeta a cambios" in body["warning"]
    assert len(body["citations"]) >= 1, "una respuesta normativa nunca va sin cita"


def test_retired_versions_stop_being_retrieved(client, account, publish_source) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.rag import SourceVersion

    term = _unique_term()
    published = publish_source(f"Una {term} debe renovar su registro cada gestión.")

    found = client.post(
        "/assistant/query", headers=account.headers, json={"message": f"sobre la {term}"}
    )
    assert found.json()["abstained"] is False

    with SessionLocal() as db:
        version = db.scalar(select(SourceVersion).where(SourceVersion.id == published["version_id"]))
        version.status = "RETIRED"
        db.commit()

    after = client.post(
        "/assistant/query", headers=account.headers, json={"message": f"sobre la {term}"}
    )
    assert after.json()["abstained"] is True, "una versión retirada no puede citarse"
    assert after.json()["citations"] == []


def test_a_version_without_chunks_cannot_be_published(client, curator, publisher) -> None:
    source = client.post(
        "/sources",
        headers=curator.headers,
        json={
            "publisher_id": publisher,
            "title": "Guía sin fragmentos",
            "canonical_url": f"https://ejemplo.test/{uuid.uuid4().hex}",
            "topic": "formalización",
        },
    )
    version = client.post(
        "/source-versions",
        headers=curator.headers,
        json={
            "source_id": source.json()["id"],
            "version_label": "2026-01",
            "content_hash": uuid.uuid4().hex + uuid.uuid4().hex,
            "storage_key": f"sources/{uuid.uuid4().hex}.pdf",
        },
    )
    response = client.post(
        f"/source-versions/{version.json()['id']}/publish", headers=curator.headers
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "No se puede publicar sin fragmentos"}


def test_publishing_requires_the_publish_permission(client, account, publisher) -> None:
    response = client.post(
        f"/source-versions/{uuid.uuid4()}/publish", headers=account.headers
    )
    assert response.status_code == 403


def test_every_answer_persists_a_traceable_run(client, account) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.conversation import AIRun

    response = client.post(
        "/assistant/query", headers=account.headers, json={"message": f"consulta {_unique_term()}"}
    )
    trace_id = response.json()["trace_id"]

    with SessionLocal() as db:
        run = db.scalar(select(AIRun).where(AIRun.trace_id == trace_id))
        assert run is not None, "cada respuesta deja un AIRun"
        assert run.abstained is True
        assert run.response_status == "ABSTAINED"
        assert run.model_name == "retrieval-only-mvp"
        assert run.prompt_policy_version == "safe-rag-v1"


def test_messages_keep_their_sequence(client, account) -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.conversation import Message

    first = client.post(
        "/assistant/query", headers=account.headers, json={"message": "primera consulta"}
    )
    assert first.status_code == 200
    conversation_id = client.get("/conversations", headers=account.headers).json()[0]["id"]

    second = client.post(
        "/assistant/query",
        headers=account.headers,
        json={"conversation_id": conversation_id, "message": "segunda consulta"},
    )
    assert second.status_code == 200

    with SessionLocal() as db:
        sequences = list(
            db.scalars(
                select(Message.sequence_number)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence_number)
            )
        )
    assert sequences == [1, 2, 3, 4], "usuaria y asistente alternan sin huecos ni choques"
