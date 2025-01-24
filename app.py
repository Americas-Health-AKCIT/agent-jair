import streamlit as st
# TODO: Add menu items
st.set_page_config(page_title="Assistente de Auditoria", page_icon="🔍", layout="wide")
import os
import argparse
import traceback

import dotenv
dotenv.load_dotenv()
from langchain_openai import ChatOpenAI
from agentLogic import create_justificativa
from model.inference import fazer_predicao_por_id
from utils.get_requisition_details import get_requisition_details

from langchain_core.pydantic_v1 import ValidationError

from utils.state import STATE_CLASS
from openai import OpenAI
client_openai = OpenAI()

@st.cache_resource
def get_state():
    return STATE_CLASS()

state = get_state()

llm = ChatOpenAI(model="gpt-4o") 

show_source = False

# Initialize session state variables
if 'show_source' not in st.session_state:
    st.session_state.show_source = None

if 'n_req' not in st.session_state:
    st.session_state.n_req = None

if 'resumo' not in st.session_state:
    st.session_state.resumo = None

if 'final_output' not in st.session_state:
    st.session_state.final_output = None

if 'feedback' not in st.session_state:
    st.session_state.feedback = {}

###############################################################################################
#############################  Streamlit Display - Requisição Input  ##########################
###############################################################################################
if st.session_state.show_source is None:
    show_source = False
    st.session_state.show_source = show_source

if 'dev_mode' in st.session_state and st.session_state.dev_mode:
    with st.sidebar:
        show_source = st.checkbox("Marque para mostrar a fonte: ", key=f"is_source_shown")
        st.session_state.show_source = show_source
        
inputcol1, inputcol2 = st.columns(2)
with inputcol1:
    st.title('Jair - Assistente de Auditoria')
    st.write('Ao digitar uma requisição, tenha o sumário da requisição e uma sugestão do Jair, o assistente de auditoria.')
    st.write('**Como usar a ferramenta:**')
    st.write('Digite o número da requisição no campo abaixo e clique o botão "Enviar".')
    st.write('No lado direito da tela, você verá um resumo da requisição, e abaixo, a resposta do assistente sobre cada item.') 
    st.write('Com base no que o assistente responder, tome a decisão final sobre a requisição.')
    st.write('Ao chegar na sua conclusão sobre a requisição, justifique sua decisão final, avalie a resposta do assistente e nos dê sua opinião sobre a qualidade da resposta.')
    st.write("")
    st.write('**Pontos importantes:**')
    st.write('- As vezes o Jair pode negar ou autorizar uma requisição dado uma condição específica. Por favor, leia a justificativa do assistente e não só a decisão final.')
    st.write('- O Jair é treinado para auxiliar na tomada de decisões no processo de auditoria.')
    st.write('- O Jair não substitui a decisão do auditor.')
    st.write('- Sempre verifique as fontes das respostas do auditor para ter certeza de que ele está fornecendo informações corretas.')
    st.write('- As vezes ao interagir com a página, ele pode te jogar pro topo dele. Não se preocupe, tudo que você fizer é salvo e ')
    st.write('- No final, avalie a resposta para o assistente poder te auxiliar melhor.')

    numberinput1, numberinput2 = st.columns(2)
    with numberinput1:
        if st.session_state.n_req is None:
            n_req_input = st.number_input(
                "Digite o número da requisição:",
                step=1,
                format="%d",
                value=None,
                placeholder="Digite aqui",
                key='n_req_input'  # Assign a unique key
            )
        else:
            # Allow the user to input a new requisition even if one is already set
            n_req_input = st.number_input(
                "Digite o número da requisição:",
                step=1,
                format="%d",
                value=st.session_state.n_req,
                placeholder="Digite aqui",
                key='n_req_input_existing'
            )
        send_button = st.button("Enviar")

    with numberinput2:
        pass

    # Update session state when button is clicked
    if send_button:
        if n_req_input == 0 or n_req_input == str or n_req_input == None:
            st.error('Digite o número da requisição dentro da caixa e aperte "Enviar" para continuar.')
        else:
            # print(f"Requisição ID type: {type(n_req_input)}")
            resumo = get_requisition_details(int(n_req_input), state)
            if resumo == {"Error": "REQUISICAO_ID not found"}:
                st.error("Número da requisição não encontrado. Por favor, confire o número da requisição e tente novamente")
                st.session_state.resumo = None
            else:
                st.session_state.resumo = resumo
                st.session_state.n_req = n_req_input
                st.session_state.final_output = None

###############################################################################################
#############################  Streamlit Display - Resumo Output  #############################
###############################################################################################

