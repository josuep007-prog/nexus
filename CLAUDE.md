# Automação DP — Contexto do projeto

Este arquivo é lido automaticamente pelo Claude Code no início de cada sessão.
Mantenha atualizado conforme o projeto evoluir (principalmente a seção
"Status atual" e "Próximos passos").

## O que é

Sistema de automação para o Departamento Pessoal de um escritório de
contabilidade brasileiro, construído a partir de um "Mapeamento de
Processos - DP". Cobre recebimento de solicitações de clientes (férias,
admissões, atestados, CAT, licenças etc.), triagem por regras CLT/CCT,
validação humana obrigatória, e (no futuro) processamento automático no
sistema Domínio e distribuição de documentos via Onvio/e-mail.

O usuário (Josué) trabalha no Departamento Pessoal de um escritório de
contabilidade e já tem experiência própria com PyAutoGUI + Tesseract OCR em
outros projetos de automação do Domínio.

**⚠️ Decisão de arquitetura (ver `docs/onvio_referencia.md`):** investigação na
Central de Soluções encontrou que **não existe API pública do Onvio para
inserir solicitações de DP** (férias, rescisão, admissão, afastamento, geral —
só há API para documentos fiscais de ERP). Isso muda o plano original:
- O Onvio→Domínio **já preenche a tela do Domínio sozinho** ao clicar
  **[Executar no sistema]** — então automatizar a tela por fora (RPA de
  PyAutoGUI) é **redundante**. `integracao/dominio_rpa.py` foi **reescrito do
  zero** (sem reaproveitar código de outros projetos do usuário) como um motor
  de **ROTEIRO por passos explícitos** (campo/texto/tecla/pausa, transcritos
  da tela real) — os `ROTEIRO_*` nascem vazios e caem para atendimento manual
  até serem preenchidos com a tela real.
- Se um dia o nexus for criar a solicitação no Onvio sozinho, o único caminho
  automatizável é a **UI web do Onvio via Playwright** (não PyAutoGUI) — não
  implementado ainda.
- O valor imediato do nexus, sem depender de nada externo: **extração** (menos
  digitação), **triagem/validação CLT obrigatória**, e **campos alinhados aos
  do Onvio** (para o repasse — manual hoje, automatizável depois — encaixar
  direto). Ver `docs/onvio_referencia.md` e `docs/dominio_referencia.md` para
  os detalhes capturados da Central de Soluções.

## Interface: só web

- **Web**: Flask (`web/app.py`, `web/templates/`, `web/static/`) — é a **única**
  interface do sistema: cliente cria solicitações, escritório valida, repassa ao
  Onvio e entrega. Também é um PWA instalável no Android (manifest.json + sw.js
  servidos na raiz). Roda em qualquer lugar, inclusive na nuvem.
- **Desktop (PyQt5) foi APOSENTADO.** Existia como "Painel do Robô" para operar
  a automação de tela do Domínio na máquina-host. Com a decisão de arquitetura
  acima (o Onvio já pré-preenche o Domínio), o robô perdeu a função e o painel
  junto — `main.py` e `ui/` foram removidos. Não recrie uma interface desktop
  sem um propósito que a web não atenda.
- **Nunca duplique lógica de negócio na interface** — ela mora em `core/`,
  `modules/`, `regras/` ou `database/`, e a web só chama essas funções.
- **Dormentes** (mantidos como referência, ninguém chama): `integracao/
  dominio_rpa.py` (motor de roteiro, `ROTEIRO_*` vazios) e
  `scripts/worker_dominio.py` (worker da fila de automação, que não é mais
  alimentada). Só voltam a fazer sentido se os roteiros forem transcritos.

## Autenticação e contas

