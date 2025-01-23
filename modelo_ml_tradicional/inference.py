import pandas as pd
import joblib
from main import carregar_dados, preparar_merged

import dotenv
dotenv.load_dotenv()

import sys
print(sys.executable)

#from utils.state import STATE_CLASS
#from utils.get_requisition_details import get_requisition_details

#from justificador.justificador import justificador

#def get_state():
#    return STATE_CLASS()

#state = get_state()


def carregar_modelo_e_pipeline():
    """Carrega o modelo treinado e a pipeline de transformação."""
    pipeline = joblib.load('modelo_ml_tradicional/pipeline_transformers.joblib')
    model = joblib.load('modelo_ml_tradicional/xgboost_model.joblib')
    return model, pipeline

def fazer_predicao_por_id(id_requisicao):
    """
    Faz a predição para uma requisição específica usando o ID_REQUISICAO.
    
    Args:
        id_requisicao: ID da requisição para fazer a predição
        
    Returns:
        dict: Dicionário contendo a predição e probabilidades
    """
    # Carrega os dados
    df_requisicao, df_itens, df_itens_nome, df_beneficiario, df_prestador = carregar_dados()
    
    print(f"\nDebug - Shapes iniciais:")
    print(f"df_requisicao: {df_requisicao.shape}")
    print(f"df_itens: {df_itens.shape}")
    print(f"df_itens_nome: {df_itens_nome.shape}")
    print(f"df_beneficiario: {df_beneficiario.shape}")
    
    # Filtra apenas a requisição desejada
    df_requisicao_filtrado = df_requisicao[df_requisicao['ID_REQUISICAO'] == id_requisicao]
    print(f"\nDebug - Após filtro por ID_REQUISICAO {id_requisicao}:")
    print(f"df_requisicao_filtrado shape: {df_requisicao_filtrado.shape}")
    
    if df_requisicao_filtrado.empty:
        raise ValueError(f"ID_REQUISICAO {id_requisicao} não encontrado em df_requisicao")
    
    # Prepara os dados da mesma forma que no treino
    df_merged = preparar_merged(df_requisicao_filtrado, df_itens, df_beneficiario, df_itens_nome)
    print(f"\nDebug - Após merge:")
    print(f"df_merged shape: {df_merged.shape}")
    
    if df_merged.empty:
        print("\nDebug - Verificando joins intermediários:")
        # Verifica join com itens
        df_itens_filtered = df_itens[df_itens['ID_REQUISICAO'] == id_requisicao]
        print(f"Itens encontrados para a requisição: {df_itens_filtered.shape[0]}")
        if not df_itens_filtered.empty:
            print("IDs dos itens encontrados:", df_itens_filtered['ID_ITEM'].tolist())
            
            # Verifica se esses IDs existem em df_itens_nome
            itens_encontrados = df_itens_nome[df_itens_nome['ID_ITEM'].isin(df_itens_filtered['ID_ITEM'])]
            print(f"Itens encontrados em df_itens_nome: {itens_encontrados.shape[0]}")
        
        raise ValueError("Após merge, não foram encontrados dados para fazer a predição")
    
    # Guarda os IDs dos itens e descrições antes da transformação
    ids_itens = df_merged['ID_REQUISICAO_ITEM'].tolist()
    descricoes_itens = df_merged['DS_ITEM'].tolist()
    
    # Carrega modelo e pipeline
    model, pipeline = carregar_modelo_e_pipeline()
    
    # Aplica as transformações
    X_transform = pipeline.transform(df_merged)
    print(f"\nDebug - Após transformação:")
    print(f"X_transform shape: {X_transform.shape}")
    
    # Remove colunas de ID e data se existirem
    colunas_para_remover = ['ID_REQUISICAO_ITEM', 'DT_ATUALIZACAO_x', 'ID_REQUISICAO', 'DS_STATUS_ITEM']
    colunas_existentes = [col for col in colunas_para_remover if col in X_transform.columns]
    X_transform = X_transform.drop(columns=colunas_existentes)
    
    print(f"\nDebug - Após remover colunas de ID:")
    print(f"X_transform shape final: {X_transform.shape}")
    
    if X_transform.empty:
        raise ValueError("Dados transformados estão vazios")
    
    # Faz a predição
    predicoes = model.predict(X_transform)
    probabilidades = model.predict_proba(X_transform)
    
    # Mapeia o resultado
    mapa_status_reverso = {0: 'Recusado', 1: 'Aprovado'}
    
    # Prepara resultados detalhados
    resultados_detalhados = []
    resultados_bool_dict = {}  # Novo dicionário para formato {id: bool}
    
    for i in range(len(predicoes)):
        resultado = {
            'id_requisicao': id_requisicao,
            'id_requisicao_item': ids_itens[i],
            'descricao_item': descricoes_itens[i],
            'predicao': mapa_status_reverso[predicoes[i]],
            'probabilidade_recusado': probabilidades[i][0],
            'probabilidade_aprovado': probabilidades[i][1]
        }
        resultados_detalhados.append(resultado)
        # Adiciona ao dicionário booleano (True para Aprovado, False para Recusado)
        resultados_bool_dict[ids_itens[i]] = (predicoes[i] == 1)
    
    # Imprime resultados detalhados
    print("\nResultados Detalhados por Item:")
    print("-" * 100)
    for resultado in resultados_detalhados:
        print(f"ID Item: {resultado['id_requisicao_item']}")
        print(f"Descrição: {resultado['descricao_item']}")
        print(f"Predição: {resultado['predicao']}")
        print(f"Probabilidade Recusado: {resultado['probabilidade_recusado']:.2%}")
        print(f"Probabilidade Aprovado: {resultado['probabilidade_aprovado']:.2%}")
        print("-" * 100)
    
    print("\nDicionário de Resultados (ID: bool):")
    print(resultados_bool_dict)
    
    # Retorna o resultado geral (mantendo a compatibilidade)
    return {
        'id_requisicao': id_requisicao,
        'resultados_por_item': resultados_detalhados,
        'resultados_bool_dict': resultados_bool_dict,  # Novo campo
        'predicao': 'Aprovado' if all(r['predicao'] == 'Aprovado' for r in resultados_detalhados) else 'Recusado',
        'total_itens': len(resultados_detalhados),
        'itens_aprovados': sum(1 for r in resultados_detalhados if r['predicao'] == 'Aprovado'),
        'itens_recusados': sum(1 for r in resultados_detalhados if r['predicao'] == 'Recusado')
    }

