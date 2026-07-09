# Automação DP — Esqueleto do Sistema

Esqueleto modular baseado no *Mapeamento de Processos - DP*. Cobre a arquitetura
inteira (Bloco 1, Bloco 2, rotinas secundárias e integrações), com o "motor"
do sistema (banco de dados, workflow, regras CLT/CCT) já funcionando, e duas
interfaces: **desktop (PyQt5)** e **web (Flask, pra testes)**.

## Como rodar

```bash
cd dp_automacao
pip install -r requirements.txt --break-system-packages   # ou sem a flag, se estiver em venv
```

### Versão desktop
```bash
python main.py
```

### Versão web
```bash
python web/app.py
```
Depois abra **http://localhost:5000** no navegador. As três versões (desktop,
web, mobile) usam o mesmo banco de dados (`data/dp_automacao.db`) — o que
você cria numa aparece nas outras.

### Versão mobile (Android)

A versão web é também um **PWA (Progressive Web App)** — não é um app nativo
separado, é a mesma versão web instalada como app no celular. Isso significa
zero código duplicado: qualquer solicitação, regra CLT ou tela nova que você
adicionar já funciona automaticamente nas três versões (desktop, web e mobile).

**Pra instalar no Android:**
1. Rode `python web/app.py` no computador (ele precisa estar ligado e na
   mesma rede Wi-Fi do celular).
2. Descubra o IP local do computador (`ipconfig` no Windows, procure algo
   como `192.168.x.x`).
3. No celular, abra o Chrome e acesse `http://<IP-do-computador>:5000`.
4. Toque no menu (⋮) do Chrome → **"Adicionar à tela inicial"** (ou vai
   aparecer um banner de instalação automático).
5. O app abre em tela cheia, com ícone próprio, sem barra do navegador —
   como um app nativo.

O layout muda sozinho pra celular: a barra lateral vira uma barra de
navegação inferior (padrão de app Android), e as listas viram cards
empilhados em vez de tabela.

**Por que PWA em vez de app nativo:** um app Android nativo de verdade
(Kotlin/Java, ou Flutter/React Native) exigiria um projeto e uma stack
totalmente separados do resto do sistema — Android Studio, emulador,
assinatura de APK — e eu não tenho como compilar/testar isso neste ambiente
de forma confiável. O PWA entrega a mesma experiência de "app instalado no
Android" reaproveitando 100% do backend Python já validado. Se um dia fizer
sentido publicar na Play Store de verdade, dá pra empacotar esse mesmo PWA
com a ferramenta **Bubblewrap** (do próprio Google) sem reescrever nada.

Na primeira execução, o sistema cria automaticamente:
- `data/dp_automacao.db` — banco SQLite com todas as tabelas
- `data/anexos_recebidos/` e `data/servidor_documentos/` — pastas de trabalho
- `logs/dp_automacao.log` — log de execução

## Catálogo de solicitações

Acesse **"+ Nova solicitação"** pra ver todos os tipos disponíveis. Cada um
tem formulário próprio (gerado automaticamente a partir de
`core/tipos_solicitacao.py`) e validação das regras CLT relevantes.

**Bloco 1 — sem anexo**
Férias · Rescisão · Alteração cadastral · Relatório de rotina · Fechamento
de folha sem variáveis · Advertência · Suspensão disciplinar · Alteração de
benefício (VT/VR/plano) · 13º salário · Transferência de local · Alteração
de jornada · Solicitação de declaração · Solicitação de PPP

**Bloco 2 — com anexo**
Admissão · Atestado · Afastamento por INSS · CAT (Comunicação de Acidente
de Trabalho) · Admissão de estagiário · Admissão de aprendiz · Inclusão/
exclusão de dependente · Lançamento de valores na folha (horas extras,
faltas, comissões, adicional noturno, DSR...) · Licença maternidade ·
Licença paternidade · Exame ocupacional (ASO)

Alguns exemplos de regra já validada automaticamente:
- **CAT**: alerta se a comunicação passou do prazo legal (1º dia útil após o acidente — Lei 8.213/91)
- **Alteração de jornada**: bloqueia jornada semanal acima de 44h (CLT art. 58)
- **Licença maternidade/paternidade**: calcula automaticamente a data de fim (120/180 ou 5/20 dias, conforme adesão ao Empresa Cidadã)
- **Estágio**: bloqueia carga horária acima de 6h/dia (Lei 11.788/2008)
- **Aprendiz**: confere faixa etária 14–24 anos (sem limite superior para PCD)

Pra adicionar um novo tipo de solicitação no futuro, basta: (1) criar a
função `validar_*` em `regras/regras_clt.py`, (2) cadastrar o tipo e seus
campos em `core/tipos_solicitacao.py`, e (3) adicionar o nome em
`config.py` (`TIPOS_BLOCO_1`/`TIPOS_BLOCO_2`). O formulário web e a
validação aparecem automaticamente, sem precisar criar tela nova.

## Módulos do Bloco 2 implementados

### Atestados — só recebimento
Acesse **"+ Novo atestado"**. Cobre só a Automação 1 do Bloco 2: recebe 1
arquivo (PDF/PNG/JPG), salva e cria a solicitação direto na fila de
Validações — sem extração ainda.

