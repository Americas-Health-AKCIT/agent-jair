import streamlit.components.v1 as components
import streamlit as st
from utils.get_requisition_details import get_requisition_details
from utils.requisition_history import RequisitionHistory

def change_button_color(
    widget_label,
    font_color="white",
    background_color="rgb(80, 184, 255)",
    border_color=None,
):
    htmlstr = f"""
        <script>
            var elements = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < elements.length; ++i) {{ 
                if (elements[i].innerText == '{widget_label}') {{ 
                    elements[i].style.color = '{font_color}';
                    elements[i].style.background = '{background_color}';
                    elements[i].style.border = '1px solid {border_color}';
                    elements[i].onmouseover = function() {{
                        this.style.backgroundColor = 'rgb(100, 204, 255)';
                    }};
                    elements[i].onmouseout = function() {{
                        this.style.backgroundColor = '{background_color}';
                    }};
                }}
            }}
        </script>
        """
    components.html(f"{htmlstr}", height=0, width=0)

def render_requisition_search(
    container,
    auditor_names,
    auditor_info,
    history=None,
    redirect_page=True,
    key_prefix=""
):
    """
    Render the requisition search widget in the provided container.

    Args:
        container: A Streamlit container (for example, st.sidebar or another st.container)
                   where the search UI will be rendered.
        auditor_names: A list with auditor names.
        auditor_info: A dict with information for the current auditor.
        history: An instance of RequisitionHistory. If None, one is instantiated.
        redirect_page: Whether to redirect to the "Jair" page after processing.
        key_prefix: A string prefix for all the keys used inside the widget.
                    This helps avoid duplicate key errors when rendering the widget multiple times.
    """
    # Instantiate history if not provided.
    if history is None:
        from utils.requisition_history import RequisitionHistory
        history = RequisitionHistory()

    container.title("Jair - Assistente de Auditoria")
    container.write("Digite o número da requisição para receber uma análise detalhada.")

    # Campo de entrada da requisição: use a chave apropriada depending on session state.
    if st.session_state.get("n_req") is None:
        n_req_input = container.text_input(
            "Número da requisição:",
            value="",
            placeholder="Digite aqui",
            key=f"{key_prefix}n_req_input",
        )
    else:
        n_req_input = container.text_input(
            "Número da requisição:",
            value=str(st.session_state.n_req),
            placeholder="Digite aqui",
            key=f"{key_prefix}n_req_input_existing",
        )

    # Determine auditor input.
    if not auditor_names:
        container.error(
            "Nenhum auditor cadastrado. Por favor, cadastre um auditor na página de Configurações."
        )
        auditor_input = None
    elif not auditor_info:
        container.error(
            "Auditor atual não encontrado. Por favor, reporte o problema para o administrador."
        )
        auditor_input = None
    else:
        auditor_input = auditor_info["name"]

    send_button = container.button(
        "Enviar", use_container_width=True, key=f"{key_prefix}enviar"
    )
    from utils.streamlit_utils import change_button_color
    change_button_color(
        "Enviar",
        font_color="black",
        background_color="rgb(255,255,255)",
        border_color="grey",
    )

    if send_button:
        if not n_req_input or not n_req_input.isdigit():
            container.error("Digite um número de requisição válido.")
        elif not auditor_input:
            container.error("O nome do auditor é obrigatório.")
        else:
            st.session_state.auditor = auditor_input
            complete_req = history.get_complete_requisition(n_req_input)
            if complete_req and complete_req.get("model_output"):
                st.session_state.resumo = complete_req["requisition"]
                st.session_state.final_output = complete_req["model_output"]
                if complete_req.get("feedback"):
                    st.session_state.feedback = complete_req["feedback"]
                st.session_state.n_req = n_req_input
            else:
                print("starting to get requisition details")
                from utils.get_requisition_details import get_requisition_details
                resumo = get_requisition_details(int(n_req_input))
                if resumo == {"Error": "REQUISICAO_ID not found"}:
                    container.error(
                        "Número da requisição não encontrado. Por favor, confire o número da requisição e tente novamente."
                    )
                    st.session_state.resumo = None
                else:
                    st.session_state.resumo = resumo
                    st.session_state.n_req = n_req_input
                    st.session_state.final_output = None

            if redirect_page:
                st.switch_page("pages/1_Jair.py")
