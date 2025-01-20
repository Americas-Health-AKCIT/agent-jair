from justificador.src.prompts import RAG_PROMPT

from langchain_qdrant import QdrantVectorStore
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

import os
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def initialize_qdrant_vector_store():
    qdrant = QdrantVectorStore.from_existing_collection(
    embedding= OpenAIEmbeddings(model="text-embedding-3-large"),
    collection_name="documents_jair",
    api_key= QDRANT_API_KEY,
    url="https://059372fd-0731-4343-a57e-e613adc7c768.us-west-2-0.aws.cloud.qdrant.io:6333/",)
    return qdrant


def retrival_item(id_item, item_info):

    qdrant = initialize_qdrant_vector_store()

    if item_info:

        rag_prompt = PromptTemplate(
        input_variables=["ID_ITEM", "DS_ITEM", "DS_CLASSIFICACAO_1"],
        template=RAG_PROMPT)

        formatted_prompt = rag_prompt.format(ID_ITEM=id_item, DS_ITEM=item_info['DS_ITEM'], DS_CLASSIFICACAO_1=item_info['DS_CLASSIFICACAO_1'])

        return qdrant.similarity_search_with_score(formatted_prompt, k=2)
    else:
        return None
    