### Admissões — recebimento + extração + validação CLT
Acesse **"+ Nova admissão"**. Já cobre um pipeline mais completo:

1. Aceita **vários documentos numa mesma solicitação** (RG, CTPS, comprovante
   de residência, dados bancários...).
2. Roda a **extração automática** (`modules/bloco2/extracao.py`) em cada
   anexo — hoje reconhece CPF, PIS e datas soltas no texto via regex.
3. Roda a **validação das regras CLT** (`regras/regras_clt.py`): confere os
   12 campos mínimos obrigatórios e valida o dígito verificador do CPF.
4. O que não for encontrado automaticamente aparece como **pendência**,
   destacada em amber tanto na fila de Validações quanto no detalhe da
   solicitação — pro analista completar manualmente antes de aprovar.

A extração por regex é só o começo: nome completo, cargo, salário e dados
bancários ainda não são reconhecidos automaticamente (dependem do layout
específico de cada documento) — é o próximo ponto natural de evolução.

## O que já funciona de verdade (não é stub)

- **Banco de dados** (`database/db_manager.py`): todas as tabelas (solicitações,
  anexos, validações, erros, alertas) e funções de CRUD.
- **Workflow** (`core/workflow.py` + `core/solicitacao.py`): máquina de estados
  fiel ao mapeamento — o sistema *não deixa* uma solicitação pular etapa.
- **Regras CLT fixas** (`regras/regras_clt.py`): validação de férias (fracionamento,
  saldo), cálculo de aviso prévio (Lei 12.506/2011), validação de CPF, campos
  mínimos de admissão.
- **Módulo de atestados** (`modules/bloco2/atestados.py`): recebimento de
  arquivo + criação de solicitação, ponta a ponta.
- **Interface desktop PyQt5** (`ui/`): 3 abas — Solicitações, Validações
  (fila de aprovação humana), Alertas.
- **Interface web Flask** (`web/`): as mesmas 3 telas + formulário de novo
  atestado com upload de arquivo, com identidade visual própria.
- **Organização de arquivos** (`utils/file_manager.py`): estrutura de pastas
  cliente/tipo/competência, já usada pelo módulo de distribuição do Bloco 1.

## O que está como stub (próximos passos)

Cada uma dessas funções levanta `NotImplementedError` de propósito — o resto
do sistema já sabe lidar com isso sem quebrar (registra erro, mantém o status
anterior). São os pontos onde entra integração externa de verdade:

| Módulo | O que falta | Onde plugar o que você já tem |
|---|---|---|
| `integracao/dominio_rpa.py` | Automação de tela (PyAutoGUI) | Seu pacote `dominio_banco_agencia` e o projeto de admissões PyQt5+Tesseract+pdfplumber |
| `integracao/onvio_api.py` | Chamadas à API/portal do Onvio | Seus scripts Batch com cURL/PowerShell |
| `integracao/esocial_monitor.py` | Consulta de status de evento no eSocial | — |
| `modules/rotinas/monitor_cct.py` | Scraping do Mediador (MTE) | — |
| `modules/rotinas/feriados.py` | Consulta de feriados nacionais/municipais | — |
| `modules/rotinas/consignado.py` | API do banco/escritório | — |
| `modules/bloco2/extracao.py` | Regex de campos por *layout* real de documento (nome, cargo, salário, dados bancários) | Precisa de exemplos reais de PDF/imagem de admissão pra calibrar |
| `modules/bloco2/atestados.py` | Extração de dados (datas, CID) e lançamento no Domínio | Ainda só recebe o arquivo — extração fica pra próxima etapa |

## Sugestão de ordem para continuar

1. **Testar o módulo de admissão** pela versão web, enviando alguns
   documentos reais e vendo quais campos a extração captura vs. o que fica
   como pendência.
2. **Refinar `modules/bloco2/extracao.py`** com regex específicas para os
   layouts reais dos seus documentos (nome, cargo, salário, dados bancários).
3. **Plugar `integracao/dominio_rpa.py::preencher_admissao()`** com a
   automação de tela que você já tem, pra fechar o ciclo depois da aprovação.
4. **`integracao/onvio_api.py`** — portar os scripts Batch/cURL existentes.

## Estrutura de pastas

```
dp_automacao/
├── main.py                    # ponto de entrada (desktop)
├── config.py                   # caminhos e constantes
├── database/                   # SQLite (db_manager.py)
├── core/                       # workflow (máquina de estados) + Solicitacao
├── regras/                     # regras fixas CLT / CCT
├── modules/
│   ├── bloco1/                  # sem anexo: recebimento, processamento, distribuição
│   ├── bloco2/                  # com anexo: recebimento, extração, atestados
│   └── rotinas/                  # feriados, CCT, consignado, alertas, compliance
├── integracao/                  # Domínio (RPA), Onvio (API), eSocial
├── utils/                       # arquivos, logging
├── ui/                          # janela principal + abas PyQt5 + estilo.qss
└── web/                         # versão web Flask (app.py, templates/, static/)
```

