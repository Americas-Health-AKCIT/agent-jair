### Tarefas de Navegação e Layout
1. **Implementação da Barra de Pesquisa**
   Arquivo: `0_Inicio.py`, `pages/1_Jair.py`, `pages/3_Resultados.py`, `pages/4_Configurações.py`
   ```python
   # Adicionar após st.set_page_config em cada arquivo
   st.markdown("""
   <style>
   .search-container {
       position: fixed;
       top: 0;
       right: 0;
       padding: 1rem;
       z-index: 1000;
   }
   </style>
   """, unsafe_allow_html=True)
   
   with st.container():
       st.markdown('<div class="search-container">', unsafe_allow_html=True)
       st.text_input("🔍 Pesquisar requisição", key="search_requisition")
       st.markdown('</div>', unsafe_allow_html=True)
   ```

2. **Botão Nova Consulta**
   Arquivo: `pages/1_Jair.py`
   ```python
   # Adicionar após a barra de pesquisa
   st.markdown("""
   <style>
   .nova-consulta-btn {
       position: fixed;
       top: 60px;
       right: 1rem;
       z-index: 1000;
   }
   </style>
   """, unsafe_allow_html=True)
   
   with st.container():
       st.markdown('<div class="nova-consulta-btn">', unsafe_allow_html=True)
       if st.button("🔄 Nova Consulta"):
           st.session_state.clear()
           st.rerun()
       st.markdown('</div>', unsafe_allow_html=True)
   ```

3. **Alterações na Estrutura do Menu**
   Arquivo: `.streamlit/config.toml`
   ```toml
   [theme]
   primaryColor = "#50B8FF"  # Cor Austa
   
   [menu]
   # Remover "0_Inicio.py" da lista
   # Renomear "1_Jair.py" para "Consulta com Jair"
   ```

### Tarefas de Estilo e Cores da UI
4. **Estilização de Botões**
   Arquivo: `pages/1_Jair.py`
   ```python
   def change_button_color(widget_label):
       return st.markdown(f"""
           <style>
           .stButton button {{
               background-color: transparent;
               border: 1px solid #ddd;
           }}
           .stButton button:hover,
           .stButton button:active,
           .stButton button:focus {{
               background-color: #50B8FF !important;
               color: white !important;
               border: 1px solid #50B8FF !important;
           }}
           </style>
       """, unsafe_allow_html=True)
   ```

### Tarefas de Layout de Conteúdo
5. **Reestruturação da Página de Análise do Jair**
   Arquivo: `pages/1_Jair.py`
   ```python
   # Substituir a seção de análise atual por:
   with st.expander("Análise do Jair", expanded=True):
       st.markdown("### Você autoriza ou recusa esse item?")
       col1, col2 = st.columns(2)
       with col1:
           autorizar = st.button("✅ Autorizar")
       with col2:
           recusar = st.button("❌ Recusar")
       
       st.markdown("### O que você achou da qualidade da justificativa do Jair?")
       qualidade = st.radio("", ["Boa", "Ruim"], horizontal=True)
       
       st.markdown("### Análise Detalhada")
       # Conteúdo da análise em acordeon
       
       col1, col2, col3 = st.columns([1,1,1])
       with col3:
           st.button("💾 Salvar Resposta")
   ```

