"""Diagnóstico propio: no se ve el de otra, y la ruta no se inventa."""

from conftest import requires_database

pytestmark = requires_database


def test_diagnostic_builds_a_route_for_the_owner(client, account, business) -> None:
    questions = client.get("/diagnostic-questions", headers=account.headers)
    assert questions.status_code == 200
    assert len(questions.json()) == 3

    started = client.post(
        "/diagnostic-sessions",
        headers=account.headers,
        json={"business_id": business},
    )
    assert started.status_code == 201, started.text
    session_id = started.json()["id"]

    for item in questions.json():
        written = client.put(
            f"/diagnostic-sessions/{session_id}/answers",
            headers=account.headers,
            json={"question_code": item["code"], "answer_text": "respuesta de prueba"},
        )
        assert written.status_code == 200, written.text

    route = client.post(
        f"/diagnostic-sessions/{session_id}/complete",
        headers=account.headers,
    )
    assert route.status_code == 200, route.text
    assert len(route.json()["steps"]) == 3

    listed = client.get(
        "/formalization-routes",
        headers=account.headers,
        params={"business_id": business},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == route.json()["id"]

    first = route.json()["steps"][0]["id"]
    done = client.post(f"/formalization-steps/{first}/complete", headers=account.headers)
    assert done.status_code == 200
    assert done.json()["steps"][0]["completed_at"]


def test_another_account_cannot_read_the_diagnostic(
    client, account, make_account, business
) -> None:
    started = client.post(
        "/diagnostic-sessions",
        headers=account.headers,
        json={"business_id": business},
    )
    other = make_account()
    peek = client.get(
        f"/diagnostic-sessions/{started.json()['id']}",
        headers=other.headers,
    )
    assert peek.status_code == 404
