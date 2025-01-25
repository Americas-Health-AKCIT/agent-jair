from langchain_openai import ChatOpenAI
import pandas as pd

from justificador.src.rag import retrival_item
from justificador.src.prompts import JUSTIFICATIVA_PROMPT
from config.config import settings

def justificador(id_item, item_info, paciente_info, status=False):

    llm = ChatOpenAI(model="gpt-4o",  temperature=0.1, api_key=settings.openai_api_key)

    rag_result = retrival_item(id_item, item_info)
    
    docs = ""
    fontes = {}
    if rag_result:
        for idx, result in enumerate(rag_result, start=1):
            docs += result[0].page_content + "\n"
            fontes[f"Fonte {idx}"] = result[0].page_content


    if status:
        formatted_prompt = JUSTIFICATIVA_PROMPT.format(DS_CLASSIFICACAO_1=item_info['DS_CLASSIFICACAO_1'], DS_ITEM=item_info['DS_ITEM'], DOCS_RELEVANTES=docs, DADOS_PACIENTE=paciente_info, DECISAO="autorizado")
    else:
        formatted_prompt = JUSTIFICATIVA_PROMPT.format(DS_CLASSIFICACAO_1=item_info['DS_CLASSIFICACAO_1'], DS_ITEM=item_info['DS_ITEM'], DOCS_RELEVANTES=docs, DADOS_PACIENTE=paciente_info, DECISAO="recusado")
    response = llm.invoke(formatted_prompt)

    return response.content, fontes

