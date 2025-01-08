## Arquivo para obter detalhes de requisição
import dotenv,os
import pandas as pd
from datetime import datetime
from utils.state import STATE_CLASS
dotenv.load_dotenv()


### FUNCOES AUXILIARES DA REQUISICAO
# Função para calcular a idade do beneficiario
def calculate_age(birth_year_str, reference_date_str):
    """Calculate age based on birth year and reference date in the format DD/MM/YY."""
    # Convert birth year to integer
    birth_year = int(birth_year_str)
    # Parse the reference date from the format 'DD/MM/YY'
    try:
        reference_date = datetime.strptime(reference_date_str, "%d-%b-%y")
    except:
        reference_date = datetime.strptime(reference_date_str, "%d/%m/%y")
    # Calculate age using the year difference
    age = reference_date.year - birth_year
    return age


# Função para checar a carência do paciente
def check_carencia(carencia):
    """Versão que verifica a coluna carencia"""
    if pd.isna(carencia) or carencia in ['nan', 'NaT']:
        return "Não"
    else:
        return f"Sim (Termina na data {carencia} para o(s) procedimento(s) solicitado(s))"


# Função para determinar a situação contratual do paciente
def determine_contrato(data_cancelamento):
    if pd.isna(data_cancelamento) or data_cancelamento in ['nan', 'NaT']:
        return "Contrato ativo"
    else:
        return f"Contrato cancelado no dia {data_cancelamento}"


###############################################################################
###############################################################################


def get_data_by_adress(requisicao_id:int)->dict:
    adress = os.environ.get("REQUISICOES_ADRESS_OR_PATH", None)
    port = os.environ.get("REQUISICOES_PORT", None)    
    
    # transform em dataframe
    
    
     
    #OMNI_DADOS_REQUISICAO.DT_REQUISICAO,
    #OMNI_DADOS_REQUISICAO.DS_TIPO_GUIA,
    #OMNI_DADOS_REQUISICAO.DS_CARATER_ATENDIMENTO,
    #
    #OMNI_DADOS_BENEFICIARIO.NM_BENEFICIARIO,
    #OMNI_DADOS_BENEFICIARIO.DATA_NASCIMENTO,
    #OMNI_DADOS_BENEFICIARIO.DATA_CANCELAMENTO,
    #OMNI_DADOS_BENEFICIARIO.DATA_INICIO_VIGENCIA,
    #OMNI_DADOS_BENEFICIARIO.DATA_FIM_CARENCIA,
    #
    #OMNI_DADOS_PRESTADOR.NM_PRESTADOR
    
    raise NotImplementedError("Ainda não implementado")

    return dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item



DADOS_CSV_LIST = [] # cache para os dados vindo do CSV


