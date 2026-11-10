# Modelos pré-treinados

Arquivos originais obtidos do repositório [OpenCV Zoo](https://github.com/opencv/opencv_zoo). Os nomes locais foram simplificados; os bytes dos modelos foram preservados.

| Arquivo local | Nome de origem | Tamanho em bytes | SHA-256 |
|---|---|---:|---|
| `yunet.onnx` | `face_detection_yunet_2023mar.onnx` | 232589 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `sface.onnx` | `face_recognition_sface_2021dec.onnx` | 38696353 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |

YuNet está sob licença MIT (`LICENSE-YuNet.txt`). SFace está sob Apache 2.0 (`LICENSE-SFace.txt`). As licenças originais acompanham os arquivos. A implementação deste projeto executa inferência desses modelos; não os treinou.

O script `baixar_modelos.py` verifica os arquivos incluídos e baixa somente os ausentes. Se a origem mudar os bytes, o hash divergente faz o script falhar em vez de instalar silenciosamente outro modelo.