6. **Aprimoramento das Informações do Beneficiário**
   Arquivo: `utils/get_requisition_details.py`
   ```python
   def get_requisition_details(requisicao_id, state):
       # Adicionar novas queries
       query_beneficiario = """
       SELECT 
           b.sexo,
           b.cidade,
           p.tipo_plano,
           p.regulamentado,
           p.data_inicio_contrato,
           p.indicacao_clinica,
           r.tipo_guia,
           CASE WHEN EXISTS (
               SELECT 1 FROM tabela_opme o 
               WHERE o.requisicao_id = r.requisicao_id
           ) THEN 'Sim' ELSE 'Não' END as tem_opme
       FROM beneficiarios b
       JOIN planos p ON b.plano_id = p.id
       JOIN requisicoes r ON b.id = r.beneficiario_id
       WHERE r.requisicao_id = %s
       """
       
       # Atualizar o dicionário de resultado
       result.update({
           "Sexo": sexo,
           "Cidade": cidade,
           "Tipo de Plano": tipo_plano,
           "Plano Regulamentado": regulamentado,
           "Data Início Contrato": data_inicio_contrato,
           "Indicação Clínica": indicacao_clinica,
           "Status OPME": tem_opme
       })
   ```

   Arquivo: `pages/1_Jair.py`
   ```python
   # Atualizar seção de informações do beneficiário
   with st.expander("Informações do Beneficiário", expanded=True):
       col1, col2, col3 = st.columns(3)
       with col1:
           st.write("**Nome:**", resumo["Nome do beneficiário"])
           st.write("**Idade:**", resumo["Idade do beneficiário"])
           st.write("**Sexo:**", resumo["Sexo"])
           st.write("**Cidade:**", resumo["Cidade"])
       with col2:
           st.write("**Tipo de Plano:**", resumo["Tipo de Plano"])
           st.write("**Plano Regulamentado:**", resumo["Plano Regulamentado"])
           st.write("**Data Início Contrato:**", resumo["Data Início Contrato"])
       with col3:
           st.write("**Situação Contratual:**", resumo["Situação contratual"])
           st.write("**Período de Carência:**", resumo["Período de carência?"])
           st.write("**Status OPME:**", resumo["Status OPME"])
   ```

### Tarefas da Página de Resultados
7. **Modificações na Página de Resultados (Admin)**
   Arquivo: `pages/3_Resultados.py`
   ```python
   # Substituir título e adicionar seletor de período
   st.title("📊 Minhas Requisições")
   
   col1, col2 = st.columns([2,1])
   with col1:
       periodo = st.date_input(
           "Período de Análise",
           [df['data'].min().date(), df['data'].max().date()]
       )
   
   # Atualizar métricas
   total_req = len(requisitions)
   total_aval = len([r for r in requisitions if r.get('has_evaluation')])
   st.metric("Requisições Avaliadas", f"{total_aval}/{total_req}")
   
   # Atualizar gráficos
   fig_quality = px.line(
       df_quality,
       x='data',
       y='percentual',  # Modificar para usar percentual
       color='avaliacao_qualidade',
       title='Avaliação de Qualidade do Jair',
       color_discrete_map={'concordou': 'green', 'não concordou': 'red'}
   )
   ```

### Tarefas da Página de Configurações
8. **Atualizações na Configuração (Admin)**
   Arquivo: `pages/4_Configurações.py`
   ```python
   # Atualizar tabela de auditores
   st.markdown("### Auditores Cadastrados")
   
   # Converter dados para DataFrame
   df_auditors = pd.DataFrame(auditors_list)
   df_auditors = df_auditors.rename(columns={
       'id': 'ID do Auditor',
       'name': 'Nome',
       'email': 'Email',
       'role': 'Cargo'
   })
   
   # Substituir valores
   df_auditors['Cargo'] = df_auditors['Cargo'].replace({
       'adm': 'administrador',
       'auditor': 'auditor'
   })
   
   # Exibir como tabela horizontal
   st.dataframe(
       df_auditors,
       use_container_width=True,
       hide_index=True
   )
   
   # Seção de alteração de senha
   st.markdown("### Alterar Senha")
   auditor_id = st.selectbox(
       "ID do Auditor",
       options=df_auditors['ID do Auditor'].tolist(),
       format_func=lambda x: f"{x} - {df_auditors[df_auditors['ID do Auditor']==x]['Nome'].iloc[0]}"
   )
   ```

