#from model.train import train_model
#
#model, pipeline = train_model(
#    ano=2024,
#    mes=8
#)


from model.inference import fazer_predicao_por_id

# ID da requisição para predição

import pandas as pd

resultado = fazer_predicao_por_id(41003166)

# Imprime o resumo dos resultados
print("\nResumo da Predição:")
print(f"ID da Requisição: {resultado['id_requisicao']}")
print(f"Total de Itens: {resultado['total_itens']}")
print(f"Itens Aprovados: {resultado['itens_aprovados']}")
print(f"Itens Recusados: {resultado['itens_recusados']}")

print("\nDicionário de Resultados:")
print(resultado['resultados_bool_dict'])