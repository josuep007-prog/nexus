"""
db_manager.py
-------------
Tudo que toca o banco SQLite passa por aqui. Isso evita ter SQL espalhado
pelos módulos e facilita mudar de banco no futuro (ex: PostgreSQL) sem
precisar reescrever cada automação.

Tabelas:
- solicitacoes : cada demanda recebida (férias, rescisão, admissão, etc.)
- anexos       : arquivos enviados pelo cliente vinculados a uma solicitação (Bloco 2)
- validacoes   : log de cada aprovação/reprovação humana (triagem, aprovação 1/2/3...)
- log_erros    : erros do sistema/eSocial vinculados a uma solicitação
- alertas      : vencimentos e avisos (férias vencendo, fim de experiência, prazos)
- usuarios     : contas de acesso (funcionário do escritório ou cliente)
- usuario_empresas : CNPJs EXTRAS de uma conta cliente (grupo econômico/filiais)
- comentarios  : conversa cliente <-> escritório dentro de uma solicitação
- push_assinaturas : inscrições de push do PWA (uma por navegador/dispositivo)
- obrigacoes_marcadas : checklist mensal de obrigações do DP (competência AAAA-MM)
- sistema      : chave-valor de estado interno (ex.: heartbeat do worker, último backup)
"""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    """Context manager de conexão. Uso: `with get_conn() as conn:`"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_banco():
    """Cria todas as tabelas caso ainda não existam. Chamar isso no início do main.py."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bloco TEXT NOT NULL,                 -- 'bloco1' ou 'bloco2'
                tipo TEXT NOT NULL,                  -- ferias, rescisao, admissao, etc.
                cliente_cnpj TEXT,
                cliente_nome TEXT,
                funcionario_nome TEXT,
                canal_origem TEXT,                   -- whatsapp, email, portal_onvio
                status TEXT NOT NULL,                -- ver core/workflow.py
                dados_json TEXT,                      -- payload com os dados da solicitação
                observacoes TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS anexos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
                caminho_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT,                    -- pdf, jpg, png, docx...
                origem TEXT NOT NULL DEFAULT 'cliente', -- 'cliente' (enviou) ou 'escritorio' (resultado entregue)
                extraido INTEGER NOT NULL DEFAULT 0,  -- 0/1
                dados_extraidos_json TEXT,
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS validacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
                etapa TEXT NOT NULL,                  -- triagem, aprovacao_1, aprovacao_2, aprovacao_3, distribuicao
                aprovado INTEGER NOT NULL,            -- 0/1
                aprovado_por TEXT,
                comentario TEXT,
                data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS log_erros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitacao_id INTEGER REFERENCES solicitacoes(id) ON DELETE CASCADE,
                modulo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                resolvido INTEGER NOT NULL DEFAULT 0,
                data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,                   -- vencimento_ferias, fim_experiencia, prazo_imposto...
                referencia_id INTEGER,                -- geralmente aponta pra solicitacoes.id
                descricao TEXT,
                data_vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',  -- pendente, notificado, resolvido
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL UNIQUE,           -- e-mail ou usuário curto usado pra logar
                senha_hash TEXT NOT NULL,             -- werkzeug.security.generate_password_hash
                tipo_conta TEXT NOT NULL,             -- 'funcionario' ou 'cliente'
                nome_exibicao TEXT NOT NULL,          -- nome da pessoa (funcionário) ou razão social (cliente)
                cliente_cnpj TEXT,                    -- só p/ tipo_conta='cliente'; NULL p/ funcionario
                ativo INTEGER NOT NULL DEFAULT 1,     -- 0/1, permite desativar sem apagar histórico
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usuario_empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                cnpj TEXT NOT NULL,
                nome TEXT,                            -- razão social da empresa extra
                UNIQUE(usuario_id, cnpj)
            );

            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
                autor TEXT NOT NULL,                  -- "Nome (login)" de quem escreveu
                tipo_conta TEXT NOT NULL,             -- 'funcionario' ou 'cliente'
                texto TEXT NOT NULL,
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS push_assinaturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                endpoint TEXT NOT NULL UNIQUE,        -- URL do push service do navegador
                assinatura_json TEXT NOT NULL,        -- subscription completa (keys etc.)
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS obrigacoes_marcadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competencia TEXT NOT NULL,            -- 'AAAA-MM'
                obrigacao TEXT NOT NULL,              -- nome da obrigação (config.OBRIGACOES_MENSAIS)
                feito INTEGER NOT NULL DEFAULT 0,
                marcado_por TEXT,
                marcado_em TEXT,
                UNIQUE(competencia, obrigacao)
            );

            CREATE TABLE IF NOT EXISTS sistema (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_solicitacoes_status ON solicitacoes(status);
            CREATE INDEX IF NOT EXISTS idx_solicitacoes_bloco_tipo ON solicitacoes(bloco, tipo);
            CREATE INDEX IF NOT EXISTS idx_anexos_solicitacao ON anexos(solicitacao_id);
            CREATE INDEX IF NOT EXISTS idx_validacoes_solicitacao ON validacoes(solicitacao_id);
            CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios(login);
            CREATE INDEX IF NOT EXISTS idx_comentarios_solicitacao ON comentarios(solicitacao_id);
            """
        )

        # Migração leve: coluna 'origem' em anexos (bancos criados antes dela).
        cols_anexos = [r["name"] for r in conn.execute("PRAGMA table_info(anexos)").fetchall()]
        if "origem" not in cols_anexos:
            conn.execute("ALTER TABLE anexos ADD COLUMN origem TEXT NOT NULL DEFAULT 'cliente'")

        # Migração leve: coluna 'email' em usuarios (para notificações).
        cols_usuarios = [r["name"] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
        if "email" not in cols_usuarios:
            conn.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")


# ---------------------------------------------------------------------------
# Funções auxiliares de CRUD - solicitações
# ---------------------------------------------------------------------------

def criar_solicitacao(bloco, tipo, status, cliente_cnpj=None, cliente_nome=None,
                       funcionario_nome=None, canal_origem=None, dados=None,
                       observacoes=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO solicitacoes
                (bloco, tipo, cliente_cnpj, cliente_nome, funcionario_nome,
                 canal_origem, status, dados_json, observacoes, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bloco, tipo, cliente_cnpj, cliente_nome, funcionario_nome, canal_origem,
             status, json.dumps(dados or {}, ensure_ascii=False), observacoes, agora, agora),
        )
        return cur.lastrowid


def atualizar_status(solicitacao_id, novo_status):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "UPDATE solicitacoes SET status = ?, atualizado_em = ? WHERE id = ?",
            (novo_status, agora, solicitacao_id),
        )


def atualizar_dados(solicitacao_id, dados: dict):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "UPDATE solicitacoes SET dados_json = ?, atualizado_em = ? WHERE id = ?",
            (json.dumps(dados, ensure_ascii=False), agora, solicitacao_id),
        )


def buscar_solicitacao(solicitacao_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM solicitacoes WHERE id = ?", (solicitacao_id,)
        ).fetchone()
        return dict(row) if row else None


def excluir_solicitacao(solicitacao_id):
    """Remove a solicitação e (por CASCADE) seus anexos, validações e erros do banco.

    Devolve a lista de caminhos de anexos que estavam vinculados, pra quem chamar
    poder apagar os arquivos do disco também.
    """
    with get_conn() as conn:
        caminhos = [r["caminho_arquivo"] for r in conn.execute(
            "SELECT caminho_arquivo FROM anexos WHERE solicitacao_id = ?", (solicitacao_id,)
        ).fetchall()]
        conn.execute("DELETE FROM solicitacoes WHERE id = ?", (solicitacao_id,))
    return caminhos


def listar_solicitacoes(status=None, bloco=None, cliente_cnpj=None,
                        tipo=None, data_inicio=None, data_fim=None):
    query = "SELECT * FROM solicitacoes WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if bloco:
        query += " AND bloco = ?"
        params.append(bloco)
    if cliente_cnpj is not None:
        # Restringe contas 'cliente' às próprias solicitações. Aceita um CNPJ
        # único (str) ou uma lista de CNPJs (conta com várias empresas do grupo).
        if isinstance(cliente_cnpj, (list, tuple, set)):
            cnpjs = list(cliente_cnpj) or [""]
            query += f" AND cliente_cnpj IN ({','.join('?' * len(cnpjs))})"
            params.extend(cnpjs)
        else:
            query += " AND cliente_cnpj = ?"
            params.append(cliente_cnpj)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    if data_inicio:
        query += " AND criado_em >= ?"
        params.append(data_inicio)
    if data_fim:
        # fim inclusivo: qualquer horário dentro do dia informado
        query += " AND criado_em <= ?"
        params.append(data_fim + "T23:59:59")
    query += " ORDER BY criado_em DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Anexos (Bloco 2)
# ---------------------------------------------------------------------------

def adicionar_anexo(solicitacao_id, caminho_arquivo, tipo_arquivo=None, origem="cliente"):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO anexos (solicitacao_id, caminho_arquivo, tipo_arquivo, origem, extraido, criado_em)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (solicitacao_id, caminho_arquivo, tipo_arquivo, origem, agora),
        )
        return cur.lastrowid


def salvar_dados_extraidos(anexo_id, dados: dict):
    with get_conn() as conn:
        conn.execute(
            "UPDATE anexos SET extraido = 1, dados_extraidos_json = ? WHERE id = ?",
            (json.dumps(dados, ensure_ascii=False), anexo_id),
        )


def listar_anexos(solicitacao_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM anexos WHERE solicitacao_id = ?", (solicitacao_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def buscar_anexo(anexo_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM anexos WHERE id = ?", (anexo_id,)).fetchone()
        return dict(row) if row else None


def excluir_anexo(anexo_id):
    """Remove um anexo. Devolve o caminho do arquivo (pra quem chamar apagar do disco)."""
    with get_conn() as conn:
        row = conn.execute("SELECT caminho_arquivo FROM anexos WHERE id = ?", (anexo_id,)).fetchone()
        conn.execute("DELETE FROM anexos WHERE id = ?", (anexo_id,))
    return row["caminho_arquivo"] if row else None


# ---------------------------------------------------------------------------
# Validações humanas (triagem / tríplice aprovação)
# ---------------------------------------------------------------------------

def registrar_validacao(solicitacao_id, etapa, aprovado, aprovado_por=None, comentario=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO validacoes (solicitacao_id, etapa, aprovado, aprovado_por, comentario, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (solicitacao_id, etapa, int(aprovado), aprovado_por, comentario, agora),
        )


def listar_validacoes(solicitacao_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM validacoes WHERE solicitacao_id = ? ORDER BY data ASC",
            (solicitacao_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def listar_validacoes_periodo(data_inicio=None, data_fim=None):
    """Todas as validações num período — usada pelo painel de produtividade."""
    query = "SELECT * FROM validacoes WHERE 1=1"
    params = []
    if data_inicio:
        query += " AND data >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND data <= ?"
        params.append(data_fim + "T23:59:59")
    query += " ORDER BY data ASC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

def registrar_erro(modulo, mensagem, solicitacao_id=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO log_erros (solicitacao_id, modulo, mensagem, resolvido, data)
            VALUES (?, ?, ?, 0, ?)
            """,
            (solicitacao_id, modulo, mensagem, agora),
        )


