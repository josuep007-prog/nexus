# Operações no Sistema Domínio — Módulo Folha / DP

> **O que é este arquivo:** referência das telas/processos do Domínio, capturada
> da Central de Soluções (suporte.dominioatendimento.com, módulo Folha) pelo
> usuário. Serve de base para calibrar `integracao/dominio_rpa.py` (os `ROTEIRO_*`)
> e para avaliar a importação por arquivo.
>
> **Status / cuidado:** o passo a passo abaixo descreve as telas de forma
> operacional ("preencha esta guia, clique neste botão"). A **ordem exata de
> navegação por TAB** e a lista campo-a-campo de obrigatoriedade NÃO são cravadas
> pela Central — precisam de confirmação contra a tela real antes de virar um
> ROTEIRO confiável. Ver a síntese de arquitetura no fim do arquivo.

---

## Admissão de funcionário

**Caminho de menu:** Arquivo > Empregados

**Tela:** Cadastro de Empregados (janela do empregado, organizada em guias: Geral, Profissionais, Pessoais, etc.)

**Campos, na ordem em que aparecem na tela:**

1. Matrícula eSocial — gerada automaticamente de forma sequencial ao clicar em [Novo]; se o empregado já foi enviado ao eSocial, deve-se informar a mesma matrícula existente no Portal do eSocial.
2. Nome completo do empregado — texto.
3. Guia **Geral** — preencher todos os campos da guia. Dentro dela:
   - PIS — facultativo.
   - Função — preencher somente para cargos de gerência ou supervisão.
   - Sindicato — informar o código do cadastro do sindicato (F2 para localizar, F7 para cadastrar).
   - Convenção Coletiva — selecionar a convenção relacionada ao empregado (após informar o sindicato).
   - Data de Admissão — data.
   - Informações contratuais.
   - Valor do salário.
   - Vínculo empregatício — ao lado, o botão [...] (reticências) abre o Contrato de experiência; se informada a prorrogação, ela é enviada automaticamente pelo evento S-2206 no dia útil seguinte à data final do primeiro período.
4. Guia **Profissionais > Geral > Admissão**:
   - Tipo de admissão — selecionar.
   - Local de trabalho — informar o local (ex.: escritório, cidade, unidade); pode selecionar um já cadastrado pela seta ao lado ou digitar a descrição de um novo (o sistema pede confirmação para criar — [Sim]). Não é obrigatório; fica a critério da empresa.
5. Subguia **Outros Dados** (dentro de Profissionais):
   - Opção para o cálculo da dedução do IRRF.
   - Informação de múltiplos vínculos.
6. Guia **Profissionais > Outros Dados**:
   - Jornada de trabalho — definir.
7. Subguia **Atestados e Exames > Monitoramento de Saúde**:
   - ASOs (Atestado de Saúde Ocupacional) — informar (opcional neste passo).
8. Guia **Pessoais** — preencher as subguias:
   - Endereço.
   - Informações Pessoais — incluindo Data de Nascimento e Raça/Cor (a Central destaca não esquecer desses dois).
9. Demais guias — preencher conforme necessário.

**Navegação/confirmação:** Iniciar em [Novo]. Percorrer campos e guias/subguias (Geral, Profissionais, Pessoais e demais). Concluir com o botão [Gravar]. O evento S-2200 (admissão) é enviado automaticamente ao eSocial após a gravação.

**Observações:** Campos que a Central marca como facultativos: PIS e Local de trabalho. Função só se aplica a gerência/supervisão. A Central enfatiza preencher Data de Nascimento e Raça/Cor. Se, em Controle > Parâmetros > Geral > e-Social > Configurações de Envio > Faseamento, estiver marcada a opção de "Não enviar automaticamente os eventos não periódicos ao eSocial a partir de:", o envio do S-2200 deve ser feito manualmente em Relatórios > eSocial > Eventos Não Periódicos, marcando "Admissão (S-2190 / S-2200 / S-2300)" e clicando em [Enviar]. A quantidade exata de campos obrigatórios validados pelo sistema não é listada na Central ("preencha todos os campos" — detalhamento campo a campo de obrigatoriedade: não encontrado na Central).

## Cálculo/lançamento de Férias

**Caminho de menu:** Processos > Férias > Individual