- **Quatro papéis**, um deles cliente e três formando uma ESCADA de acesso no
  escritório (cada nível faz tudo do de baixo). Constantes e níveis em
  `core/usuario.py` (`TIPO_CLIENTE/FUNCIONARIO/GESTOR/ADMIN`, `NIVEIS`,
  `NIVEL_FUNCIONARIO=1/GESTOR=2/ADMIN=3`):
  - **cliente** (nível 0): empresa cliente, só cria/vê as **próprias**
    solicitações (por `cliente_cnpj`); não vê validações/alertas. (não é
    parte da escada de acesso do escritório.)
  - **funcionário** (1): operacional — recebe, valida, processa, entrega,
    alertas e obrigações.
  - **gestor** (2): funcionário **+ relatórios/produtividade + gestão de
    contas de CLIENTE** (onboarding, reset de senha, empresas extras).
  - **administrador** (3): tudo **+ gestão de contas do ESCRITÓRIO**
    (criar/desativar/redefinir funcionário/gestor/admin) e configurações.
- Propriedades em `Usuario`: `nivel`, `papel` (rótulo), `eh_cliente`,
  `eh_funcionario` (= é da equipe, QUALQUER nível — usado nos gates gerais
  "escritório x cliente"), `eh_gestor` (nível ≥ 2), `eh_admin`, e
  `pode_gerir(tipo_alvo)` (regra central: gestor gere cliente; só admin mexe
  em conta do escritório — impede um gestor se promover).
- **Gate de acesso** (`web/app.py::exigir_login`): `ROTAS_NIVEL_MINIMO` mapeia
  cada rota interna ao nível mínimo; quem não alcança recebe 404. As rotas de
  gestão de contas ainda checam o ALVO por ação (`_gerir_conta_ou_abortar`,
  `criar_usuario_web`) — defesa no servidor, não só na UI. A página `/usuarios`
  recebe `pode_gerir_equipe = eh_admin` (mostra/oculta criação de contas do
  escritório e as ações sobre elas).
- **Bootstrap** (`database/db_manager.py::inicializar_banco`): garante que
  sempre exista ao menos um `administrador` — se não houver, promove a conta
  de login `administrador` (ou o funcionário mais antigo). Evita ficar sem
  ninguém que gerencie a equipe ao migrar bancos antigos (2 papéis → 4).
- Toda a autenticação mora em `core/usuario.py` (`Usuario.autenticar/criar`,
  hash via werkzeug) — usada pela web; a lógica de senha nunca é reimplementada.
  Sessão web é `flask.session` simples (sem flask-login).
- Contas são criadas por gestor/admin na web (`/usuarios`) ou via
  `python scripts/criar_usuario.py` (útil pro 1º admin). Não há autocadastro.
- Nos formulários de criação, para conta **cliente** o servidor ignora o
  `cliente_cnpj`/`cliente_nome` enviados e usa os da conta logada (impede
  abrir solicitação em nome de outra empresa). Detalhe e download de anexo
  checam posse (404 se não for do cliente).

## Tema claro/escuro

- Todo o CSS usa tokens (variáveis) definidos em `:root` (claro) e
  `[data-tema="escuro"]` — o tema escuro só redefine tokens, sem duplicar
  regras. **Ao adicionar CSS, use os tokens** (`--surface`, `--text`,
  `--border`, `--accent-*`, `--sidebar-*`), nunca cores fixas, senão o
  escuro quebra.
- O tema é aplicado no `<html>` por um script no `<head>` (segue o sistema
  na 1ª visita, guarda a escolha; sem flash). Toggle "Tema" na navegação
  (base.html) e botão flutuante no login. `sw.js` tem `CACHE_NAME` versionado
  — **incremente ao mudar CSS/JS** pra o PWA pegar os assets novos.

## Arquitetura