if st.session_state.resumo:
    with inputcol2: 
        st.markdown("## Resumo da Requisição:")
        st.write("#### Informações do Beneficiário")
        st.markdown(f"""
        - **Número da Requisição:** {st.session_state.resumo['Número da requisição']}  
        - **Nome do Beneficiário:** {st.session_state.resumo['Nome do beneficiário']}  
        - **Idade do Beneficiário:** {st.session_state.resumo['Idade do beneficiário']} anos  
        - **Situação Contratual:** {st.session_state.resumo['Situação contratual']}  
        - **Período de Carência:** {st.session_state.resumo['Período de carência?']}  
        """)

        st.write("")
        st.write("#### Informações do Atendimento")
        st.markdown(f"""
        - **Médico Solicitante:** {st.session_state.resumo['Médico solicitante']}  
        - **Data da Abertura da Requisição:** {st.session_state.resumo['Data da abertura da requisição']}  
        - **Caráter de Atendimento:** {st.session_state.resumo['Caráter de atendimento (Urgência ou eletiva)']}  
        - **Tipo de Guia:** {st.session_state.resumo['Tipo Guia']}  
        """)

        st.write("")
        st.write("#### Procedimentos Solicitados")
        descricao_procedimentos = st.session_state.resumo['Descrição dos procedimentos']
        if len(descricao_procedimentos) > 5:
            with st.expander(f"Ver todos os {len(descricao_procedimentos)} itens"):
                for codigo, descricao in descricao_procedimentos.items():
                    st.markdown(f"""
                    - **ID do Item:** {codigo}  
                    - **Descrição:** {descricao}  
                    """)
        else:
            for codigo, descricao in descricao_procedimentos.items():
                st.markdown(f"""
                - **ID do Item:** {codigo}  
                - **Descrição:** {descricao}  
                """)
        # Debugging print statement (optional)
        print(f'{st.session_state.resumo}\n\n')

    st.divider()
    if st.session_state.resumo and st.session_state.final_output is None:
        try:
            is_large = len(st.session_state.resumo['Descrição dos procedimentos'])
            if is_large > 4:
                st.toast('Carregando resposta do Jair, essa requisição pode demorar mais que o esperado...', icon="⏳")
            else:
                st.toast('Carregando resposta do Jair, isso pode demorar até 20 segundos...', icon="⏳")
            with st.spinner("O Jair está pensando... ⏳"):
                resultado = fazer_predicao_por_id(st.session_state.resumo['Número da requisição'])
                print("resultado: ", resultado['resultados_bool_dict'])

                final_output = create_justificativa(st.session_state.resumo, resultado['resultados_bool_dict'])
                st.session_state.final_output = final_output
                print("passou")
                print("final output: ", final_output)
                print("\nstate 1: ", st.session_state)
                print("state: ", st.session_state.final_output)
        except ValidationError as e:
            st.error(f"Erro de validação JSON: {e}")
            st.error(traceback.format_exc())
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
            st.error(traceback.format_exc())

###############################################################################################
#############################  Streamlit Display - Jair Output  ###############################
###############################################################################################

if st.session_state.final_output:
    col1, col2, col3, col4 = st.columns([0.3, 3, 2, 1])
    col1.write("")
    col2.write("#### Itens da Requisição")
    col3.write("#### Avaliação do Jair")
    col4.write("#### Ver mais")
    st.divider()

    autorizado_items = []
    negado_items = []
    checkboxes = {}
    justifications = {}

    st.write("")
    st.write("")
    for idx, item in enumerate(st.session_state.final_output["items"]):
        col1, col2, col3, col4 = st.columns([0.3, 3, 2, 1])
        
        # Caxinha pro auditor marcar
        with col1:
            checkboxes[f'check_{idx}'] = st.checkbox("this shouldnt appear", key=f"check_{idx}", label_visibility="collapsed")
        
        # Nome do item e cd do TUSS
        with col2:
            st.markdown(f"#### {item['description']} - {item['Código correspondente ao item']}")
        
        # APROVADO, NEGADO ou SEM CÓDIGO
        with col3:
            st.write(f"**{item.get('Situação', 'Jair não conseguiu processar esse item')}**")
        
        # Toggle para mostrar a resposta do Jair
        with col4:
            toggle_state = st.toggle("Ver mais", key=f"toggle_{idx}")

        # Printar justificativas e criar a váriavel do estado
        st.write("")
        st.write("")
        justificativa_key = f'justificativa_auditor_{idx+1}'
        justificativa_auditor = st.text_input(f"Justificativa pela decisão em {item['description']} - {item['Código correspondente ao item']}",key=justificativa_key)
        justifications[justificativa_key] = justificativa_auditor

        # Quando o toggle liga, mostra mais dados
        if toggle_state:
            st.write("")
            st.markdown(f"##### **Analise do Assistente:**")
            st.markdown(item['analysis'])
            with st.expander("Fonte"):
                source_raw = item.get('source', 'Jair não conseguiu processar esse item')
                source = list(source_raw.items())[0][1]
                st.markdown(f"**Conteudo:** {source}")
        
        st.write("")
        st.write("")
        st.divider()
        st.write("")
        st.write("")

        # print("pain: ", st.session_state.final_output)

        for item in st.session_state.final_output["items"]:
            situacao = item.get("Situação", "")
            if situacao == "AUTORIZADO":
                autorizado_items.append(item)
            elif situacao == "RECUSADO" or situacao == "NEGADO":
                negado_items.append(item)
            else:
                continue