**Tela:** Férias — Individual (janela de cálculo de férias do colaborador)

**Campos, na ordem em que aparecem na tela:**

1. Colaborador — informar o colaborador; depois clicar em [Nova...].
2. Quadro **Período aquisitivo** — demonstra (somente exibição) o período a que o colaborador tem direito.
3. Quadro **Pagar férias gozadas**:
   - Início — data (não superior a 90 dias da data atual).
   - Dias de férias gozadas — quantidade.
4. Opção **Pagar abono pecuniário** — marcar caso o empregado tenha vendido 1/3 das férias (10 dias).
5. Quadro **Pagamento**:
   - Data — preenchida automaticamente, 2 dias úteis antes do início do gozo.
6. Quadro **Opções das férias** — selecionar conforme a necessidade.
7. Opção **Informar médias manualmente** — marcar caso o empregado tenha vindo de outra contabilidade durante o ano; ao marcar, preencher as colunas de médias.

**Navegação/confirmação:** Após informar o colaborador, clicar em [Nova...]. Se for preciso calcular alguma rubrica nas férias, usar o botão [Lançamentos...]. Concluir com o botão [Calcular] para efetuar o cálculo das férias.

**Observações:** A data de Início não pode ser superior a 90 dias da data atual; para datas futuras acima disso, usar o Simulador de férias. O evento S-2230 é enviado automaticamente ao eSocial na data efetiva (início e retorno do gozo). O prazo de envio ao eSocial é até o dia 15 do mês seguinte; para antecipar o início, usar Processos > Afastamentos > [Enviar eSocial Início]. As rubricas vão no S-1200 do mês do cálculo e o líquido no S-1210 da competência do pagamento. No cálculo de férias são gerados FGTS, INSS e IRRF, recolhidos junto com a apuração mensal (sem guia específica por férias). Botão [Nova...] às vezes precisa ser habilitado (há solução relacionada "Como habilitar o botão [Nova...] Férias?").

## Rescisão

**Caminho de menu:** Processos > Rescisões > Individual

**Tela:** Rescisão — Individual (janela de rescisão do colaborador)

**Campos, na ordem em que aparecem na tela:**

1. Colaborador — informar o código do colaborador.
2. Demitido em — data da demissão.
3. Motivo da rescisão — selecionar; o **Motivo eSocial** é preenchido automaticamente conforme o motivo escolhido.
4. Quadro **FGTS**:
   - Opção "Antecipar vencimento do débito do mês anterior" — marcar caso o desligamento seja entre os dias 1 e 9 do mês e o FGTS Mensal do mês anterior esteja em aberto.
   - Saldo em Banco — informar o valor do saldo do FGTS para fins rescisórios.

**Navegação/confirmação:** Para lançamentos na rescisão, usar o botão [Lançamentos]. Concluir com o botão [Calcular] e conferir os valores do desligamento. O envio ao eSocial (S-2299/S-2399) é feito pelo botão [Enviar eSocial] na janela de rescisão; se aparecer mensagem sobre rubricas ainda não enviadas, clicar em [Sim] para enviá-las.

**Observações:** Se desejar emitir Aviso Prévio, ele deve ser cadastrado antes em Processos > Rescisões > Aviso Prévio > Individual. Para cálculos com data superior a 90 dias da data atual, usar a simulação de rescisão. Prazo de envio do Desligamento ao eSocial: até 10 dias corridos após a rescisão (envio antecipado aceito só até 10 dias antes da data). Se a rescisão for recalculada, é necessário excluir o S-1210 correspondente e reenviar S-2299 e S-2210. Rescisão com aviso indenizado aparece duas vezes no eSocial (data real + projeção do aviso).

## Alteração cadastral

**Caminho de menu:** Arquivo > Empregados (para empregados). Também Arquivo > Contribuintes e Arquivo > Estagiários > Cadastro, conforme o tipo de colaborador.

**Tela:** Cadastro do colaborador (mesma janela de cadastro, guias Geral e Pessoais)

**Campos, na ordem em que aparecem na tela:** depende do dado alterado. A Central separa em dois tipos:

- **Alteração Cadastral (evento S-2205)** — abrange endereço, cidade, documentos pessoais, escolaridade e estado civil. Exemplo dado: guia **Pessoais > Endereço** → alterar o endereço do colaborador.
- **Alteração Contratual (eventos S-2206 empregados / S-2306 contribuintes, estagiários)** — abrange serviço, cargo, função e salário. Exemplo dado: guia **Geral** → alterar o código do **Cargo**.

