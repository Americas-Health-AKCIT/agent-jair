## Arquivo para obter detalhes de requisição
import dotenv,os
import pandas as pd
import numpy as np
from datetime import datetime
from .state import STATE_CLASS
import re


dotenv.load_dotenv()


def is_aws_endpoint(address: str) -> bool:
    """
    Check if the given address is an AWS endpoint.
    Returns True if the address matches AWS endpoint patterns (e.g. s3://, amazonaws.com, etc.)
    """
    if not address:
        return False
        
    aws_patterns = [
        r'^s3://',  # S3 URI pattern
        r'\.amazonaws\.com',  # AWS domain pattern
        r'^https?://[^/]+\.aws\.',  # AWS HTTPS endpoint pattern
        r'^[^/]+\.aws\.'  # AWS endpoint without protocol
    ]
    
    return any(re.search(pattern, address, re.IGNORECASE) for pattern in aws_patterns)


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
    dt_nascimento = birth_year
    return age, dt_nascimento


# Função para checar a carência do paciente
def check_carencia(carencia):
    """Versão que verifica a coluna carencia"""
    if pd.isna(carencia) or carencia in ['nan', 'NaT']:
        return "Não"
    else:
        return f"Sim (Termina na data {carencia} para o(s) procedimento(s) solicitado(s))"
    
def carencia_for_model(carencia):
    """Versão que verifica a coluna carencia"""
    if pd.isna(carencia) or carencia in ['nan', 'NaT']:
        return np.nan
    else:
        return carencia


# Função para determinar a situação contratual do paciente
def determine_contrato(data_cancelamento):
    if pd.isna(data_cancelamento) or data_cancelamento in ['nan', 'NaT']:
        return "Contrato ativo"
    else:
        return f"Contrato cancelado no dia {data_cancelamento}"


###############################################################################
###############################################################################


def get_data_by_adress(requisicao_id:int)->dict:
    """
    Load data from AWS S3 using pandas read_csv
    """
    # Get the base path from environment
    base_path = os.environ.get("REQUISICOES_ADRESS_OR_PATH", None)
    
    try:
        # Load all required CSV files
        dados_requisicao = pd.read_csv(f"{base_path}/OMNI_DADOS_REQUISICAO.csv", encoding='latin1')
        dados_item = pd.read_csv(f"{base_path}/OMNI_DADOS_ITEM.csv", encoding='latin1')
        dados_prestador = pd.read_csv(f"{base_path}/OMNI_DADOS_PRESTADOR.csv", encoding='latin1')
        dados_beneficiario = pd.read_csv(f"{base_path}/OMNI_DADOS_BENEFICIARIO.csv", encoding='latin1')
        dados_requisicao_item = pd.read_csv(f"{base_path}/OMNI_DADOS_REQUISICAO_ITEM.csv", encoding='latin1')
        
        return dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item
        
    except Exception as e:
        raise ValueError(f"Erro ao carregar dados da AWS: {str(e)}")



DADOS_CSV_LIST = [] # cache para os dados vindo do CSV


