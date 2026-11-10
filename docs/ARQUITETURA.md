# Estrutura e decisões de implementação

## Fluxo

O login começa com usuário e senha. O Flask verifica o hash e cria uma etapa facial temporária, sem liberar acesso restrito. O navegador então captura ou seleciona uma imagem. O servidor obtém a biometria com OpenCV e confirma que ela pertence ao mesmo usuário. Só depois das duas provas é criada uma sessão revogável. As consultas subsequentes recuperam o nível do cadastro no banco e só retornam documentos autorizados.

O frontend nunca decide sozinho se um documento pode ser acessado. A lista é filtrada no SQL; o endpoint de detalhe revalida a autorização antes de devolver o conteúdo. Mesmo alterando botões, parâmetros ou URLs, o perfil não ganha acesso a documentos superiores.

## Banco SQLite

| Tabela | Uso |
|---|---|
| `users` | Nome, identificador único, hash scrypt da senha, nível e estado ativo |
| `face_challenges` | Etapas faciais de uso único, com conta, expiração e tentativas |
| `samples` | Três vetores faciais por cadastro; chave estrangeira com exclusão em cascata |
| `records` | Documentos demonstrativos e seus níveis |
| `sessions` | Hash do token aleatório, usuário e expiração absoluta |
| `audit` | Eventos, ator quando conhecido e detalhes operacionais |
| `attempts` | Controle persistente de tentativas por endereço |
| `settings` | Hashes dos códigos de configuração e ativação de contas antigas |

Transações de cadastro usam `BEGIN IMMEDIATE` para serializar cadastro e validação de duplicidade. Um índice parcial impede dois usuários de nível 3. Consultas parametrizadas separam parâmetros do SQL. A configuração WAL permite leituras durante a persistência de outras operações.

## Identificação, verificação e autorização

- **Detecção**: localiza uma face; não determina identidade.
- **Identificação**: compara a amostra contra todas as pessoas ativas e seleciona a melhor candidata, desde que ultrapasse o limiar e a margem.
- **Verificação**: exige que a identidade facial aceita seja a da conta cuja senha foi validada na etapa anterior. A implementação examina as demais candidatas para evitar aceitar um resultado ambíguo.
- **Autorização**: após autenticar, consulta as permissões do cadastro e aplica as regras por nível.

As três fotos de cadastro precisam ser distintas em bytes e mutuamente semelhantes. Essa verificação não comprova capturas independentes, integridade da fonte nem presença física. Um teste com alterações da mesma foto pode passar; isso não é prova de vida.

## Relação com o documento da APS

| Orientação | Implementação |
|---|---|
| Java ou Python | Servidor e reconhecimento em Python |
| Identificação e autenticação biométrica | Identificação no motor facial e verificação vinculada ao usuário/senha |
| Entrada por imagens, vídeos ou câmera | Arquivos JPG/PNG e quadros capturados de webcam; vídeo gravado não é necessário nem implementado |
| Base de informações ambientais | SQLite com registros fictícios sobre propriedades, água e investigações |
| Três níveis | Público/servidor, diretor e ministro; hierarquia cumulativa documentada |
| Tratamento de erros e funcionalidade | Validação de arquivos, falhas de face, duplicidade, limites e sessões |
| Programa apresentável | Login dedicado, confirmação facial, cadastro guiado, áreas por nível, gestão e auditoria |
| Explicação da estrutura | README, este documento e comentários no código |
| Texto acadêmico e fichas | Fora do escopo desta etapa, que foi definida como programa e instruções |

## Atualização de cadastros

A migração é aditiva: cria `password_hash` quando ausente, cria `face_challenges`, define `user_version=2` e revoga as sessões antigas somente na primeira migração. Os cadastros existentes começam sem senha e permanecem inacessíveis às áreas restritas até a ativação. A ativação exige código emitido no terminal e o rosto correspondente; o hash é gravado no mesmo usuário, preservando os vetores.

A senha usa scrypt com salt por meio do Werkzeug. A consulta pública de usuário seleciona campos explicitamente: o hash não aparece na API, no HTML ou nos cookies. Redefinições de senha, desativações e exclusões revogam sessões e etapas pendentes.

A confirmação facial não confia no usuário enviado pelo cliente: a conta vem da etapa intermediária persistida. Cada etapa dura até 5 minutos e permite até 5 tentativas, sendo consumida atomicamente após sucesso.

## Estrutura de navegação

A raiz abre o login para visitantes e Minha área para autenticados. Boletins continuam públicos. Investigações exigem nível 2 e Gabinete exige nível 3. Usuários e Histórico são exclusivos do ministro. Cada menu é montado no servidor de acordo com o perfil; os endpoints revalidam os mesmos limites.

## Componentes e disciplinas relacionadas

- Processamento de imagens: leitura, redução, detecção, alinhamento e validação visual.
- Inteligência artificial: inferência de redes pré-treinadas para detecção e representação facial.
- Álgebra linear: normalização de vetores e produto escalar para similaridade.
- Banco de dados: entidades, relacionamentos, transações e integridade.
- Redes e desenvolvimento web: cliente HTTP, servidor, formulários e respostas JSON.
- Engenharia de software: separação de responsabilidades, testes e tratamento de erros.
- Segurança: autenticação, autorização, sessões revogáveis e minimização de dados persistidos.

Estas relações são uma base para a compreensão técnica; a reflexão sobre a formação dos integrantes deve ser escrita pelo grupo a partir do trabalho efetivamente realizado.

## Escolhas e limites

A configuração privilegia execução local e demonstração em sala. Não há nuvem, treino próprio, dependência de GPU, integração real com o Ministério, prova de vida, criptografia do SQLite ou garantia de precisão para uma população. A qualidade deve ser avaliada com participantes autorizados e capturas independentes. O limiar e a margem são decisões iniciais, não resultados de validação de campo.
