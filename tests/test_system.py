"""Testes de autorização e persistência com vetores controlados (sem webcam)."""
from io import BytesIO
import json
import time

import numpy as np
import pytest
from werkzeug.security import generate_password_hash
from biometria import create_app, issue_setup_code
from biometria.db import get_db
from biometria.face import FaceError, rank_candidates


class ControlledEngine:
    def extract(self, blob):
        if blob == b"invalid":
            raise FaceError("Imagem inválida")
        vector = np.zeros(128, dtype=np.float32)
        vector[blob[0] % 128] = 1
        return vector


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)}, engine=ControlledEngine())


@pytest.fixture
def client(app):
    return app.test_client()


def token(client):
    return client.get("/api/state").json["csrf"]


def post(client, path, data):
    return client.post(path, data=data, headers={"X-CSRF-Token": token(client)})


def enroll_data(login="minister", marker=b"a", level="2"):
    return {"password":"SenhaTeste123!", "password_confirm":"SenhaTeste123!", "name": "Participante " + login, "login": login, "level": level, "consent": "yes",
            "photos": [(BytesIO(marker+str(i).encode()), f"foto{i}.jpg") for i in range(3)]}


def setup(app, client):
    data = enroll_data()
    data["setup_code"] = issue_setup_code(app)
    response = post(client, "/api/setup", data)
    assert response.status_code == 201, response.json


def login(client, marker=b"a", mode="identify", name=""):
    account = name or {b"a":"minister",b"b":"server",b"c":"director"}.get(marker,"unknown")
    response = post(client, "/api/auth/password", {"login":account,"password":"SenhaTeste123!"})
    if response.status_code != 200:
        return response
    return post(client, "/api/login", {"photos": (BytesIO(marker), "photo.jpg")})


def add_user(app, level, marker, name):
    with app.app_context():
        db = get_db()
        uid = db.execute("INSERT INTO users(name,login,level,password_hash) VALUES(?,?,?,?)", (name, name, level, generate_password_hash("SenhaTeste123!"))).lastrowid
        vector = ControlledEngine().extract(marker).tolist()
        db.execute("INSERT INTO samples(user_id,vector) VALUES(?,?)", (uid, json.dumps(vector)))
        db.commit()
        return uid