def get_requisition_details(requisicao_id:int, state : STATE_CLASS)->dict:
    
    placeholder = "Nan"
    # caminho = r'D:\CEIA\agente-jair-autorizacao\data\Dados_Austa_07_2023_ate_10_2024'
    # print('Caminho hardcoded:', caminho)
    print(os.environ.get('REQUISICOES_ADRESS_OR_PATH'))

    requisicoes_path = os.environ.get('REQUISICOES_ADRESS_OR_PATH')
    print(f'Verificando endereço de requisições: {requisicoes_path}')

    if os.path.exists(requisicoes_path):
        # carregar os dados a partir do arquivo csv local
        dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = state.DADOS_CSV_LIST
    elif is_aws_endpoint(requisicoes_path):
        # carregar os dados a partir do endpoint AWS usando pandas
        print("Carregando dados da AWS")
        try:
            dados_requisicao, dados_item, dados_prestador, dados_beneficiario, dados_requisicao_item = get_data_by_adress(requisicao_id)
        except Exception as e:
            raise ValueError(f"Erro ao carregar dados da AWS: {str(e)}")
    else:
        raise ValueError(f"Endereço de requisições inválido ou inacessível: {requisicoes_path}")

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
    ds_cbo_profissional = requisicao['DS_CBO_PROFISSIONAL'].iloc[0]
    ds_tipo_internacao = requisicao['DS_TIPO_INTERNACAO'].iloc[0]
    ds_regime_internacao = requisicao['DS_REGIME_INTERNACAO'].iloc[0]
    ds_tipo_sadt = requisicao['DS_TIPO_SADT'].iloc[0]
    ds_tipo_consulta = requisicao['DS_TIPO_CONSULTA'].iloc[0]

    # Pega o beneficiário no df de beneficiarios
    beneficiario = dados_beneficiario[dados_beneficiario['ID_BENEFICIARIO'] == id_beneficiario]
    
    if beneficiario.empty:
        return {"Erro": "Beneficiario não encontrado"}

    # Extraindo informações do beneficiarios
    nome_beneficiario = beneficiario['NM_BENEFICIARIO'].iloc[0]
    data_nascimento = str(beneficiario['DATA_NASCIMENTO'].iloc[0])
    print("Data nascimento: ", data_nascimento)
    data_cancelamento = beneficiario['DATA_CANCELAMENTO'].iloc[0]
    data_inicio_vigencia = beneficiario['DATA_INICIO_VIGENCIA'].iloc[0]
    carencia_raw = beneficiario['DATA_FIM_CARENCIA'].iloc[0]
    titularidade = beneficiario['TITULARIDADE'].iloc[0]

    # Calculando a idade, verificando a carência e a situação contratual
    idade, data_nascimento_modelo = calculate_age(data_nascimento, dt_requisicao)
    carencia = check_carencia(carencia_raw)
    carencia_modelo = carencia_for_model(carencia_raw)
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

    # Extraindo informações dos itens 
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

    # Creating id_requisicao_item_dict from dados_requisicao_item
    id_requisicao_item_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']
    
        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        id_item_display = item_info['CD_ITEM'].iloc[0]
        id_item_display = int(id_item_display)
        
        id_requisicao_item = item['ID_REQUISICAO_ITEM']
        if not pd.isna(id_requisicao_item):
            id_requisicao_item_dict[id_item_display] = id_requisicao_item
        else:
            raise ValueError(f"Critical Error: No requisition item ID found for item ID {id_item_display}, please check the data")
    
    # Creating data_atualizacao_reqitem_dict from dados_requisicao_item
    data_atualizacao_reqitem_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']
    
        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        id_item_display = item_info['CD_ITEM'].iloc[0]
        id_item_display = int(id_item_display)
    
        data_atualizacao_reqitem = item['DT_ATUALIZACAO']
        if not pd.isna(data_atualizacao_reqitem):
            data_atualizacao_reqitem_dict[id_item_display] = pd.to_datetime(data_atualizacao_reqitem)
        else:
            raise ValueError(f"Critical Error: No update date found in requisicao_items for item ID {id_item_display}, please check the data")
    
    # Creating data_atualizacao_item_dict from dados_item
    data_atualizacao_item_dict = {}
    for idx, item in requisicao_items.iterrows():
        id_item = item['ID_ITEM']
    
        item_info = dados_item[dados_item['ID_ITEM'] == id_item]
        if not item_info.empty:
            id_item_display = item_info['CD_ITEM'].iloc[0]
            id_item_display = int(id_item_display)
    
            data_atualizacao_item = item_info['DT_ATUALIZACAO'].iloc[0]
            if not pd.isna(data_atualizacao_item):
                data_atualizacao_item_dict[id_item_display] = pd.to_datetime(data_atualizacao_item)
            else:
                raise ValueError(f"Critical Error: No update date found in dados_item for item ID {id_item_display}, please check the data")
        else:
            raise ValueError(f"Critical Error: Item ID {id_item} not found in dados_item, please check the data")

    # Dict final (Primeiro bloco para auditores, segundo é pro resto)
    result = {
        "Número da requisição": requisicao_id, # ID_REQUISICAO
        "Nome do beneficiário": nome_beneficiario, # NM_BENEFICIARIO
        "Médico solicitante": nome_prestador, # NM_PRESTADOR
        "Data da abertura da requisição": dt_requisicao, # DT_REQUISICAO
        "Tipo Guia": ds_tipo_guia, # DS_TIPO_GUIA
        "Caráter de atendimento (Urgência ou eletiva)": ds_carater_atendimento, # DS_CARATER_ATENDIMENTO
        "Idade do beneficiário": idade, # DATA_NASCIMENTO, DT_REQUISICAO
        "Situação contratual": situacao_contratual, # DATA_CANCELAMENTO
        "Período de carência?": carencia, # DATA_FIM_CARENCIA
        "Descrição dos procedimentos": descriptions_dict, # DS_ITEM
        "Tipo dos itens (nivel 1)": item_type_dict, # DS_TIPO_ITEM
        "Tipo dos itens (nivel 2)": specific_item_type_dict, # DS_CLASSIFICACAO_1

        "ID_REQUISICAO_ITEM": id_requisicao_item_dict,
        "DT_ATUALIZACAO": data_atualizacao_item_dict, # Versão da tabela OMNI_DADOS_ITEM
        "DT_ATUALIZACAO_REQ": data_atualizacao_reqitem_dict, # Versão da tabela OMNI_DADOS_REQUISICAO_ITEM
        "DS_CBO_PROFISSIONAL": ds_cbo_profissional,
        "DS_TIPO_INTERNACAO": ds_tipo_internacao,
        "DS_REGIME_INTERNACAO": ds_regime_internacao,
        "DS_TIPO_SADT": ds_tipo_sadt,
        "DS_TIPO_CONSULTA": ds_tipo_consulta,
        "TITULARIDADE": titularidade,
        "DATA_CANCELAMENTO": data_cancelamento,
        "DATA_FIM_CARENCIA": carencia_modelo,
        "DATA_NASCIMENTO": data_nascimento_modelo
    }
    
    return result