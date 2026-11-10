"""Execute: python run.py. Interrompa com Ctrl+C."""
import argparse
from waitress import serve
from biometria import create_app, issue_setup_code
from biometria.auth import issue_activation_code


def main():
    parser = argparse.ArgumentParser(description="Guardião • APS de autenticação biométrica")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de escuta; padrão restrito ao próprio computador")
    args = parser.parse_args()
    try:
        app = create_app()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    code = issue_setup_code(app)
    activation = issue_activation_code(app)
    print(f"\nGuardião disponível em http://localhost:{args.port}", flush=True)
    if code:
        print(f"\nPrimeiro uso: abra /configurar e informe este código: {code}\n"
              "Cadastre o rosto do participante que representará o ministro.\n", flush=True)
    if activation:
        print(f"\nCadastros anteriores sem senha: abra /ativar-conta. Código: {activation}\n"
              "Cada participante confirma o próprio rosto e define sua senha.\n", flush=True)
    print("Mantenha este terminal aberto. Para encerrar: Ctrl+C.\n", flush=True)
    serve(app, host=args.host, port=args.port, threads=4, max_request_body_size=22*1024*1024)


if __name__ == "__main__":
    main()