**Navegação/confirmação:**
1. Abrir o cadastro do colaborador (Empregados / Contribuintes / Estagiários).
2. Alterar o campo desejado na guia correspondente (Pessoais > Endereço para cadastral; Geral para contratual).
3. Clicar em [Gravar] e salvar como [Alteração].
4. Na janela **Alterações**, informar a **Data da alteração** e clicar em [Gravar]. O evento é enviado automaticamente na data da alteração.

**Observações:** Campo obrigatório na confirmação: Data da alteração. Para conferir o que foi enviado, usar o botão [Histórico...] (guia Dados Contratuais para S-2206/S-2306; guia Dados Cadastrais para S-2205). Se a empresa estiver configurada para envio manual (opção de faseamento marcada em Controle > Parâmetros > Geral > e-Social > Configurações de Envio > Faseamento), enviar por Relatórios > eSocial > Eventos Não Periódicos, marcando "Alteração Contratual (S-2206 / S-2306)" ou "Alteração Cadastral (S-2205)" e clicando em [Enviar]. Alterações contratuais e cadastrais de empregados domésticos não são enviadas pelo Domínio — o cadastro deve ser feito manualmente no Portal do eSocial.

## Importação por arquivo

**O Domínio permite importar dados por layout de arquivo?** Sim, parcialmente. A Central documenta a importação por arquivo texto pelo menu **Utilitários > Importação > de Arquivo texto**, com layouts (leiautes) específicos publicados para:

- De Contribuintes
- De RPA
- De Lançamentos
- Notas de Aquisição Rural

**Importante — importação de admissões/empregados CLT:** um layout de arquivo texto para importar admissões/cadastro de **empregados (S-2200)** não foi encontrado na Central. Os leiautes disponíveis para cadastro cobrem Contribuintes (autônomos/individuais), não empregados celetistas. Portanto, importar admissões de empregados por arquivo .txt/.csv: **não encontrado na Central**.

**Como importar (procedimento geral, exemplo do leiaute de Contribuintes):**
1. Acesse Utilitários > Importação > de Arquivo texto > de Contribuintes.
2. No campo Arquivo, clique no botão [...] (reticências) e localize o arquivo texto.
3. Indique se deseja importar Cadastros já existentes, selecionando uma das opções.
4. Clique no botão [Importar].

**Layout do arquivo texto — De Contribuintes (formato posicional, arquivo .txt):**
O arquivo é de largura fixa, definido por posições. Principais campos, na ordem:

