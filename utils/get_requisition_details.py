## Arquivo para obter detalhes de requisição
import dotenv, os
import pandas as pd
import numpy as np
from datetime import datetime
import re
import requests
import json
from config.config import settings

dotenv.load_dotenv()


def is_aws_endpoint(address: str) -> bool:
    """
    Check if the given address is an AWS endpoint.
    Returns True if the address matches AWS endpoint patterns (e.g. s3://, amazonaws.com, etc.)
    """
    if not address:
        return False

    aws_patterns = [
        r"^s3://",  # S3 URI pattern
        r"\.amazonaws\.com",  # AWS domain pattern
        r"^https?://[^/]+\.aws\.",  # AWS HTTPS endpoint pattern
        r"^[^/]+\.aws\.",  # AWS endpoint without protocol
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
        reference_date = datetime.strptime(reference_date_str[:10], "%Y-%m-%d")
    except:
        reference_date = datetime.strptime(reference_date_str, "%d/%m/%y")
    # Calculate age using the year difference
    age = reference_date.year - birth_year
    dt_nascimento = birth_year
    return age, dt_nascimento


# Função para checar a carência do paciente
def check_carencia(carencia):
    """Versão que verifica a coluna carencia"""
    if pd.isna(carencia) or carencia in ["nan", "NaT"]:
        return "Não"
    else:
        carencia = datetime.fromisoformat(carencia)
        carencia = carencia.strftime("%d/%m/%Y")
        return (
            f"Sim (Termina na data {carencia} para o(s) procedimento(s) solicitado(s))"
        )


def carencia_for_model(carencia):
    """Versão que verifica a coluna carencia"""
    if pd.isna(carencia) or carencia in ["nan", "NaT"]:
        return np.nan
    else:
        return carencia


# Função para determinar a situação contratual do paciente
def determine_contrato(data_cancelamento):
    if pd.isna(data_cancelamento) or data_cancelamento in ["nan", "NaT"]:
        return "Contrato ativo"
    else:
        data_cancelamento = datetime.fromisoformat(data_cancelamento)
        data_cancelamento = data_cancelamento.strftime("%d/%m/%Y")
        return f"Contrato cancelado no dia {data_cancelamento}"


###############################################################################
###############################################################################


def get_data_by_adress(requisicao_id: int) -> dict:
    """
    Load data from AWS S3 using pandas read_csv
    """
    # Get the base path from environment
    base_path = os.environ.get("REQUISICOES_ADRESS_OR_PATH", None)

    try:
        # Load all required CSV files
        dados_requisicao = pd.read_csv(
            f"{base_path}/OMNI_DADOS_REQUISICAO.csv", encoding="latin1"
        )
        dados_item = pd.read_csv(f"{base_path}/OMNI_DADOS_ITEM.csv", encoding="latin1")
        dados_prestador = pd.read_csv(
            f"{base_path}/OMNI_DADOS_PRESTADOR.csv", encoding="latin1"
        )
        dados_beneficiario = pd.read_csv(
            f"{base_path}/OMNI_DADOS_BENEFICIARIO.csv", encoding="latin1"
        )
        dados_requisicao_item = pd.read_csv(
            f"{base_path}/OMNI_DADOS_REQUISICAO_ITEM.csv", encoding="latin1"
        )

        return (
            dados_requisicao,
            dados_item,
            dados_prestador,
            dados_beneficiario,
            dados_requisicao_item,
        )

    except Exception as e:
        raise ValueError(f"Erro ao carregar dados da AWS: {str(e)}")


def get_austa_api_token() -> str:
    """
    Obtém o token de autenticação da API.
    """
    username = settings.austa_api_username
    password = settings.austa_api_password
    base_url = settings.austa_api_base_url

    if not username or not password:
        raise ValueError("API_USERNAME and API_PASSWORD must be set in .env file")

    headers = {"Content-Type": "application/json"}
    data = {"username": username, "password": password}

    try:
        response = requests.post(
            f"{base_url}/token/", headers=headers, data=json.dumps(data)
        )
        response.raise_for_status()  # Lança um erro se a resposta não for 200
        return response.json().get("access", "")

    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.ConnectionError:
        return "Failed to connect to API"
    except requests.exceptions.Timeout:
        return "Request timed out"
    except requests.exceptions.RequestException as err:
        return f"Request error: {err}"


def get_requisition_details(requisicao_id: int) -> dict:
    """
    Obtém os detalhes da requisição diretamente da API,
    agrupando os dados da requisição e dos seus itens
    no mesmo formato esperado pela aplicação.
    """
    base_url = settings.austa_api_base_url

    API_TOKEN = get_austa_api_token()

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    params = {"request_id": requisicao_id}

    try:
        response = requests.get(
            f"{base_url}/auditor/requests/", headers=headers, params=params
        )
        response.raise_for_status()  # Lança exceção se o status não for 200
        data = response.json()

        if not data:
            return {"Error": "REQUISICAO_ID not found"}

        # Caso a API retorne uma lista de itens para a mesma requisição
        requisition_items = data if isinstance(data, list) else [data]

        # Usamos o primeiro item para os campos da requisição (dados de cabeçalho)
        first_item = requisition_items[0]

        # Cálculo da idade e formatação da data de nascimento (pode ser adaptado conforme sua função)
        idade, data_nascimento_modelo = calculate_age(
            str(first_item["DATA_NASCIMENTO"]), first_item["DT_REQUISICAO"]
        )

        # Determina a situação contratual e carência a partir dos campos da requisição
        situacao_contratual = determine_contrato(first_item["DATA_CANCELAMENTO"])
        carencia = check_carencia(first_item["DATA_FIM_CARENCIA"])
        carencia_modelo = carencia_for_model(first_item["DATA_FIM_CARENCIA"])

        # Criação dos dicionários para agrupar as informações dos itens
        # Como na versão CSV você usava o campo CD_ITEM para a chave,
        # aqui, por não termos esse campo, usaremos o ID_REQUISICAO_ITEM.
        descriptions_dict = {}
        item_type_dict = {}
        specific_item_type_dict = {}
        id_requisicao_item_dict = {}
        data_atualizacao_item_dict = {}
        data_atualizacao_reqitem_dict = {}

        for item in requisition_items:
            # Usamos o ID_REQUISICAO_ITEM como chave (deve ser único para cada item)
            key = item["ID_REQUISICAO_ITEM"]

            descriptions_dict[key] = item.get("DS_ITEM", "N/A")
            item_type_dict[key] = item.get("DS_TIPO_ITEM", "N/A")
            specific_item_type_dict[key] = item.get("DS_CLASSIFICACAO_1", "N/A")
            id_requisicao_item_dict[key] = item["ID_REQUISICAO_ITEM"]

            # Converte a string de data para objeto datetime, se disponível
            dt_atualizacao = item.get("DT_ATUALIZACAO")
            if dt_atualizacao:
                dt_atualizacao = pd.to_datetime(dt_atualizacao)
            data_atualizacao_item_dict[key] = dt_atualizacao

            data_atualizacao_reqitem_dict[key] = dt_atualizacao

        data_vigencia = first_item.get("DATA_INICIO_VIGENCIA", "N/A")
        data_vigencia = datetime.fromisoformat(data_vigencia)
        data_vigencia = data_vigencia.strftime("%d/%m/%Y")

        data_requisicao = first_item.get("DT_REQUISICAO", "N/A")
        data_requisicao = datetime.fromisoformat(data_requisicao)
        data_requisicao = data_requisicao.strftime("%d/%m/%Y")

        # Monta o dicionário final com os dados da requisição e dos itens
        result = {
            "Número da requisição": first_item["ID_REQUISICAO"],
            "Nome do beneficiário": first_item["NM_BENEFICIARIO"],
            "Médico solicitante": first_item["NM_PRESTADOR"],
            "Data da abertura da requisição": data_requisicao,
            "Tipo Guia": first_item["DS_TIPO_GUIA"],
            "Caráter de atendimento (Urgência ou eletiva)": first_item[
                "DS_CARATER_ATENDIMENTO"
            ],
            "Idade do beneficiário": idade,
            "Situação contratual": situacao_contratual,
            "Sexo do beneficiário": first_item.get("SEXO", "N/A"),
            "Período de carência?": carencia,
            "Início da vigência": data_vigencia,
            "Descrição dos procedimentos": descriptions_dict,
            "Tipo dos itens (nivel 1)": item_type_dict,
            "Tipo dos itens (nivel 2)": specific_item_type_dict,
            "ID_REQUISICAO_ITEM": id_requisicao_item_dict,
            "DT_ATUALIZACAO": data_atualizacao_item_dict,
            "DT_ATUALIZACAO_REQ": data_atualizacao_reqitem_dict,
            "DS_CBO_PROFISSIONAL": first_item.get("DS_CBO_PROFISSIONAL", "N/A"),
            "DS_TIPO_INTERNACAO": first_item.get("DS_TIPO_INTERNACAO", "N/A"),
            "DS_REGIME_INTERNACAO": first_item.get("DS_REGIME_INTERNACAO", "N/A"),
            "DS_TIPO_SADT": first_item.get("DS_TIPO_SADT", "N/A"),
            "DS_TIPO_CONSULTA": first_item.get("DS_TIPO_CONSULTA", "N/A"),
            "TITULARIDADE": first_item.get("TITULARIDADE", "N/A"),
            "DATA_CANCELAMENTO": first_item["DATA_CANCELAMENTO"],
            "DATA_FIM_CARENCIA": carencia_modelo,
            "DATA_NASCIMENTO": data_nascimento_modelo,
        }

        return result

    except requests.exceptions.HTTPError as http_err:
        return {"Error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.ConnectionError:
        return {"Error": "Failed to connect to API"}
    except requests.exceptions.Timeout:
        return {"Error": "Request timed out"}
    except requests.exceptions.RequestException as err:
        return {"Error": f"Request error: {err}"}


if __name__ == "__main__":
    # Testando
    requisicao_id = 1
    data = get_requisition_details(42089629)
    print(data)
