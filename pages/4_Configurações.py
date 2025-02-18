import streamlit as st
from utils.firebase_admin_init import verify_token
import utils.auth_functions as auth_functions
import boto3
import json
from botocore.exceptions import ClientError
import streamlit.components.v1 as components
from utils.requisition_history import RequisitionHistory
from utils.get_user_info import load_auditors
from utils.streamlit_utils import change_button_color
from utils.streamlit_utils import render_requisition_search
import pandas as pd

if 'user_info' not in st.session_state:
    st.switch_page("0_Inicio.py")

# Verify token on each request
decoded_token = verify_token(st.session_state.id_token)
if not decoded_token:
    # Token is invalid or expired, clear session and force re-login
    st.session_state.clear()
    st.session_state.auth_warning = 'Session expired. Please sign in again.'
    st.rerun()

BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"
history = RequisitionHistory()
s3 = history.s3

current_user = auth_functions.get_current_user_info(st.session_state.id_token)
auditors_data = load_auditors(s3, BUCKET, AUDITORS_KEY)
auditors_list = auditors_data.get("auditors", [])
auditor_names = [a["name"] for a in auditors_list]
auditor_info = next(
    (a for a in auditors_list if a["email"] == current_user["email"]), None
)

with st.sidebar:
    render_requisition_search(st.sidebar, auditor_names, auditor_info, history)

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

current_user = auth_functions.get_current_user_info(st.session_state.id_token)
if current_user['role'] == 'adm':

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
            elif str(new_id) in [str(id) for id in existing_ids]:  # Comparar como strings
                st.error(f"ID {new_id} já está em uso. Por favor, use um ID diferente.")
            else:
                with auth_notification, st.spinner('Criando conta...'):
                    auth_functions.create_account_adm(new_email, new_password, role=new_role)

                    if 'auth_success' in st.session_state:
                        new_auditor = {
                            "id": str(new_id),
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
        # Inicializar estado de edição se não existir
        if 'editing_mode' not in st.session_state:
            st.session_state.editing_mode = False
        
        # Botão para alternar modo de edição
        col1, col2 = st.columns([6, 1])
        with col2:
            if not st.session_state.editing_mode:
                edit_button = st.button("✏️ Editar", use_container_width=True)
                if edit_button:
                    st.session_state.editing_mode = True
                    st.rerun()
            else:
                save_button = st.button("💾 Salvar", type="primary", use_container_width=True)
                if save_button:
                    st.session_state.editing_mode = False
                    # Atualizar dados no S3
                    save_auditors(st.session_state.auditors_data)
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()

        # Criar uma tabela para exibir os auditores
        auditors_list = st.session_state.auditors_data['auditors']
        # Ordenar por ID
        auditors_list = sorted(auditors_list, key=lambda x: x['id'])

        if st.session_state.editing_mode:
            # Modo de edição usando st.data_editor
            edited_df = pd.DataFrame(auditors_list)
            edited_df['role'] = edited_df['role'].map({'adm': 'Administrador', 'auditor': 'Auditor'})
            edited_df = edited_df.rename(columns={
                'id': 'ID do Auditor',
                'name': 'Nome',
                'email': 'Email',
                'role': 'Cargo'
            })
            
            edited_df = st.data_editor(
                edited_df,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "ID do Auditor": st.column_config.NumberColumn(
                        "ID do Auditor",
                        help="Identificador único do auditor",
                        disabled=True
                    ),
                    "Cargo": st.column_config.SelectboxColumn(
                        "Cargo",
                        help="Cargo do usuário no sistema",
                        options=["Administrador", "Auditor"]
                    )
                }
            )
            
            # Converter de volta para o formato original
            edited_df['role'] = edited_df['Cargo'].map({'Administrador': 'adm', 'Auditor': 'auditor'})
            edited_df = edited_df.rename(columns={
                'ID do Auditor': 'id',
                'Nome': 'name',
                'Email': 'email',
                'Cargo': 'role'
            })
            
            # Atualizar dados na sessão
            st.session_state.auditors_data['auditors'] = edited_df.to_dict('records')
            
        else:
            # Modo de visualização
            auditors_df = pd.DataFrame(auditors_list)
            auditors_df['role'] = auditors_df['role'].map({'adm': 'Administrador', 'auditor': 'Auditor'})
            auditors_df = auditors_df.rename(columns={
                'id': 'ID do Auditor',
                'name': 'Nome',
                'email': 'Email',
                'role': 'Cargo'
            })
            
            st.dataframe(
                auditors_df,
                hide_index=True,
                use_container_width=True
            )

    st.divider()
    with st.form(key="change_password_form"):
        st.subheader("Alterar Senha dos Auditores")

        col1, col2 = st.columns(2)
        with col1:
            new_altered_password = st.text_input("Nova Senha", type="password", placeholder="Digite a nova senha do auditor")

        with col2:
            # Criar lista de nomes dos auditores
            auditor_names = [a['name'] for a in st.session_state.auditors_data.get('auditors', [])]
            selected_auditor = st.selectbox("Selecione o Auditor", options=auditor_names)

        submit_button = st.form_submit_button("Mudar Senha", use_container_width=True)

        if submit_button:
            if not selected_auditor:
                st.error("Por favor, selecione um auditor.")
            elif not new_altered_password:
                st.error("Por favor, digite a nova senha.")
            elif len(new_altered_password) < 6:  # Firebase requires minimum 6 characters
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                auditor = next((a for a in st.session_state.auditors_data['auditors'] if a['name'] == selected_auditor), None)
                with auth_notification, st.spinner('Alterando senha...'):
                    auth_functions.reset_password_adm(auditor['email'], new_altered_password)
                    st.rerun()

st.divider()
st.markdown("<div style='margin-top: 40px'></div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h3 style='text-align: center;'>🔐 Sair</h3>", unsafe_allow_html=True)
    
    # Create a centered container for the button
    st.markdown("""
        <div style='display: flex; justify-content: center;'>
            <div style='width: 200px;'>  <!-- Adjust width as needed -->
    """, unsafe_allow_html=True)
    
    st.button(
        label='Clique aqui para sair',
        on_click=auth_functions.sign_out,
        type='primary',
        use_container_width=True
    )
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# st.text("current user")
# st.text(auth_functions.get_current_user_info(st.session_state.id_token))