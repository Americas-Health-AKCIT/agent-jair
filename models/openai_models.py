from langchain_openai import ChatOpenAI
from config.config import settings

def gpt_4o(prompt):
    llm = ChatOpenAI(model="gpt-4o", api_key=settings.openai_api_key)
    return llm.invoke(prompt).content

def gpt_4o_mini(prompt):
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)
    return llm.invoke(prompt).content
