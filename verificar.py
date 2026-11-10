"""Diagnóstico local sem cadastrar pessoas ou iniciar o servidor."""
from io import BytesIO
from pathlib import Path
import platform
import sys


def main():
    print(f"Python {platform.python_version()} • {platform.system()} {platform.machine()}")
    if not (3, 10) <= sys.version_info[:2] <= (3, 14):
        raise SystemExit("Utilize Python 3.14 de 64 bits, versão recomendada para este projeto.")
    from PIL import Image
    from biometria.face import FaceEngine, FaceError
    engine = FaceEngine(Path(__file__).resolve().parent / "models")
    content = BytesIO(); Image.new("RGB", (320,320), "white").save(content, "PNG")
    try:
        engine.extract(content.getvalue())
    except FaceError as error:
        if "Nenhum rosto" not in str(error):
            raise
    else:
        raise RuntimeError("Falha inesperada no teste sem rosto.")
    print("Dependências e modelos OK. Execute iniciar.bat ou python run.py.")


if __name__ == "__main__":
    main()
