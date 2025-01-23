import dotenv
dotenv.load_dotenv()

import sys
print(sys.executable)

import json

from utils.state import STATE_CLASS
from utils.get_requisition_details import get_requisition_details

from justificador.justificador import justificador


response_test = {40306798: False,
            40308383: True,
            40324192: True,
            40304361: False,
            40311210: True}

def process_requisition():
    raise NotImplementedError("Parte onde o input é o resumo, e o output é a resposta do modelo")

def create_justificativa(resumo, response=response_test):

    paciente_info = {
        'ID_REQUISICAO': resumo['Número da requisição'],
        'Nome do beneficiário': resumo['Nome do beneficiário'],
        'Médico solicitante': resumo['Médico solicitante'],
        'DT_REQUISICAO': resumo['Data da abertura da requisição'],
        'DS_TIPO_GUIA': resumo['Tipo Guia'],
        'DS_CARATER_ATENDIMENTO': resumo['Caráter de atendimento (Urgência ou eletiva)'],
        'Idade do beneficiário': resumo['Idade do beneficiário'],
        'DATA_CANCELAMENTO': resumo['Situação contratual'],
        'DATA_FIM_CARENCIA': resumo['Período de carência?'],
        'DS_CBO_PROFISSIONAL': resumo['DS_CBO_PROFISSIONAL'],
        'DS_TIPO_INTERNACAO': resumo['DS_TIPO_INTERNACAO'],
        'DS_REGIME_INTERNACAO': resumo['DS_REGIME_INTERNACAO'],
        'DS_TIPO_SADT': resumo['DS_TIPO_SADT'],
        'DS_TIPO_CONSULTA': resumo['DS_TIPO_CONSULTA'],
        'TITULARIDADE': resumo['TITULARIDADE'],
        'DATA_NASCIMENTO': resumo['DATA_NASCIMENTO']
    }

    justificativas = []
    id_itens = []
    item_descs = []
    classificacoes = []
    fontes = []
    responses = []

    ds_item_map = resumo["Descrição dos procedimentos"]
    ds_classificacao_map = resumo["Tipo dos itens (nivel 2)"]
    
    for id_item, item_desc in ds_item_map.items():
        classificacao = ds_classificacao_map.get(id_item, "N/A")  # Lookup classification
        justificativa, fonte = justificador(
            id_item,
            {"DS_ITEM": item_desc, "DS_CLASSIFICACAO_1": classificacao},
            paciente_info,
            status=response.get(id_item)
        )

        justificativas.append(justificativa)
        fontes.append(fonte)
        id_itens.append(id_item)
        item_descs.append(item_desc)
        classificacoes.append(classificacao)
        responses.append(response[id_item])

    items = []
    for id_item, item_desc, fonte, justificativa, response in zip(id_itens, item_descs, fontes, justificativas, responses):
        situacao = "AUTORIZADO" if response else "NEGADO"
        item = {
            "Código correspondente ao item": id_item,
            "description": item_desc,
            "source": fonte,
            "analysis": justificativa,
            "Situação": situacao
        }
        items.append(item)

    data = {"items": items}

    return data

if __name__ == "__main__":

    def get_state():
        return STATE_CLASS()

    state = get_state()

    resumo = get_requisition_details(41971486, state) 
    print("Resumo: ", resumo)
    # model = None #enquanto não temos o modelo
    # response = model(resumo)

    data = create_justificativa(resumo)