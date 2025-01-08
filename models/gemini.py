from langchain_google_genai import ChatGoogleGenerativeAI
import dotenv
dotenv.load_dotenv()

def gemini_flash(prompt):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    return llm.invoke(prompt).content