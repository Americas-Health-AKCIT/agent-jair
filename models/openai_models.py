from langchain_openai import ChatOpenAI
import dotenv
dotenv.load_dotenv()

def gpt_4o(prompt):
    llm = ChatOpenAI(model="gpt-4o")
    return llm.invoke(prompt).content

def gpt_4o_mini(prompt):
    llm = ChatOpenAI(model="gpt-4o-mini")
    return llm.invoke(prompt).content
