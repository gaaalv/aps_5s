# Guardião 2 — usuário, senha e reconhecimento facial em Python

Sistema acadêmico para a APS de Ciência da Computação descrita no documento **APS — 5º e 6º CC 2025/2**. O servidor, a biometria, a autorização e a persistência são implementados em Python. A interface usa HTML, CSS e JavaScript no navegador.

O projeto já inclui os modelos de reconhecimento facial. Depois de instalar as dependências, o processamento funciona localmente, sem enviar fotos para serviços externos. Todos os dados ambientais são fictícios.

## Já está usando a primeira versão?

Leia **ATUALIZAR.md** antes de trocar os arquivos. Preserve a pasta `instance`: ela contém seus usuários e rostos. A atualização adiciona senhas aos cadastros existentes, sem exigir novas três fotos. Sessões antigas são encerradas.

## Comece por aqui — instalação nova no Windows

1. Instale **Python 3.14 de 64 bits**, com o Python Launcher (`py`), a partir de [Python para Windows](https://www.python.org/downloads/windows/).
2. Extraia **todo o ZIP** para uma pasta. Não execute os arquivos de dentro do ZIP.
3. Execute **`instalar.bat`** e aguarde a conclusão. A instalação das dependências precisa de internet.
4. Execute **`iniciar.bat`** e mantenha a janela aberta.
5. Abra **http://localhost:5000**. A primeira tela é o login.
6. No primeiro uso, clique em **Criar a conta do ministro**. Informe o código do terminal, nome, usuário e senha. Avance para vincular o rosto.
7. Capture **três fotos diferentes** da mesma pessoa, confira o resumo da conta e confirme o consentimento. Salve o cadastro.
8. Na tela de login, informe o **usuário e a senha** criados. Clique em continuar.
9. A segunda tela mostra o nome e o usuário da conta. Capture uma foto e clique em **Confirmar rosto e entrar**.
10. Na área do ministro, abra **Usuários e rostos → Cadastrar usuário** para adicionar os participantes com perfil de servidor ou diretor.

O cadastro de rosto e o login também aceitam arquivos JPG/PNG. **Pessoas diferentes devem representar usuários diferentes.** O sistema bloqueia rostos repetidos, incluindo os de cadastros inativos. Não existe login apenas pela foto nem entrada nas áreas restritas apenas pela senha.

O botão **Consultar boletins públicos** mantém o nível 1 disponível sem login, conforme o enunciado. Não é solicitado ou armazenado e-mail.

Para encerrar, pressione **Ctrl+C** no terminal. Usuários, senhas protegidas e biometrias continuam salvos para a próxima execução.

## Instalação manual

No terminal aberto na pasta do projeto, no Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe baixar_modelos.py
.\.venv\Scripts\python.exe verificar.py
.\.venv\Scripts\python.exe run.py
```

No Linux/macOS, com Python 3.14 disponível:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python baixar_modelos.py
.venv/bin/python verificar.py
.venv/bin/python run.py
```

Não é necessário instalar Node.js, compilar JavaScript, instalar um banco separado ou configurar GPU. O primeiro carregamento pode levar alguns segundos. Uma webcam comum é suficiente para realizar as capturas; a qualidade depende da câmera e da iluminação.

## Fluxos e menus

O login tem duas etapas: **usuário e senha → rosto → minha área**. A etapa facial mostra claramente o usuário ao qual a foto deve corresponder, e permite voltar para trocar de conta. A senha sozinha não abre uma sessão autenticada.

O cadastro também tem duas etapas: **dados e senha → vínculo facial**. Antes de salvar, o resumo mostra nome, usuário e perfil. O botão final só fica disponível com as fotos necessárias e o consentimento.

| Perfil | Opções de conteúdo no menu | Administração |
|---|---|---|
| Visitante sem login | Boletins públicos — nível 1 | Nenhuma |
| Servidor | Boletins públicos — nível 1 | Nenhuma |
| Diretor de divisão | Boletins públicos e Investigações — níveis 1 e 2 | Nenhuma |
| Ministro | Boletins públicos, Investigações e Gabinete — níveis 1, 2 e 3 | Usuários e rostos; Histórico de acesso |

Cada área possui uma página própria, com busca por título/região. As opções do menu refletem as permissões, e o servidor também verifica a autorização em todas as consultas; mudar a URL não libera conteúdo restrito.

O nível 1 foi interpretado como público, e os níveis superiores são cumulativos. O ministro também consulta investigações. O enunciado não define quem administra contas; este projeto atribui essa tarefa ao único ministro.

Outras funções: desativar/reativar/excluir participantes, confirmar exclusões em uma janela própria, registrar acessos, validar fotos, limitar tentativas e revogar sessões. A lista de participantes mostra se senha e rosto já estão vinculados.

A base é fictícia e não se conecta ao Ministério do Meio Ambiente. Sua finalidade é demonstrar o controle de acesso a informações de propriedades rurais e investigações ambientais por um serviço web.

## Como o reconhecimento funciona

1. Após validar usuário e senha, o servidor libera uma etapa facial temporária vinculada àquela conta. O navegador envia uma foto para comparação.
2. O Pillow valida o arquivo e corrige a orientação EXIF; imagens grandes são reduzidas para processamento.
3. O **YuNet** localiza a face e seus pontos de referência. A imagem precisa conter exatamente um rosto adequado.
4. O **SFace** alinha o rosto e produz um vetor de 128 valores. O vetor é normalizado.
5. A comparação usa similaridade de cosseno. O maior resultado entre as três amostras representa o cadastro.
6. O rosto aceito precisa pertencer ao usuário que informou a senha. A sessão só é criada após ambas as confirmações, sem ambiguidade; o perfil é recuperado no banco.

O limiar deste projeto é **0,50**, com diferença mínima de **0,08** entre os dois melhores cadastros. São parâmetros iniciais de demonstração, não uma calibração feita com a turma. A pontuação não é uma porcentagem de certeza. Os números de desempenho publicados para o modelo em outros conjuntos de dados não representam a precisão deste programa.

Para estudar outro limiar, defina `GUARDIAO_THRESHOLD` antes de iniciar. Exemplo no PowerShell:

```powershell
$env:GUARDIAO_THRESHOLD = "0.50"
.\.venv\Scripts\python.exe run.py
```

Avalie pessoas diferentes e fotos independentes antes de alterar esse valor. Um limiar menor facilita aceitar desconhecidos; um maior pode rejeitar usuários legítimos. Não reduza o limiar apenas para forçar uma foto ruim a passar.

Referências técnicas: [detecção e reconhecimento com OpenCV](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html), [modelo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), [modelo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface).

## Arquivos do projeto

| Arquivo/pasta | Responsabilidade |
|---|---|
| `run.py` | Inicialização do servidor Waitress e código de primeiro acesso |
| `biometria/__init__.py` | Rotas, cadastro, áreas e respostas da aplicação |
| `biometria/auth.py` | Senha, etapa facial, sessão, autorização e ativação de contas antigas |
| `biometria/face.py` | Validação da imagem, YuNet, SFace e comparação |
| `biometria/db.py` | Estrutura SQLite, consultas e dados demonstrativos |
| `biometria/templates/` | Páginas HTML renderizadas pelo Flask |
| `biometria/static/` | Estilos e interação com a câmera/API |
| `models/` | Modelos ONNX e respectivas licenças |
| `baixar_modelos.py` | Verificação SHA-256 e restauração dos modelos ausentes |
| `verificar.py` | Diagnóstico de dependências e carregamento dos modelos |
| `redefinir_senha.py` | Redefinição local de senha, preservando o vínculo facial |
| `ATUALIZAR.md` | Atualização de uma instalação existente sem perder cadastros |
| `tests/` | Testes de reconhecimento, autorização e fluxos HTTP |
| `docs/ROTEIRO_DE_APRESENTACAO.md` | Passos para demonstrar o trabalho |
| `docs/ARQUITETURA.md` | Estrutura, decisões e relação com o enunciado |
| `docs/VALIDACAO.md` | Resultados dos testes e limites da validação |
| `instance/` | Banco e chave local, criados na primeira execução |

O pacote não contém banco com pessoas cadastradas, fotos de participantes, chave de sessão ou código de configuração reutilizável.

## Dados, sessões e limitações

Senhas são armazenadas como **hash scrypt com salt**, usando [Werkzeug](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash). Senhas e hashes não aparecem nas respostas da API, histórico ou cookies. Não há campo de e-mail.

As fotos de cadastro/autenticação não são gravadas pelo servidor. Ele mantém no SQLite os vetores biométricos de cadastro, hashes de senha, nomes, identificadores, níveis e registros de auditoria. As prévias ficam na memória do navegador até limpar, concluir ou sair da página. Os vetores **continuam sendo dados biométricos**, não são anônimos nem hashes de senha; o SQLite desta versão não possui criptografia em repouso.

O código de ativação de cadastros antigos é emitido no terminal enquanto houver usuários ativos sem senha. Cada ativação exige usuário, código e o rosto já cadastrado; ela não autoriza redefinir uma senha existente.

O código inicial aparece somente no terminal, tem seu hash armazenado e deixa de valer após o cadastro do ministro. Reiniciar o servidor antes de concluir a configuração gera outro código. Depois do primeiro cadastro, não existe cadastro público.

A etapa intermediária de confirmação facial dura até 5 minutos e permite no máximo 5 tentativas. Ela é vinculada à conta e ao navegador, consumida uma única vez e não autoriza consulta restrita. As sessões duram no máximo 20 minutos após a confirmação de senha e rosto, com token revogável no banco. O servidor confere o perfil em cada consulta. A aplicação usa cookies HttpOnly/SameSite, token CSRF, consultas SQL parametrizadas e cabeçalhos de segurança. As requisições de senha, rosto, ativação e configuração compartilham um limite de 10 por minuto por endereço; cada login completo usa pelo menos duas dessas requisições; a janela persiste no banco. Consulte também as [considerações de segurança do Flask](https://flask.palletsprojects.com/en/stable/web-security/).

**Não há prova de vida.** Uma foto impressa, imagem em uma tela ou arquivo da pessoa pode ser aceita. O login também exige a senha, mas essa limitação da etapa facial permanece. O programa não deve ser tratado como autenticação segura de produção. A aplicação não é um controle de rede de nível industrial, não cifra a base e não foi auditada para uso governamental. Use somente participantes que autorizem o cadastro e dados ambientais fictícios.

O histórico registra falhas biométricas e consultas individuais; não é um log completo de todas as requisições HTTP nem possui proteção contra alteração por quem administra o arquivo do banco. A exclusão remove o cadastro e os vetores logicamente do banco ativo; não é garantia de apagamento forense de backups, páginas livres do SQLite ou arquivos do sistema.

## Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Os testes comuns não precisam de webcam e usam bancos temporários. Parte das regras usa vetores controlados para testar autorização sem depender da qualidade de uma foto. Os testes de arquivo inválido, formato, dimensões e ausência de rosto executam o motor real.

Dois testes adicionais precisam de imagens autorizadas de **duas pessoas diferentes**, com uma face frontal nítida em cada arquivo. Coloque-as fora da pasta do projeto com os nomes `face_a.jpg` e `face_b.png`, e execute:

```powershell
$env:GUARDIAO_TEST_FACES = "C:\FotosDeTeste"
.\.venv\Scripts\python.exe -m pytest -q
```

Esses testes incluem inferência real e cadastro/login em duas etapas via API. Eles criam variações de luminosidade para um teste de funcionamento, sem substituir uma avaliação biométrica com capturas independentes. A pasta de fotos não acompanha o pacote.

## Problemas comuns

| Situação | Como resolver |
|---|---|
| `py` ou Python 3.14 não encontrado | Instale o Python 3.14 com o Launcher ou use os comandos manuais com o caminho do seu Python. |
| Falha no download de dependências | Confira a conexão e a mensagem do `pip`; execute novamente `instalar.bat`. |
| `DLL load failed` ao importar OpenCV no Windows | Confira se o Python é 64 bits e se o Microsoft Visual C++ Redistributable x64 está instalado. |
| Modelo ausente ou corrompido | Execute `baixar_modelos.py`. Se houver divergência SHA-256, renomeie o arquivo indicado antes de baixar novamente. |
| Navegador não abre o painel | Aguarde a mensagem do servidor, mantenha o terminal aberto e use `http://localhost:5000`. |
| Porta ocupada | Inicie com `python run.py --port 5001` e abra `http://localhost:5001`. |
| Câmera bloqueada | Permita a câmera nas configurações do site no navegador e feche outros programas que a estejam usando. |
| Sem webcam | Use a seleção de arquivos JPG ou PNG. |
| Rosto não encontrado/rejeitado | Melhore a luz, aproxime a câmera, mantenha o rosto frontal e inteiro; se necessário, recadastre com fotos melhores. |
| Cadastro duplicado | Use outra pessoa ou localize o cadastro existente para reativá-lo; um rosto não deve representar vários perfis. |
| Muitas tentativas | Aguarde pelo menos 60 segundos. Reiniciar o servidor não elimina imediatamente a janela. |
| Página expirada | Recarregue a página. Se a sessão terminou, autentique novamente. |

### Esqueci a senha

O responsável pelo computador do servidor pode redefinir a senha localmente, sem e-mail:

```powershell
.\.venv\Scripts\python.exe redefinir_senha.py nome.do.usuario
```

O programa pede e confirma a nova senha sem exibi-la no terminal. O rosto vinculado é preservado, e as sessões e etapas de login pendentes são encerradas. O usuário continua precisando confirmar o rosto no próximo acesso. Esse comando pressupõe acesso administrativo ao computador e ao banco; não é uma recuperação pública de conta.

### Refazer toda a demonstração

Só quando quiser reiniciar **todos os dados**: encerre o servidor e renomeie a pasta `instance` para backup. A próxima execução cria uma base vazia. Para restaurar, pare o servidor e restaure a pasta completa, incluindo banco e chave. Não faça isso para uma simples troca de senha. Não compartilhe backups biométricos.

### Apresentação em rede local

Por padrão o servidor escuta somente no próprio computador. Se a apresentação precisar de outro computador na mesma rede, execute `python run.py --host 0.0.0.0` e acesse pelo endereço IP do servidor. A liberação no firewall é uma configuração do computador. Por HTTP em um endereço remoto, use envio de fotos; a captura de webcam no navegador exige contexto seguro (HTTPS), com exceção de localhost. Não exponha essa demonstração à internet. A configuração HTTPS/proxy não acompanha esta versão.

## Licenças e trabalho acadêmico

YuNet: licença MIT em `models/LICENSE-YuNet.txt`. SFace: Apache 2.0 em `models/LICENSE-SFace.txt`. Modelos pré-treinados e bibliotecas são dependências de terceiros, e devem ser citados. O código da aplicação possui implementação própria para seus fluxos e regras, mas foi produzido com assistência de IA: revise, compreenda e registre esse uso conforme as regras do professor. Não atribua o treinamento dos modelos ao grupo.

Esta entrega cobre **programa e instruções**, conforme solicitado. O enunciado também exige texto acadêmico, apêndice de código e fichas individuais de atividades; essas entregas deverão ser elaboradas com os dados reais do grupo. Não invente resultados de campo, horas realizadas ou participação dos integrantes.