```
config.py                    caminhos, constantes, TIPOS_BLOCO_1 / TIPOS_BLOCO_2
database/db_manager.py       todo o SQL mora aqui (solicitacoes, anexos, validacoes, log_erros, alertas, usuarios)
core/workflow.py             máquina de estados (StatusBloco1, StatusBloco2, REPROVADA) — transições válidas
core/solicitacao.py          classe Solicitacao; .avancar() valida a transição; .pertence_a() checa posse
core/usuario.py              autenticação compartilhada (funcionario/cliente) — usada por web e desktop
core/tipos_solicitacao.py    registro central: cada tipo tem título, campos de formulário e validação
regras/regras_clt.py         validar_*(dados) -> (ok, erros, extra) — uma função por tipo
regras/regras_cct.py         regras por convenção coletiva (ainda simples, a evoluir)
modules/bloco1/              recebimento.py (férias/rescisão, fluxo dedicado) + generico.py (demais tipos)
modules/bloco2/              admissao.py e atestados.py (fluxos dedicados) + generico.py + extracao.py (OCR/regex)
modules/dossie.py            Dossiê do Empregado + conferência CLT automática (Cenário A/B)
integracao/                  stubs propositais (Domínio via roteiro de passos, Onvio, eSocial)
docs/                         onvio_referencia.md e dominio_referencia.md — capturas da Central de Soluções
scripts/criar_usuario.py     CLI p/ o escritório criar contas (funcionario/cliente) — único jeito de cadastrar
utils/                       file_manager.py (organização de pastas), logger.py
web/                         app.py (rotas Flask) + templates/ + static/ (style.css, app.js, PWA)
(o desktop PyQt5 foi aposentado — ver "Interface: só web")
```

### Depois da aprovação: repasse ao Onvio x atendimento direto

Ao aprovar (Bloco 1: `aguardando_validacao_humana`; Bloco 2:
`aguardando_aprovacao_1`), o caminho depende de o tipo ter equivalente no Onvio
(`onvio_solicitacao` no schema — `web/app.py::_vai_para_onvio`):

- **Com equivalente** → botão "✓ Aprovar e repassar ao Onvio" → status
  `aguardando_repasse_onvio`. O analista abre a tela de repasse
  (`/solicitacoes/<id>/onvio`, template `repasse_onvio.html`), que mostra o
  **de-para pronto**: cada campo já com o NOME DO CAMPO NO ONVIO e o valor,
  com botão de copiar (e "copiar todos"). Ele lança no Onvio, informa o nº
  (opcional) e confirma → etapa `repasse_onvio` no histórico e status
  `aguardando_entrega`. Daí o Onvio leva ao Domínio, que abre a tela já
  pré-preenchida em [Executar no sistema].
- **Sem equivalente** (CND, declaração, PPP, folha sem variáveis...) → botão
  "✓ Aprovar e atender" → `em_atendimento_manual`: o escritório resolve direto.

Os dois convergem na MESMA entrega em `/processamento`: revisar → anexar o
resultado → "Concluir e entregar ao cliente" (`concluir_atendimento_manual`
grava `resumo_entrega`, salva anexos com `origem='escritorio'`, finaliza em
`concluida`).

O de-para vem de `core/tipos_solicitacao.py::campos_para_onvio`, que lê duas
fontes: a chave `"onvio"` de cada campo do formulário e, para tipos com tela
dedicada (admissão, atestado) ou valores determinados pelo próprio tipo
(ex.: "Tipo do Afastamento"), a lista `"onvio_campos"` (aceita `valor_fixo`).

Anexos têm coluna `origem`: `cliente` (o que o cliente enviou) vs `escritorio`
(o resultado entregue). No detalhe, o cliente vê as duas seções separadas
("Documentos que você enviou" x "✓ Entregue pelo escritório" + resumo).

Status genéricos (core/workflow.py): `aguardando_repasse_onvio`,
`aguardando_entrega`, `em_atendimento_manual` — e `na_fila_automacao`, que é
**legado** (nada mais enfileira nele; a página só o exibe se sobrar algum).

