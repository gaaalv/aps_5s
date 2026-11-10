# Atualizar para o Guardião 2 sem perder os rostos

Se você já cadastrou participantes na primeira versão, siga esta sequência.

1. **Encerre o servidor antigo** com Ctrl+C. Não mantenha as duas versões usando o mesmo banco.
2. Na pasta antiga `guardiao`, faça uma cópia de segurança da pasta **`instance` inteira**. Ela contém o banco, a chave e, quando presentes, os arquivos auxiliares do SQLite. Essa cópia fica somente com você.
3. Extraia o novo ZIP em **outra pasta**.
4. Copie a pasta `instance` da instalação antiga para dentro da nova pasta `guardiao`, ao lado de `run.py`. Faça isso antes de iniciar a nova versão. Não é necessário copiar `.venv`.
5. Execute `instalar.bat` na nova pasta e, depois, `iniciar.bat`.
6. A migração adiciona o campo de senha e encerra as sessões antigas. **Nomes, usuários, rostos, níveis, documentos e histórico são preservados.** Não existe senha padrão.
7. Enquanto houver cadastros ativos sem senha, o terminal mostra um **código de ativação**. No login, clique em **Ativar minha conta existente**.
8. Cada participante informa seu usuário atual, o código de ativação e a nova senha. Depois envia uma foto para confirmar o rosto que já estava cadastrado.
9. Após a ativação, entre normalmente: **usuário e senha → confirmação facial**.

O código pode ativar os cadastros antigos restantes, mas cada conta exige o respectivo rosto. Ele não permite alterar senhas que já foram definidas. Reiniciar o servidor gera outro código enquanto houver contas a ativar. Quando todos os cadastros ativos tiverem senha, o código deixa de ser emitido.

Cadastros inativos permanecem inativos. Se o ministro reativar uma conta antiga ainda sem senha, reinicie o servidor para emitir um código de ativação, ou use o comando local de redefinição de senha descrito no README.

**Se o programa pedir para criar um ministro do zero apesar de você já ter cadastros**, pare o servidor e confira se copiou `instance` para a pasta correta. Não cadastre uma segunda base por engano.

Depois de conferir a nova versão, use apenas a nova pasta. Para retornar à versão anterior, utilize a cópia de segurança feita antes da migração; não aponte a versão antiga para o banco já atualizado.

Para uma instalação nova, ignore a migração e siga o início do README.