@pytest.mark.parametrize("path", ["/boletins", "/entrar", "/configurar"])
def test_public_pages(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b'lang="pt-BR"' in response.data
    assert response.headers["Cache-Control"] == "no-store"


def test_public_sql_filter_and_direct_url(client):
    rows = client.get("/api/records").json["records"]
    assert len(rows) == 3 and {r["level"] for r in rows} == {1}
    assert all("Fazenda" not in r["title"] for r in rows)
    assert client.get("/api/records/4").status_code == 403
    assert client.get("/api/records/6").status_code == 403


@pytest.mark.parametrize("path", ["/api/users", "/api/audit", "/usuarios", "/auditoria"])
def test_anonymous_admin_denied(client, path):
    assert client.get(path).status_code == (401 if path.startswith("/api/") else 302)


def test_csrf_required(client):
    assert client.post("/api/setup", data=enroll_data()).status_code == 400


def test_setup_requires_local_secret(app, client):
    issue_setup_code(app)
    assert post(client, "/api/setup", enroll_data()).status_code == 403


def test_bootstrap_once_and_no_automatic_auth(app, client):
    setup(app, client)
    assert client.get("/api/state").json["user"] is None
    assert issue_setup_code(app) is None
    assert post(client, "/api/setup", enroll_data()).status_code == 409
    assert client.get("/configurar").status_code == 302


@pytest.mark.parametrize("level,marker,name,expected", [(1,b"b","server",3),(2,b"c","director",5),(3,b"a","minister",6)])
def test_role_matrix(app, client, level, marker, name, expected):
    setup(app, client)
    if level != 3:
        add_user(app, level, marker, name)
    assert login(client, marker).status_code == 200
    records = client.get("/api/records").json["records"]
    assert len(records) == expected and max(r["level"] for r in records) == level
    assert client.get("/api/records/6").status_code == (200 if level == 3 else 403)
    assert client.get("/api/users").status_code == (200 if level == 3 else 403)


def test_verification_wrong_claim_and_unknown(app, client):
    setup(app, client)
    assert login(client, mode="verify", name="minister").status_code == 200
    assert login(client, mode="verify", name="someoneelse").status_code == 401
    assert client.get("/api/state").json["user"] is None
    assert login(client, marker=b"z").status_code == 401


def test_ambiguous_identity_rejected(app, client):
    setup(app, client)
    add_user(app, 1, b"a", "duplicate_fixture")
    assert login(client).status_code == 401


def test_duplicate_face_blocked(app, client):
    setup(app, client); login(client)
    assert post(client, "/api/users", enroll_data("another", b"a")).status_code == 409


def test_mixed_enrollment_rejected(app, client):
    setup(app, client); login(client)
    data = enroll_data("mixed", b"b")
    data["photos"][-1] = (BytesIO(b"z4"), "other.jpg")
    assert post(client, "/api/users", data).status_code == 422


def test_three_unique_photos_and_consent(app, client):
    setup(app, client); login(client)
    data = enroll_data("identical", b"b")
    data["photos"] = [(BytesIO(b"same"), f"{i}.jpg") for i in range(3)]
    assert post(client, "/api/users", data).status_code == 400
    data = enroll_data("noconsent", b"c"); data.pop("consent")
    assert post(client, "/api/users", data).status_code == 400


def test_cannot_create_second_minister(app, client):
    setup(app, client); login(client)
    assert post(client, "/api/users", enroll_data("intruder", b"b", "3")).status_code == 400


def test_enroll_disable_revoke_and_delete(app, client):
    setup(app, client); login(client)
    assert post(client, "/api/users", enroll_data("director", b"b")).status_code == 201
    users = client.get("/api/users").json["users"]
    assert all("vectors" not in u for u in users)
    uid = next(u["id"] for u in users if u["login"] == "director")
    other = app.test_client()
    assert login(other, b"b", name="director").status_code == 200
    response = client.patch(f"/api/users/{uid}", json={"active": False}, headers={"X-CSRF-Token": token(client)})
    assert response.status_code == 200
    assert other.get("/api/state").json["user"] is None
    assert login(other, b"b", name="director").status_code == 401
    response = client.delete(f"/api/users/{uid}", headers={"X-CSRF-Token": token(client)})
    assert response.status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM samples WHERE user_id=?", (uid,)).fetchone()[0] == 0


def test_minister_cannot_delete_or_disable_self(app, client):
    setup(app, client); login(client)
    uid = client.get("/api/state").json["user"]["id"]
    assert client.delete(f"/api/users/{uid}", headers={"X-CSRF-Token": token(client)}).status_code == 403
    assert client.patch(f"/api/users/{uid}", json={"active": False}, headers={"X-CSRF-Token": token(client)}).status_code == 403


def test_logout_server_side_revocation(app, client):
    setup(app, client); login(client)
    cookie = client.get_cookie("session").value
    assert post(client, "/api/logout", {}).status_code == 200
    replay = app.test_client(); replay.set_cookie("session", cookie)
    assert replay.get("/api/users").status_code == 401


def test_session_expiry(app, client):
    setup(app, client); login(client)
    with app.app_context():
        get_db().execute("UPDATE sessions SET expires_at=?", (time.time()-1,)); get_db().commit()
    assert client.get("/api/users").status_code == 401


def test_rate_limit_persistent(app, client):
    for _ in range(10):
        assert login(client, b"z").status_code == 401
    assert login(client, b"z").status_code == 429
    assert login(app.test_client(), b"z").status_code == 429


def test_upload_limits_and_invalid_image(app, client):
    setup(app, client)
    assert post(client, "/api/auth/password", {"login":"minister","password":"SenhaTeste123!"}).status_code == 200
    assert post(client, "/api/login", {"photos": (BytesIO(b"invalid"), "a.jpg")}).status_code == 422
    assert post(client, "/api/login", {}).status_code == 400
    app.config["MAX_CONTENT_LENGTH"] = 1024
    assert post(client, "/api/login", {"photos": (BytesIO(b"a"*2000), "a.jpg")}).status_code == 413


def test_audit_and_protected_templates(app, client):
    setup(app, client); login(client)
    assert client.get("/usuarios").status_code == 200
    assert client.get("/auditoria").status_code == 200
    assert client.get("/api/records/6").status_code == 200
    events = client.get("/api/audit").json["events"]
    assert {"cadastro", "autenticacao_aceita", "consulta"} <= {e["event"] for e in events}


def test_ranking_is_by_person_not_photo():
    probe = np.array([1.,0.])
    result = rank_candidates(probe, [{"id":1,"vectors":[[1.,0.],[0.9,0.1]]}, {"id":2,"vectors":[[0.,1.]]}])
    assert [u["id"] for _,u in result] == [1,2]