**Auditoria por usuário**: cada etapa é registrada na tabela `validacoes` com
`aprovado_por = "{nome_exibicao} ({login})"` do usuário LOGADO (não há mais
campo livre "Seu nome"). O helper é `web/app.py::_ator(g.usuario)` /
`_registrar_etapa`. Etapas logadas: `recebimento` e `reenvio` (cliente),
`triagem`/`aprovacao_*` (funcionário), `processamento_manual` (funcionário) e
`processamento_automatico` ("Automação (worker)"). O detalhe mostra tudo em
"Histórico — quem fez o quê". PyAutoGUI controla a tela da
máquina onde roda, então a automação só funciona no PC-host com o Domínio
aberto/logado/desbloqueado — a web pode estar em qualquer lugar.

### Fluxo de reprovação (solicitação volta ao cliente)

Quando o analista reprova na fila de validação, a solicitação vai para o
status genérico `reprovada` (core/workflow.py), grava o `motivo_reprovacao`
e sai da fila. O cliente dono vê um banner no detalhe e pode **Editar e
reenviar** (volta pra validação — só tipos de formulário do Bloco 1, via
`modules/bloco1/generico.py::atualizar_e_reenviar`) ou **Excluir**
(`db_manager.excluir_solicitacao`, apaga anexos do disco também). As rotas
`/solicitacoes/<id>/editar` e `/excluir` checam posse + status `reprovada`.

### O "pulo do gato": formulário genérico

`core/tipos_solicitacao.py` guarda, para cada um dos 21 tipos de
solicitação, um dicionário com `titulo`, `campos` (lista de campos do
formulário) e `validar` (referência à função em `regras_clt.py`). O template
`web/templates/solicitacao_generica.html` lê esse schema e monta o
formulário sozinho — **não crie uma tela HTML nova para cada tipo**.

Para adicionar um tipo de solicitação novo:
1. Escreva `validar_novo_tipo(dados: dict) -> (ok: bool, erros: list, extra: dict)` em `regras/regras_clt.py`.
2. Cadastre em `core/tipos_solicitacao.py` (`REGISTRO_BLOCO1` ou `REGISTRO_BLOCO2`).
3. Adicione o nome em `config.py` (`TIPOS_BLOCO_1`/`TIPOS_BLOCO_2`).

O formulário web e a validação aparecem automaticamente — nenhum outro
arquivo precisa mudar.

Tipos que mapeiam para uma solicitação do Onvio Portal do Cliente levam
`"onvio_solicitacao"` no schema, e cada campo mapeável leva a chave
`"onvio"` com o nome do campo equivalente lá (ver `docs/onvio_referencia.md`
§2). Três automatismos evitam repetição e digitação à toa:
- **"Assunto"** é derivado (`assunto_para_onvio`: título do tipo + empregado) —
  o Onvio pede, mas obrigar o cliente a escrever seria digitação inútil;
- **"Expectativa de conclusão"** é anexado a todos os tipos alinhados por um
  laço no fim do registro (`_CAMPO_EXPECTATIVA`), em vez de repetir 12 vezes;
- vários campos do nexus que caem no MESMO campo do Onvio (que tem menos
  campos que nós) são **unidos numa linha só**, cada um rotulado — ex.:
  `Observações = Idade: 17 · Pessoa com deficiência?: nao`.

O formulário genérico **esconde o campo "Funcionário"** quando o schema já
pede `empregado_nome` (senão perguntaria a mesma pessoa duas vezes); nesse
caso a rota usa `empregado_nome` para preencher a coluna `funcionario_nome`,
que alimenta listagens e dossiê. Hoje alinhados: `ferias` ("Cálculo de Férias"), `rescisao` ("Cálculo de
Rescisão"), `outros` ("Solicitação Geral"). Campos sem `"onvio"` (ex.:
`saldo_dias_direito` — que nem existe mais como campo digitado) são só do
nexus, para a conferência CLT antes da validação humana.