#################################################################################################
#############################  Streamlit Display - Feedback Submission  #########################
#################################################################################################

    all_items_not_found = all(item['Situação'] == "NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO" for item in st.session_state.final_output["items"])

    with st.form(key='my_form'):
        st.write("1 - Para cada item acima, assinale apenas os itens que você AUTORIZA. Também escreva uma breve justificativa.")
        if not all_items_not_found:
            explainIncorrect = st.text_input("2 - Para os itens errados, explique o que o assistente errou (caso não tenha erro, escreva N/A)", key='explainIncorrect')
            st.write("3 - Para os itens que o assistente acertou, qual foi a qualidade da resposta?")
            correctChoiceReview = st.feedback("thumbs", key='correctChoiceReview')
            comment = st.text_input("4 - Se você tiver algum comentário adicional, escreva aqui (opcional)", key='comment')

        submit_button = st.form_submit_button(label="Submeter")

    if submit_button:
        invalid_justifications = [item['description'] for idx, item in enumerate(st.session_state.final_output["items"]) 
                                  if len(justifications.get(f'justificativa_auditor_{idx+1}', '')) < 3]
        if invalid_justifications:
            st.warning(f"As justificativas nos seguintes itens são muito pequenos, siga as intruções e preencha eles:")
            for item in invalid_justifications:
                st.warning(item)
        elif not all_items_not_found and not explainIncorrect.strip():
            st.warning("Por favor, preencha a questão 2. Se não houver erros, escreva 'N/A'.")
        elif not all_items_not_found and correctChoiceReview not in [0, 1]:
            st.warning("Por favor, selecione uma opção na questão 3.")
        else:
            # Guardando feedback no state
            st.session_state.feedback = {
                'authorized_items': [],
                'explainIncorrect': explainIncorrect if not all_items_not_found else '',
                'correctChoiceReview': correctChoiceReview if not all_items_not_found else None,
                'comment': comment if not all_items_not_found else '',
                'justifications': justifications
            }

            # Pegando os itens que foram marcados
            for idx, item in enumerate(st.session_state.final_output["items"]):
                key = f'check_{idx}'
                if checkboxes.get(key):  # Check if the checkbox was ticked
                    item_str = f"{item['description']} - {item['Código correspondente ao item']}"
                    st.session_state.feedback['authorized_items'].append(item_str)

            st.success("Feedback enviado com sucesso!")

            # Mostrando o feedback (para debugging)
            st.markdown("## Feedback Recebido")
            st.write(f"**Itens Autorizados:** {', '.join(st.session_state.feedback['authorized_items']) if st.session_state.feedback['authorized_items'] else 'Nenhum item autorizado.'}")
            if not all_items_not_found:
                st.write(f"**Explicação de Itens Incorretos:** {st.session_state.feedback['explainIncorrect']}")
                st.write(f"**Qualidade das Respostas:** {st.session_state.feedback['correctChoiceReview']}")
                st.write(f"**Comentários Adicionais:** {st.session_state.feedback['comment']}")
            st.write("**Justificativas:**")
            for key, justification in st.session_state.feedback["justifications"].items():
                st.write(f"{key}: {justification}")
    
    # Reniciar app, limpa o state inteiro. Ver o que faremos sobre o session_id
    if st.button("Clique aqui para reniciar"):
        for key in ['n_req', 'resumo', 'final_output', 'feedback']:
            st.session_state[key] = None
        st.rerun()



if __name__ == "__main__":

    if 'run_once' not in st.session_state:
        # This block will only run once
        parser = argparse.ArgumentParser(description="Assistente de Auditoria")
        parser.add_argument('--dev', action='store_true', help="Show the sidebar (dev mode)")
        try:
            args = parser.parse_args()
        except SystemExit as e:
            os._exit(e.code)

        # Store the dev_mode flag and mark that argparse has run
        st.session_state.dev_mode = args.dev
        st.session_state.run_once = True 
        st.rerun()
    
    print("App rodando")