if __name__ == '__main__':
    # Exemplo de uso
    try:
        id_requisicao = 41633869  
        resultado = fazer_predicao_por_id(id_requisicao)
        print("\nResumo da Predição:")
        print(f"ID Requisição: {resultado['id_requisicao']}")
        print(f"Total de Itens: {resultado['total_itens']}")
        print(f"Itens Aprovados: {resultado['itens_aprovados']}")
        print(f"Itens Recusados: {resultado['itens_recusados']}")
        print(f"Resultado Final: {resultado['predicao']}")
        print("\nDicionário de Resultados:")
        print(resultado['resultados_bool_dict'])

    except Exception as e:
        print(f"Erro ao fazer predição: {str(e)}") 

#    resumo = get_requisition_details(id_requisicao, state) 
#
#    response = resultado['resultados_bool_dict']
#
#    paciente_info = {
#        'ID_REQUISICAO': resumo['ID_REQUISICAO'],
#        'Nome do beneficiário': resumo['Nome do beneficiário'],
#        'Médico solicitante': resumo['Médico solicitante'],
#        'DT_REQUISICAO': resumo['DT_REQUISICAO'],
#        'DS_TIPO_GUIA': resumo['DS_TIPO_GUIA'],
#        'DS_CARATER_ATENDIMENTO': resumo['DS_CARATER_ATENDIMENTO'],
#        'Idade do beneficiário': resumo['Idade do beneficiário'],
#        'DATA_CANCELAMENTO': resumo['DATA_CANCELAMENTO'],
#        'DATA_FIM_CARENCIA': resumo['DATA_FIM_CARENCIA'],
#        'DS_CBO_PROFISSIONAL': resumo['DS_CBO_PROFISSIONAL'],
#        'DS_TIPO_INTERNACAO': resumo['DS_TIPO_INTERNACAO'],
#        'DS_REGIME_INTERNACAO': resumo['DS_REGIME_INTERNACAO'],
#        'DS_TIPO_SADT': resumo['DS_TIPO_SADT'],
#        'DS_TIPO_CONSULTA': resumo['DS_TIPO_CONSULTA'],
#        'TITULARIDADE': resumo['TITULARIDADE'],
#        'DATA_NASCIMENTO': resumo['DATA_NASCIMENTO']
#    }
#
#    justificativas = []
#    for id_item, item_desc in resumo["DS_ITEM"].items():
#        classificacao = resumo["DS_CLASSIFICACAO_1"].get(id_item, "N/A")
#        
#        justificativas.append(justificador(id_item, {"DS_ITEM": item_desc, "DS_CLASSIFICACAO_1": classificacao}, paciente_info, status=response[id_item]))
