from langchain_openai import ChatOpenAI
import pandas as pd

from justificador.src.rag import retrival_item
from justificador.src.prompts import PROMPT_RECUSADO, PROMPT_AUTORIZADO

def justificador(id_item, item_info, paciente_info, status=False):

    llm = ChatOpenAI(model="gpt-4o",  temperature=0.1)

    rag_result = retrival_item(id_item, item_info)
    
    docs = ""
    if rag_result:
        for result in rag_result:
            docs += result[0].page_content + "\n"

    if status:
        formatted_prompt = PROMPT_AUTORIZADO.format(DS_CLASSIFICACAO_1=item_info['DS_CLASSIFICACAO_1'], DS_ITEM=item_info['DS_ITEM'], DOCS_RELEVANTES=docs, DADOS_PACIENTE=paciente_info)
    else:
        formatted_prompt = PROMPT_RECUSADO.format(DS_CLASSIFICACAO_1=item_info['DS_CLASSIFICACAO_1'], DS_ITEM=item_info['DS_ITEM'], DOCS_RELEVANTES=docs, DADOS_PACIENTE=paciente_info)
    response = llm.invoke(formatted_prompt)

    return response.content

