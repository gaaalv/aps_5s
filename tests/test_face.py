"""Verifica o motor real com os modelos ONNX distribuídos no projeto."""
from io import BytesIO
from pathlib import Path
import os

import numpy as np
import pytest
from PIL import Image, ImageEnhance
from biometria.face import FaceEngine, FaceError


@pytest.fixture(scope="module")
def engine():
    return FaceEngine(Path(__file__).resolve().parents[1] / "models")


def blob(image):
    stream = BytesIO(); image.save(stream, format="PNG"); return stream.getvalue()


@pytest.mark.parametrize("content", [b"not an image", b"", b"x"*(5*1024*1024+1)])
def test_invalid_image_rejected(engine, content):
    with pytest.raises(FaceError):
        engine.extract(content)


def test_blank_has_no_face(engine):
    with pytest.raises(FaceError, match="Nenhum rosto"):
        engine.extract(blob(Image.new("RGB", (640,480), "white")))


def test_format_and_dimensions(engine):
    out = BytesIO(); Image.new("RGB", (100,100)).save(out, "GIF")
    with pytest.raises(FaceError, match="Formato"):
        engine.extract(out.getvalue())
    with pytest.raises(FaceError, match="grande"):
        engine.extract(blob(Image.new("RGB", (4100,4000), "white")))


@pytest.mark.skipif(not os.environ.get("GUARDIAO_TEST_FACES"), reason="Forneça uma pasta de imagens de teste autorizadas, conforme README.")
def test_real_similarity_and_multiple_faces(engine):
    folder = Path(os.environ["GUARDIAO_TEST_FACES"])
    a = Image.open(folder / "face_a.jpg").convert("RGB")
    b = Image.open(folder / "face_b.png").convert("RGB")
    va = engine.extract(blob(a)); va2 = engine.extract(blob(ImageEnhance.Brightness(a).enhance(0.85)))
    vb = engine.extract(blob(b))
    assert va.shape == (128,) and np.isclose(np.linalg.norm(va),1)
    assert float(va @ va2) >= 0.5
    assert float(va @ vb) < 0.5
    pair = Image.new("RGB", (1024,512)); pair.paste(a.resize((512,512))); pair.paste(b.resize((512,512)),(512,0))
    with pytest.raises(FaceError, match="mais de um"):
        engine.extract(blob(pair))
