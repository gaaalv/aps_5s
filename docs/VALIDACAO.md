# Validação da entrega

Data: 09/09/2026. Versão 2 (UX e login com senha).

Ambiente executado: Linux x86_64, Python 3.12.13, Flask 3.1.2, OpenCV 4.12.0, NumPy 2.2.6. Dependências e versões diretas estão em `requirements.txt`.

## Resultado

**50 testes diferentes aprovados**, em duas execuções complementares: suíte padrão (48 aprovados, 2 ignorados por exigirem imagens) e módulo facial/fluxo real com imagens (7 aprovados, incluindo os 2 opcionais e 5 já executados). Nenhuma falha.

Comandos executados:

```bash
python -m pytest -q
GUARDIAO_TEST_FACES=/caminho/das/imagens python -m pytest tests/test_face.py tests/test_real_flow.py -q
```

As imagens externas de validação não acompanham o pacote e os bancos de teste são temporários.

## Cobertura

Novas verificações da versão 2:

- Login como entrada inicial e boletins públicos preservados.
- Senha correta sem autorização até a confirmação facial.
- Impossibilidade de usar o endpoint facial antigo para pular a senha.
- Vinculação da etapa facial à conta da senha, ignorando troca de usuário no formulário de foto.
- Consumo único, expiração, cancelamento e limite de tentativas da etapa facial.
- Senhas fracas ou confirmação divergente rejeitadas.
- Hash scrypt válido no banco, sem senha ou hash expostos nos endpoints/páginas verificados.
- Menus e páginas coerentes com os níveis 1, 2 e 3.
- Bloqueio de uma etapa facial pendente após desativação do usuário.
- Migração de esquema antigo, preservação exata do vetor, revogação da sessão antiga e ativação com o rosto correto.
- Ativação rejeitada com código ou rosto incorreto, sem reutilização após definir a senha.
- Reinício idempotente sem apagar as sessões da versão 2.

Verificações anteriores mantidas e adaptadas:

- Páginas públicas e renderização das páginas administrativas via Flask.
- Proteção contra POST sem token CSRF e configuração sem segredo local.
- Configuração única do ministro, sem autenticação automática após cadastro.
- Matriz de permissões de visitante, servidor, diretor e ministro.
- Bloqueio de URL direta para conteúdo restrito e de endpoints administrativos.
- Verificação com usuário/senha incorretos, rosto desconhecido e correspondência ambígua.
- Cadastro de rosto repetido, mistura de identidades, fotos idênticas e falta de consentimento.
- Impedimento de criar um segundo ministro ou de excluir/desativar o ministro pela interface.
- Desativação, exclusão de vetores e revogação de sessões.
- Expiração de sessão e tentativa de reutilizar cookie após logout.
- Janela persistente de limitação de tentativas e limites de upload.
- Registro dos eventos de autenticação, cadastro e consulta.
- Motor ONNX real: arquivos inválidos, formatos, dimensões, imagem sem rosto e com múltiplos rostos.
- Similaridade real: mesma imagem com variação de luz aceita e outra identidade rejeitada.
- Fluxo HTTP com inferência real: configuração de ministro com senha, login em duas etapas, cadastro de diretor, novo login em duas etapas e bloqueio do nível 3.

Também foram verificadas a sintaxe Python, a sintaxe JavaScript, a carga dos modelos e a integridade SHA-256 dos dois arquivos ONNX.

## Limites

Não foram executados navegador gráfico, webcam física ou instaladores `.bat` em Windows neste ambiente. Esses pontos precisam ser conferidos no computador da apresentação pelo roteiro incluído. Os testes de páginas via Flask não medem layout nem execução do JavaScript no navegador.

Os testes de autorização usam vetores controlados para produzir casos determinísticos. Os testes de imagem real usam duas imagens de referência e variações de luminosidade: verificam funcionamento, sem constituir avaliação de precisão, resistência a fraude ou generalização para usuários reais. Não foi medida uma taxa FAR/FRR em uma população.

Fontes das imagens de referência usadas apenas na validação local: [amostra do OpenCV](https://github.com/opencv/opencv/blob/4.x/samples/data/lena.jpg) e [amostra astronaut do scikit-image](https://github.com/scikit-image/scikit-image/blob/v0.19.3/skimage/data/astronaut.png). As imagens foram usadas com identidades técnicas de teste e não são conteúdo de demonstração entregue.

## Rodada em Python 3.14 (10/11/2026)

Ambiente: Windows 11, Python 3.14.5, Flask 3.1.3, Werkzeug 3.1.9, OpenCV 4.13.0.92, NumPy 2.3.5, Pillow 12.0.0, pytest 9.2.0. Veja `docs/ATUALIZACAO_PYTHON_314.html`.

Resultado: **50 aprovados, 0 ignorados e 0 falhas** com `GUARDIAO_TEST_FACES` apontando para as duas imagens de referência citadas acima; sem as imagens, 48 aprovados e 2 ignorados. `verificar.py` e a verificação SHA-256 dos modelos passaram, e o servidor respondeu às rotas públicas, de redirecionamento e de bloqueio. Os limites da seção anterior continuam válidos: webcam, navegador gráfico e os `.bat` não foram exercitados.
