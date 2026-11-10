"""As duas provas são obrigatórias e a migração não destrói cadastros."""
from io import BytesIO
import json
import sqlite3
import time

import pytest
from werkzeug.security import check_password_hash
from biometria import create_app
from biometria.auth import issue_activation_code
from biometria.db import get_db
from test_system import app, client, setup, login, post, token, enroll_data, add_user, ControlledEngine


def credentials(client, name="minister", password="SenhaTeste123!"):
    return post(client, "/api/auth/password", {"login":name,"password":password})


def face(client, marker=b"a", **extra):
    return post(client, "/api/login", {"photos":(BytesIO(marker),"face.jpg"), **extra})


def test_login_is_entry_and_public_stays_public(client):
    assert client.get("/").location == "/entrar"
    assert client.get("/boletins").status_code == 200
    html = client.get("/entrar").get_data(as_text=True)
    assert 'id="credentials-form"' in html and 'name="password"' in html
    assert 'type="email"' not in html and 'name="email"' not in html
    assert 'id="camera"' not in html


def test_password_alone_does_not_authorize(app, client):
    setup(app, client)
    assert credentials(client).status_code == 200
    assert client.get("/api/state").json["user"] is None
    assert client.get("/api/users").status_code == 401
    assert client.get("/api/records/6").status_code == 403
    assert client.get("/confirmar-rosto").status_code == 200
    assert face(client).status_code == 200
    assert client.get("/api/users").status_code == 200


def test_cannot_bypass_password_with_old_face_endpoint(app, client):
    setup(app, client)
    assert face(client, mode="identify",login="minister").status_code == 401
    assert client.get("/confirmar-rosto").location == "/entrar"
    assert credentials(client, password="wrong-password").status_code == 401
    assert face(client).status_code == 401


def test_face_is_bound_to_password_identity(app, client):
    setup(app, client); add_user(app,2,b"b","director")
    assert credentials(client, "director").status_code == 200
    assert face(client,b"a",login="minister",mode="identify").status_code == 401
    assert client.get("/api/state").json["user"] is None
    assert face(client,b"b",login="minister").status_code == 200
    assert client.get("/api/state").json["user"]["login"] == "director"
    assert client.get("/api/records?level=3").status_code == 403


def test_one_use_expiration_and_cancel(app, client):
    setup(app, client); credentials(client)
    pending_cookie = client.get_cookie("session").value
    assert face(client).status_code == 200
    replay = app.test_client(); replay.set_cookie("session",pending_cookie)
    assert face(replay).status_code == 401
    credentials(client)
    with app.app_context():
        get_db().execute("UPDATE face_challenges SET expires_at=?",(time.time()-1,)); get_db().commit()
    assert face(client).status_code == 401
    credentials(client)
    assert post(client,"/api/auth/cancel",{}).status_code == 200
    assert face(client).status_code == 401


def test_pending_challenge_limited_to_five_attempts(app, client):
    setup(app,client); credentials(client)
    for _ in range(5):
        assert face(client,b"z").status_code == 401
    assert face(client,b"a").status_code == 401
    assert client.get("/api/state").json["face_pending"] is False


def test_hash_not_exposed_or_plaintext(app, client):
    setup(app,client); login(client)
    for endpoint in ("/api/state","/api/users","/api/audit","/usuarios"):
        response = client.get(endpoint).get_data(as_text=True)
        assert "SenhaTeste123!" not in response and "scrypt:" not in response and "password_hash" not in response
    with app.app_context():
        stored = get_db().execute("SELECT password_hash FROM users").fetchone()[0]
        assert stored.startswith("scrypt:") and check_password_hash(stored,"SenhaTeste123!")


@pytest.mark.parametrize("password,confirm",[("short","short"),("validpass123","different"),("a"*129,"a"*129)])
def test_invalid_new_password_rejected(app, client, password,confirm):
    setup(app,client); login(client)
    data=enroll_data("another",b"b"); data.update(password=password,password_confirm=confirm)
    assert post(client,"/api/users",data).status_code == 400


@pytest.mark.parametrize("level,marker,name,visible",[(1,b"b","server",["/boletins"]),(2,b"c","director",["/boletins","/investigacoes"]),(3,b"a","minister",["/boletins","/investigacoes","/gabinete","/usuarios","/auditoria"])])
def test_menus_reflect_permissions(app,client,level,marker,name,visible):
    setup(app,client)
    if level!=3: add_user(app,level,marker,name)
    assert login(client,marker,name=name).status_code == 200
    html=client.get("/painel").get_data(as_text=True)
    for path in ("/boletins","/investigacoes","/gabinete","/usuarios","/auditoria"):
        assert (f'href="{path}"' in html) == (path in visible)
    assert client.get("/api/records?level=1").status_code == 200
    assert client.get("/api/records?level=2").status_code == (200 if level>=2 else 403)
    assert client.get("/gabinete").status_code == (200 if level==3 else 403)


def test_disabled_user_cannot_finish_pending_login(app,client):
    setup(app,client); login(client)
    uid=add_user(app,2,b"b","director")
    other=app.test_client(); assert credentials(other,"director").status_code==200
    assert client.patch(f"/api/users/{uid}",json={"active":False},headers={"X-CSRF-Token":token(client)}).status_code==200
    assert face(other,b"b").status_code==401


def test_legacy_migration_and_password_activation(tmp_path):
    db=sqlite3.connect(tmp_path / "guardiao.sqlite3")
    db.executescript("""
    CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,login TEXT NOT NULL UNIQUE,level INTEGER NOT NULL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE samples(id INTEGER PRIMARY KEY,user_id INTEGER,vector TEXT);
    CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER,expires_at REAL);
    """)
    db.execute("INSERT INTO users(id,name,login,level) VALUES(1,'Ministro anterior','minister',3)")
    original=json.dumps(ControlledEngine().extract(b"a").tolist())
    db.execute("INSERT INTO samples(user_id,vector) VALUES(1,?)",(original,))
    db.execute("INSERT INTO sessions VALUES('old-session',1,?)",(time.time()+1000,))
    db.commit(); db.close()
    app=create_app({"TESTING":True,"DATA_DIR":str(tmp_path)},engine=ControlledEngine())
    client=app.test_client()
    with app.app_context():
        assert get_db().execute("SELECT vector FROM samples").fetchone()[0] == original
        assert get_db().execute("SELECT count(*) FROM sessions").fetchone()[0]==0
    assert credentials(client).status_code==401
    code=issue_activation_code(app)
    def activation(marker=b"a", supplied_code=code):
        return post(client,"/api/activate",{"login":"minister","password":"NovaSenha123!","password_confirm":"NovaSenha123!","activation_code":supplied_code,"photos":(BytesIO(marker),"face.jpg")})
    assert activation(supplied_code="wrong").status_code==403
    assert activation(b"b").status_code==401
    assert activation().status_code==200
    assert activation().status_code==409
    assert client.get("/api/state").json["user"] is None
    assert credentials(client,password="NovaSenha123!").status_code==200
    assert face(client).status_code==200
    assert issue_activation_code(app) is None
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM users").fetchone()[0]==1
        assert get_db().execute("SELECT vector FROM samples").fetchone()[0]==original
    # Reabrir v2 não apaga sessões válidas nem repete a migração.
    create_app({"TESTING":True,"DATA_DIR":str(tmp_path)},engine=ControlledEngine())
    assert client.get("/api/users").status_code==200
