"""Administrador local: python redefinir_senha.py usuario (sem e-mail)."""
import argparse
from getpass import getpass

from werkzeug.security import generate_password_hash
from biometria import create_app
from biometria.db import get_db, audit


def main():
    parser = argparse.ArgumentParser(description="Redefinir a senha de um cadastro local, preservando o rosto")
    parser.add_argument("usuario")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        db = get_db()
        user = db.execute("SELECT id FROM users WHERE login=?", (args.usuario.strip().lower(),)).fetchone()
        if not user:
            raise SystemExit("Usuário não encontrado. Nenhuma alteração realizada.")
        password = getpass("Nova senha (mínimo 8 caracteres): ")
        confirmation = getpass("Confirme a nova senha: ")
        if password != confirmation or not 8 <= len(password) <= 128:
            raise SystemExit("Senhas diferentes ou tamanho inválido. Nenhuma alteração realizada.")
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password, method="scrypt"), user["id"]))
        db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        db.execute("DELETE FROM face_challenges WHERE user_id=?", (user["id"],))
        audit("senha_redefinida", "Redefinição pelo administrador local", user["id"])
        print("Senha redefinida. O rosto permanece vinculado e será exigido no próximo login.")


if __name__ == "__main__":
    main()