### Dossiê do Empregado + conferência CLT automática

`modules/dossie.py` mantém um espelho local de cada empregado (tabelas
`empregados` + `empregado_historico`, em `database/db_manager.py`), alimentado
por: massa de teste (`scripts/seed_empregados.py`), solicitações processadas
(`registrar_solicitacao_processada`, chamado por `fila_processamento.py` ao
concluir) e, no futuro, sincronização do Onvio (`integracao/onvio_sync.py` —
stub, sem API real disponível).

Ao criar/reeenviar uma solicitação com conferência automática definida (hoje só
`ferias`, em `modules.dossie._CONFERENCIAS`), `modules/bloco1/generico.py`
cruza os dados com o dossiê e decide entre dois cenários — **nunca bloqueia**:
- **Cenário A** (empregado achado + saldo conhecido no cadastro): o nexus
  valida a conformidade CLT sozinho (reaproveita `regras_clt.validar_ferias`).
  A fila de validação mostra o selo **✓ conferido**.
- **Cenário B** (empregado não encontrado ou sem saldo cadastrado): não
  bloqueia — segue para validação humana com o selo **🔎 conferência manual**
  e uma caixa de alerta listando o que o analista precisa checar na mão.

Os dados da conferência (`conferencia_cenario`, `conferencia_alerta`,
`conferencia_pontos`, `conferencia_erros`) ficam em `sol.dados`, prefixados
com `conferencia_` — o template esconde essas chaves do dump cru de dados.

Para adicionar conferência automática a outro tipo: escreva uma função
`conferir_<tipo>(dados, cliente_cnpj)` em `modules/dossie.py` seguindo o
padrão de `conferir_ferias`, e registre em `_CONFERENCIAS`.

## Convenções do projeto

- **Português** em nomes de variáveis, funções, comentários e mensagens de
  erro — é assim que o usuário lê e entende o código.
- Módulos em `integracao/` são **stubs propositais**: levantam
  `NotImplementedError` e quem chama já trata isso sem quebrar (registra
  erro, mantém o status anterior). Não implemente essas integrações de
  verdade sem antes pedir ao usuário credenciais/exemplos reais (layout de
  tela do Domínio, token da API do Onvio etc.) — implementar um stub de
  integração "no chute" pode gerar código incompatível com o ambiente real dele.
- **Toda solicitação passa por validação humana obrigatória** antes de
  qualquer processamento (`core/workflow.py` não permite pular essa etapa).
- Extração de documentos (`modules/bloco2/extracao.py`): busca **por RÓTULO**
  ("Nome: X", "Cargo: Y"), com sinônimos por campo em `_ROTULOS` — padrão
  universal de ficha de registro/admissão, que funciona em qualquer layout.
  **Nunca decore a posição de um campo num modelo específico** (quebra no
  primeiro documento diferente) e não invente formato: para calibrar com
  documento real use `python scripts/testar_extracao.py <arquivo>`, veja o que
  faltou e acrescente o rótulo que aquele documento usa.
  Três regras que o módulo já garante e devem ser mantidas:
  1. valor passa por normalização (data→ISO, R$→decimal) e, quando há regra
     (CPF/PIS), por dígito verificador — **dado ruim vira pendência, não
     entra como se fosse bom**;
  2. o retorno traz `_diagnostico` (achados/faltando/recusados/falha_leitura),
     consumido por `recebimento_anexo.extrair_e_validar` para virar pendência
     explícita — inclusive "PDF sem camada de texto" (escaneado), que antes
     falhava em silêncio;
  3. `_diagnostico` é removido antes de virar dado da solicitação.

## Como testar

```bash
pip install -r requirements.txt --break-system-packages
python web/app.py          # web/PWA — abre em http://localhost:5000 (dev)
pytest tests/              # testes de workflow, regras CLT, tipos, prazos e repasse
python scripts/rodar_producao.py   # produção (waitress) — defina SECRET_KEY
```

