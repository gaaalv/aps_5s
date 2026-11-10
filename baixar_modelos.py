"""Verifica os modelos incluídos; baixa novamente somente se estiverem ausentes."""
from hashlib import sha256
from pathlib import Path
import sys
import urllib.request

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODELS = {
    "yunet.onnx": (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "sface.onnx": (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"),
}


def main():
    MODEL_DIR.mkdir(exist_ok=True)
    for name, (url, expected) in MODELS.items():
        path = MODEL_DIR / name
        if path.exists():
            if sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"{name}: integridade inválida. Renomeie o arquivo e execute novamente.")
            print(f"{name}: integridade OK")
            continue
        print(f"Baixando {name} do repositório oficial OpenCV Zoo…", flush=True)
        temp = path.with_suffix(".download")
        try:
            with urllib.request.urlopen(url, timeout=90) as response, temp.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if sha256(temp.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"{name}: SHA-256 divergente; arquivo não instalado.")
            temp.replace(path)
            print(f"{name}: pronto")
        finally:
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Falha: {error}", file=sys.stderr)
        raise SystemExit(1) from error
