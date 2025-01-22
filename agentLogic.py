import dotenv
dotenv.load_dotenv()

import sys
print(sys.executable)

from utils.state import STATE_CLASS
from utils.get_requisition_details import get_requisition_details

from justificador.justificador import justificador


def get_state():
    return STATE_CLASS()

state = get_state()

resumo = get_requisition_details(41971486, state) 

# model = None #enquanto não temos o modelo
# response = model(resumo)

response = {40306798: False,
            40308383: True,
            40324192: True,
            40304361: False,
            40311210: True}


paciente_info = {
    'ID_REQUISICAO': resumo['ID_REQUISICAO'],
    'Nome do beneficiário': resumo['Nome do beneficiário'],
    'Médico solicitante': resumo['Médico solicitante'],
    'DT_REQUISICAO': resumo['DT_REQUISICAO'],
    'DS_TIPO_GUIA': resumo['DS_TIPO_GUIA'],
    'DS_CARATER_ATENDIMENTO': resumo['DS_CARATER_ATENDIMENTO'],
    'Idade do beneficiário': resumo['Idade do beneficiário'],
    'DATA_CANCELAMENTO': resumo['DATA_CANCELAMENTO'],
    'DATA_FIM_CARENCIA': resumo['DATA_FIM_CARENCIA'],
    'DS_CBO_PROFISSIONAL': resumo['DS_CBO_PROFISSIONAL'],
    'DS_TIPO_INTERNACAO': resumo['DS_TIPO_INTERNACAO'],
    'DS_REGIME_INTERNACAO': resumo['DS_REGIME_INTERNACAO'],
    'DS_TIPO_SADT': resumo['DS_TIPO_SADT'],
    'DS_TIPO_CONSULTA': resumo['DS_TIPO_CONSULTA'],
    'TITULARIDADE': resumo['TITULARIDADE'],
    'DATA_NASCIMENTO': resumo['DATA_NASCIMENTO']
}

justificativas = []
for id_item, item_desc in resumo["DS_ITEM"].items():
    classificacao = resumo["DS_CLASSIFICACAO_1"].get(id_item, "N/A")
    
    justificativas.append(justificador(id_item, {"DS_ITEM": item_desc, "DS_CLASSIFICACAO_1": classificacao}, paciente_info, status=response[id_item]))

# print("Resumo: ", resumo)