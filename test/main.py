import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
import dotenv
dotenv.load_dotenv()
import pandas as pd
from app import get_requisition_details, process_requisition, state
import tqdm
import datetime
import json
from gen_graph import gen_graph
from prompt import prompt, prompt_deicider_sim_ou_nao

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI
client_openai = OpenAI()


def write_readme(acuracia_geral, percent_without_context,  qtd_itens, dashboard_path, modelo):
    print("O Teste finalizou, você gostaria de adicionar algum comentário?")
    try:
        comentario = input()
    except:
        comentario = ""
        
    #| Data | qtd. de itens das Amostras | modelo | Acurácia| % sem contexto | Comentário |
    # | ---- |      ----------------      |   ---- |   ----  |       ----     |   -------  | 

    dashboard_path = dashboard_path.replace('./test/','./')
    
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    text_to_write = f"""\n| {date} | {qtd_itens} | {modelo} | {acuracia_geral} | {percent_without_context} | {comentario} | [Dashboard]({dashboard_path}) |"""
    
    with open('./test/README.md', 'a') as f:
        # append to the file
        f.write(text_to_write)

def run(amostra_path = 'sample_100.csv', modelo='', verbose=False, folder_to_save="./test/tests/", teste_para_continuar=''):
    # folder to save logs
    last_requisition = None
    
    if teste_para_continuar == '':
        folder = os.path.join(folder_to_save, 'test_'+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        
    else:
        folder = os.path.join(folder_to_save, teste_para_continuar)
        # se existe result.csv
        if os.path.exists(os.path.join(folder,'result.csv')):
            df_tmp = pd.read_csv(os.path.join(folder,'result.csv'))
            last_requisition = df_tmp['ID_REQUISICAO'].values[-1]
            print('Retornando a ultima requisiçao:',last_requisition)
        else:
            raise Exception("Result.csv nao encontrado, inicie um novo teste!")
        
    folder_req = os.path.join(folder, 'response_llm')
    os.makedirs(folder,exist_ok=True)
    os.makedirs(folder_req,exist_ok=True)
    
    description_test = f""" Amostra: {amostra_path}
                               Data: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                        """
                        
    with open(os.path.join(folder, 'README.MD'), 'w') as f:
        f.write(description_test)
        
    
    # load dataframes
    dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = state.DADOS_CSV_LIST

    # load amostra dataframe
    df_amostra = pd.read_csv(amostra_path)
    
    
    df_result = { 'ID_REQUISICAO':[],
                  'ID_ITEM':[],
                  'STATUS': [],
                  'y_hat': [],
                }
    if last_requisition is not None:
        # carrega o df_result
        df_tmp = df_tmp[df_tmp.ID_REQUISICAO != last_requisition]
        df_result['ID_REQUISICAO'] = list(df_tmp.ID_REQUISICAO.values)
        df_result['ID_ITEM'] =       list(df_tmp.ID_ITEM.values)
        df_result['STATUS'] =        list(df_tmp.STATUS.values)
        df_result['y_hat'] =         list(df_tmp.y_hat.values)
    
    # Inicializa o modelo OpenAI
    llm = ChatOpenAI(model="gpt-4o")

    # Configura o RAG (Retriever-augmented generation)
    custom_rag_prompt = PromptTemplate(input_variables=["context", "question"], template=prompt)
    custom_yes_no_prompt = PromptTemplate(input_variables=["description", "analysis"], template=prompt_deicider_sim_ou_nao)

    #ID_REQUISICAO,STATUS
    
    quantidade_itens = 10
    
    for _, row in tqdm.tqdm(df_amostra.iterrows(), total=df_amostra.shape[0]):
        id_req = row['ID_REQUISICAO']
        if (last_requisition is not None) and (last_requisition != id_req):
            print('Requisicao ', id_req,' ignorada')
            continue
        
        print("rodando:",id_req)
        
        ith_resumo = get_requisition_details(int(id_req),state)
    
        ith_requisition_items = dados_requisicao_item[dados_requisicao_item['ID_REQUISICAO'] == id_req]
        
        if verbose:
            print(ith_resumo)
        
        def get_cod_item(id_item):        
            item_info = dados_item[dados_item['ID_ITEM'] == id_item]
            id_item_display = item_info['CD_ITEM'].iloc[0]
            return int(id_item_display)
        
        # cria um dicionario com todos os itens da requisição com o label
        ith_requisition_items = { get_cod_item(row['ID_ITEM']): {'label':row['QT_SOLICITADA'] == row['QT_LIBERADA'],
                                                   'y_hat':'Default',
                                                   }
                                 for _, row in ith_requisition_items.iterrows()}

        # chama a API da OpenAI para julgar a requisição
        ith_requistion_label , ith_resition_retriever = process_requisition(state,ith_resumo, custom_rag_prompt, custom_yes_no_prompt, llm, client_openai, verbose)
        
        for i in range(len(ith_requistion_label['items'])):
            ith_requistion_label['items'][i]['document'] = None
                    
        # save  requisition
        for obj,nome in zip([ith_requistion_label], ['llm']):
            with open(os.path.join(folder_req, f'{id_req}_{nome}.json'), 'w') as f:
                json.dump(obj, f)        

        
        if verbose:
            print(ith_requistion_label)
        
        # adiciona no dicionario anterior o label
        for item in ith_requistion_label['items']:
            try:
                cod_item = int(item['Código correspondente ao item'])
                y_hat = item['Situação']
                
                if cod_item not in ith_requisition_items:
                    ith_requisition_items[cod_item] = {'label': 'Item inexistente', 'y_hat': y_hat}
                else:
                    ith_requisition_items[cod_item]['y_hat'] = y_hat
                    
            except Exception as e:
                print('**Warning  item exception**', e, item)



        for item in ith_requisition_items.keys():
            df_result['ID_REQUISICAO'] += [id_req]
            df_result['ID_ITEM'] += [item]
            df_result['STATUS'] += [ith_requisition_items[item]['label']]
            df_result['y_hat'] += [ith_requisition_items[item]['y_hat']]
    
    

        if verbose:
            print(ith_requisition_items)
        
        #quantidade_itens -= 1
        #if quantidade_itens <= 0:
        #    break
    
        
        #rag_chain(row['ID_REQUISICAO'], row['ID_ITEM'], row['ID_PRESTADOR'], row['ID_BENEFICIARIO'], row['ID_REQUISICAO_ITEM'])
        
        pd.DataFrame(df_result).to_csv(os.path.join(folder,'result.csv'), index=False)
        last_requisition = None
        
    df = pd.DataFrame(df_result)

    filtered_requisicao = dados_requisicao_item[dados_requisicao_item['ID_REQUISICAO'].isin(df['ID_REQUISICAO'])]
    merged_filtered_itens = filtered_requisicao.merge(dados_item, left_on='ID_ITEM', right_on='ID_ITEM', how='inner')[['ID_REQUISICAO','ID_ITEM', 'CD_ITEM', 'DS_TIPO_ITEM']]
    merged_filtered_itens = merged_filtered_itens.drop_duplicates()
    merged_filtered_itens = merged_filtered_itens.drop(columns=['ID_ITEM'])
    merged_filtered_itens = merged_filtered_itens.rename(columns={'CD_ITEM': 'ID_ITEM'})
    final_merged_df = merged_filtered_itens.merge(df, on=['ID_REQUISICAO', 'ID_ITEM'], how='inner')

    acuracia_geral, percent_without_context, qtd_itens = gen_graph(final_merged_df, os.path.join(folder, 'dashboard.png'))
    
    write_readme(acuracia_geral, percent_without_context, qtd_itens,  os.path.join(folder, 'dashboard.png'), modelo)
    
    
        
    #print(df_amostra.head())
    #load_data()
    #print('ok')
    #print(llm)

def redraw():
    dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = state.DADOS_CSV_LIST
    
    tests_path = './test/tests'
    # caminha por todas as pastas
    for folder in os.listdir(tests_path):
        path = os.path.join(tests_path, folder)
        result_path = os.path.join(path, 'result.csv')
        
        if os.path.isdir(path) and os.path.exists(result_path):
            print(result_path)
            df = pd.read_csv(result_path)

            filtered_requisicao = dados_requisicao_item[dados_requisicao_item['ID_REQUISICAO'].isin(df['ID_REQUISICAO'])]
            merged_filtered_itens = filtered_requisicao.merge(dados_item, left_on='ID_ITEM', right_on='ID_ITEM', how='inner')[['ID_REQUISICAO','ID_ITEM', 'CD_ITEM', 'DS_TIPO_ITEM']]
            merged_filtered_itens = merged_filtered_itens.drop_duplicates()
            merged_filtered_itens = merged_filtered_itens.drop(columns=['ID_ITEM'])
            merged_filtered_itens = merged_filtered_itens.rename(columns={'CD_ITEM': 'ID_ITEM'})
            final_merged_df = merged_filtered_itens.merge(df, on=['ID_REQUISICAO', 'ID_ITEM'], how='inner')

            acuracia_geral, percent_without_context, qtd_itens = gen_graph(final_merged_df, os.path.join(path, 'dashboard.png'))
            
            write_readme(acuracia_geral, percent_without_context, qtd_itens,  os.path.join(path, 'dashboard.png'), 'GPT-4o')
    
    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--amostra', type=str, default='./test/sample_100.csv', help='Path to the sample dataframe file')
    parser.add_argument('--continue_test',type=str, default='', help='if exists a test, start with test_yyy-mm-DD....')
    args = parser.parse_args()
    model_name = os.getenv("JUDGE_MODEL",None)
    run(args.amostra, model_name, teste_para_continuar=args.continue_test)