**Demonstrar na nuvem** (link fixo, qualquer computador — ver [DEPLOY.md](DEPLOY.md)):
publicar no Render via `render.yaml` (Blueprint, publica a branch `main`). O
deploy usa `requirements-web.txt` (enxuto: sem PyQt5/pyautogui/OCR — imports
pesados são lazy em `modules/bloco2/extracao.py` e `integracao/dominio_rpa.py`,
com guarda por `Exception` — não só `ImportError` — porque pyautogui quebra ao
importar em ambiente sem DISPLAY; o app sobe sem eles e a extração/RPA
degradam graciosamente). `rodar_producao.py` lê a porta de `$PORT`; com
`DEMO_SEED=1` roda `scripts/seed_demo.py` no boot (mesmas contas do PC —
`administrador/funcionario/gestor/cliente/...`, senha `123` — só se o banco
estiver vazio; `scripts/seed_empregados.py` semeia a massa de teste do Dossiê
junto). SQLite é efêmero no plano free (reinicia a cada deploy) — ok pra demo.

O banco fica em `data/dp_automacao.db`. Pra testar do zero, apague as pastas
`data/` e `logs/`. Como a web tem login, crie ao menos uma conta:
`python scripts/criar_usuario.py` (ex: um `funcionario` e um `cliente`) —
ou, logado como funcionário, use a página `/usuarios`.

Notificações são opcionais e desligam sozinhas sem configuração:
- E-mail: defina `SMTP_HOST/SMTP_PORTA/SMTP_USUARIO/SMTP_SENHA/EMAIL_ESCRITORIO` (env).
- Push PWA: `pip install pywebpush`, gere chaves com `python scripts/gerar_chaves_push.py`
  e defina `VAPID_CHAVE_PRIVADA/VAPID_CHAVE_PUBLICA` (env).

Todo formulário POST precisa do token CSRF — nos templates que estendem
`base.html` o `app.js` injeta o campo `_csrf` sozinho (meta `csrf`); páginas
standalone (login) incluem o campo na mão; chamadas fetch mandam o header
`X-CSRF`. Novo form em página nova = nada a fazer, só estender base.html.

## Status atual

