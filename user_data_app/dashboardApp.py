import os
import streamlit as st
from streamlit_option_menu import option_menu
st.set_page_config(layout="wide")
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from langchain_openai import ChatOpenAI
import dotenv
dotenv.load_dotenv()
current_directory = os.path.dirname(os.path.abspath(__file__))
save_charts_path = os.path.join(current_directory, "charts")
os.makedirs(save_charts_path, exist_ok=True)
from pandasai import SmartDataframe
from config.config import settings


llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)

# Load the CSV data
req_df = pd.read_csv('./auditor_avaliacao.csv')
req_item_df = pd.read_csv('./auditor_avaliacao_itens.csv')
merged_df = pd.merge(req_df, req_item_df, on='id_auditor_avalicao')
req_df['date'] = pd.to_datetime(req_df['date'], errors='coerce')
merged_df['date'] = pd.to_datetime(merged_df['date'], errors='coerce')

if 'llm_output' not in st.session_state:
    st.session_state.llm_output = None

if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 'Dashboard'  # Default tab


###############################################################################
#############################  Streamlit Display  #############################
###############################################################################

titleCol1, titleCol2, titleCol3 = st.columns([1, 2, 1])
with titleCol1:
    pass

with titleCol2:
    st.title("Dashboard + Consulte os Dados")
    selected_tab = option_menu(
        menu_title='Páginas',
        options=['Dashboard', 'Consulte os Dados'],
        icons=['dpad', 'book'],
        menu_icon='pie-chart',
        orientation='horizontal',
        default_index=0 if st.session_state.current_tab == 'Dashboard' else 1
    )
    
    # Update the tab state if a new tab is selected
    if selected_tab != st.session_state.current_tab:
        st.session_state.current_tab = selected_tab
        st.rerun()  # Immediately rerun the app to apply the tab change

with titleCol3:
    pass

st.write("")
st.write("")

# "Consulte os Dados" tab functionality
if st.session_state.current_tab == 'Consulte os Dados':
    sdf = SmartDataframe(merged_df, config={"llm": llm, "save_charts": True, "save_charts_path": save_charts_path, "open_charts": False, "save_logs": False})
    st.dataframe(merged_df)
    prompt = st.text_area("Enter your prompt")

    if st.button("Generate"):
        if prompt:
            with st.spinner("Generating Response..."):
                response = sdf.chat(prompt)
                if isinstance(response, str) and os.path.exists(response) and response.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    st.success(response)
                    st.image(response)
                else:
                    st.write("### GPT: ")
                    st.write("#####", str(response))
        else:
            st.warning("Please enter a prompt")

elif st.session_state.current_tab == 'Dashboard':

    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # 1. Distribution of Evaluation Ratings
            req_df['evaluation_display'] = req_df['evaluation'].replace({True: "Positivo", False: "Negativo"})
            fig1 = px.histogram(req_df, x='evaluation_display', title='Avaliação da Qualidade da Resposta do Modelo',
                                category_orders={"evaluation_display": ["Positivo", "Negativo"]})
            st.plotly_chart(fig1)

        with col2:
            # 2. Auditor's Error Justification Word Cloud
            st.markdown("###### WordCloud da Justificativa de Erro do Auditor")
            wordcloud = WordCloud(background_color='white').generate(' '.join(req_df['auditor_error_justification']))
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            st.pyplot(plt)

    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)

        with col3:
            # 3. Count of Matching vs Conflicting Decision
            decision_counts = merged_df['agent_decision_error'].replace({True: "Positivo", False: "Negativo"}).value_counts().reset_index()
            decision_counts.columns = ['Decision', 'Count']

            fig2 = px.bar(decision_counts, x='Decision', y='Count',
                          title='Congruência vs Conflito nas Decisões',
                          category_orders={"Decision": ["Positivo", "Negativo"]},
                          labels={'Decision': 'Conflito de Decisão'})

            st.plotly_chart(fig2)

        with col4:
            # 4. Auditor Decision vs Agent Decision Confusion Matrix
            confusion_matrix = pd.crosstab(merged_df['auditor_decision'], merged_df['agent_decision'])
            z = confusion_matrix.values
            fig3 = go.Figure(data=go.Heatmap(
                z=z,
                x=confusion_matrix.columns,
                y=confusion_matrix.index,
                hoverinfo='text',
                text=z,
                texttemplate="%{text}",
                colorscale='Blues'
            ))
            fig3.update_layout(
                title='Auditor Decision vs Agent Decision',
                xaxis_title='Agent Decision',
                yaxis_title='Auditor Decision'
            )
            st.plotly_chart(fig3)

    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)

        with col5:
           # 5. Agent Decision Errors (Por Semana)
           merged_df['week'] = merged_df['date'].dt.to_period('W')
           error_by_month = merged_df.groupby('week')['agent_decision_error'].sum().reset_index()
           error_by_month['week'] = error_by_month['week'].dt.to_timestamp()
           fig4 = px.line(error_by_month, x='week', y='agent_decision_error',
                          title='Agent Decision Errors Over Time (Weekly Aggregation)')
           fig4.update_layout(xaxis_title='Week', yaxis_title='Agent Decision Errors')
           st.plotly_chart(fig4)

        with col6:
            # 6. Evaluation Ratings Over Time (Histogram with 7-Day Bins)
            req_df['7_day_period'] = req_df['date'].dt.to_period('7D').dt.start_time
            eval_counts = req_df.groupby(['7_day_period', 'evaluation_display']).size().reset_index(name='counts')
            fig5 = px.histogram(eval_counts, x='7_day_period', y='counts', color='evaluation_display', barmode='group',
                                title='Evaluation Ratings Over Time (7-Day Bins)')
            fig5.update_layout(xaxis_title='Date', yaxis_title='Count of Evaluations')
            st.plotly_chart(fig5)


    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        col7, col8 = st.columns(2)

        with col7:
            # 7. Count of Items by Decision (Authorized/Denied by Auditor)
            auditor_decision_df = merged_df.copy()  
            auditor_decision_df['auditor_decision_display'] = auditor_decision_df['auditor_decision'].replace({
                True: "Autorizado", False: "Negado", pd.NA: "Cod. not found"
            })
            fig6 = px.pie(auditor_decision_df, names='auditor_decision_display', title='Count of Items by Auditor Decision')
            st.plotly_chart(fig6)

        with col8:
            # 8. Count of Items by Agente Decision
            agent_decision_df = merged_df.copy()  
            agent_decision_df['agent_decision_display'] = agent_decision_df['agent_decision'].replace({
                True: "Autorizado", False: "Negado", pd.NA: "Cod. not found"
            })
            fig8 = px.pie(agent_decision_df, names='agent_decision_display', title='Count of Items by Agente Decision')
            st.plotly_chart(fig8)

    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        col9, col10 = st.columns(2)

        with col9:
            st.write("")
            st.markdown("<br><br><br><br><br><h3 style='text-align: center;'>Alguem adicione um gráfico aqui, não tive outra ideia</h3>", unsafe_allow_html=True)

        with col10:
            st.write("")
            st.markdown("<br><br><br><br><br><h3 style='text-align: center;'>Alguem adicione um gráfico aqui, não tive outra ideia</h3>", unsafe_allow_html=True)