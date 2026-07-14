# Publicar o Automação DP na nuvem (para demonstrar em qualquer computador)

Objetivo: colocar a **versão web** no ar com um endereço fixo (ex.:
`https://nexus-dp.onrender.com`) que qualquer pessoa abre no navegador de
qualquer computador ou celular — **sem depender do seu PC estar ligado**.

Usaremos o **Render** (render.com), que tem plano **gratuito** e lê sozinho a
"planta" que já está no repositório ([render.yaml](render.yaml)).

> A automação do Domínio (Painel do Robô) **não** vai pra nuvem — ela precisa
> da máquina com o Domínio aberto. Na demo, quando algo seria automatizado, o
> sistema apenas mostra "em atendimento manual". Todo o resto funciona.

---

## Passo a passo (uma vez)

1. **Crie uma conta no Render**: acesse https://render.com e clique em
   *Get Started* — dá pra entrar com a mesma conta do GitHub (mais fácil).
2. No painel do Render, clique em **New +** → **Blueprint**.
3. **Conecte o repositório** `josuep007-prog/nexus` (autorize o Render a ver
   seus repositórios do GitHub, se ele pedir).
4. O Render vai detectar o arquivo `render.yaml` e mostrar o serviço
   **nexus-dp** já configurado. Clique em **Apply** (ou *Create*).
5. Aguarde o **build** terminar (uns 2–4 minutos na primeira vez). Quando
   aparecer *Live*, o endereço público fica no topo da página — algo como
   `https://nexus-dp.onrender.com`.
6. Abra o endereço e entre com uma das contas de demonstração abaixo.

Pronto. Esse link é fixo — mande pra quem quiser, funciona em qualquer lugar.

---

## Qual branch o Render publica

O deploy está fixado na branch de trabalho **`claude/great-darwin-0110uv`**
(campo `branch:` no `render.yaml`) — é onde está todo o desenvolvimento. Se o
serviço no Render já tiver sido criado apontando para outra branch (ex.: `main`),
ajuste em **Settings → Branch** para `claude/great-darwin-0110uv` e clique em
**Manual Deploy → Deploy latest commit**. Ao mesclar tudo na `main` no futuro,
troque o `branch:` do `render.yaml` (ou remova a linha) para voltar a seguir a `main`.

---

## Contas de demonstração (já criadas no 1º acesso)

Senha de todas: **123**

| Login           | Papel                     | Enxerga |
|-----------------|---------------------------|---------|
| `administrador` | Administrador master      | Tudo, incluindo gestão de contas do escritório |
| `gestor`        | Gestor do departamento    | Operacional + relatórios + contas de cliente |
| `funcionario`   | Funcionário do escritório | Recebe, valida, processa e entrega |
| `cliente`       | Cliente (empresa)         | Só as próprias solicitações |

> Dica para demonstrar os papéis: entre como `administrador` para mostrar a
> visão completa, depois saia e entre como `cliente` para mostrar a experiência
> de quem abre solicitações. Os menus mudam conforme o papel.

Além das contas, o 1º acesso também cria uma **massa de empregados de teste**
(Dossiê do Empregado) vinculada aos clientes, para exercitar a conferência CLT
automática.

---

## Como testar a conferência automática (Cenário A x Cenário B)

1. Entre como **`cliente`** e abra **Nova → Férias**.
2. **Cenário A (dados completos):** no campo Empregado use `José da Silva` e no
   CPF `123.456.789-00` (empregado com saldo de 30 dias no cadastro). Peça
   **30 dias** → passa; peça **40 dias** → o sistema devolve para correção
   (excede o saldo). Não é preciso digitar saldo nenhum: ele vem do cadastro.
3. **Cenário B (dados insuficientes):** use um nome qualquer que não exista no
   cadastro (ex.: `Fulano da Silva`). A solicitação **não é bloqueada** — segue
   normal, mas fica marcada para o analista.
4. Entre como **`funcionario`** (ou `administrador`) e abra **Validações**: a de
   José aparece com o selo **✓ conferido**; a do Fulano com **🔎 conferência
   manual** e uma caixa em destaque dizendo o que checar na mão.

---

## Atualizar a demo depois de mudar o código

É automático: todo `git push` para a branch publicada (acima) faz o Render
**rebuildar e republicar** sozinho em 1–2 minutos. Os dados (banco temporário do
plano free) recomeçam limpos a cada publicação, já com as contas e a massa de
teste repostas.

---

## Coisas boas de saber

- **O serviço "dorme"** após ~15 min sem ninguém acessando (plano free). O
  próximo acesso demora ~30–50s pra "acordar" e depois fica rápido. Se for
  demonstrar ao vivo, abra o link 1 minuto antes pra ele já estar acordado.
- **Os dados são reiniciados** a cada nova publicação (o banco é temporário no
  plano free). Para uma demo isso é ótimo: começa sempre limpo, com as contas
  de exemplo repostas. Se um dia quiser dados permanentes, migra-se para um
  banco de rede (Postgres) — dá pra fazer quando precisar.
- **Nada sensível vai pro repositório**: a `SECRET_KEY` é gerada pelo próprio
  Render; e-mail/push só ligam se você configurar as variáveis deles.

---

## Alternativa rápida (sem publicar): túnel do seu PC

Se um dia precisar mostrar **na hora** direto da sua máquina, sem deploy:

```bash
# 1. rode o sistema localmente
python web/app.py
# 2. em outro terminal, exponha a porta 5000 com um túnel (instale o ngrok antes)
ngrok http 5000
```

O ngrok mostra um link público temporário (ex.: `https://abc123.ngrok-free.app`)
que qualquer pessoa abre enquanto seu PC estiver ligado rodando. O link muda a
cada execução — por isso o Render é melhor para demos recorrentes.
