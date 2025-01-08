import os
import time
from datetime import datetime, timedelta

# Caminho do diretório
caminho_diretorio = './response_llm'

# Função para listar arquivos e marcar a hora de criação
def listar_arquivos_e_horario_criacao(caminho):
    
    arquivos = []
    
    for arquivo in os.listdir(caminho):
        caminho_arquivo = os.path.join(caminho, arquivo)
        
        if os.path.isfile(caminho_arquivo):
            # Obtendo o timestamp de criação
            hora_criacao = os.path.getctime(caminho_arquivo)
            arquivos.append(hora_criacao)
            
    return arquivos

# Função para ordenar a lista de horários e calcular as diferenças
def calcular_diferencas(lista_tempos):
    lista_tempos.sort()  # Ordena a lista de tempos
    diferencas = []

    for i in range(1, len(lista_tempos)):
        # Calcula a diferença entre os tempos consecutivos
        diferenca = lista_tempos[i] - lista_tempos[i-1]
        diferencas.append(diferenca)
        
    return diferencas

# Função para formatar as diferenças para um formato legível
def formatar_diferencas(diferencas):
    diferencas_formatadas = []
    for diferenca in diferencas:
        diferenca_legivel = str(datetime.utcfromtimestamp(diferenca).strftime("%H:%M:%S"))
        diferencas_formatadas.append(diferenca_legivel)
    return diferencas_formatadas

# Função para remover diferenças maiores que uma hora e somar as horas
def remover_e_somar_horas_maiores_que_uma(diferencas):
    diferencas_menores_que_uma_hora = []
    soma_diferencas_maiores = timedelta()  # Inicializando para somar horas
    
    for diferenca in diferencas:
        if diferenca > 3600:  # Se a diferença for maior que uma hora (3600 segundos)
            soma_diferencas_maiores += timedelta(seconds=diferenca)
        else:
            diferencas_menores_que_uma_hora.append(diferenca)
    
    return diferencas_menores_que_uma_hora, soma_diferencas_maiores

# Chamar a função com o caminho do diretório desejado
lista_tempo = listar_arquivos_e_horario_criacao(caminho_diretorio)

# Calcular as diferenças
diferencas = calcular_diferencas(lista_tempo)

# Remover diferenças maiores que uma hora e somar as horas
diferencas_menores, soma_maiores = remover_e_somar_horas_maiores_que_uma(diferencas)

# Formatando as diferenças menores para exibição legível
diferencas_menores_formatadas = formatar_diferencas(diferencas_menores)

# Exibindo as diferenças menores que uma hora
print("Diferenças menores que uma hora:")
for i, diferenca in enumerate(diferencas_menores_formatadas, 1):
    print(f"Diferença {i}: {diferenca}")

# Exibindo a soma das diferenças maiores que uma hora
print("\nSoma total das diferenças maiores que uma hora:")
print(str(soma_maiores))
