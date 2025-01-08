import streamlit as st
import os,time
import ast
import dotenv
dotenv.load_dotenv()
from langchain_openai import ChatOpenAI
from prompt import prompt, prompt_deicider_sim_ou_nao
from langchain_openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, ValidationError
import pandas as pd
from datetime import datetime
from utils.state import STATE_CLASS
from openai import OpenAI
from models._models import run_prompt


# Classe que define o JSON dos dados dos CSVs
class ItemModel(BaseModel):
    nome_do_item: str = Field(..., alias="Nome do Item")
    codigo_correspondente_ao_item: str = Field(..., alias="Código correspondente ao item")
    situacao: str = Field(..., alias="Situação")
    justificativa: str = Field(..., alias="Justificativa")


# Função que retorna os códigos dos itens da requisição
def get_item_id_codes(verbose:bool = False):

    source_files = os.path.join('data') 
    source_files = os.listdir(source_files)
    source_files = [file for file in source_files if file.endswith('_codes.txt')]
    source_files = [os.path.join('data',file)  for file in source_files ]
    
    # Read contents of each _codes.txt file and append to all_codes list
    all_codes_set = set()
    for txt_file_path in source_files:
        #txt_file_name = os.path.splitext(file_name)[0] + '_codes.txt'  # Construct the txt file name
        #txt_file_path = os.path.join('data', txt_file_name)  # Assuming files are in the 'data' directory
        
        if verbose:
            print(f'Txt File Path: {txt_file_path}')

        if os.path.exists(txt_file_path):
            with open(txt_file_path, 'r') as file:
                codes_list = ast.literal_eval(file.read().strip())
                all_codes_set.update(codes_list)
        else:
            print("There are no codes in the file, therefore there is no txt.")
            return [0]


    # Transformando elementos dentro da lista de string para int
    all_codes = list(all_codes_set)
    all_codes = [int(code) for code in all_codes]

    return all_codes


# Função que retorna a decisão final do assistente
def return_yes_no_decision(API_RESPONSE):
    top_two_logprobs = API_RESPONSE.choices[0].logprobs.content[0].top_logprobs
    for item in top_two_logprobs:
        print(item.token)
        if item.token in ['sim', 'Sim', 'Sí', 'SIM', ' Sim']:
            return "AUTORIZADO"
        if item.token in ['não', 'Não', 'No']:
            return "RECUSADO"
        if item.token in ['ins', 'Ins', 'In', 'Insuficiente', 'Insuficient', 'Insufficient', 'INSUFICIENTE']:
            return "NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO"
    raise ValueError(f"Não foi possível encontrar um token representativo: {str([item.token for item in top_two_logprobs])}")


# Função para o agente processar a requisição 
def process_requisition(state: STATE_CLASS, resumo, custom_rag_prompt, custom_yes_no_prompt, llm, client_openai, verbose: bool = False):
    items_results = []
    fontes_dict = []
    
    all_codes = get_item_id_codes(verbose)
    # print("Resumo Debug", resumo)

    if resumo == {'Error': 'REQUISICAO_ID not found'}:
        raise ValueError("Não existe requisição com esse ID")

    for item_id, item_description in resumo['Descrição dos procedimentos'].items(): # para cada item
        item_resumo = resumo.copy()
        item_resumo['Descrição dos procedimentos'] = {item_id: item_description}
        
                
        item = {'Código correspondente ao item':item_id, 
                'description':item_description,
                'document': [],
                'justificativa': None,
                
                }
        
        ###############################################
        ### RAG  - Gerando o contexto de cada item  ###
        ###############################################
        
        rag_result = state.retriever.invoke(str(item_description))
        rag_text = format_docs(rag_result)
        
        item['document'] = []  # Inicializa a lista de fontes para o item
        for doc in rag_result:
            fonte = {
                #"Documento": doc.page_content,
                #"Página":    doc.metadata["page"],
                "Trecho":    doc.page_content,
            }
            item['document'].append(fonte)
        
        item['document'] = rag_result    
        
        if verbose:
            print(f'Current Item ID: {item_id}')
            print(f'All Codes: {all_codes}')
            print(f'Item ID found') if item_id in all_codes else print(f'Item ID not found')
        
        if item_id in all_codes or all_codes == [0]:
            ###############################################################################
            ### PROMPT 1  - Gerando um motivo para decidir se o item é aprovado ou não  ###
            ###############################################################################

            #prompt customizado
            prompt = custom_rag_prompt.invoke({"context":rag_text, "question": str(item_resumo)}).text

            # passa o prompt para o LLM
            ouput_llm_text = run_prompt(prompt)
            item['analysis'] =  ouput_llm_text
    
    
            ##########################################################################
            ### PROMPT 2  - Dado o motivo, decidir se deve ser aceito ou recusado  ### 
            ##########################################################################

            prompt = custom_yes_no_prompt.invoke(item).text
            
            tentativas = 0
            while True:
                try:
                    API_RESPONSE = client_openai.chat.completions.create(messages=[{"role": "user", "content": prompt}],
                                                                    model="gpt-4o-mini",
                                                                    logprobs=True,
                                                                    top_logprobs=20,
                                                                    max_tokens=1,
                                                                    seed=0,
                                                                    )
                    break
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    print("tentando nova chamada ....")
                    tentativas += 1
                    if tentativas == 10:
                        raise Exception("Não foi possível chamar a API da OpenAi com o modelo GPT-4O-mini")
                    
            item['Situação'] = return_yes_no_decision(API_RESPONSE)
        
        else:
            item['Situação'] = "NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO"
            item['analysis'] = 'Item não encontrado nos DOCUMENTOS, portanto não há como fazer uma análise. Porém, o assistente procurou sobre o assunto nos DOCUMENTOS e você pode conferir o que ele achou abaixo, na aba de "fontes".'
                
        items_results.append(item)  # Collect the result for each item
        
        
        
    # Combine all the individual item results into a single JSON list
    for item in items_results:
        fontes_dict.append({item_description: item['document']})

    return {"items": items_results} , fontes_dict


# Função para formatar documentos
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

if __name__ == "__main__":
    # Execução do código simples para usar de referência

    client_openai = OpenAI()
    
    path_file = os.path.dirname(__file__)
    json_output_parser = JsonOutputParser(pydantic_object=ItemModel)
    llm = ChatOpenAI(model="gpt-4o")

    custom_rag_prompt = PromptTemplate(input_variables=["context", "question"], template=prompt)
    custom_yes_no_prompt = PromptTemplate(input_variables=["description", "analysis"], template=prompt_deicider_sim_ou_nao)

    
    def get_state():
        return STATE_CLASS()

    state = get_state()


    rag_chain = (
        {"context": state.retriever | format_docs, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | json_output_parser
    )
    
    from utils.get_requisition_details import get_requisition_details

    # resumo = get_requisition_details(182541, state) # Req do sample antigo
    resumo = get_requisition_details(41991240, state) # Req do sample de agosto
    final_output , fontes_dict = process_requisition(state=state, resumo=resumo, custom_rag_prompt=custom_rag_prompt, custom_yes_no_prompt=custom_yes_no_prompt, llm=llm, client_openai=client_openai)

    print("Resumo: ", resumo)
    print("\n\n\nFinal output: ", final_output)
