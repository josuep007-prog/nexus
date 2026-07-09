"""
core/solicitacao.py
--------------------
Camada fina em cima do database/db_manager.py: representa uma solicitação
como objeto Python, com um método `avancar()` que já valida a transição
usando core/workflow.py antes de gravar no banco.

Qualquer módulo (bloco1, bloco2, ui) deve mexer no status de uma solicitação
através daqui, e não chamando db_manager.atualizar_status() direto.
"""

import json

from database import db_manager
from core import workflow


class TransicaoInvalidaError(Exception):
    pass


class Solicitacao:
    def __init__(self, row: dict):
        self._row = row

    # -- construtores -------------------------------------------------
    @classmethod
    def criar(cls, bloco, tipo, canal_origem=None, cliente_cnpj=None,
              cliente_nome=None, funcionario_nome=None, dados=None):
        status = workflow.status_inicial(bloco)
        novo_id = db_manager.criar_solicitacao(
            bloco=bloco, tipo=tipo, status=status,
            cliente_cnpj=cliente_cnpj, cliente_nome=cliente_nome,
            funcionario_nome=funcionario_nome, canal_origem=canal_origem,
            dados=dados,
        )
        return cls.carregar(novo_id)

    @classmethod
    def carregar(cls, solicitacao_id):
        row = db_manager.buscar_solicitacao(solicitacao_id)
        if row is None:
            raise ValueError(f"Solicitação {solicitacao_id} não encontrada")
        return cls(row)

    @classmethod
    def listar(cls, status=None, bloco=None, cliente_cnpj=None,
               tipo=None, data_inicio=None, data_fim=None):
        rows = db_manager.listar_solicitacoes(status=status, bloco=bloco, cliente_cnpj=cliente_cnpj,
                                              tipo=tipo, data_inicio=data_inicio, data_fim=data_fim)
        return [cls(r) for r in rows]

    # -- propriedades ---------------------------------------------------
    @property
    def id(self):
        return self._row["id"]

    @property
    def bloco(self):
        return self._row["bloco"]

    @property
    def tipo(self):
        return self._row["tipo"]

    @property
    def status(self):
        return self._row["status"]

    @property
    def cliente_cnpj(self):
        return self._row.get("cliente_cnpj")

    @property
    def dados(self) -> dict:
        return json.loads(self._row["dados_json"] or "{}")

    def pertence_a(self, cliente_cnpj):
        """True se esta solicitação pertence ao cliente informado (checagem de posse).

        Aceita um CNPJ único (str) ou uma lista de CNPJs — contas cliente podem
        ter várias empresas do mesmo grupo econômico.
        """
        if isinstance(cliente_cnpj, (list, tuple, set)):
            return self.cliente_cnpj in cliente_cnpj
        return self.cliente_cnpj == cliente_cnpj

    def recarregar(self):
        self._row = db_manager.buscar_solicitacao(self.id)
        return self

    # -- ações ------------------------------------------------------------
    def avancar(self, novo_status, forcar=False):
        """Move a solicitação para `novo_status`, validando a transição.

        `forcar=True` pula a validação (usar só em correções manuais/admin).
        """
        if not forcar and not workflow.transicao_valida(self.bloco, self.status, novo_status):
            permitidos = workflow.proximos_status_possiveis(self.bloco, self.status)
            raise TransicaoInvalidaError(
                f"Não é possível ir de '{self.status}' para '{novo_status}'. "
                f"Próximos status válidos: {permitidos}"
            )
        db_manager.atualizar_status(self.id, novo_status)
        self.recarregar()
        return self

    def atualizar_dados(self, novos_dados: dict, mesclar=True):
        dados_finais = {**self.dados, **novos_dados} if mesclar else novos_dados
        db_manager.atualizar_dados(self.id, dados_finais)
        self.recarregar()
        return self

    def validar(self, etapa, aprovado, aprovado_por=None, comentario=None):
        """Registra uma aprovação/reprovação humana (triagem, aprovação 1/2/3...)."""
        db_manager.registrar_validacao(
            self.id, etapa, aprovado, aprovado_por=aprovado_por, comentario=comentario
        )

    def historico_validacoes(self):
        return db_manager.listar_validacoes(self.id)

    def anexos(self):
        return db_manager.listar_anexos(self.id)

    def registrar_erro(self, modulo, mensagem):
        db_manager.registrar_erro(modulo, mensagem, solicitacao_id=self.id)

    def __repr__(self):
        return f"<Solicitacao #{self.id} {self.bloco}/{self.tipo} status={self.status}>"
