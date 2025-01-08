# JAIR

Agente capaz de automatizar o trabalho dos atendentes.

A pipeline atual do agente segue o seguinte esquema:

- Dado uma requisição, criamos um resumo da requisição. Esse resumo é usado pelo auditor e o agente, e contém as informações mais importantes
- Nos criamos os dois prompts para ele. O primeiro prompt tem apenas informações sobre um dos itens da requisição, e é pedido que o agente pese os pros e contras de autorizar ou negar o item.
- O segundo prompt válida a saida do primeiro prompt e toma a decisão final após ler o que o primeiro agente escolheu.
- Antes de passar os itens para o modelo e rodar os prompts, a gente verifica se o código daquela requisição está na nossa base. Se ela estiver, a gente deixa o modelo tomar uma decisão. Se não estiver, a gente não avalia o item e deixa o seu status como "Não encontrado código nos documentos". Isso é para evitar alucinações de códigos (porém as vezes ele continua não achando códigos).
- Assim, a gente passa cada item para a pipeline, e o modelo usa o RAG para conseguir achar o melhor chunk que pode ajudar com a avaliação.
- Ele termina a requisição e completa seu trabalho

# Como rodar código

### app.py

Uso de variáveis de ambiente para rodar o código, é recomendado criar um arquivo .env com as variáveis de ambiente necessárias.

```bash
   export DATA_PATH=./data/embeddings_05_09_2024
   export OPENAI_API_KEY=
   export JUDGE_MODEL=GPT-4o

   # Salvar o feedback do usuário
   export FEEDBACK_ADRESS=
   export FEEDBACK_PORT=80

   # carregar os dados de requisições
   export REQUISICOES_ADRESS_OR_PATH=./data/Dados_Novos_30_07_2024/
   export REQUISICOES_PORT=80
```

- DATA_PATH: Caminho para o arquivo de embeddings.
- OPENAI_API_KEY: Chave de API do OpenAI.
- FEEDBACK_ADRESS: Endereço para salvar o feedback do usuário.
- FEEDBACK_PORT: Porta para salvar o feedback do usuário.
- REQUISICOES_ADRESS_OR_PATH: Endereço para carregar os dados de requisições, ou o caminho para os arquivos de csv que contem os dados de requisições.
- REQUISICOES_PORT: Porta para carregar os dados de requisições, caso utilize um ADRESS para carregar os dados.

O app.py roda um webapp local do streamlit:

```bash
   streamlit run app.py
```
Para rodar no modo desenvolvidor, coloque dois traços "--" para avisar ao streamlit que um argumento nosso será rodado, e depois mais dois traços para passar o argumento em si:

```bash
   streamlit run app.py -- --dev
```

Por enquanto, o modo desenvolvedor só possui um flag para mostrar a fonte (desativado por default), mas dado a necessidade de mais features, elas serão adicionadas

Dentro do webapp, você pode inserir um código de uma requisição para rodar o agente naquela requisição especifica.

### test/main.py

**Sempre rode o main.py no root do repositório**

O main.py é uma rotina de testes que roda o agente em multiplas requisições. É necessário rodar o código fornecendo o caminho de um CSV que contém duas colunas:

- ID_REQUISICAO: ID de uma requisição.
- Status: O status daquela requisição, necessário para conseguir métricas da rotina de testes

Exemplo de execução:

```bash
   python ./test/main.py --amostra ./test/sample_100.csv
```

### utils/codeExtractor.py

Necessário para extrair os códigos dos dados.

Explicação dos Argumentos de Linha de Comando:

1. --use_pdf:

   - **Função**: Este flag é usado para indicar que o arquivo de entrada é um PDF.
   - **Exemplo**: `--use_pdf`
   - **Explicação**: Se este flag estiver definido, o script irá extrair códigos de um arquivo PDF. Se o flag não for definido, o script extrairá códigos de um arquivo CSV.
2. --file_path:

   - **Função**: Especifica o caminho para o arquivo PDF ou CSV de onde os códigos serão extraídos.
   - **Exemplo**: `--file_path ./manual_auditoria.pdf`
   - **Explicação**: Este é um argumento obrigatório que indica o arquivo contendo os dados.
3. --column_names:

   - **Função**: Os nomes das colunas no arquivo CSV das quais os códigos serão extraídos.
   - **Exemplo**: `--column_names Codes AnotherColumn`
   - **Explicação**: Este argumento é obrigatório quando o arquivo de entrada é um CSV. Ele informa ao script quais colunas contêm os dados a serem processados. Pode-se passar um ou mais nomes de colunas.
4. --code_format:

   - **Função**: Um padrão de expressão regular (regex) usado para extrair os códigos do texto.
   - **Exemplo**: `--code_format '[A-Za-z0-9]{6}'`
   - **Explicação**: O padrão regex padrão é `\\d{8}`, que extrai códigos de 8 dígitos. Você pode fornecer um padrão de regex personalizado para coincidir com outros formatos.
5. --save_dir:

   - **Função**: Especifica o diretório onde os códigos extraídos devem ser salvos.
   - **Exemplo**: `--save_dir /caminho/para/diretorio`
   - **Explicação**: Se não for fornecido, os códigos extraídos serão salvos no diretório atual. Se este argumento for fornecido, o arquivo será salvo no diretório especificado.
6. --save_to_file:

   - **Função**: Salva os códigos extraídos em um arquivo de texto se definido.
   - **Exemplo**: `--save_to_file`
   - **Explicação**: Se este flag for definido, os códigos extraídos serão salvos em um arquivo. Se não for definido, os códigos serão apenas impressos no console.
7. --allow_duplicates:

   - **Função**: Permite códigos duplicados na lista de saída.
   - **Exemplo**: `--allow_duplicates`
   - **Explicação**: Se este flag for definido, os códigos duplicados serão incluídos na lista de saída. Se não for definido, os códigos duplicados serão removidos.
8. --clean_codes:

   - **Função**: Remove todos os caracteres não numéricos dos códigos extraídos, dado que ele seja um código válido (um código com 8 digitos).
   - **Exemplo**: `--clean_codes`
   - **Explicação**: Quando este flag é definido, os códigos extraídos serão limpos, removendo todos os caracteres não numéricos. Após a limpeza, o código será validado para garantir que tenha exatamente 8 dígitos. Se um código não contiver 8 dígitos após a limpeza, um erro será gerado.

**Coisas importantes para se lembrar**:

- Não pode usar espaços nas colunas dos CSVs.

### **Exemplos de uso**

- Extrair códigos de um PDF e salvar em um diretorio especifico.
  python codeExtractor.py --use_pdf --file_path ./manual_auditoria.pdf --save_dir /path/to/directory --save_to_file
- Extrair codigos de um CSV e salvar para o diretorio atual.
  python codeExtractor.py --file_path ./tuss.csv --column_name Codes --save_to_file
- Extrair códigos de um CSV mudando o regex de busca, limpando o código e usando multiplas colunas.
  python codeExtractor.py --file_path ../data/Tabela-CBHPM-2018.csv --column_names nivel_1 nivel_2 conteudo --code_format '\d\.\d{2}\.\d{2}\.\d{2}-\d' --clean_codes --save_to_file
