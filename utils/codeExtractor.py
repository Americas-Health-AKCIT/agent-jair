import argparse
import PyPDF2
import pandas as pd
import re
import os

"""
Exemplos de uso

- Extrair códigos de um PDF e salvar em um diretorio especifico.
python codeExtractor.py --use_pdf --file_path ./manual_auditoria.pdf --save_dir /path/to/directory --save_to_file

- Extrair codigos de um CSV e salvar para o diretorio atual.
python codeExtractor.py --file_path ../data/Manual_de_instruções.csv --column_names conteudo --save_to_file

- Extrair códigos de um CSV mudando o regex de busca, limpando o código e usando multiplas colunas.
python codeExtractor.py --file_path ../data/Tabela-CBHPM-2018.csv --column_names nivel_1 nivel_2 conteudo --code_format '\d\.\d{2}\.\d{2}\.\d{2}-\d' --clean_codes --save_to_file

"""

# Função para extrair códigos de um PDF
def extract_codes_from_pdf(pdf_path):
    """
    Extrai texto de um arquivo PDF e retorna uma lista de padrões específicos encontrados.

    Argumentos:
    - pdf_path (str): Caminho para o arquivo PDF.

    Retorna:
    - Lista de strings que correspondem ao padrão de 8 dígitos consecutivos encontrados no texto extraído do PDF.
    """

    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()  # Append text from each page
    pattern = r'\d{8}'  # Regular expression pattern for 8 consecutive digits
    return re.findall(pattern, text)

# Função para extrair códigos de um CSV
def extract_codes_from_csv(csv_path, column_names, code_format=r'\d{8}', exclude_null=True, allow_duplicates=False):
    """
    Extrai todos os valores de uma ou mais colunas específicas em um arquivo CSV e os retorna como uma lista.
    
    Argumentos:
    - csv_path (str): Caminho para o arquivo CSV.
    - column_names (list or str): O nome ou uma lista de nomes das colunas das quais extrair os valores.
    - code_format (str): O padrão de expressão regular que os códigos devem seguir. O padrão é r'\d{8}'.
    - exclude_null (bool): Se True, exclui valores NULL (vazios) da lista de saída. O padrão é True.
    - allow_duplicates (bool): Se False, remove códigos duplicados da lista de saída. O padrão é False.
    
    Retorna:
    - Lista de valores das colunas especificadas, na ordem em que aparecem no arquivo CSV.
    """
    df = pd.read_csv(csv_path)
    
    # Se column_names for string, convertê-la para uma lista para manipulação uniforme
    if isinstance(column_names, str):
        column_names = [column_names]
    
    extracted_codes = []
    pattern = re.compile(code_format)

    # Iterar sobre cada coluna fornecida
    for column_name in column_names:
        if column_name in df.columns:
            values = df[column_name].astype(str)  # Garantir que os valores sejam strings

            # Aplicar a expressão regular em cada valor da coluna e coletar os códigos encontrados
            for value in values:
                codes = pattern.findall(value)  # Extrair todos os códigos que correspondem ao padrão
                extracted_codes.extend(codes)  # Adicionar os códigos encontrados à lista
        else:
            print(f"Warning: Column '{column_name}' not found in CSV.")

    # Excluir valores vazios, se exclude_null for True
    if exclude_null:
        extracted_codes = [code for code in extracted_codes if code and pd.notna(code)]
    
    # Remover duplicados se allow_duplicates for False
    if not allow_duplicates:
        extracted_codes = list(set(extracted_codes))

    return extracted_codes

def change_code_format(codes):
    """
    Remove todos os caracteres que não sejam números e transforma os códigos para conter apenas dígitos,
    garantindo que o código final tenha exatamente 8 dígitos.
    
    Argumentos:
    - codes (list): Lista de códigos extraídos.

    Retorna:
    - Lista de códigos transformados contendo apenas números, com exatamente 8 dígitos.

    Throws:
    - ValueError: Se os códigos não tiverem exatamente 8 dígitos após a transformação.
    """
    transformed_codes = []

    for code in codes:
        # Remover todos os caracteres que não sejam números
        only_digits = re.sub(r'\D', '', code)

        # Verificar se o código resultante tem exatamente 8 dígitos
        if len(only_digits) != 8:
            raise ValueError(f"Erro: O código '{code}' não contém exatamente 8 dígitos após a transformação.")

        transformed_codes.append(only_digits)

    return transformed_codes

def save_codes_to_txt(codes, txt_path):
    """
    Salva uma lista de códigos em um arquivo de texto.
    
    Argumentos:
    - codes (list): Lista de códigos para salvar no arquivo.
    - txt_path (str): Caminho onde o arquivo de texto será salvo.
    """
    with open(txt_path, 'w') as file:
        file.write(str(codes)) # Escreve os códigos como uma lista na forma de string. Se precisar os códigos separados por linha, descomente o código abaixo.
        # for code in codes:
        #     file.write(f"{code}\n")


def main():
    parser = argparse.ArgumentParser(description="Extract codes from PDF or CSV and optionally save them to a text file.")

    parser.add_argument('--use_pdf', action='store_true', help='Use PDF function if set, otherwise use CSV function.')
    parser.add_argument('--file_path', type=str, required=True, help='Path to the PDF or CSV file.')
    parser.add_argument('--column_names', type=str, nargs='+', help='Name(s) of the column(s) to extract from (required if using CSV). Multiple column names can be provided.')
    parser.add_argument('--code_format', type=str, default=r'\d{8}', help='Regex pattern to extract codes (default is 8 digits).')
    parser.add_argument('--save_dir', type=str, help='Directory where the text file will be saved.')
    parser.add_argument('--save_to_file', action='store_true', help='Save the extracted codes to a text file if set.')
    parser.add_argument('--allow_duplicates', action='store_true', help='Allow duplicate codes in the output. If not set, duplicates will be removed.')
    parser.add_argument('--clean_codes', action='store_true', help='Clean the extracted codes by removing non-numeric characters and ensuring 8 digits.')

    args = parser.parse_args()

    if args.use_pdf:
        codes = extract_codes_from_pdf(args.file_path)
    else:
        if not args.column_names:
            parser.error("--column_names is required when --use_pdf is not set.")
        codes = extract_codes_from_csv(
            args.file_path, 
            args.column_names, 
            code_format=args.code_format, 
            allow_duplicates=args.allow_duplicates
        )
    
    if args.clean_codes:
        try:
            codes = change_code_format(codes)
        except ValueError as e:
            print(e)
            return

    if args.save_to_file:
        # Automatically generate the save file name using the base file name and chosen directory
        base_name = os.path.basename(args.file_path).rsplit('.', 1)[0] + '_codes.txt'
        if args.save_dir:
            save_path = os.path.join(args.save_dir, base_name)
        else:
            save_path = base_name
        
        save_codes_to_txt(codes, save_path)
        print(f"Codes saved to {save_path}")
    else:
        print("Extracted codes:\n", codes)

if __name__ == "__main__":
    main()

    # path = '/home/pressprexx/Code/Evah/agente-de-autorizacoes/data/manual_auditoria.pdf'
    # sequences = extract_codes_from_pdf(path)
    # print(sequences)
