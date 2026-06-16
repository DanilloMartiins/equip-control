from thefuzz import fuzz

SINONIMOS = {
    'codigo': [
        'TX_NUM_EQUIPAMENTO', 'Chave Primária', 'Código SAP PM Eq.',
        'Equipamento SAP PM', 'idSAP', 'Código', 'CodigoAtivoConcessionaria',
        'NUMERO_SGPMR', 'Número SGPMR', 'Equipamento', 'NumeroOperacional',
        'Num_Operacional', 'N�mero SGPMR',
        'C�digo SAP PM Eq.', 'codigo',
        'EQUIPAMENTOS_PM',
    ],
    'regional': [
        'Agente', 'Região', 'Regional', 'REGIAO', 'Regi�o',
    ],
    'tipo': [
        'Entidade', 'Tipo de Equipamento SAP', 'Tipo Equipamento',
        'TIPO_EQUIPAMENTO_DO_SAP', 'Tipo de Equipamento BQ',
        'TIPO_EQUIPAMENTO', 'TipoCorrente', 'Tipo_Corrente',
        'Tipo de Equipamento SGBDIT', 'TIPO_EQUIPAMENTO_DO_SGBDIT',
    ],
    'fabricante': [
        'Fabricante', 'NOME_FABRICANTE', 'Fabricante_Tipo',
    ],
    'modelo': [
        'Modelo', 'Número modelo', 'N�mero modelo',
        'Norma_especificacao', 'NormaEspecificacao',
    ],
    'numero_serie': [
        'Número de Série', 'Nº série', 'Nº s�rie', 'N�mero de S�rie',
        'NumeroPatrimonio', 'N�mero de S�rie',
        'numero_serie', 'número_serie',
        'N� s�rie', 'Nº s�rie',
    ],
    'local_instalacao': [
        'Local de Instalação', 'Loc.instalação', 'Local de Instala��o',
        'LOCALIZACAO', 'Localização', 'LocalizacaoNomeEquipamento',
        'Local de Instala��o', 'Loc.instala��o',
    ],
    'idbdit': [
        'idbdit', 'IDBDIT', 'IdBDIT', 'Ident_Equip_Def_ONS',
        'IdBDITSubestacao',
    ],
    'data_cadastro': [
        'Data de Cadastro', 'Data de cadastro', 'Data_cadastro',
        'Data de atualização', 'Data de atualiza��o', 'DATA_ATUALIZACAO',
        'Data de Entrada em Opera��o', 'DataEntradaOperacaoComercial',
    ],
    'data_solicitacao': [
        'Data de Solicitação de Envio', 'Data Sol. ATVAPT',
        'Data Conclusão Tez&Tez', 'Dt.entr.serviço', 'Dt.entr.servi�o',
        'Data de Entrada em Operação', 'DataFabricacao',
        'Entrada_Operacao_Comercial',
    ],
    'status': [
        'Status', 'Status Usuário', 'Status Usu�rio', 'STATUS_DA_ANALISE_DE_CADASTRO_EQUIP',
        'Status_Usuario', 'Status_Sistema',
    ],
    'sgpmr': [
        'NUMERO_SGPMR', 'Número SGPMR', 'N�mero SGPMR',
    ],
}

CAMPO_PADRAO = {
    'codigo': 'codigo',
    'regional': 'regional',
    'tipo': 'tipo',
    'fabricante': 'fabricante',
    'modelo': 'modelo',
    'numero_serie': 'numero_serie',
    'local_instalacao': 'local_instalacao',
    'idbdit': 'idbdit',
    'data_cadastro': 'data_cadastro',
    'data_solicitacao': 'data_solicitacao',
    'status': 'status',
}

def identificar_colunas(cabecalhos):
    """
    Recebe uma lista de strings (cabeçalhos da planilha)
    e retorna um dict {campo_banco: indice_coluna}
    """
    mapping = {}
    usados = set()

    for campo_db, sinonimos in SINONIMOS.items():
        melhor_score = 0
        melhor_idx = None

        for i, cab in enumerate(cabecalhos):
            if i in usados:
                continue
            cab_str = str(cab).strip() if cab else ''
            if not cab_str:
                continue

            for sino in sinonimos:
                score = fuzz.ratio(cab_str.lower(), sino.lower())
                if score > melhor_score:
                    melhor_score = score
                    melhor_idx = i

        if melhor_score >= 70 and melhor_idx is not None:
            mapping[campo_db] = melhor_idx
            usados.add(melhor_idx)

    return mapping


def mapear_para_insert(linha, mapping, headers_originais):
    """
    Converte uma linha da planilha em dict pra INSERT,
    usando o mapping {campo_db: indice_coluna}
    """
    dados = {}
    for campo, idx in mapping.items():
        val = linha[idx] if idx < len(linha) else None
        if val is not None:
            if isinstance(val, float) and val == int(val):
                val = str(int(val))
            else:
                val = str(val).strip()
        dados[campo] = val

    return dados
