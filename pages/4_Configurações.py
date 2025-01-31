import streamlit as st
from utils.firebase_admin_init import verify_token
import utils.auth_functions as auth_functions
import boto3
import json
from botocore.exceptions import ClientError

if 'user_info' not in st.session_state:
    st.switch_page("0_Inicio.py")

# Verify token on each request
decoded_token = verify_token(st.session_state.id_token)
if not decoded_token:
    # Token is invalid or expired, clear session and force re-login
    st.session_state.clear()
    st.session_state.auth_warning = 'Session expired. Please sign in again.'
    st.rerun()

st.set_page_config(page_title="Configurações - Assistente de Auditoria", page_icon="⚙️", layout="wide")

# Configuração do S3
s3 = boto3.client('s3')
BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"

def load_auditors():
    try:
        response = s3.get_object(Bucket=BUCKET, Key=AUDITORS_KEY)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return {"auditors": []}
        raise

def save_auditors(auditors_data):
    s3.put_object(
        Bucket=BUCKET,
        Key=AUDITORS_KEY,
        Body=json.dumps(auditors_data, ensure_ascii=False, indent=2).encode('utf-8'),
        ContentType='application/json'
    )


st.title("⚙️ Configurações")

# Authentication success and warning messages
auth_notification = st.empty()
if 'auth_success' in st.session_state:
    auth_notification.success(st.session_state.auth_success)
    del st.session_state.auth_success
elif 'auth_warning' in st.session_state:
    auth_notification.warning(st.session_state.auth_warning)
    del st.session_state.auth_warning

if st.session_state.user_role == "adm":

    # Carregar auditores existentes
    if 'auditors_data' not in st.session_state:
        st.session_state.auditors_data = load_auditors()

    # Seção de Auditores
    st.header("👥 Gerenciamento de Usuários")

    # Formulário para adicionar novo auditor
    with st.form(key="add_auditor_form"):
        st.subheader("Adicionar Novo Usuário")

        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Nome completo", placeholder="Digite o nome do usuário")
            new_email = st.text_input("Email", placeholder="Digite o email do usuário")
            new_role = st.selectbox("Role", options=["auditor", "adm"], index=0)

        with col2:
            # Gerar próximo ID disponível
            existing_ids = [int(a.get('id', 0)) for a in st.session_state.auditors_data.get('auditors', [])]
            next_id = max(existing_ids, default=0) + 1
            new_id = st.number_input("ID", value=next_id, disabled=True)
            new_password = st.text_input("Senha", type="password", placeholder="Digite a senha do usuário")

        submit_button = st.form_submit_button("Adicionar Usuário", use_container_width=True)

        if submit_button:
            if not new_name or not new_email or not new_password:
                st.error("Por favor, preencha todos os campos.")
            elif not "@" in new_email:
                st.error("Por favor, insira um email válido.")
            elif len(new_password) < 6:  # Firebase requires minimum 6 characters
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif new_id in existing_ids:
                st.error(f"ID {new_id} já está em uso. Por favor, use um ID diferente.")
            else:
                with auth_notification, st.spinner('Criando conta...'):
                    auth_functions.create_account_adm(new_email, new_password, role=new_role)

                    if 'auth_success' in st.session_state:
                        new_auditor = {
                            "id": new_id,
                            "name": new_name,
                            "email": new_email,
                            "role": new_role
                        }

                        if 'auditors' not in st.session_state.auditors_data:
                            st.session_state.auditors_data['auditors'] = []

                        st.session_state.auditors_data['auditors'].append(new_auditor)
                        save_auditors(st.session_state.auditors_data)
                    st.rerun()

    # Lista de auditores existentes
    st.divider()
    st.subheader("Auditores Cadastrados")

    if not st.session_state.auditors_data.get('auditors'):
        st.info("Nenhum auditor cadastrado ainda.")
    else:
        # Criar uma tabela para exibir os auditores
        auditors_list = st.session_state.auditors_data['auditors']

        # Ordenar por ID
        auditors_list = sorted(auditors_list, key=lambda x: x['id'])

        # Criar colunas para cada auditor
        cols = st.columns(len(auditors_list))

        for idx, auditor in enumerate(auditors_list):
            with cols[idx]:
                st.markdown(f"**ID:** {auditor['id']}")
                st.markdown(f"**Nome:** {auditor['name']}")
                st.markdown(f"**Email:** {auditor['email']}")
                st.markdown(f"**Role:** {auditor.get('role', 'Erro ao carregar role')}")

                # Botão para remover auditor
                if st.button("🗑️ Remover", key=f"remove_{auditor['id']}", use_container_width=True):
                    with auth_notification, st.spinner('Removendo conta...'):
                        auth_functions.delete_account_adm(auditor['email'])
                        st.session_state.auditors_data['auditors'].remove(auditor)
                        save_auditors(st.session_state.auditors_data)
                        st.success(f"Auditor {auditor['name']} removido com sucesso!")
                        st.rerun()

    st.divider()
    with st.form(key="change_password_form"):
        st.subheader("Alterar Senha dos Auditores")

        col1, col2 = st.columns(2)
        with col1:
            new_altered_password = st.text_input("Nova Senha", type="password", placeholder="Digite a nova senha do auditor")

        with col2:
            existing_ids = [a.get('id', 0) for a in st.session_state.auditors_data.get('auditors', [])]
            user_id = st.number_input("ID", step=1, min_value=1)

        submit_button = st.form_submit_button("Mudar Senha", use_container_width=True)

        if submit_button:
            if not user_id in existing_ids:
                st.error("Por favor, use um ID válido.")
            elif not new_altered_password:
                st.error("Por favor, digite a nova senha.")
            elif len(new_altered_password) < 6:  # Firebase requires minimum 6 characters
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                auditor = next((a for a in st.session_state.auditors_data['auditors'] if a['id'] == user_id), None)
                with auth_notification, st.spinner('Alterando senha...'):
                    auth_functions.reset_password_adm(auditor['email'], new_altered_password)
                    st.rerun()

st.divider()
st.markdown("<div style='margin-top: 40px'></div>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([3, 1, 1, 3])
with col2:
    st.subheader("🔐 Sair")
with col3:
    st.button(label='Clique aqui para sair',on_click=auth_functions.sign_out,type='primary')

# st.text("current user")
# st.text(auth_functions.get_current_user_info(st.session_state.id_token))