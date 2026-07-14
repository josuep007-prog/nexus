"""
core/tipos_solicitacao.py
----------------------------
Registro central de todos os tipos de solicitação do sistema: qual bloco
pertence, quais campos o formulário deve mostrar, e qual função de
`regras/regras_clt.py` valida os dados.

Isso existe pra não precisar criar uma tela (arquivo .html) nova pra cada
tipo de solicitação — o formulário web genérico (`web/templates/
solicitacao_generica.html`) lê esse registro e se monta sozinho.

Tipos que têm fluxo próprio e mais completo (admissão, atestado) continuam
com suas telas dedicadas — aqui eles aparecem só com `rota_especial`
apontando pra essa tela, pro catálogo conseguir listar tudo num lugar só.
"""

from regras import regras_clt

# Tipos de campo suportados pelo formulário genérico: text, textarea, number, date, select, checkbox


REGISTRO_BLOCO1 = {
    "ferias": {
        "titulo": "Férias",
        # Alinhado à solicitação "Cálculo de Férias" do Onvio Portal do Cliente.
        # Cada campo com chave "onvio" é repassado à solicitação equivalente no
        # Onvio; os sem "onvio" (ex.: saldo_dias_direito) são só do nexus, para a
        # conferência CLT antes da validação humana.
        "onvio_solicitacao": "Cálculo de Férias",
        "campos": [
            {"nome": "empregado_nome", "rotulo": "Empregado", "tipo": "text", "obrigatorio": True,
             "onvio": "Empregado"},
            {"nome": "empregado_cpf", "rotulo": "CPF do empregado", "tipo": "text", "obrigatorio": False,
             "onvio": "Empregado (localização por CPF)"},
            {"nome": "data_inicio_gozo", "rotulo": "Data de início do gozo", "tipo": "date", "obrigatorio": True,
             "onvio": "Data de início do gozo"},
            {"nome": "dias_solicitados", "rotulo": "Dias de gozo", "tipo": "number", "obrigatorio": True,
             "onvio": "Dias de gozo"},
            {"nome": "abono_pecuniario", "rotulo": "Pagar abono pecuniário (vender 1/3)", "tipo": "select",
             "obrigatorio": False, "opcoes": ["nao", "sim"], "onvio": "Pagar abono pecuniário"},
            {"nome": "adiantar_13", "rotulo": "Adiantar 1ª parcela do 13º salário", "tipo": "select",
             "obrigatorio": False, "opcoes": ["nao", "sim"], "onvio": "Adiantar a 1ª parcela do 13º salário"},
            # O saldo de dias de direito NÃO é mais digitado: vem do Dossiê do
            # Empregado (conferência automática em modules/dossie.py).
            {"nome": "descricao", "rotulo": "Observações", "tipo": "textarea", "obrigatorio": False,
             "onvio": "Descrição"},
        ],
        "validar": regras_clt.validar_ferias_dados,
        "rota_especial": None,
    },
    "rescisao": {
        "titulo": "Rescisão",
        # Alinhado à solicitação "Cálculo de Rescisão" do Onvio Portal do Cliente.
        "onvio_solicitacao": "Cálculo de Rescisão",
        "campos": [
            {"nome": "empregado_nome", "rotulo": "Empregado", "tipo": "text", "obrigatorio": True,
             "onvio": "Empregado"},
            {"nome": "empregado_cpf", "rotulo": "CPF do empregado", "tipo": "text", "obrigatorio": False,
             "onvio": "Empregado (localização por CPF)"},
            {"nome": "tipo_rescisao", "rotulo": "Motivo da rescisão", "tipo": "select", "obrigatorio": True,
             "opcoes": ["sem_justa_causa", "pedido_demissao", "justa_causa", "acordo_comum", "termino_contrato"],
             "onvio": "Motivo da rescisão"},
            {"nome": "data_demissao", "rotulo": "Data de demissão", "tipo": "date", "obrigatorio": True,
             "onvio": "Data de demissão"},
            {"nome": "data_aviso_previo", "rotulo": "Data do aviso prévio", "tipo": "date", "obrigatorio": False,
             "onvio": "Data do aviso prévio"},
            {"nome": "tipo_aviso_previo", "rotulo": "Tipo do aviso prévio", "tipo": "select", "obrigatorio": False,
             "opcoes": ["trabalhado", "indenizado", "dispensado"], "onvio": "Tipo do aviso prévio"},
            {"nome": "data_admissao", "rotulo": "Data de admissão (conferência CLT)", "tipo": "date",
             "obrigatorio": True},
            {"nome": "descricao", "rotulo": "Observações", "tipo": "textarea", "obrigatorio": False,
             "onvio": "Descrição"},
        ],
        "validar": regras_clt.validar_rescisao_dados,
        "rota_especial": None,
    },
    "alteracao_cadastral": {
        "titulo": "Alteração cadastral",
        "campos": [
            {"nome": "campo_alterado", "rotulo": "Campo alterado", "tipo": "text", "obrigatorio": True},
            {"nome": "novo_valor", "rotulo": "Novo valor", "tipo": "text", "obrigatorio": True},
        ],
        "validar": None,
        "rota_especial": None,
    },
    "advertencia": {
        "titulo": "Advertência",
        "campos": [
            {"nome": "tipo_advertencia", "rotulo": "Tipo", "tipo": "select", "obrigatorio": True,
             "opcoes": ["verbal", "escrita"]},
            {"nome": "motivo", "rotulo": "Motivo", "tipo": "textarea", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_advertencia,
    },
    "suspensao": {
        "titulo": "Suspensão disciplinar",
        "campos": [
            {"nome": "motivo", "rotulo": "Motivo", "tipo": "textarea", "obrigatorio": True},
            {"nome": "dias_suspensao", "rotulo": "Dias de suspensão", "tipo": "number", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_suspensao,
    },
    "alteracao_beneficio": {
        "titulo": "Alteração de benefício (VT/VR/plano)",
        "campos": [
            {"nome": "tipo_beneficio", "rotulo": "Benefício", "tipo": "text", "obrigatorio": True,
             "placeholder": "Ex: Vale-transporte, Vale-refeição, Plano de saúde"},
            {"nome": "acao", "rotulo": "Ação", "tipo": "select", "obrigatorio": True,
             "opcoes": ["incluir", "alterar", "excluir"]},
            {"nome": "detalhes", "rotulo": "Detalhes", "tipo": "textarea", "obrigatorio": False},
        ],
        "validar": regras_clt.validar_alteracao_beneficio,
    },
    "decimo_terceiro": {
        "titulo": "13º salário",
        "campos": [
            {"nome": "parcela", "rotulo": "Parcela", "tipo": "select", "obrigatorio": True, "opcoes": ["1", "2"]},
            {"nome": "competencia", "rotulo": "Competência (ano)", "tipo": "text", "obrigatorio": True, "placeholder": "2026"},
        ],
        "validar": regras_clt.validar_decimo_terceiro,
    },
    "folha_adiantamento": {
        "titulo": "Folha de adiantamento",
        "campos": [
            {"nome": "competencia", "rotulo": "Competência", "tipo": "text", "obrigatorio": True, "placeholder": "07/2026"},
            {"nome": "percentual", "rotulo": "Percentual do adiantamento (%)", "tipo": "number", "obrigatorio": False, "placeholder": "40"},
            {"nome": "observacoes_adiantamento", "rotulo": "Observações", "tipo": "textarea", "obrigatorio": False},
        ],
        "validar": regras_clt.validar_folha_adiantamento,
    },
    "rpa": {
        "titulo": "RPA — Recibo de Pagamento a Autônomo",
        "campos": [
            {"nome": "prestador_nome", "rotulo": "Nome do prestador (autônomo)", "tipo": "text", "obrigatorio": True},
            {"nome": "prestador_cpf", "rotulo": "CPF do prestador", "tipo": "text", "obrigatorio": True, "placeholder": "000.000.000-00"},
            {"nome": "valor_servico", "rotulo": "Valor do serviço (R$)", "tipo": "number", "obrigatorio": True, "placeholder": "1500.00"},
            {"nome": "descricao_servico", "rotulo": "Descrição do serviço", "tipo": "textarea", "obrigatorio": True},
            {"nome": "competencia", "rotulo": "Competência / data", "tipo": "text", "obrigatorio": True, "placeholder": "07/2026"},
        ],
        "validar": regras_clt.validar_rpa,
    },
    "transferencia_local": {
        "titulo": "Transferência de local de trabalho",
        "campos": [
            {"nome": "novo_local", "rotulo": "Novo local", "tipo": "text", "obrigatorio": True},
            {"nome": "data_transferencia", "rotulo": "Data da transferência", "tipo": "date", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_transferencia_local,
    },
    "alteracao_jornada": {
        "titulo": "Alteração de jornada",
        "campos": [
            {"nome": "nova_jornada_semanal", "rotulo": "Nova jornada semanal (horas)", "tipo": "number", "obrigatorio": True},
            {"nome": "motivo", "rotulo": "Motivo", "tipo": "textarea", "obrigatorio": False},
        ],
        "validar": regras_clt.validar_alteracao_jornada,
    },
    "declaracao": {
        "titulo": "Solicitação de declaração",
        "campos": [
            {"nome": "tipo_declaracao", "rotulo": "Tipo de declaração", "tipo": "text", "obrigatorio": True,
             "placeholder": "Ex: vínculo empregatício, tempo de serviço"},
        ],
        "validar": regras_clt.validar_declaracao,
    },
    "ppp": {
        "titulo": "Solicitação de PPP",
        "campos": [
            {"nome": "motivo_solicitacao", "rotulo": "Motivo da solicitação", "tipo": "text", "obrigatorio": True,
             "placeholder": "Ex: aposentadoria, mudança de emprego"},
        ],
        "validar": regras_clt.validar_ppp,
    },
    "cnd": {
        "titulo": "Solicitação de CND",
        "campos": [
            {"nome": "tipo_certidao", "rotulo": "Tipo de certidão", "tipo": "select", "obrigatorio": True,
             "opcoes": ["CRF FGTS", "CNDT (débitos trabalhistas)", "CND Federal (Receita/INSS)"]},
            {"nome": "finalidade", "rotulo": "Finalidade", "tipo": "text", "obrigatorio": True,
             "placeholder": "Ex: licitação, financiamento, exigência de contrato"},
        ],
        "validar": regras_clt.validar_cnd,
    },
    "relatorio_rotina": {
        "titulo": "Relatório de rotina",
        "campos": [
            {"nome": "tipo_relatorio", "rotulo": "Tipo de relatório", "tipo": "text", "obrigatorio": True},
        ],
        "validar": None,
    },
    "folha_sem_variaveis": {
        "titulo": "Fechamento de folha sem variáveis",
        "campos": [
            {"nome": "competencia", "rotulo": "Competência", "tipo": "text", "obrigatorio": True, "placeholder": "07/2026"},
        ],
        "validar": None,
    },
}

REGISTRO_BLOCO2 = {
    "admissao": {
        "titulo": "Admissão",
        "campos": [],
        "validar": None,
        "rota_especial": "nova_admissao",  # tem fluxo dedicado com múltiplos anexos
    },
    "atestado": {
        "titulo": "Atestado",
        "campos": [],
        "validar": None,
        "rota_especial": "novo_atestado",
    },
    "afastamento_inss": {
        "titulo": "Afastamento por INSS (auxílio-doença)",
        "campos": [
            {"nome": "data_inicio", "rotulo": "Data de início do afastamento", "tipo": "date", "obrigatorio": True},
            {"nome": "motivo_afastamento", "rotulo": "Motivo / CID", "tipo": "text", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_afastamento_inss,
    },
    "cat": {
        "titulo": "CAT — Comunicação de Acidente de Trabalho",
        "campos": [
            {"nome": "data_acidente", "rotulo": "Data do acidente", "tipo": "date", "obrigatorio": True},
            {"nome": "data_comunicacao", "rotulo": "Data da comunicação", "tipo": "date", "obrigatorio": True},
            {"nome": "descricao", "rotulo": "Descrição do acidente", "tipo": "textarea", "obrigatorio": False},
        ],
        "validar": regras_clt.validar_cat,
    },
    "admissao_estagiario": {
        "titulo": "Admissão de estagiário",
        "campos": [
            {"nome": "instituicao_ensino", "rotulo": "Instituição de ensino", "tipo": "text", "obrigatorio": True},
            {"nome": "carga_horaria_diaria", "rotulo": "Carga horária diária (h)", "tipo": "number", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_admissao_estagiario,
    },
    "admissao_aprendiz": {
        "titulo": "Admissão de aprendiz",
        "campos": [
            {"nome": "idade", "rotulo": "Idade", "tipo": "number", "obrigatorio": True},
            {"nome": "eh_pcd", "rotulo": "Pessoa com deficiência?", "tipo": "select", "obrigatorio": True,
             "opcoes": ["nao", "sim"]},
        ],
        "validar": regras_clt.validar_admissao_aprendiz,
    },
    "inclusao_dependente": {
        "titulo": "Inclusão de dependente",
        "campos": [
            {"nome": "nome_dependente", "rotulo": "Nome do dependente", "tipo": "text", "obrigatorio": True},
            {"nome": "parentesco", "rotulo": "Parentesco", "tipo": "text", "obrigatorio": True},
            {"nome": "data_nascimento", "rotulo": "Data de nascimento", "tipo": "date", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_dependente,
    },
    "exclusao_dependente": {
        "titulo": "Exclusão de dependente",
        "campos": [
            {"nome": "nome_dependente", "rotulo": "Nome do dependente", "tipo": "text", "obrigatorio": True},
            {"nome": "parentesco", "rotulo": "Parentesco", "tipo": "text", "obrigatorio": True},
            {"nome": "data_nascimento", "rotulo": "Data de nascimento", "tipo": "date", "obrigatorio": True},
        ],
        "validar": regras_clt.validar_dependente,
    },
    "folha_com_variaveis": {
        "titulo": "Lançamento de valores na folha",
        "campos": [
            {"nome": "tipo_valor", "rotulo": "Tipo de valor", "tipo": "select", "obrigatorio": True,
             "opcoes": ["horas_extras", "faltas", "comissao", "adicional_noturno", "dsr", "outro"]},
            {"nome": "valor", "rotulo": "Valor (R$)", "tipo": "number", "obrigatorio": True},
            {"nome": "horas_por_dia", "rotulo": "Horas por dia (se horas extras)", "tipo": "number", "obrigatorio": False},
            {"nome": "competencia", "rotulo": "Competência", "tipo": "text", "obrigatorio": True, "placeholder": "07/2026"},
        ],
        "validar": regras_clt.validar_lancamento_valores_folha,
    },
    "licenca_maternidade": {
        "titulo": "Licença maternidade",
        "campos": [
            {"nome": "data_inicio", "rotulo": "Data de início", "tipo": "date", "obrigatorio": True},
            {"nome": "empresa_cidada", "rotulo": "Empresa aderiu ao Empresa Cidadã?", "tipo": "select", "obrigatorio": False,
             "opcoes": ["nao", "sim"]},
        ],
        "validar": regras_clt.validar_licenca_maternidade,
    },
    "licenca_paternidade": {
        "titulo": "Licença paternidade",
        "campos": [
            {"nome": "data_inicio", "rotulo": "Data de início", "tipo": "date", "obrigatorio": True},
            {"nome": "empresa_cidada", "rotulo": "Empresa aderiu ao Empresa Cidadã?", "tipo": "select", "obrigatorio": False,
             "opcoes": ["nao", "sim"]},
        ],
        "validar": regras_clt.validar_licenca_paternidade,
    },
    "exame_ocupacional": {
        "titulo": "Exame ocupacional (ASO)",
        "campos": [
            {"nome": "tipo_exame", "rotulo": "Tipo de exame", "tipo": "select", "obrigatorio": True,
             "opcoes": ["admissional", "periodico", "demissional", "mudanca_funcao", "retorno"]},
        ],
        "validar": regras_clt.validar_exame_ocupacional,
    },
    "outros": {
        "titulo": "Outros (fora da lista)",
        # Alinhado à "Solicitação Geral" do Onvio Portal do Cliente.
        "onvio_solicitacao": "Solicitação Geral",
        "campos": [
            {"nome": "departamento", "rotulo": "Departamento responsável", "tipo": "text", "obrigatorio": False,
             "placeholder": "Ex: Departamento Pessoal", "onvio": "Departamento responsável pela solicitação"},
            {"nome": "assunto", "rotulo": "Assunto", "tipo": "text", "obrigatorio": True,
             "placeholder": "Resumo do que você precisa", "onvio": "Assunto"},
            {"nome": "descricao", "rotulo": "Descrição", "tipo": "textarea", "obrigatorio": True,
             "placeholder": "Descreva a solicitação com o máximo de detalhes. Se tiver documento, anexe abaixo.",
             "onvio": "Descrição"},
        ],
        "validar": regras_clt.validar_outros,
        "automatizavel": False,  # solicitação livre — só atendimento manual
    },
}


def schema_do_tipo(bloco: str, tipo: str) -> dict:
    registro = REGISTRO_BLOCO1 if bloco == "bloco1" else REGISTRO_BLOCO2
    return registro.get(tipo)


def catalogo_completo():
    """Retorna [(bloco, tipo, schema), ...] pra montar a página de catálogo."""
    itens = [("bloco1", tipo, schema) for tipo, schema in REGISTRO_BLOCO1.items()]
    itens += [("bloco2", tipo, schema) for tipo, schema in REGISTRO_BLOCO2.items()]
    return itens


# ---------------------------------------------------------------------------
# Agrupamento por categoria (só pra organização visual do catálogo web —
# não afeta bloco/workflow/validação, que continuam vindo do registro acima).
# ---------------------------------------------------------------------------
CATEGORIAS = {
    "Admissão e desligamento": ["admissao", "admissao_estagiario", "admissao_aprendiz", "rescisao"],
    "Férias e jornada": ["ferias", "alteracao_jornada", "transferencia_local"],
    "Folha de pagamento": ["folha_sem_variaveis", "folha_com_variaveis", "decimo_terceiro",
                           "folha_adiantamento", "rpa", "alteracao_beneficio"],
    "Afastamentos e saúde": ["afastamento_inss", "cat", "exame_ocupacional", "atestado",
                             "licenca_maternidade", "licenca_paternidade"],
    "Cadastro e dependentes": ["alteracao_cadastral", "inclusao_dependente", "exclusao_dependente"],
    "Disciplinar": ["advertencia", "suspensao"],
    "Documentos e relatórios": ["declaracao", "ppp", "cnd", "relatorio_rotina"],
    "Outros": ["outros"],
}


def catalogo_por_categoria():
    """Retorna [(nome_categoria, [(bloco, tipo, schema), ...]), ...] pra exibição agrupada no catálogo."""
    tipo_para_item = {tipo: (bloco, tipo, schema) for bloco, tipo, schema in catalogo_completo()}
    grupos = []
    for categoria, tipos in CATEGORIAS.items():
        itens = sorted((tipo_para_item[tipo] for tipo in tipos if tipo in tipo_para_item),
                       key=lambda item: item[2]["titulo"])
        if itens:
            grupos.append((categoria, itens))
    return grupos
