"""Fluxo HTTP completo com inferência real; imagens externas opcionais."""
from io import BytesIO
from pathlib import Path
import os

import pytest
from PIL import Image, ImageEnhance
from biometria import create_app, issue_setup_code


pytestmark = pytest.mark.skipif(not os.environ.get("GUARDIAO_TEST_FACES"), reason="Exige imagens de teste autorizadas.")


def image_bytes(image, factor=1):
    out = BytesIO()
    ImageEnhance.Brightness(image).enhance(factor).save(out, "JPEG", quality=95)
    return out.getvalue()


def test_real_enroll_login_and_authorization(tmp_path):
    folder = Path(os.environ["GUARDIAO_TEST_FACES"])
    a = Image.open(folder / "face_a.jpg").convert("RGB")
    b = Image.open(folder / "face_b.png").convert("RGB")
    app = create_app({"TESTING": True,"DATA_DIR": str(tmp_path)})
    client = app.test_client()

    def post(path, data):
        csrf = client.get("/api/state").json["csrf"]
        return client.post(path, data=data, headers={"X-CSRF-Token": csrf})

    def samples(image):
        return [(BytesIO(image_bytes(image, factor)), f"{i}.jpg") for i,factor in enumerate((.85,1,1.1))]

    result = post("/api/setup", {"password":"SenhaTeste123!","password_confirm":"SenhaTeste123!","name":"Teste Ministro","login":"ministro","consent":"yes", "setup_code":issue_setup_code(app), "photos":samples(a)})
    assert result.status_code == 201, result.json
    assert post("/api/auth/password", {"login":"ministro","password":"SenhaTeste123!"}).status_code == 200
    result = post("/api/login", {"photos":(BytesIO(image_bytes(a,.95)),"foto.jpg"),"mode":"verify","login":"ministro"})
    assert result.status_code == 200, result.json
    assert len(client.get("/api/records").json["records"]) == 6
    result = post("/api/users", {"password":"SenhaTeste123!","password_confirm":"SenhaTeste123!","name":"Teste Diretor","login":"diretor","level":"2","consent":"yes","photos":samples(b)})
    assert result.status_code == 201, result.json
    assert post("/api/logout",{}).status_code == 200
    assert post("/api/auth/password", {"login":"diretor","password":"SenhaTeste123!"}).status_code == 200
    result = post("/api/login", {"photos":(BytesIO(image_bytes(b,.95)),"foto.jpg"),"mode":"identify"})
    assert result.status_code == 200, result.json
    assert client.get("/api/state").json["user"]["level"] == 2
    assert len(client.get("/api/records").json["records"]) == 5
    assert client.get("/api/records/6").status_code == 403
    assert client.get("/api/users").status_code == 403
