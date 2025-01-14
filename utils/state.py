import os
import pandas as pd
path_file = os.path.dirname(__file__)
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.documents import Document

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

import dotenv
dotenv.load_dotenv()


class STATE_CLASS():
    """
        Classe para colocar todas as necessidades das requisições
    """
    def __init__(self):   
        # self._init_vector_store()
        # self.retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 1})
        self.DADOS_CSV_LIST = [] # buffer dos dados quando utilizar offline

        if os.path.exists(os.environ.get("REQUISICOES_ADRESS_OR_PATH",None)):
            # carregar os dados a partir do arquivo csv
            if len(self.DADOS_CSV_LIST) == 0:
                self.load_offline_data()
                
    
    def load_offline_data(self):
        """
            Função para carregar os dados de requisição a partir de arquivos csv
            
            Returns: Generator[pd.DataFrame]: lista contendo os dataframes:
                    0: dados_requisicao
                    1: dados_item
                    2: dados_prestador
                    3: dados_beneficiario
                    4: dados_requisicao_item
        """
        
        data_path = os.environ.get("REQUISICOES_ADRESS_OR_PATH", None)
        print('carregando dados de ', data_path)

        csv_files =  ["OMNI_DADOS_REQUISICAO.csv",
                    "OMNI_DADOS_ITEM.csv",
                    "OMNI_DADOS_PRESTADOR.csv",
                    "OMNI_DADOS_BENEFICIARIO.csv",
                    "OMNI_DADOS_REQUISICAO_ITEM.csv"
                    ]
        
        self.DADOS_CSV_LIST = []
        for file in csv_files:
            path_csv = os.path.join(data_path, file)
            print(path_csv)
            if not os.path.exists(path_csv):
                print(path_csv)
                raise FileNotFoundError(f'Arquivo {file} não encontrado, por favor verifique a variável de ambiente "REQUISICOES_ADRESS_OR_PATH')
            
            self.DADOS_CSV_LIST.append(pd.read_csv(path_csv, encoding='latin1'))
            #yield pd.read_csv(path_csv, encoding='latin1')

 
#     def _init_vector_store(self, data_path=None):
#         if data_path is None:
#             data_path = os.environ.get("DATA_PATH", None)
#             if data_path is None:
#                 raise ValueError("DATA_PATH não foi definido, defina um valor de variável de ambiente")
#             
#         vectorstore_path = os.path.join(data_path,"vectorstore")
# 
#         # Tenta carregar o vetorstore salvo
#         self.vectorstore = None
#         if os.path.exists(vectorstore_path):
#             self.vectorstore = FAISS.load_local(vectorstore_path, OpenAIEmbeddings(), allow_dangerous_deserialization=True)
#         else:            
#             
#             
#             #loader = PyPDFLoader(os.path.join(data_path,"manual_auditoria.pdf"))
#             #loader = PyPDFLoader(os.path.join(data_path,"manual_auditoria_V.11.pdf"))
#             print('data_path',data_path)
#             # import Document class from langchain_community
#             
#             
#             
#             df = pd.read_csv(os.path.join(data_path,"merged_09_10_2024.csv"))
#             
#             docs_text = df['conteudo'].values
# 
#             docs = []
#             for i in range(len(df)):
#                 docs.append(Document(page_content=df["conteudo"][i], metadata=eval(df["metadata"][i])))
#             # transform in documents
#             
#             # Cria o vetorstore
#             print('Criando o vetorstore...')
#             self.vectorstore = FAISS.from_documents(documents=docs, embedding=OpenAIEmbeddings())
#             print('Salvando o vetorstore...')
#             # Salva o vetorstore
#             self.vectorstore.save_local(vectorstore_path)