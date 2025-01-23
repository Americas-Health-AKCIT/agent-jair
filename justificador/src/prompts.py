RAG_PROMPT = """
ID do Item: {ID_ITEM}
Classificação: {DS_CLASSIFICACAO_1}
Descrição do Item: {DS_ITEM}
"""

PROMPT_RECUSADO = """
Classificação: {DS_CLASSIFICACAO_1}
Descrição do Item: {DS_ITEM}

Documentos relevantes:
{DOCS_RELEVANTES}

Dados do paciente:
{DADOS_PACIENTE}
Com base nos documentos acima e nos dados do paciente, justifique por que esse item pode ter sido recusado:
"""

PROMPT_AUTORIZADO = """
Classificação: {DS_CLASSIFICACAO_1}
Descrição do Item: {DS_ITEM}

Documentos relevantes:
{DOCS_RELEVANTES}

Dados do paciente:
{DADOS_PACIENTE}
Com base nos documentos acima e nos dados do paciente, justifique por que esse item pode ter sido autorizado:
"""