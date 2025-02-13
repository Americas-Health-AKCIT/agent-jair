import streamlit as st
import utils.auth_functions as auth_functions
from utils.firebase_admin_init import verify_token

st.cache_data.clear()

st.set_page_config(
    page_title="Login - Assistente de Auditoria",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)
# Initialize authentication state
if "user_info" not in st.session_state:

    st.markdown(
        """
        <style>
            [data-testid="collapsedControl"] {display: none}
            section[data-testid="stSidebar"] {display: none}
            #MainMenu {visibility: hidden;}
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='text-align: center;'>
            <h3 style='display: inline-block;'>Login - Jair</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    # Authentication form layout
    # do_you_have_an_account = col2.selectbox(label='Do you have an account?',options=('Yes','No'))
    auth_form = col2.form(key="Authentication form", clear_on_submit=False)
    email = auth_form.text_input(label="Email").strip()
    password = auth_form.text_input(
        label="Senha", type="password"
    )  # if do_you_have_an_account in {'Yes','No'} else auth_form.empty()
    auth_notification = col2.empty()

    # Sign In - New
    if auth_form.form_submit_button(
        label="Entrar", use_container_width=True, type="primary"
    ):
        with auth_notification, st.spinner("Entrando..."):
            auth_functions.sign_in(email, password)

    # Authentication success and warning messages
    if "auth_success" in st.session_state:
        auth_notification.success(st.session_state.auth_success)
        del st.session_state.auth_success
    elif "auth_warning" in st.session_state:
        auth_notification.warning(st.session_state.auth_warning)
        del st.session_state.auth_warning

else:
    decoded_token = verify_token(st.session_state.id_token)
    if not decoded_token:
        # Token is invalid or expired, clear session and force re-login
        st.session_state.clear()
        st.session_state.auth_warning = (
            "Sua sessão expirou. Por favor, faça login novamente."
        )
        st.rerun()

    # Pegando a role para definir as paginas que cada user pode acessar
    current_user = auth_functions.get_current_user_info(st.session_state.id_token)
    if current_user is None:
        st.session_state.clear()
        st.session_state.auth_warning = (
            "Sua sessão expirou. Por favor, faça login novamente."
        )
        st.rerun()
    
    role = current_user.get("role", "")

    if role == "adm":
        pages = [
            st.Page("pages/1_Jair.py", title="Jair", icon="🔍", default=True),
            st.Page("pages/2_Instruções.py", title="Instruções", icon="📖"),
            st.Page("pages/3_Resultados.py", title="Resultados", icon="📊"),
            st.Page("pages/4_Configurações.py", title="Configurações", icon="⚙️"),
            st.Page("pages/5_Batch.py", title="Batch", icon="🔄"),
        ]
    elif role == "auditor":
        pages = [
            st.Page("pages/1_Jair.py", title="Jair", icon="🔍", default=True),
            st.Page("pages/2_Instruções.py", title="Instruções", icon="📖"),
            st.Page("pages/3_Resultados.py", title="Minhas Requisições", icon="📊"),
            st.Page("pages/4_Configurações.py", title="Configurações", icon="⚙️"),
        ]
    else:
        st.session_state.clear()
        st.error("O usuário não deve conseguir chegar aqui.")
        st.switch_page("0_Inicio.py")

    navigation = st.navigation(pages)
    navigation.run()