- ✅ Banco de dados, workflow, 25 tipos de solicitação com formulário + regra de validação (inclui "Outros" livre e, na folha, adiantamento e RPA)
- ✅ Módulo de atestados (só recebimento de PDF/PNG)
- ✅ Módulo de admissão (múltiplos anexos + extração por rótulo + validação CLT completa)
- ✅ **Extração de documentos por rótulo** (`extracao.py`): acha os 14 campos mínimos da admissão numa ficha de registro, normaliza (data→ISO, R$→decimal), valida dígito de CPF/PIS (dado ruim vira pendência) e reporta o motivo quando não lê (PDF escaneado, OCR ausente). Calibrar com `scripts/testar_extracao.py`
- ✅ Catálogo de solicitações na web com busca em tempo real (tolerante a acento/ordem), agrupado por categoria
- ✅ PWA mobile (Android) instalável
- ✅ Login com dois tipos de conta (funcionário/cliente) na web; cliente vê só o próprio CNPJ
- ✅ Desktop (PyQt5) **aposentado**: o sistema é só web. `main.py` e `ui/` removidos junto com a automação de tela do Domínio (ver Decisão de arquitetura)
- ✅ Tema claro/escuro (segue o sistema, com toggle salvo) em todas as páginas web
- ✅ Reprovação devolve a solicitação ao cliente para editar/reenviar ou excluir
- ✅ Painel de solicitações ordena: não finalizadas → concluídas não vistas pelo cliente (selo "nova entrega") → concluídas já vistas; flag `visto_pelo_cliente` marcada quando o cliente dono abre o detalhe
- ✅ Home do painel é um gráfico de rosca (donut) por situação; a lista aparece ao clicar numa fatia/legenda
- ✅ Página `/acompanhamento` (só cliente): grupos por prioridade — devolvidas p/ correção → novas entregas → em andamento → concluídas
- ✅ Após aprovar: **repasse ao Onvio** (tela `/solicitacoes/<id>/onvio` com o de-para pronto e botão de copiar) para tipos com equivalente lá; atendimento direto para os demais. Página `/processamento` reorganizada em: a repassar → revisar/entregar → atendimento direto
- ✅ `integracao/dominio_rpa.py` reescrito do zero (sem código de outros projetos): motor de ROTEIRO por passos explícitos (`campo/texto/tecla/pausa`) — a navegação é explícita, não assume layout. Os `ROTEIRO_*` (admissão/férias/rescisão/alteração) nascem VAZIOS e a tela levanta `NotImplementedError` (cai pro manual) até serem transcritos da tela real do Domínio
- ✅ Segurança: CSRF em todo POST (meta + injeção via app.js; login tem campo fixo), rate-limit de login (5 erros/10min → 5min bloqueado), upload com whitelist de extensões + limite de 10 MB (config.py)
- ✅ `/conta` (todos): troca de senha, e-mail de avisos, ativar push; `/usuarios` (funcionário): criar/desativar conta, resetar senha, e-mail, empresas extras
- ✅ Multi-CNPJ por conta cliente (tabela `usuario_empresas`): filtros e posse usam `usuario.cnpjs`; formulários mostram seletor de empresa (`macros.html::escolha_empresa`)
- ✅ Notificações: e-mail via SMTP_* (env) e push PWA via chaves VAPID (env + `scripts/gerar_chaves_push.py` + pywebpush) — as duas desligam graciosamente sem config; ganchos em `utils/notificacoes.py` (nova solicitação → escritório; reprovação/entrega/comentário → cliente)
- ✅ Comentários cliente↔escritório no detalhe (tabela `comentarios`, seção "Mensagens")
- ✅ SLA por tipo (config.SLA_POR_TIPO + utils/prazos.py): selo "vence hoje/vencida" nas filas do funcionário
- ✅ `/obrigacoes` (funcionário): checklist mensal por competência (config.OBRIGACOES_MENSAIS + tabela `obrigacoes_marcadas`)
- ✅ Alertas de fim de experiência (45/90 dias) gerados ao abrir `/alertas` (`utils/prazos.py::gerar_alertas_experiencia`, idempotente)
- ✅ `/relatorios` (funcionário): filtros por período/tipo, export CSV (BOM+`;` p/ Excel), impressão (@media print) e produtividade por analista
- ✅ Backup diário do SQLite com rotação (`utils/backup.py` → `backups/`, 14 cópias) — dispara no boot da web e nas rodadas do worker
- ✅ Heartbeat do worker (tabela `sistema`) — selo online/offline em `/processamento`
- ✅ Testes: `pytest tests/` (workflow, regras CLT, registro de tipos, prazos)
- ✅ Produção: `python scripts/rodar_producao.py` (waitress) + SECRET_KEY por env
- ✅ Deploy na nuvem p/ demonstração: `render.yaml` (Blueprint do Render) + `requirements-web.txt` enxuto + `scripts/seed_demo.py` (DEMO_SEED=1) + guia em `DEPLOY.md`
- ✅ Design: sidebar com ícones SVG e gradiente, stepper de fluxo no detalhe, avatar+papel no rodapé, cards com filete colorido, login com fundo decorado
- ✅ Sidebar rolável (overflow-y) quando o menu passa da altura da tela
- ✅ Pesquisa de contas de Usuários (nome/CNPJ/empresa) e acordeões (barra-resumo) em Validações/Processamento
- ✅ Relatórios: barras proporcionais "por tipo"/"por cliente" + tabela de colunas alinhadas na produtividade por analista
- ✅ Referência de Onvio/Domínio capturada da Central de Soluções (`docs/onvio_referencia.md`, `docs/dominio_referencia.md`) — achado: **sem API pública do Onvio para solicitações de DP**; RPA de tela no Domínio é redundante (ver seção "Decisão de arquitetura" no topo)
- ✅ `integracao/dominio_rpa.py` reescrito do zero (sem código de outros projetos): motor de ROTEIRO por passos explícitos (`campo/texto/tecla/pausa`) — a navegação é explícita, não assume layout. Os `ROTEIRO_*` (admissão/férias/rescisão/alteração) nascem VAZIOS e a tela levanta `NotImplementedError` (cai pro manual) até serem transcritos da tela real do Domínio
- ✅ **12 tipos alinhados ao Onvio**: Cálculo de Férias, Cálculo de Rescisão, Solicitação Geral, Cadastro de Colaborador (admissão/estagiário/aprendiz), Afastamento de Empregado (atestado/INSS/CAT/licenças) e Lançamento de Rubricas — metadado `"onvio"` por campo + `"onvio_campos"` (com `valor_fixo`) para telas dedicadas
- ✅ Catálogo reagrupado pelo momento do contrato (entrada → férias → afastamentos → folha → mudanças → dependentes → disciplinar → rescisão → documentos), preservando a ordem declarada em `CATEGORIAS`
- ✅ Dossiê do Empregado (`modules/dossie.py`, tabelas `empregados`/`empregado_historico`) + conferência CLT automática de férias (Cenário A conferido / Cenário B alerta manual, nunca bloqueia) — selo na fila de validação
- ⬜ Integração real com Domínio (ROTEIRO_* ainda vazios), Onvio (sem API — via UI web/Playwright, não implementado), eSocial (stub)
- ⬜ Extração de layout específico de documentos (além de CPF/PIS/datas)
- ⬜ Rotinas secundárias (feriados, monitor de CCT via MTE, consignado) — ainda stub

