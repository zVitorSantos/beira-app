import pandas as pd
import subprocess
import requests
import sys
import json
import tkinter as tk
from tkinter import ttk

sys.path.append(r'C:\Users\Usuario\Desktop\Bling API')
from tokens import ACCESS_TOKEN

# Caminhos para os arquivos
file_path_dados_coletados = r"C:\Users\Usuario\Desktop\Bling API\dados.xlsx"
file_path_tabela_xlsx = r"C:\Users\Usuario\Desktop\Bling API\tabela.xlsx"

# 1. Carregar os Dados
dados_coletados_itens_df = pd.read_excel(file_path_dados_coletados, sheet_name='Items')
dados_coletados_infos_df = pd.read_excel(file_path_dados_coletados, sheet_name='Infos')
tabela_df = pd.read_excel(file_path_tabela_xlsx)

class LogWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Log de Informações")
        self.master.geometry("600x300")

        self.text = tk.Text(self.master, wrap='word')
        self.text.pack(fill=tk.BOTH, expand=1)

    def log_message(self, message, width=None, height=None):
        self.text.insert(tk.END, message + "\n")
        self.text.see(tk.END)
        
        if width and height:
            self.master.geometry(f"{width}x{height}")
        else:
            self.master.update_idletasks()
            width = self.master.winfo_reqwidth()
            height = self.master.winfo_reqheight()
            self.master.geometry(f"{width}x{height}")

root = tk.Tk()
log_window = LogWindow(root)

missing_codes = dados_coletados_itens_df[~dados_coletados_itens_df['Código'].isin(tabela_df['Cod. Item'])]['Código']

if not missing_codes.empty:
    log_window.log_message(f"Código(s) faltando:\n{missing_codes.tolist()}\nPor favor, abra manualmente o arquivo 'tabela.py',\nadicione os itens faltantes e tente novamente.", width=200, height=50)
    root.mainloop()
    sys.exit("Programa encerrado para adição manual de itens.")

resultados_finais = []
for index, row in dados_coletados_itens_df.iterrows():
    # Filtrar a tabela pelo código do item e código da cor
    tabela_filtered = tabela_df[(tabela_df['Cod. Item'] == row['Código']) & (tabela_df['Cod. Cor'] == row['Cor'])]
    if not tabela_filtered.empty:
        match = tabela_filtered.iloc[0]
        resultado = {
            'ID': match['ID'],
            'SKU': match['SKU'],
            'Quantidade': row['Quant.'],
            'Valor Unitário': row['Vl. Unit.'],
            'Total': row['Total'],
            'Data Emissão': dados_coletados_infos_df['Data de Emissão'].iloc[0],
            'Data Prevista': dados_coletados_infos_df['Data Prevista'].iloc[0],
            'Número OC': dados_coletados_infos_df['Número OC'].iloc[0]
        }
        resultados_finais.append(resultado)

resultado_final_df = pd.DataFrame(resultados_finais)

# Função para criar a estrutura de item para o JSON
def create_item(row):
    return {
        "id": str(row['ID']),
        "codigo": str(row['SKU']),
        "unidade": "",
        "quantidade": str(row['Quantidade']),
        "desconto": 0,
        "valor": str(row['Valor Unitário']),
        "aliquotaIPI": 0,
        "descricao": "",
        "descricaoDetalhada": "",
        "produto": {
            "id": str(row['ID'])
        },
        "comissao": {
            "base": "<float>",
            "aliquota": "<float>",
            "valor": "<float>"
        }
    }

itens_list = [create_item(row) for index, row in resultado_final_df.iterrows()]

json_data = {
        "id":"",
        "numero": str(dados_coletados_infos_df['Número OC'].iloc[0]),
        "data": dados_coletados_infos_df['Data de Emissão'].iloc[0],
        "dataPrevista": dados_coletados_infos_df['Data Prevista'].iloc[0],
        "contato": {
            "id": 16251322487,
            "nome":"",
            "tipoPessoa": "J",
            "numeroDocumento": "88.379.771/0035-21"
        },
        "categoria": {
            "id": 14650247114
        },
        "itens": itens_list,
        "vendedor": {
            "id": 15596262453
        }
}

log_window.log_message(json.dumps(json_data, indent=4))

url = "https://www.bling.com.br/Api/v3/pedidos/vendas"
headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
response = requests.post(url, json=json_data, headers=headers)

# Capturando e exibindo o código de status e o corpo da resposta
status_code = response.status_code
response_body = response.json()

# Verificando a resposta
if response.status_code == 200 or response.status_code == 201:
    print("Pedido de venda concluído com sucesso!")
    log_window.log_message(f"Pedido de venda concluído com sucesso!\nCódigo de Status: {status_code}\nResposta: {response_body}")
else:
    print("Erro ao concluir o pedido de venda. Código de erro:", response.status_code)
    log_window.log_message("Erro ao concluir o pedido de venda. Código de erro: " + str(response.status_code))

root.mainloop()
