from pdfminer.high_level import extract_text
import subprocess
import tabula
import pandas as pd
import re
import time
import sys
sys.path.append(r'C:\Users\Usuario\Desktop\Bling API')
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from datetime import datetime

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Erro ao formatar a data: {e}")
        return None

def extrair_dados(pdf_path):
    texto = extract_text(pdf_path)
    numero_oc = re.search(r'Número OC:\s*(\d+)', texto)
    data_emissao = re.search(r'DATA DE EMISSÃO:\s*(\d{2}/\d{2}/\d{4})', texto)
    tabelas = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
    tabela_produtos = tabelas[0]
    # Inicializar o multiplicador com o valor padrão
    multiplicador_quant = 1
    multiplicador_vl_unit = 1

    # Criar uma nova tabela para armazenar as linhas transformadas
    nova_tabela_produtos = pd.DataFrame(columns=tabela_produtos.columns)

    # Iterar pelas linhas da tabela original
    for index, row in tabela_produtos.iterrows():
        if 'MIL' in str(row['Seq.']):
            multiplicador_quant = 1000
            multiplicador_vl_unit = 1/1000
        elif 'PAR' in str(row['Seq.']):
            multiplicador_quant = 1
            multiplicador_vl_unit = 1/2

        # Se a linha não for problemática, aplicar os multiplicadores e adicionar à nova tabela
        if not 'Remessa:' in str(row['Seq.']):
            row['Quant.'] = pd.to_numeric(row['Quant.'], errors='coerce') * multiplicador_quant
            row['Vl. Unit.'] *= multiplicador_vl_unit
            nova_tabela_produtos.loc[index] = row

    # Manter a tabela nova como a tabela de produtos
    tabela_produtos = nova_tabela_produtos

    # Remover as colunas não necessárias e manter a coluna 'Código'
    tabela_produtos = tabela_produtos.drop(columns=['Seq.', '% IPI', 'Tam.', 'Descrição'])
    
    data_prevista = tabela_produtos['Dt.'].iloc[0]

    # Filtrar a coluna 'Cor' para pegar apenas o primeiro conjunto de números
    tabela_produtos['Cor'] = tabela_produtos['Cor'].str.split(' ').str[0]

    # Reordenar as colunas e adicionar uma coluna 'Item' com números sequenciais
    colunas_ordenadas = ['Cor', 'Código', 'Quant.', 'Vl. Unit.', 'Total']
    tabela_produtos = tabela_produtos[colunas_ordenadas]
    tabela_produtos['Item'] = range(1, len(tabela_produtos) + 1)

    # Ajustar a ordem final das colunas
    colunas_finais = ['Item', 'Código', 'Cor', 'Quant.', 'Vl. Unit.', 'Total']
    tabela_produtos = tabela_produtos[colunas_finais]

    general_info = {
    'Número OC': numero_oc.group(1) if numero_oc else 'Não encontrado',
    'Data de Emissão': format_date(data_emissao.group(1)) if data_emissao else 'Não encontrado',
    'Data Prevista': format_date(data_prevista)
    }

    general_info_df = pd.DataFrame([general_info])

    file_name = 'dados.xlsx'
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')

    general_info_df.to_excel(writer, sheet_name='Infos', index=False)

    tabela_produtos.to_excel(writer, sheet_name='Items', index=False)

    writer.close()

    time.sleep(2)
    subprocess.call(["python", "scripts/post.py"])

def selecionar_pdf():
    root = tk.Tk()
    root.withdraw() 
    # Abre a janela de seleção de arquivo
    pdf_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if pdf_path:
        extrair_dados(pdf_path)
    else:
        print("Nenhum arquivo selecionado.")

selecionar_pdf()