def listar_erros(resolvido=None):
    query = "SELECT * FROM log_erros WHERE 1=1"
    params = []
    if resolvido is not None:
        query += " AND resolvido = ?"
        params.append(int(resolvido))
    query += " ORDER BY data DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

def criar_alerta(tipo, descricao, data_vencimento=None, referencia_id=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO alertas (tipo, referencia_id, descricao, data_vencimento, status, criado_em)
            VALUES (?, ?, ?, ?, 'pendente', ?)
            """,
            (tipo, referencia_id, descricao, data_vencimento, agora),
        )
        return cur.lastrowid


def listar_alertas(status="pendente"):
    query = "SELECT * FROM alertas"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY data_vencimento ASC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def atualizar_status_alerta(alerta_id, novo_status):
    with get_conn() as conn:
        conn.execute("UPDATE alertas SET status = ? WHERE id = ?", (novo_status, alerta_id))


# ---------------------------------------------------------------------------
# Usuários (autenticação)
# ---------------------------------------------------------------------------

def criar_usuario(login, senha_hash, tipo_conta, nome_exibicao, cliente_cnpj=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO usuarios
                (login, senha_hash, tipo_conta, nome_exibicao, cliente_cnpj, ativo, criado_em)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (login, senha_hash, tipo_conta, nome_exibicao, cliente_cnpj, agora),
        )
        return cur.lastrowid


def buscar_usuario_por_login(login):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE login = ?", (login,)
        ).fetchone()
        return dict(row) if row else None


def buscar_usuario_por_id(usuario_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return dict(row) if row else None


def listar_usuarios():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM usuarios ORDER BY tipo_conta, nome_exibicao").fetchall()
        return [dict(r) for r in rows]


def atualizar_senha_usuario(usuario_id, novo_hash):
    with get_conn() as conn:
        conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (novo_hash, usuario_id))


def atualizar_email_usuario(usuario_id, email):
    with get_conn() as conn:
        conn.execute("UPDATE usuarios SET email = ? WHERE id = ?", (email or None, usuario_id))


def definir_usuario_ativo(usuario_id, ativo):
    with get_conn() as conn:
        conn.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (int(ativo), usuario_id))


def buscar_clientes_por_cnpj(cnpj):
    """Contas cliente donas de um CNPJ (principal ou extra) — p/ notificações."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT u.* FROM usuarios u
            LEFT JOIN usuario_empresas e ON e.usuario_id = u.id
            WHERE u.tipo_conta = 'cliente' AND u.ativo = 1
              AND (u.cliente_cnpj = ? OR e.cnpj = ?)
            """,
            (cnpj, cnpj),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Empresas extras de uma conta cliente (grupo econômico / filiais)
# ---------------------------------------------------------------------------

def listar_empresas_usuario(usuario_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM usuario_empresas WHERE usuario_id = ? ORDER BY nome", (usuario_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def adicionar_empresa_usuario(usuario_id, cnpj, nome=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO usuario_empresas (usuario_id, cnpj, nome) VALUES (?, ?, ?)",
            (usuario_id, cnpj, nome),
        )


def remover_empresa_usuario(empresa_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM usuario_empresas WHERE id = ?", (empresa_id,))


# ---------------------------------------------------------------------------
# Comentários (conversa cliente <-> escritório dentro da solicitação)
# ---------------------------------------------------------------------------

def adicionar_comentario(solicitacao_id, autor, tipo_conta, texto):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO comentarios (solicitacao_id, autor, tipo_conta, texto, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (solicitacao_id, autor, tipo_conta, texto, agora),
        )
        return cur.lastrowid


def listar_comentarios(solicitacao_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM comentarios WHERE solicitacao_id = ? ORDER BY criado_em ASC",
            (solicitacao_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Push (PWA): inscrições por usuário/dispositivo
# ---------------------------------------------------------------------------

def salvar_assinatura_push(usuario_id, endpoint, assinatura_json):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO push_assinaturas (usuario_id, endpoint, assinatura_json, criado_em)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET usuario_id = excluded.usuario_id,
                                                assinatura_json = excluded.assinatura_json
            """,
            (usuario_id, endpoint, assinatura_json, agora),
        )