## Próximos passos sugeridos

O sistema já está inteiro alinhado à proposta `cliente → nexus → Onvio →
Domínio` (repasse implementado, 12 tipos mapeados, desktop/RPA aposentados).
Daqui pra frente, em ordem de valor:

1. **Validar o de-para com o Onvio real.** Os nomes de campo vieram da Central
   de Soluções (`docs/onvio_referencia.md` §2), não de uma tela aberta. Ao usar
   pela primeira vez, conferir se batem e ajustar os rótulos `"onvio"` — é
   barato e evita atrito no repasse.
2. Estender a conferência automática (`modules/dossie.py`) a outros tipos além
   de férias (ex.: rescisão, usando a data de admissão do dossiê).
3. **Calibrar a extração com documentos reais** do escritório (rodar
   `scripts/testar_extracao.py` e completar `_ROTULOS` com os rótulos que
   aparecerem). O motor já funciona; falta ajustá-lo ao vocabulário real.
   Pendência conhecida: PDF escaneado (sem camada de texto) não é lido — exigiria
   pdf2image + poppler; hoje o sistema avisa em vez de falhar calado.
4. Alinhar os tipos que faltam ao Onvio, se aparecer necessidade: "Aviso Prévio
   de Férias" e "Aviso Prévio de Rescisão" não têm equivalente nosso ainda.
5. Só se fizer sentido: automação de navegador (Playwright) para criar a
   solicitação no Onvio sozinho — exige acesso real ao Onvio para desenvolver e
   checar os Termos de Uso antes.
6. Rotinas secundárias (feriados, monitor de CCT, consignado).

## Preferências de comunicação do usuário

- Direto e objetivo, sem rodeios nem reescritas não solicitadas.
- Antes de implementar algo com escopo grande/ambíguo, prefira confirmar a
  profundidade desejada (ex: "só recebimento" vs "recebimento + validação
  completa") em vez de assumir o máximo de uma vez.
