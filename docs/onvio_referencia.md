# Onvio — Referência (Central de Soluções)

> **O que é este arquivo:** referência do Onvio (portal do cliente nativo do
> Domínio), capturada da Central de Soluções pelo usuário. Base para a decisão
> de arquitetura de integração do nexus. Ver a síntese do time no fim.

## 1. Visão geral

O Onvio é uma plataforma online que moderniza a comunicação entre escritórios
contábeis e clientes: compartilhamento de documentos, solicitações de serviços e
gestão centralizada. Duas frentes: **ONVIO Gestão** (administração do ambiente do
escritório) e **ONVIO Portal do Cliente** (funcionalidades do cliente final).

Módulos/áreas na Central: Onvio Folha, Onvio Escrita, Onvio Contabilidade, Onvio
Portal do Cliente, Onvio Portal do Empregado, Domínio Messenger, Domínio
Processos, Onvio Gestão, Domínio Custos, **Onvio API** (categoria própria).

**Recurso que trata das SOLICITAÇÕES que o cliente envia ao escritório (DP):**
é o **ONVIO Portal do Cliente**, via **Solicitações de Serviços** (aba "Portal do
Cliente"). Na Folha, abrangem: Solicitações Gerais, Cadastro de Colaborador,
Lançamento de Rubricas, Aviso Prévio de Férias, Cálculo de Férias, Aviso Prévio de
Rescisão, Cálculo de Rescisão e Afastamento de Empregado.

## 2. Portal do cliente / Solicitações

**Passo a passo genérico (cliente):** acessar o Portal do Cliente → aba **Portal do
Cliente** → escolher o tipo → **[Adicionar]** → preencher campos → opcionalmente
anexar arquivos e informar "Expectativa de conclusão" → **[Salvar e Enviar para o
Escritório]** (ou **[Rascunho]**). Situação evolui: "Enviado para o escritório" →
"Respondido" → "Cadastro efetuado"/"Concluído" (acompanhamento pela guia
**Trâmites**).

**Tipos de solicitação (Folha/DP):**
1. Solicitação Geral
2. Cadastro de Colaborador (Empregado, Contribuinte ou Estagiário) — equivale à admissão
3. Lançamento de Rubricas
4. Aviso Prévio de Férias
5. Cálculo de Férias
6. Aviso Prévio de Rescisão
7. Cálculo de Rescisão
8. Afastamento de Empregado (inclui atestado/acidente de trabalho)

Atestados/afastamento médico entram dentro de **Afastamento de Empregado** (não há
tipo "atestado" separado).

### Campos por tipo

**Cadastro de Colaborador (admissão):** Tipo (Empregado/Contribuinte/Estagiário);
campos obrigatórios do cadastro (lista nominal não detalhada no artigo; os
obrigatórios são definíveis pelo escritório); Observações (opcional); permite
anexos (documentos obrigatórios anexados pelo cliente antes do processamento).

**Cálculo de Férias:** Empregado (obrig.); Data de início do gozo (obrig.); Dias de
gozo (obrig.); Pagar abono pecuniário (sim/não); Adiantar 1ª parcela do 13º
(sim/não); Assunto; Descrição; Expectativa de conclusão (opc.); anexos: sim.

**Aviso Prévio de Férias:** Empregado (obrig.); Data de início do gozo (obrig.);
Dias de gozo (obrig.); Dias de abono; Data do aviso das férias (opc.); Data do
pagamento (opc.); Assunto; Descrição; Expectativa (opc.); anexos: sim.

**Cálculo de Rescisão:** Empregado (obrig.); Data de demissão (obrig.); Motivo da
rescisão (opc.); Data do aviso prévio (opc.); Tipo do aviso prévio; Assunto;
Descrição; Expectativa (opc.); anexos: sim.

**Aviso Prévio de Rescisão:** Empregado (obrig.); Motivo da rescisão; Aviso prévio
concedido por (Empregado/Empregador); Data do aviso do empregado; Assunto;
Descrição; Expectativa (opc.); anexos: sim.

**Afastamento de Empregado:** Empregado (obrig.); Tipo do Afastamento (obrig.);
Data de afastamento (obrig.); se acidente de trabalho: Data da CAT, Tipo e Número
da CAT (só p/ tipos de acid. de trabalho); Assunto; Descrição; Expectativa (opc.);
anexos: sim.

**Solicitação Geral:** Departamento responsável (obrig.); Assunto (obrig.);
Descrição (obrig.); Expectativa (opc.); anexos: sim.

**Lançamento de Rubricas:** pré-condição: escritório gera as rubricas permitidas no
Domínio (Utilitários > Lançamentos > Gerar Rubricas no ONVIO). Cliente preenche:
Tipo de Lançamento; Competência; filtro por Empregado/Contribuinte/Estagiário/
todos; adicionar funcionários; valor da rubrica por funcionário; Descrição (opc.).

## 3. Integração Onvio → Domínio

- Solicitações enviadas pelo cliente ficam disponíveis no Domínio **assim que
  enviadas**, desde que o **Agente de Comunicação** esteja **ativo** (ícone verde).
  Disponibilização automática/online.
- A execução/importação no Domínio **NÃO é automática**: o analista importa
  manualmente pelos atalhos na barra inferior esquerda (ícones separados para
  Solicitações de Serviço, Cadastro de colaboradores e Lançamento de rubricas).

**Fluxo manual do analista:**
1. Clicar no atalho da solicitação.
2. Abrir a pendente → [i] Detalhes para revisar.
3. Guia **Trâmites** → status **Em análise**.
4. Se preciso, [Ativar empresa dessa solicitação].
5. **[Executar no sistema]** — o Domínio abre a tela correspondente (admissão,
   férias, rescisão...) com **os dados já preenchidos**.
6. Conferir/ajustar → **[Gravar]**.
7. Trâmites → **Concluído** (cliente notificado automaticamente).

**Automático:** transporte das solicitações Onvio→Domínio (Agente de Comunicação),
**preenchimento prévio dos campos na tela do Domínio ao "Executar no sistema"**, e a
notificação de conclusão ao cliente.
**Manual:** abrir cada solicitação, mudar status, executar, conferir e gravar.

## 4. Entrada programática (o ponto crítico)

Na Central, "API" refere-se principalmente à **importação automática de documentos
fiscais (notas) de ERPs homologados** — não a uma API pública para inserir
solicitações de DP.

- **Existe API**, voltada a documentos fiscais (NF-e, NFC-e, NFS-e, CF-e, CT-e...).
  Também importação de rubricas/folha quando o cliente tem sistema de ponto com
  integração via API.
- **Autenticação:** **chave de habilitação** gerada no ONVIO Gestão > API > Chave >
  [Nova Habilitação], mais **credenciais Onvio (e-mail e senha)**. Sem menção a
  OAuth/bearer token. A chave é repassada ao ERP do cliente.
- **Endpoints:** não encontrado na Central.
- **Payload:** documentos trafegam em **XML padrão** (ex.: leiaute padrão de NF-e).
  Formato JSON próprio: não encontrado na Central.
- **Doc de desenvolvedor:** a Central **não fornece portal técnico público**. As
  "especificações técnicas" são enviadas pela Domínio diretamente ao ERP após
  homologação. Homologação é solicitada pelo **próprio ERP** ([Quero ser parceiro]).
- Contexto: existem "API Integra Contador" (Fisco) e "SIEG" (hub de notas),
  distintas da API de ERP.

**Importação por arquivo:** para documentos fiscais, sim (Utilitários > Importação
> Importação Padrão > Importação API, ou painel Docs Fiscais), em **XML padrão**.

**Conclusão da entrada programática:** para as **solicitações de DP (admissão,
férias, rescisão, afastamento, geral)**, a Central descreve **apenas** o
preenchimento pela **interface web** do Portal do Cliente, com importação manual do
analista no Domínio. **NÃO há API pública para inserir solicitações de DP
programaticamente** (exceção: rubricas/folha via sistema de ponto com API).

## 5. Observações e limitações

- API de notas: só importa a partir da data da parametrização; disponibilidade de
  até **60 dias**; parametrização só no usuário **GERENTE**; dá pra usar sem migrar
  do Domínio Atendimento pro Onvio.
- **Agente de Comunicação** precisa estar verde para documentos e solicitações
  chegarem ao Domínio.
- Cadastro de colaborador exige empresa **habilitada** no Portal do Cliente +
  permissão + Agente conectado.
- Tipos de colaborador nas solicitações de cadastro: Empregado, Contribuinte,
  Estagiário.
- Se o cliente não acessa o Portal, o **próprio escritório** pode registrar a
  solicitação (visão escritório).

---

## Síntese de arquitetura (leitura do time)

**Achado decisivo:** **não existe API pública do Onvio para inserir solicitações de
DP** (admissão, férias, rescisão, afastamento, geral) — a única entrada dessas
solicitações é a **interface web** do Portal do Cliente. A API do Onvio é só para
documentos fiscais de ERPs homologados.

Consequências para o nexus:

1. **RPA de tela no Domínio está morto E é redundante.** O Onvio→Domínio já faz o
   que o `dominio_rpa.py` tentava: no **[Executar no sistema]**, o Domínio abre a
   tela **já preenchida** com os dados da solicitação. Automatizar a tela do
   Domínio por fora seria refazer, pior, o que o trilho nativo já entrega. →
   **Abandonar `integracao/dominio_rpa.py` como estratégia.**

2. **O único bridge automatizável para o Onvio é a UI web.** Sem API de DP, se um
   dia quisermos que o nexus crie a solicitação no Onvio sozinho, o caminho é
   **automação de navegador (Playwright)** na tela web do Onvio — não PyAutoGUI de
   desktop. Playwright usa seletores reais (mais robusto), e o ambiente já vem com
   Chromium/Playwright. Custo: exige acesso real ao Onvio pra desenvolver, depende
   da estabilidade da UI de terceiro e de checar os Termos de Uso do Onvio.

3. **Onde o nexus agrega valor sem depender de nada externo (fazer AGORA):**
   - **Menos digitação:** cliente sobe documento → nexus **extrai** os campos
     (módulo `bloco2/extracao.py`) → some a "digitação na mão" que o Onvio exige.
   - **Triagem CLT/CCT + validação humana obrigatória:** o Onvio não faz; é o
     coração do nexus.
   - **Alinhar os tipos/campos do nexus aos do Onvio** (férias, rescisão,
     afastamento, cadastro de colaborador, rubricas, geral — campos exatos na
     seção 2), pra que a saída do nexus encaixe direto no Onvio, seja o repasse
     manual (analista) ou, depois, automatizado (Playwright).

**Norte (visão-alvo):** cliente → **nexus** (fácil, pouca digitação, com extração e
validação) → solicitação criada no **Onvio** (repasse manual do analista agora;
automação de navegador depois) → Agente de Comunicação → **Domínio** com
[Executar no sistema] pré-preenchido → [Gravar]. O cliente nunca toca na UI
confusa do Onvio; o analista ganha o pré-preenchimento nativo no Domínio.