def listar_assinaturas_push(usuario_ids=None):
    query = "SELECT * FROM push_assinaturas"
    params = []
    if usuario_ids:
        query += f" WHERE usuario_id IN ({','.join('?' * len(usuario_ids))})"
        params.extend(usuario_ids)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def remover_assinatura_push(endpoint):
    with get_conn() as conn:
        conn.execute("DELETE FROM push_assinaturas WHERE endpoint = ?", (endpoint,))


# ---------------------------------------------------------------------------
# Obrigações mensais (checklist por competência AAAA-MM)
# ---------------------------------------------------------------------------

def marcar_obrigacao(competencia, obrigacao, feito, marcado_por=None):
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO obrigacoes_marcadas (competencia, obrigacao, feito, marcado_por, marcado_em)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(competencia, obrigacao) DO UPDATE SET
                feito = excluded.feito, marcado_por = excluded.marcado_por, marcado_em = excluded.marcado_em
            """,
            (competencia, obrigacao, int(feito), marcado_por, agora),
        )


def listar_obrigacoes_marcadas(competencia):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM obrigacoes_marcadas WHERE competencia = ?", (competencia,)
        ).fetchall()
        return {r["obrigacao"]: dict(r) for r in rows}


# ---------------------------------------------------------------------------
# Estado do sistema (chave-valor): heartbeat do worker, último backup etc.
# ---------------------------------------------------------------------------

def definir_valor_sistema(chave, valor):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sistema (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, str(valor)),
        )


def obter_valor_sistema(chave):
    with get_conn() as conn:
        row = conn.execute("SELECT valor FROM sistema WHERE chave = ?", (chave,)).fetchone()
        return row["valor"] if row else None