| Posição | Tamanho | Tipo | Campo |
|--------|--------|------|-------|
| 001-007 | 07 | Numérico | Código da empresa |
| 008-018 | 11 | Numérico | CPF do contribuinte |
| 019-029 | 11 | Numérico | Número PIS/NIS (opcional) |
| 030-099 | 70 | Alfanumérico | Nome do contribuinte |
| 100-109 | 10 | Numérico | Código do serviço |
| 110-119 | 10 | Numérico | Código do cargo |
| 120-129 | 10 | Numérico | Código do departamento |
| 130-139 | 10 | Numérico | Código do centro de custo |
| 140-147 | 08 | Data | Data de início do contrato (AAAAMMDD) |
| 148-149 | 02 | Numérico | Categoria da Sefip |
| 150 | 01 | Numérico | Tipo de contribuinte (1 Empregador, 2 Facultativo, 3 Autônomo, 4 Produtor Rural, 5 MEI, 6 Segurado Especial, 7 Autônomo MEI) |
| 151-156 | 06 | Numérico | Código da rubrica |
| 157-164 | 08 | Numérico | Valor do salário |
| 165 | 01 | Alfanumérico | Tipo serviço (N/C/P) |
| 166-173 | 08 | Data | Data de nascimento (AAAAMMDD) |
| 174 | 01 | Numérico | Forma de pagamento (1 Cheque, 2 Crédito em conta, 3 Dinheiro, 4 PIX) |
| 175 | 01 | Numérico | Tipo de chave PIX (1 CPF, 2 Celular, 3 E-mail, 4 Chave Aleatória) |
| 176-245 | 70 | Alfanumérico | Chave PIX |
| 246-251 | 06 | Numérico | Código do banco |
| 252-263 | 12 | Numérico | Número da conta |
| 264-265 | 02 | Numérico | Dígito verificador |
| 266-267 | 02 | Alfanumérico | Tipo de conta (01 Não informada, 02 Corrente, 03 Salário, 04 Poupança) |
| 268-270 | 03 | Alfanumérico | País da nacionalidade (Código SISCOMEX) |
| 271-277 | 07 | Alfanumérico | Município de nascimento (Código IBGE) |
| 278-377 | 100 | Alfanumérico | Endereço |
| 378-383 | 06 | Numérico | Número |
| 384-463 | 80 | Alfanumérico | Bairro |
| 464-471 | 08 | Numérico | CEP |
| 472-478 | 07 | Alfanumérico | Município (Código IBGE) |
| 479-481 | 03 | Alfanumérico | Categoria eSocial (701, 711, 712, 721, 722, 723, 731, 734, 738, 741, 751, 761, 771, 781, 902) |
| 482 | 01 | Alfanumérico | Enviar contribuinte via evento S-1200 (S/N) |
| 483-490 | 08 | Data | Data da opção do FGTS (AAAAMMDD) |
| 491 | 01 | Numérico | Múltiplos vínculos (1 Não, 2 Sim, 3 Sim acima do teto) |
| 492-502 | 11 | Numérico | Matrícula do INSS |
| 503-504 | 02 | Numérico | Ocorrência SEFIP (00 a 08) |
| 505-574 | 70 | Alfanumérico | Nome do Pai |
| 575-644 | 70 | Alfanumérico | Nome da Mãe |
| 645 | 01 | Numérico | Raça (1 Indígena, 2 Branca, 3 Preta, 4 Amarela, 5 Parda, 6 Não informado) — obrigatório; sem ela, o sistema gera advertência ao importar |

Observação sobre o layout: é um arquivo texto posicional (largura fixa), não um CSV com separador para este leiaute. Existe também uma solução "Importação Padrão — Leiaute Domínio Sistemas com Separador" na Central, mas o detalhamento desse leiaute com separador: não consultado neste documento. Os leiautes detalhados de RPA, Lançamentos e Notas de Aquisição Rural existem na Central, porém seus campos posição a posição não foram transcritos aqui (consultar os respectivos artigos "Leiaute: Importação Arquivo Texto | De RPA / De Lançamentos / Notas de Aquisição Rural").

---

## Síntese de arquitetura (leitura do time)

O que esta referência muda no plano de integração com o Domínio:

1. **Admissão de empregado CLT é o caso mais difícil de automatizar por tela.** A
   janela é cheia de **guias e subguias** (Geral, Profissionais > Geral > Admissão,
   Profissionais > Outros Dados, Pessoais > Endereço/Informações Pessoais...),
   campos com busca (F2/F7, Sindicato) e botões `[...]` que abrem subjanelas
   (Contrato de experiência). Um `ROTEIRO_*` linear só de TAB é **frágil** aqui —
   exigiria trocar de guia, tratar diálogos de busca, etc. E a Central não crava a
   ordem de TAB nem a obrigatoriedade campo a campo.

2. **Importar admissão CLT por arquivo NÃO é possível pela Central.** Os leiautes de
   importação cobrem **Contribuintes (autônomos), RPA, Lançamentos e Notas de
   Aquisição Rural** — não há layout para empregado celetista (S-2200).

3. **Onde a importação por arquivo é viável, ela vence o robô de tela.** O leiaute
   **De Contribuintes** está totalmente especificado (posicional, largura fixa) e um
   gerador desse arquivo é **determinístico e testável offline** (sem depender do
   Domínio aberto) — muito mais robusto que PyAutoGUI.

**Recomendação:** arquitetura **híbrida** —
   - Onde há importação (Contribuintes / RPA / Lançamentos): **gerar o arquivo** no
     leiaute e importar. Robusto e testável.
   - Onde não há (admissão CLT, férias, rescisão): manter no **atendimento manual**
     (fluxo que já funciona ponta a ponta) e, quando valer, calibrar `ROTEIRO_*` de
     tela contra a tela real — começando pelas telas mais simples (Férias, Rescisão),
     não pela Admissão.
