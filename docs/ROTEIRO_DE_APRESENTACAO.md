# Roteiro para demonstrar o Guardião

## Preparação antes da aula

1. Instale e execute o programa no computador que será usado.
2. Confirme o funcionamento da webcam e as permissões do navegador.
3. Separe três participantes diferentes, que autorizem o cadastro: ministro, diretor e servidor.
4. Cadastre o ministro pelo código inicial, com usuário, senha e três fotos. Entre com senha e rosto e cadastre o diretor e o servidor.
5. Faça testes com fotos novas, sem reaproveitar as fotos de cadastro. Confirme reconhecimento com a iluminação da sala.
6. Tenha fotos autorizadas como alternativa se a webcam não funcionar; explique que o sistema admite arquivos e não tem prova de vida.

## Sequência sugerida

| Etapa | Ação | Resultado esperado |
|---|---|---|
| 1 | Abra o sistema e clique em Consultar boletins públicos | Login como tela inicial; três documentos públicos disponíveis pelo link |
| 2 | Tente abrir `/api/records/6` sem sessão | HTTP 403, sem conteúdo estratégico |
| 3 | Entre com usuário/senha do servidor e confirme seu rosto | Menu com Minha área e Boletins públicos |
| 4 | Saia; entre com usuário/senha do diretor e confirme seu rosto | O menu ganha Investigações; níveis 1 e 2 em páginas próprias |
| 5 | Como diretor, tente `/api/records/6` | HTTP 403 |
| 6 | Saia; entre com usuário/senha do ministro e confirme seu rosto | O menu ganha Gabinete, Usuários e rostos e Histórico |
| 7 | Valide a senha de um usuário e use o rosto de outro | Identidade negada; a senha sozinha não autoriza acesso |
| 8 | Envie uma imagem sem rosto ou com dois rostos | Erro específico de validação |
| 9 | Autentique o ministro e abra o histórico | Eventos de sucesso, falha e bloqueio |
| 10 | Desative o diretor e tente autenticar esse participante | Acesso negado; cadastros inativos não participam da identificação |
| 11 | Reative o diretor | Novo login com senha e rosto volta a ser possível |

A auditoria usa horário UTC no banco; a tela converte para o horário local do navegador. A base inicial tem IDs de 1 a 6. Cada apresentação pode gerar novos eventos de auditoria.

## Explicações técnicas para a apresentação

- Mostrar a distinção entre detectar um rosto, identificar uma pessoa e autorizar um documento.
- Apontar `face.py` para o processamento, `auth.py` para senha/rosto/autorização e `__init__.py` para as áreas e os cadastros.
- Demonstrar o cadastro em duas etapas, com o resumo da conta à qual o rosto será vinculado.
- Mostrar que o menu muda conforme o perfil, enquanto a API mantém o bloqueio mesmo por acesso direto.
- Mostrar que `records` é filtrada pelo nível antes de enviar a resposta ao navegador.
- Explicar por que a pontuação de similaridade não significa “porcentagem de certeza”.
- Explicar que as fotos não são persistidas, mas os vetores continuam sendo biometria.
- Informar que os modelos são pré-treinados de terceiros, com fontes e licenças incluídas.
- Reconhecer que aceitar fotos permite ataques por reapresentação: não existe prova de vida nesta entrega.

## Avaliação do grupo

Para gerar resultados próprios, registrem tentativas legítimas e tentativas de impostores com capturas independentes, autorização dos participantes e condições anotadas. Separem erros de detecção de falsas aceitações e falsas rejeições. Não convertam os testes automatizados deste pacote em uma alegação de precisão biométrica; eles verificam funcionamento e regras.
