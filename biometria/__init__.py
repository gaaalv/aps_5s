"""Aplicação web acadêmica: identificação 1:N e autenticação facial 1:1."""
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import time

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session
from werkzeug.exceptions import HTTPException

from .db import audit, candidates, close_db, get_db, init_db
from .face import FaceEngine, FaceError, rank_candidates
from .auth import (current_user, require_level, pending_identity, needs_password_setup,
                   password_from_form, register_auth)

ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    return sha256(value.encode()).hexdigest()


def create_app(test_config=None, engine=None):
    app = Flask(__name__)
    data_dir = Path(os.environ.get("GUARDIAO_DATA", str(ROOT / "instance")))
    if test_config and "DATA_DIR" in test_config:
        data_dir = Path(test_config["DATA_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    key_path = data_dir / "secret.key"
    try:
        with key_path.open("x", encoding="ascii") as stream:
            stream.write(secrets.token_hex(32))
        key_path.chmod(0o600)
    except FileExistsError:
        pass
    app.config.update(
        SECRET_KEY=key_path.read_text(encoding="ascii").strip(),
        DATABASE=str(data_dir / "guardiao.sqlite3"),
        MAX_CONTENT_LENGTH=21 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=64 * 1024,
        MAX_FORM_PARTS=20,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("GUARDIAO_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=20),
        FACE_THRESHOLD=float(os.environ.get("GUARDIAO_THRESHOLD", "0.50")),
        FACE_MARGIN=0.08,
        SESSION_SECONDS=1200,
        MODEL_DIR=str(ROOT / "models"),
    )
    if test_config:
        app.config.update(test_config)
    if not 0.3 <= app.config["FACE_THRESHOLD"] <= 0.9:
        raise ValueError("GUARDIAO_THRESHOLD deve estar entre 0.3 e 0.9.")
    app.teardown_appcontext(close_db)
    # Falha explícita ao iniciar se os modelos não estiverem disponíveis.
    app.extensions["face_engine"] = engine or FaceEngine(app.config["MODEL_DIR"])
    with app.app_context():
        init_db()

    def setup_pending():
        return not get_db().execute("SELECT 1 FROM users LIMIT 1").fetchone()

    @app.before_request
    def protect_requests():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        if request.method in ("POST", "PATCH", "DELETE", "PUT"):
            value = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(value, session["csrf"]):
                abort(400, "Página expirada. Atualize a página e tente novamente.")
        if request.path in ("/api/login", "/api/setup", "/api/auth/password", "/api/activate") and request.method == "POST":
            # Sem confiar em X-Forwarded-For. Janela persistida inclusive após reinício.
            db = get_db()
            now = time.time()
            address = request.remote_addr or "local"
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM attempts WHERE stamp < ?", (now - 60,))
            count = db.execute("SELECT count(*) FROM attempts WHERE address=?", (address,)).fetchone()[0]
            if count >= 10:
                db.commit()
                abort(429, "Muitas tentativas. Aguarde um minuto antes de tentar novamente.")
            db.execute("INSERT INTO attempts VALUES(?,?)", (address, now))
            db.commit()

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if response.status_code == 429:
            response.headers["Retry-After"] = "60"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = "Envio muito grande. Use no máximo 3 fotos de até 5 MB cada." if error.code == 413 else error.description
        if request.path.startswith("/api/"):
            return jsonify(error=message), error.code
        return render_template("error.html", message=message, code=error.code), error.code

    @app.errorhandler(FaceError)
    def face_error(error):
        if request.path == "/api/login":
            audit("autenticacao_negada", str(error))
        return jsonify(error=str(error)), 422

    @app.errorhandler(Exception)
    def unexpected_error(error):
        get_db().rollback()
        app.logger.exception("Erro interno no processamento")
        if request.path.startswith("/api/"):
            return jsonify(error="Não foi possível concluir. Consulte o terminal do servidor e tente novamente."), 500
        return render_template("error.html", message="Falha interna. Consulte o terminal do servidor.", code=500), 500

    @app.context_processor
    def template_context():
        return dict(user=current_user(), csrf=session.get("csrf", ""))

    @app.get("/")
    def home():
        return redirect("/painel" if current_user() else "/entrar")

    @app.get("/entrar")
    def login_page():
        if current_user():
            return redirect("/painel")
        return render_template("login.html", setup_pending=setup_pending(),
                               legacy_accounts=needs_password_setup())

    @app.get("/confirmar-rosto")
    def face_page():
        pending = pending_identity()
        if not pending:
            return redirect("/entrar")
        return render_template("face_login.html", identity=pending)

    @app.get("/ativar-conta")
    def activation_page():
        if not needs_password_setup():
            return redirect("/entrar")
        return render_template("activate.html")

    @app.get("/configurar")
    def setup_page():
        if not setup_pending():
            return redirect("/entrar")
        return render_template("enroll.html", initial=True)

    @app.get("/painel")
    @require_level(1)
    def overview():
        return render_template("dashboard.html")

    def documents(level, title, description):
        return render_template("documents.html", section_level=level,
                               section_title=title, section_description=description)

    @app.get("/boletins")
    def bulletins():
        return documents(1, "Boletins públicos", "Informações ambientais e orientações disponíveis para todos.")

    @app.get("/investigacoes")
    @require_level(2)
    def investigations():
        return documents(2, "Investigações", "Dossiês e ocorrências acompanhados pelas diretorias de divisão.")

    @app.get("/gabinete")
    @require_level(3)
    def cabinet():
        return documents(3, "Gabinete do ministro", "Diretrizes e informações estratégicas de acesso exclusivo ao ministro.")

    @app.get("/usuarios")
    @require_level(3)
    def users_page():
        return render_template("users.html")

    @app.get("/usuarios/novo")
    @require_level(3)
    def new_user_page():
        return render_template("enroll.html", initial=False)

    @app.get("/auditoria")
    @require_level(3)
    def audit_page():
        return render_template("audit.html")

    @app.get("/api/state")
    def state():
        return jsonify(user=current_user(), setup_pending=setup_pending(),
                       csrf=session["csrf"], face_pending=bool(pending_identity()))

    @app.get("/api/records")
    def records():
        user = current_user()
        level = user["level"] if user else 1
        # Filtragem no SQL: dados restritos nunca são enviados para o navegador público.
        requested = request.args.get("level")
        if requested is not None:
            if requested not in ("1", "2", "3"):
                abort(400, "Nível inválido.")
            if int(requested) > level:
                abort(403, "Seu perfil não tem acesso a esta área.")
            rows = get_db().execute("SELECT * FROM records WHERE level=? ORDER BY id", (int(requested),))
        else:
            rows = get_db().execute("SELECT * FROM records WHERE level<=? ORDER BY level,id", (level,))
        return jsonify(records=[dict(row) for row in rows], level=level)

    @app.get("/api/records/<int:record_id>")
    def record_detail(record_id):
        row = get_db().execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            abort(404, "Registro não encontrado.")
        user = current_user()
        if row["level"] > (user["level"] if user else 1):
            audit("acesso_negado", f"Registro {record_id}", user["id"] if user else None)
            abort(403, "Seu perfil não tem acesso a esta informação.")
        audit("consulta", f"Registro {record_id}", user["id"] if user else None)
        return jsonify(record=dict(row))

    def extract_uploads(count):
        files = request.files.getlist("photos")
        if len(files) != count:
            abort(400, f"Envie exatamente {count} foto(s).")
        blobs = [file.read(5 * 1024 * 1024 + 1) for file in files]
        if count > 1 and len({sha256(blob).hexdigest() for blob in blobs}) != count:
            abort(400, "Use três fotos diferentes da mesma pessoa.")
        return [app.extensions["face_engine"].extract(blob) for blob in blobs]

    def enrollment(initial):
        if request.form.get("consent") != "yes":
            abort(400, "É necessário o consentimento da pessoa para cadastrar a biometria.")
        name = request.form.get("name", "").strip()
        login = request.form.get("login", "").strip().lower()
        if not 3 <= len(name) <= 80:
            abort(400, "Informe um nome entre 3 e 80 caracteres.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,39}", login):
            abort(400, "Identificador: 3 a 40 letras sem acento, números, ponto, hífen ou sublinhado.")
        if initial:
            level = 3
        else:
            raw_level = request.form.get("level")
            if raw_level not in ("1", "2"):
                abort(400, "Escolha servidor (nível 1) ou diretor (nível 2).")
            level = int(raw_level)
        password_hash = password_from_form()
        vectors = extract_uploads(3)
        threshold = app.config["FACE_THRESHOLD"]
        for i in range(len(vectors)):
            for j in range(i):
                if float(vectors[i] @ vectors[j]) < threshold:
                    raise FaceError("As fotos não são consistentes. Use a mesma pessoa, de frente e com boa luz.")
        db = get_db()
        # Serializa validação de duplicidade e cadastro; impede dois ministros no bootstrap.
        db.execute("BEGIN IMMEDIATE")
        try:
            if initial:
                if not setup_pending():
                    abort(409, "A configuração inicial já foi concluída.")
                stored = db.execute("SELECT value FROM settings WHERE key='setup_hash'").fetchone()
                token = request.form.get("setup_code", "")
                if not stored or not secrets.compare_digest(digest(token), stored[0]):
                    abort(403, "Código de configuração inválido. Confira o terminal do servidor.")
            else:
                require_level(3)(lambda: None)()
            if db.execute("SELECT 1 FROM users WHERE login=?", (login,)).fetchone():
                abort(409, "Este identificador já está cadastrado.")
            # Inclui cadastros inativos para impedir duplicação da identidade.
            existing = []
            for row in db.execute("SELECT user_id,vector FROM samples"):
                existing.append({"vectors": [json.loads(row["vector"])]})
            for vector in vectors:
                matches = rank_candidates(vector, existing)
                if matches and matches[0][0] >= threshold:
                    abort(409, "Este rosto parece já estar cadastrado. Consulte a lista de usuários.")
            cursor = db.execute("INSERT INTO users(name,login,level,password_hash) VALUES(?,?,?,?)", (name, login, level, password_hash))
            user_id = cursor.lastrowid
            db.executemany("INSERT INTO samples(user_id,vector) VALUES(?,?)",
                           [(user_id, json.dumps(v.tolist())) for v in vectors])
            if initial:
                db.execute("DELETE FROM settings WHERE key='setup_hash'")
            actor = user_id if initial else current_user()["id"]
            db.execute("INSERT INTO audit(user_id,event,detail) VALUES(?,?,?)",
                       (actor, "cadastro", f"Usuário {user_id}; nível {level}; consentimento confirmado"))
            db.commit()
        except Exception:
            db.rollback()
            raise
        return jsonify(message="Usuário criado. Senha e rosto vinculados ao mesmo cadastro.", login=login, next="/entrar?cadastro=1" if initial else "/usuarios?cadastro=1"), 201

    @app.post("/api/setup")
    def setup():
        if not setup_pending():
            abort(409, "A configuração inicial já foi concluída.")
        # Valida o segredo antes do processamento de imagens.
        stored = get_db().execute("SELECT value FROM settings WHERE key='setup_hash'").fetchone()
        if not stored or not secrets.compare_digest(digest(request.form.get("setup_code", "")), stored[0]):
            abort(403, "Código de configuração inválido. Confira o terminal do servidor.")
        return enrollment(True)

    @app.post("/api/users")
    @require_level(3)
    def create_user():
        return enrollment(False)

    register_auth(app, extract_uploads)

    @app.get("/api/users")
    @require_level(3)
    def users():
        rows = get_db().execute("SELECT id,name,login,level,active,created_at,(password_hash IS NOT NULL) AS password_ready FROM users ORDER BY level DESC,name")
        return jsonify(users=[dict(row) for row in rows])

    @app.patch("/api/users/<int:user_id>")
    @require_level(3)
    def change_user(user_id):
        body = request.get_json(silent=True) or {}
        if type(body.get("active")) is not bool:
            abort(400, "Informe o estado ativo ou inativo.")
        db = get_db()
        target = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not target:
            abort(404, "Usuário não encontrado.")
        if target["level"] == 3:
            abort(403, "O ministro não pode ser desativado pela interface.")
        db.execute("UPDATE users SET active=? WHERE id=?", (int(body["active"]), user_id))
        db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM face_challenges WHERE user_id=?", (user_id,))
        audit("cadastro_alterado", f"Usuário {user_id}; ativo={body['active']}", current_user()["id"])
        return jsonify(message="Situação atualizada. Sessões anteriores foram encerradas.")

    @app.delete("/api/users/<int:user_id>")
    @require_level(3)
    def delete_user(user_id):
        db = get_db()
        row = db.execute("SELECT level FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            abort(404, "Usuário não encontrado.")
        if row["level"] == 3:
            abort(403, "O ministro não pode ser excluído pela interface.")
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        audit("cadastro_excluido", f"Usuário {user_id}; biometria e sessões removidas", current_user()["id"])
        return jsonify(message="Usuário e biometria excluídos.")

    @app.get("/api/audit")
    @require_level(3)
    def audit_entries():
        rows = get_db().execute(
            "SELECT a.*,u.name FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 200"
        )
        return jsonify(events=[dict(row) for row in rows])

    return app


def issue_setup_code(app):
    """Segredo local de uso único; nunca exposto por endpoint ou incluído no ZIP."""
    with app.app_context():
        db = get_db()
        if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return None
        token = secrets.token_urlsafe(18)
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('setup_hash',?)", (digest(token),))
        db.commit()
        return token
