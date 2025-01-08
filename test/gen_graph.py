import matplotlib.pyplot as plt
import pandas as pd


colors = { 'AUTORIZADO': 'green', 
            'RECUSADO': 'red', 
            'NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO': '#FFA500',
            'Default': '#FFA500',
            'Alucinação': '#FFA500'
        }


def make_pie(ax, serie):
        # sort series by index
        serie = serie.sort_index()
        
        _, texts, _ = ax.pie( serie,  
                              labels=serie.index,  
                                        autopct='%1.1f%%',  
                              colors=serie.index.map(colors).values)
        for text in texts:
            if ('AUTORIZADO' in text.get_text()) or ('RECUSADO' in text.get_text()):
                text.set_fontweight('bold')  
                text.set_color(colors[text.get_text()])                         
                text.set_fontsize(12)
        
        ax.set_ylabel('')


def gen_graph(df_input, path_To_save):        

    df = df_input.copy()
    df.y_hat = df.y_hat.apply(lambda x: 'AUTORIZADO' if 'AUTORIZADO' in x else x)
    
    dict_status = {True: 'AUTORIZADO', 
                   False: 'RECUSADO',
                   'True': 'AUTORIZADO',
                'False': 'RECUSADO',
                   }
    df.STATUS = df.STATUS.map(dict_status)
    df.y_hat = df.y_hat.apply(lambda x: 'Alucinação' if 'Default' in x else x)
    df['acerto'] = df.STATUS == df.y_hat
    df['erro'] = df.STATUS != df.y_hat
    df['sem_doc_or_codigo'] = (df.y_hat == 'NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO') | (df.y_hat == 'Alucinação')
    ######
    qtd_itens = df.shape[0]
    
    
    fig, axs = plt.subplots(4, 2, figsize=(20, 15))
    df_filtrado = df[~df['sem_doc_or_codigo']]
    ################# 0, 0
    ax = axs[0][0]
    acuracia_geral = df_filtrado.acerto.sum() / df_filtrado.shape[0]

    # horizontal bar plot
    ax.barh(0,df_filtrado.shape[0], color='gray', label='Total', edgecolor='black',alpha=0.4)
    ax.barh(0,df_filtrado.acerto.sum(), color='green', label='Acertos')

    ax.legend()
    ax.set_title(f'Acurácia do modelo - {acuracia_geral:.2f}')
    ax.set_yticks([])





    ################# 0, 1
    ax = axs[0][1]
    percent_without_context = (df.sem_doc_or_codigo.sum() / df.shape[0]) * 100
    ax.barh(0,df.shape[0], color='gray', label='Total',alpha=0.4)
    ax.barh(0,df['sem_doc_or_codigo'].sum()+df.acerto.sum(), color='green', label='Acertos')
    
    ax.barh(0,df['sem_doc_or_codigo'].sum(), color='#FFA500', label='Sem Documentos ou Código')

    ax.legend()
    ax.set_title(f'Sem códigou ou sem informações - {percent_without_context:.2f} %')
    ax.set_yticks([])


    ################# 1, 0 -  dos itens Autorizados, quais foram autorizados?
    ax = axs[1][0]
    df_autorizado = df[df.STATUS == 'AUTORIZADO']
    df_autorizado = df_autorizado.y_hat.value_counts()
    df_autorizado = df_autorizado[df_autorizado.index != 'NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO']
    make_pie(ax, df_autorizado)
    ax.set_title('Apenas Itens Autorizados ( {} itens )'.format(df_autorizado.sum()))
    
    

    ################# 1, 1 - Dos itens Autorizados respondidos, quais foram autorizados?
    ax = axs[1][1]
    df_autorizado = df [ (df.STATUS == 'AUTORIZADO') & ((df.y_hat == 'AUTORIZADO') | (df.y_hat == 'RECUSADO'))]
    df_autorizado = df_autorizado.y_hat.value_counts()
    make_pie(ax, df_autorizado)
    ax.set_title('Dos itens Autorizados, quantos foram respondidos?( {} itens )'.format(df_autorizado.sum()))
    


    #######################################
    #################### ITENS NEGADOS
    #######################################


    ################# 2, 0 - dos itens Negados, quantos foram realmente negados?
    ax = axs[2][0]
    df_recusado = df[df.STATUS == 'RECUSADO']
    df_recusado = df_recusado.y_hat.value_counts()
    df_recusado = df_recusado[df_recusado.index != 'NÃO ENCONTRADO DOCUMENTOS QUE AUXILIEM A DECISÃO']
    make_pie(ax, df_recusado)
    ax.set_title('Apenas Itens recusados ({} itens )'.format(df_recusado.sum()))






    # Dos itens REJEITADOS respondidos, quais foram autorizados?
    ax = axs[2][1]
    df_recusado = df [ (df.STATUS == 'RECUSADO') & ((df.y_hat == 'AUTORIZADO') | (df.y_hat == 'RECUSADO'))]
    df_recusado = df_recusado.y_hat.value_counts()
    make_pie(ax, df_recusado)
    ax.set_title('Dos itens recusados, quantos foram respondidos?( {} itens )'.format(df_recusado.sum()))
    
    ########################
    ## matriz de confusao
    #####################
    
    ax = axs[3][0]
    respondidos = df[ (df.y_hat == 'AUTORIZADO') | (df.y_hat == 'RECUSADO')]
    confusion_matrix = pd.crosstab(respondidos.STATUS, respondidos.y_hat)
    if confusion_matrix.shape[0] + confusion_matrix.shape[1]  > 0:
        confusion_matrix.plot(kind='bar', ax=ax, color=[colors[x] for x in confusion_matrix.columns],
                            edgecolor='black')
    
    ax.set_title(f'Matriz de Confusão - apenas dos itens considerados como respondidos ( {respondidos.shape[0]} itens )')
    ax.xaxis.set_label_text('Status do Item', fontsize=12, fontweight='bold')
    ax.legend(title='Classificação do Modelo')
    
    
    
    #######################
    ## procedimentos/materiais aprovados e rejeitados
    #######################
    
    ax = axs[3][1]
    status_counts = df_input.groupby(['DS_TIPO_ITEM', 'STATUS']).size().unstack(fill_value=0)
    cores = ['red', 'green']
    status_counts.plot(kind='bar', stacked=True, color=cores, ax=ax)
    ax.set_title('Contagem de STATUS por Tipo de Item')
    ax.set_xlabel('Tipo de Item', fontweight='bold') 
    ax.set_ylabel('Contagem')
    ax.legend(title='STATUS', labels=['Erro', 'Acerto'])
    for container in ax.containers:
        ax.bar_label(container, label_type='center', color='white')

    fig.savefig(path_To_save)
    plt.close(fig)
    
    
    return acuracia_geral, percent_without_context,qtd_itens


    