### Recursos Adicionais
9. **Exibição de Status de Requisição**
   Arquivo: `pages/3_Resultados.py`
   ```python
   # Adicionar coluna de status e botão de visualização
   def format_status(row):
       if not row['tem_avaliacao']:
           return "Ainda não avaliado"
       return row['decisao_auditor']
   
   df['status'] = df.apply(format_status, axis=1)
   
   # Adicionar botão de visualização
   def view_button(requisicao_id):
       if st.button("👁️ Ver Requisição", key=f"view_{requisicao_id}"):
           st.session_state.n_req = requisicao_id
           st.switch_page("pages/1_Jair.py")
   
   # Atualizar exibição da tabela
   st.dataframe(
       df[['requisicao', 'data', 'auditor', 'descricao', 'status']]\
       .sort_values('data', ascending=False)\
       .style.format({'data': lambda x: x.strftime('%d/%m/%Y')}),
       column_config={
           "requisicao": st.column_config.Column(
               "Requisição",
               width="medium",
               help="Número da requisição"
           ),
           "view": st.column_config.Column(
               "Ações",
               width="small"
           )
       },
       use_container_width=True
   )
   ```

### Tarefas de Dados e Campos Adicionais
10. **Novos Campos a Serem Implementados**
    Arquivo: `utils/get_requisition_details.py`
    ```python
    # Adicionar novas queries para campos pendentes
    query_doencas = """
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 FROM doencas_pre_existentes d
            WHERE d.beneficiario_id = b.id
        ) THEN 'Sim' ELSE 'Não' END as tem_doencas_pre
    FROM beneficiarios b
    WHERE b.id = %s
    """
    
    query_pagamento = """
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 FROM pagamentos p
            WHERE p.beneficiario_id = b.id
            AND p.data_vencimento < CURRENT_DATE - INTERVAL '2 months'
            AND p.data_pagamento IS NULL
        ) THEN 'Sim' ELSE 'Não' END as tem_atraso
    FROM beneficiarios b
    WHERE b.id = %s
    """
    
    # Atualizar o dicionário de resultado com campos pendentes
    result.update({
        "Doenças Pré-existentes": tem_doencas_pre if tem_doencas_pre else "Informação não disponível",
        "Atraso Pagamento": tem_atraso if tem_atraso else "Informação não disponível"
    })
    ```

11. **Modificações na Estrutura de Dados**
    Arquivo: `model/database.py`
    ```python
    # Criar novas tabelas se necessário
    CREATE_TABLES = """
    CREATE TABLE IF NOT EXISTS doencas_pre_existentes (
        id SERIAL PRIMARY KEY,
        beneficiario_id INTEGER REFERENCES beneficiarios(id),
        doenca VARCHAR(100),
        data_registro DATE
    );
    
    CREATE TABLE IF NOT EXISTS pagamentos (
        id SERIAL PRIMARY KEY,
        beneficiario_id INTEGER REFERENCES beneficiarios(id),
        data_vencimento DATE,
        data_pagamento DATE,
        valor DECIMAL(10,2)
    );
    """
    ```

12. **Atualizações no Frontend**
    Arquivo: `pages/1_Jair.py`
    ```python
    # Reorganizar informações em seções
    with st.expander("Informações do Plano", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Tipo de Plano:**", resumo["Tipo de Plano"])
            st.write("**Plano Regulamentado:**", resumo["Plano Regulamentado"])
            st.write("**Data Início Contrato:**", resumo["Data Início Contrato"])
        with col2:
            st.write("**Doenças Pré-existentes:**", resumo["Doenças Pré-existentes"])
            st.write("**Atraso Pagamento:**", resumo["Atraso Pagamento"])
    
    with st.expander("Informações do Atendimento", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Tipo de Guia:**", resumo["Tipo Guia"])
            st.write("**Tipo de Internação:**", resumo["DS_TIPO_INTERNACAO"])
            st.write("**Regime de Internação:**", resumo["DS_REGIME_INTERNACAO"])
        with col2:
            st.write("**Status OPME:**", resumo["Status OPME"])
            st.write("**Tipo SADT:**", resumo["DS_TIPO_SADT"])
            st.write("**Tipo Consulta:**", resumo["DS_TIPO_CONSULTA"])
    ```
