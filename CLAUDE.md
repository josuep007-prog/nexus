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
outros projetos de automação do Domínio — ao implementar
`integracao/dominio_rpa.py`, prefira reaproveitar os padrões que ele já usa
em vez de propor uma abordagem do zero.

## Três interfaces, um único núcleo

- **Desktop**: PyQt5 (`main.py`, `ui/`)
- **Web**: Flask (`web/app.py`, `web/templates/`, `web/static/`) — também é
  um PWA instalável no Android (manifest.json + sw.js servidos na raiz)
- Todas compartilham o mesmo banco SQLite (`data/dp_automacao.db`) e a
  mesma lógica de negócio. **Nunca duplique lógica de negócio numa interface
  específica** — ela sempre mora em `core/`, `modules/`, `regras/` ou
  `database/`, e as interfaces só chamam essas funções.

## Autenticação e contas

- Duas experiências, com login obrigatório (web/PWA **e** desktop PyQt5):
  - **funcionário**: pessoal do escritório, acesso total (todas as
    solicitações, fila de validações e alertas).
  - **cliente**: empresa cliente, só cria e vê as **próprias** solicitações
    (filtradas por `cliente_cnpj`); não vê validações nem alertas.
- Toda a autenticação mora em `core/usuario.py` (`Usuario.autenticar/criar`,
  hash via werkzeug) — **web e desktop chamam a mesma função**, nunca
  reimplementam. Sessão web é `flask.session` simples (sem flask-login).
- Não há autocadastro: contas são criadas pelo escritório com
  `python scripts/criar_usuario.py`.
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
integracao/                  stubs propositais (Domínio via PyAutoGUI, Onvio, eSocial)
scripts/criar_usuario.py     CLI p/ o escritório criar contas (funcionario/cliente) — único jeito de cadastrar
utils/                       file_manager.py (organização de pastas), logger.py
web/                         app.py (rotas Flask) + templates/ + static/ (style.css, app.js, PWA)
ui/                          main_window.py + dialogo_login.py + telas PyQt5 + estilo.qss
```

### Processamento no Domínio: automático (worker) x manual (analista)

Ao aprovar no ponto em que o trabalho no Domínio acontece (Bloco 1:
`aguardando_validacao_humana`; Bloco 2: `aguardando_aprovacao_1`), o analista
escolhe **Aprovar e automatizar** ou **Aprovar e atender manual** — a escolha
grava `modo_processamento` e leva a solicitação para `na_fila_automacao` ou
`em_atendimento_manual` (status genéricos em core/workflow.py).

Os dois caminhos convergem para a MESMA etapa de entrega na página
`/processamento` (funcionário): revisar → anexar o resultado → "Concluir e
entregar ao cliente" (`concluir_atendimento_manual` grava `resumo_entrega`,
salva os anexos com `origem='escritorio'` e finaliza em `concluida`).

- **Automático**: `scripts/worker_dominio.py` roda 24h **no PC-host** (a máquina
  com o Domínio aberto), pega a fila e chama `modules/fila_processamento.py::
  processar_automatico` (aciona o RPA de integracao/dominio_rpa.py). Se der
  certo, a solicitação vai para `aguardando_entrega` (o escritório revisa e
  entrega). Se o RPA falhar, registra o erro e joga para
  `em_atendimento_manual` — nunca dá como concluído sozinho.
- **Manual**: o analista faz na mão no Domínio e usa a seção "Em atendimento
  manual" da mesma página para entregar.

Anexos têm coluna `origem`: `cliente` (o que o cliente enviou) vs `escritorio`
(o resultado entregue). No detalhe, o cliente vê as duas seções separadas
("Documentos que você enviou" x "✓ Entregue pelo escritório" + resumo).

Status genéricos do processamento (core/workflow.py): `na_fila_automacao`,
`aguardando_entrega`, `em_atendimento_manual`.

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
- Extração de documentos (`modules/bloco2/extracao.py`) hoje é regex básico
  (CPF, PIS, datas soltas) — qualquer melhoria de layout específico precisa
  de documentos reais de exemplo do usuário, não invente formato.

## Como testar

```bash
pip install -r requirements.txt --break-system-packages
python web/app.py          # abre em http://localhost:5000 (dev)
python main.py             # versão desktop
pytest tests/              # testes de workflow, regras CLT, tipos e prazos
python scripts/rodar_producao.py   # produção (waitress) — defina SECRET_KEY
```

As três versões usam o mesmo `data/dp_automacao.db`. Pra testar do zero,
apague a pasta `data/` e `logs/`. Como há login, crie ao menos uma conta:
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
- ✅ Módulo de admissão (múltiplos anexos + extração básica por regex + validação CLT completa)
- ✅ Catálogo de solicitações na web com busca em tempo real (tolerante a acento/ordem), agrupado por categoria
- ✅ PWA mobile (Android) instalável
- ✅ Login com dois tipos de conta (funcionário/cliente) na web e no desktop; cliente vê só o próprio CNPJ
- ✅ Tema claro/escuro (segue o sistema, com toggle salvo) em todas as páginas web
- ✅ Reprovação devolve a solicitação ao cliente para editar/reenviar ou excluir
- ✅ Painel de solicitações ordena: não finalizadas → concluídas não vistas pelo cliente (selo "nova entrega") → concluídas já vistas; flag `visto_pelo_cliente` marcada quando o cliente dono abre o detalhe
- ✅ Home do painel é um gráfico de rosca (donut) por situação; a lista aparece ao clicar numa fatia/legenda
- ✅ Página `/acompanhamento` (só cliente): grupos por prioridade — devolvidas p/ correção → novas entregas → em andamento → concluídas
- ✅ Na aprovação, analista escolhe automatizar (fila do worker no PC-host) ou atender manual; página `/processamento` + `scripts/worker_dominio.py`
- ✅ `integracao/dominio_rpa.py::preencher_admissao()` portado do projeto DominioAutoFill (TAB + digitação); ordem dos campos a conferir na tela real
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
- ✅ Design: sidebar com ícones SVG e gradiente, stepper de fluxo no detalhe, avatar+papel no rodapé, cards com filete colorido, login com fundo decorado
- ⬜ Integração real com Domínio (login/telas restantes), Onvio, eSocial (stubs)
- ⬜ Extração de layout específico de documentos (além de CPF/PIS/datas)
- ⬜ Rotinas secundárias (feriados, monitor de CCT via MTE, consignado) — ainda stub

## Próximos passos sugeridos (nessa ordem, segundo o usuário)

1. Plugar `integracao/dominio_rpa.py::preencher_admissao()` com a automação
   PyAutoGUI que o usuário já tem em outro projeto próprio.
2. Refinar `modules/bloco2/extracao.py` com layouts reais de documentos de
   admissão (nome, cargo, salário, dados bancários).
3. `integracao/onvio_api.py` — portar os scripts Batch/cURL que o usuário já tem.
4. Rotinas secundárias (feriados, monitor de CCT, consignado).

## Preferências de comunicação do usuário

- Direto e objetivo, sem rodeios nem reescritas não solicitadas.
- Antes de implementar algo com escopo grande/ambíguo, prefira confirmar a
  profundidade desejada (ex: "só recebimento" vs "recebimento + validação
  completa") em vez de assumir o máximo de uma vez.