def get_requisition_details(requisicao_id:int, state : STATE_CLASS)->dict:
    
    
    print(os.environ.get("REQUISICOES_ADRESS_OR_PATH",None))
    if os.path.exists(os.environ.get("REQUISICOES_ADRESS_OR_PATH",None)):
        # carregar os dados a partir do arquivo csv
        #if len(state.DADOS_CSV_LIST) == 0:
        #    state.load_offline_data()
            
        dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = state.DADOS_CSV_LIST

    else:
        # carregar os dados a partir do banco de dados
        dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = get_data_by_adress(requisicao_id)
    
    
    
    
    # Pegando o ID da requisição
    requisicao = dados_requisicao[dados_requisicao['ID_REQUISICAO'] == requisicao_id]
    if requisicao.empty:
        return {"Error": "REQUISICAO_ID not found"}

    # Extraindo informações da requisição
    id_beneficiario = requisicao['ID_BENEFICIARIO'].iloc[0]
    print('ID Beneficiario:', id_beneficiario)
    id_prestador = requisicao['ID_PRESTADOR'].iloc[0]
    dt_requisicao = requisicao['DT_REQUISICAO'].iloc[0]
    ds_tipo_guia = requisicao['DS_TIPO_GUIA'].iloc[0]
    ds_carater_atendimento = requisicao['DS_CARATER_ATENDIMENTO'].iloc[0]

    # Pega o beneficiário no df de beneficiarios
    beneficiario = dados_beneficiario[dados_beneficiario['ID_BENEFICIARIO'] == id_beneficiario]
    
    if beneficiario.empty:
        return {"Erro": "Beneficiario não encontrado"}

    # Extraindo informações do beneficiarios
    nome_beneficiario = beneficiario['NM_BENEFICIARIO'].iloc[0]
    data_nascimento = str(beneficiario['DATA_NASCIMENTO'].iloc[0])
    data_cancelamento = beneficiario['DATA_CANCELAMENTO'].iloc[0]
    data_inicio_vigencia = beneficiario['DATA_INICIO_VIGENCIA'].iloc[0]
    carencia = beneficiario['DATA_FIM_CARENCIA'].iloc[0]

    # Calculando a idade, verificando a carência e a situação contratual
    idade = calculate_age(data_nascimento, dt_requisicao)
    carencia = check_carencia(carencia)
    situacao_contratual = determine_contrato(data_cancelamento)

    # Pegando o prestador atribuido a requisição
    prestador = dados_prestador[dados_prestador['ID_PRESTADOR'] == id_prestador]

    if prestador.empty:
        return {"Erro": "Prestador não encontrado"}
    
    # Extraindo informações do beneficiarios
    nome_prestador = prestador['NM_PRESTADOR'].iloc[0]

    # Pegando os itens atribuidos a requisição
    requisicao_items = dados_requisicao_item[dados_requisicao_item['ID_REQUISICAO'] == requisicao_id].copy()

    if requisicao_items.empty:
        return {"Erro": "Items não foram encontrado para essa REQUISICAO_ID"}

    try:
        requisicao_items.loc[:, 'DT_ATUALIZACAO'] = pd.to_datetime(requisicao_items['DT_ATUALIZACAO'], format='%d-%b-%y')
    except:
        requisicao_items.loc[:, 'DT_ATUALIZACAO'] = pd.to_datetime(requisicao_items['DT_ATUALIZACAO'], format='%d/%m/%y')

    requisicao_items = requisicao_items.sort_values(by='DT_ATUALIZACAO')

    descriptions_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']

        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        id_item_display = item_info['CD_ITEM'].iloc[0]
        id_item_display = int(id_item_display)
        
        item_description = dados_item[dados_item['ID_ITEM'] == id_item]['DS_ITEM'].iloc[0]
        if not pd.isna(item_description):
            descriptions_dict[id_item_display] = item_description
        else:
            raise ValueError("Critical Error: No item description found, please check the data")

    item_type_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']

        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        id_item_display = item_info['CD_ITEM'].iloc[0]
        id_item_display = int(id_item_display)
        
        item_type = dados_item[dados_item['ID_ITEM'] == id_item]['DS_TIPO_ITEM'].iloc[0]
        if not pd.isna(item_type):
            item_type_dict[id_item_display] = item_type
        else:
            raise ValueError("Critical Error: No item type found, please check the data")

    specific_item_type_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']

        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        id_item_display = item_info['CD_ITEM'].iloc[0]
        id_item_display = int(id_item_display)
        
        item_type = dados_item[dados_item['ID_ITEM'] == id_item]['DS_CLASSIFICACAO_1'].iloc[0]
        if not pd.isna(item_type):
            specific_item_type_dict[id_item_display] = item_type
        else:
            raise ValueError("Critical Error: No item type found, please check the data")



    # Dict final
    result = {
        "Número da requisição": requisicao_id,
        "Nome do beneficiário": nome_beneficiario,
        "Médico solicitante": nome_prestador,
        "Data da abertura da requisição": dt_requisicao,
        "Tipo Guia": ds_tipo_guia,
        "Caráter de atendimento (Urgência ou eletiva)": ds_carater_atendimento,
        "Idade do beneficiário": idade,
        "Situação contratual": situacao_contratual,
        "Período de carência?": carencia,
        "Descrição dos procedimentos": descriptions_dict,
        "Tipo dos itens (nivel 1)": item_type_dict,
        "Tipo dos itens (nivel 2)": specific_item_type_dict
    }
    
    return result

