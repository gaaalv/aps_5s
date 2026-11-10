"""Detecção YuNet, alinhamento SFace e comparação de vetores normalizados."""
from io import BytesIO
from pathlib import Path
import threading
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


class FaceError(ValueError):
    pass


def unit(vector):
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(vector).all() or norm < 1e-8:
        raise FaceError("Não foi possível calcular a biometria. Tente outra foto.")
    return vector / norm


def rank_candidates(probe, users):
    """Máxima similaridade por pessoa; nenhuma pontuação é probabilidade."""
    ranked = []
    for user in users:
        score = max(float(np.dot(probe, unit(v))) for v in user["vectors"])
        ranked.append((score, user))
    return sorted(ranked, key=lambda item: item[0], reverse=True)


class FaceEngine:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        for name in ("yunet.onnx", "sface.onnx"):
            if not (model_dir / name).is_file():
                raise RuntimeError("Modelos ausentes. Execute: python baixar_modelos.py")
        # Objetos DNN têm estado interno; uma trava protege inferências concorrentes.
        self.lock = threading.Lock()
        self.detector = cv2.FaceDetectorYN.create(
            str(model_dir / "yunet.onnx"), "", (320, 320), 0.9, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(model_dir / "sface.onnx"), "")

    def extract(self, content):
        if not content or len(content) > 5 * 1024 * 1024:
            raise FaceError("Envie uma imagem JPG ou PNG de até 5 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as source:
                    if source.format not in ("JPEG", "PNG"):
                        raise FaceError("Formato inválido. Use JPG ou PNG.")
                    if source.width * source.height > 16_000_000:
                        raise FaceError("Imagem muito grande. Limite: 16 megapixels.")
                    photo = ImageOps.exif_transpose(source).convert("RGB")
                    photo.thumbnail((1280, 1280))
                    frame = cv2.cvtColor(np.asarray(photo), cv2.COLOR_RGB2BGR)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise FaceError("Arquivo inválido ou imagem danificada.") from exc

        height, width = frame.shape[:2]
        with self.lock:
            self.detector.setInputSize((width, height))
            _, faces = self.detector.detect(frame)
            if faces is None or len(faces) == 0:
                raise FaceError("Nenhum rosto encontrado. Melhore a luz e olhe para a câmera.")
            if len(faces) != 1:
                raise FaceError("Há mais de um rosto. Fotografe apenas uma pessoa.")
            face = faces[0]
            x, y, w, h = face[:4]
            if min(w, h) < 70:
                raise FaceError("O rosto está pequeno. Aproxime-se da câmera.")
            if x < 0 or y < 0 or x + w > width or y + h > height:
                raise FaceError("O rosto está cortado. Centralize-o na imagem.")
            crop = frame[int(y):int(y+h), int(x):int(x+w)]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            if gray.mean() < 35 or gray.mean() > 235:
                raise FaceError("Iluminação inadequada. Evite sombra ou luz muito forte.")
            if cv2.Laplacian(gray, cv2.CV_64F).var() < 20:
                raise FaceError("Imagem desfocada. Mantenha a câmera firme e tente novamente.")
            aligned = self.recognizer.alignCrop(frame, face)
            return unit(self.recognizer.feature(aligned).copy())
