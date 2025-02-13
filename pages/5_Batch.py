import streamlit as st
import boto3
import json
import asyncio
import aiohttp
import time
from botocore.exceptions import ClientError
from utils.firebase_admin_init import verify_token
import pandas as pd
from utils.get_requisition_details import get_requisition_details
from utils.requisition_history import RequisitionHistory
from agentLogic import create_justificativa
from utils.state import STATE_CLASS
from model.inference import fazer_predicao_por_id
from tenacity import retry, stop_after_attempt, wait_exponential
import utils.auth_functions as auth_functions
from utils.get_user_info import load_auditors
from utils.streamlit_utils import change_button_color
from utils.streamlit_utils import render_requisition_search

# st.set_page_config(
#     page_title="Processamento em Lote - Assistente de Auditoria",
#     page_icon="🔄",
#     layout="wide",
# )

if 'user_info' not in st.session_state:
    st.switch_page("0_Inicio.py")

# Verify token on each request
decoded_token = verify_token(st.session_state.id_token)
if not decoded_token:
    # Token is invalid or expired, clear session and force re-login
    st.session_state.clear()
    st.session_state.auth_warning = 'Session expired. Please sign in again.'
    st.rerun()

# Configuração do S3
s3 = boto3.client("s3")
BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"

# Configurações de retry
MAX_RETRIES = 3
INITIAL_WAIT = 1  # segundos
MAX_WAIT = 10  # segundos


def load_auditors():
    try:
        response = s3.get_object(Bucket=BUCKET, Key=AUDITORS_KEY)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return {"auditors": []}
        raise


current_user = auth_functions.get_current_user_info(st.session_state.id_token)
auditors_data = load_auditors()
auditors_list = auditors_data.get("auditors", [])

if current_user["role"] != "adm":
    st.switch_page("pages/1_Jair.py")

elif current_user["role"] == "auditor":

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=INITIAL_WAIT, max=MAX_WAIT),
    )
    async def process_single_requisition(
        req_num: str,
        state: STATE_CLASS,
        history: RequisitionHistory,
        selected_auditor: str,
    ):
        """Processa uma única requisição com mecanismo de retry"""
        try:
            # Verificar se já existe
            if history.has_requisition(req_num):
                return {
                    "status": "already_processed",
                    "message": f"Requisição {req_num} já processada anteriormente.",
                }

            # Obter detalhes da requisição
            resumo = get_requisition_details(int(req_num))

            if resumo == {"Error": "REQUISICAO_ID not found"}:
                return {
                    "status": "not_found",
                    "message": f"Requisição {req_num} não encontrada",
                }

            # Adicionar delay para evitar rate limits
            await asyncio.sleep(1)

            # Fazer predição do modelo
            response = fazer_predicao_por_id(int(req_num))

            # Adicionar delay para evitar rate limits
            await asyncio.sleep(1)

            # Gerar análise
            final_output = create_justificativa(resumo, response)

            # Salvar no S3
            history.save_complete_requisition(
                resumo, final_output, None, auditor=selected_auditor
            )

            return {
                "status": "success",
                "message": f"Requisição {req_num} processada com sucesso",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Erro ao processar requisição {req_num}: {str(e)}",
            }

    async def process_batch(
        req_numbers: list,
        state: STATE_CLASS,
        history: RequisitionHistory,
        selected_auditor: str,
    ):
        """Processa um lote de requisições de forma assíncrona"""
        # Criar semáforo para limitar o número de requisições simultâneas
        semaphore = asyncio.Semaphore(5)  # máximo de 5 requisições simultâneas

        async def process_with_semaphore(req_num):
            async with semaphore:
                return await process_single_requisition(
                    req_num, state, history, selected_auditor
                )

        # Processar requisições em paralelo
        tasks = [process_with_semaphore(req_num) for req_num in req_numbers]
        return await asyncio.gather(*tasks)

    # Inicializar objetos necessários
    history = RequisitionHistory()
    state = STATE_CLASS()

    st.title("🔄 Processamento em Lote")

    # Carregar lista de auditores
    auditors_data = load_auditors()
    auditors_list = auditors_data.get("auditors", [])
    auditor_names = [a["name"] for a in auditors_list]

    if not auditor_names:
        st.error(
            "Nenhum auditor cadastrado. Por favor, cadastre um auditor na página de Configurações."
        )
        st.stop()

    # Interface principal
    st.write(
        "Digite os números das requisições (um por linha) para processamento em lote:"
    )

    # Área de texto para números de requisição
    requisition_numbers = st.text_area(
        "Números das Requisições",
        height=200,
        placeholder="Digite um número de requisição por linha\nExemplo:\n12345678\n87654321\n...",
    )

    # Seleção do auditor
    selected_auditor = st.selectbox(
        "Selecione o Auditor Responsável:", options=auditor_names
    )

    # Configurações avançadas
    with st.expander("⚙️ Configurações Avançadas"):
        col1, col2 = st.columns(2)
        with col1:
            max_concurrent = st.number_input(
                "Máximo de Requisições Simultâneas",
                min_value=1,
                max_value=10,
                value=5,
                help="Limite de requisições processadas simultaneamente",
            )
        with col2:
            retry_count = st.number_input(
                "Tentativas em Caso de Erro",
                min_value=1,
                max_value=5,
                value=3,
                help="Número de tentativas em caso de falha",
            )

    # Botão de processamento
    if st.button("Processar Requisições", use_container_width=True, type="primary"):
        if not requisition_numbers.strip():
            st.error("Por favor, insira pelo menos um número de requisição.")
            st.stop()

        # Converter o texto em lista de números
        req_numbers = [
            num.strip() for num in requisition_numbers.split("\n") if num.strip()
        ]

        # Criar barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Contadores
        total = len(req_numbers)

        # Processar requisições de forma assíncrona
        with st.spinner("Processando requisições..."):
            results = asyncio.run(
                process_batch(req_numbers, state, history, selected_auditor)
            )

        # Contabilizar resultados
        success = sum(1 for r in results if r["status"] == "success")
        already_processed = sum(
            1 for r in results if r["status"] == "already_processed"
        )
        errors = [
            r["message"] for r in results if r["status"] in ["error", "not_found"]
        ]

        # Relatório final
        st.success(
            f"""
        #### Processamento Concluído!
        - Total de requisições: {total}
        - Processadas com sucesso: {success}
        - Já processadas anteriormente: {already_processed}
        - Erros: {len(errors)}
        """
        )

        if errors:
            st.error("#### Erros encontrados:")
            for error in errors:
                st.write(f"- {error}")

    # Adicionar instruções de uso
    with st.expander("ℹ️ Como usar"):
        st.markdown(
            """
        ### Instruções de Uso

        1. **Preparação**:
            - Digite os números das requisições que deseja processar
            - Um número por linha
            - Remova espaços extras e caracteres especiais

        2. **Seleção do Auditor**:
            - Escolha o auditor responsável pelo lote
            - O nome do auditor será registrado em todas as requisições processadas

        3. **Configurações Avançadas**:
            - Ajuste o número máximo de requisições simultâneas
            - Configure o número de tentativas em caso de erro

        4. **Processamento**:
            - Clique em "Processar Requisições"
            - O sistema processará as requisições em paralelo
            - O progresso será mostrado em tempo real

        5. **Resultados**:
            - Ao final, você verá um resumo do processamento
            - Requisições já processadas serão identificadas
            - Erros serão listados com detalhes

        6. **Verificação**:
            - Após o processamento, você pode verificar cada requisição na página principal
            - As requisições estarão disponíveis no histórico
        """
        )
