import dotenv
dotenv.load_dotenv()

import sys
print(sys.executable)

import json

from utils.state import STATE_CLASS
from utils.get_requisition_details import get_requisition_details

from justificador.justificador import justificador

from modelo_ml_tradicional.inference import carregar_modelo_e_pipeline, fazer_predicao_por_id


response_test = {13692546: True, 13692559: True, 13692560: True, 13692561: True, 13692562: True, 13692563: True, 13692564: True, 13692576: True, 13692577: True, 13692578: True, 13692579: True, 13692580: True, 13692581: True, 13692582: True, 13692584: True, 13692607: True, 13692543: True, 13692549: True, 13692547: True, 13692552: False, 13692555: True, 13692556: True, 13692558: True, 13692565: True, 13692566: True, 13692567: True, 13692568: True, 13692569: True, 13692570: True, 13692571: True, 13692572: True, 13692573: True, 13692574: True, 13692586: True, 13692587: True, 13692588: True, 13692590: False, 13692591: False, 13692592: True, 13692593: True, 13692594: True, 13692595: True, 13692596: True, 13692597: True, 13692598: True, 13692599: True, 13692600: True, 13692601: True, 13692602: True, 13692603: False, 13692604: True, 13692605: True, 13692606: True}

def process_requisition():
    raise NotImplementedError("Parte onde o input é o resumo, e o output é a resposta do modelo")

def create_justificativa(resumo, response):

    paciente_info = {
        'ID_REQUISICAO': resumo['Número da requisição'],
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