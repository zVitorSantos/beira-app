import requests
import re
import os
from tkinter import ttk
import pandas as pd
from tkinter import filedialog
import tkinter as tk
import tkinter.messagebox as messagebox
import sys
sys.path.append(r'C:\Users\Usuario\Desktop\Bling API')
from tokens import ACCESS_TOKEN

BASE_URL = 'https://www.bling.com.br/Api/v3'

access_token = ACCESS_TOKEN
arquivo = 'tabela.xlsx'
indices_exibidos = None
tree = None

def carregar_skus_do_arquivo():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, 'r') as f:
            skus = f.read().splitlines()
        return skus
    else:
        return []
    
def buscar_multiplos_skus():
    skus = carregar_skus_do_arquivo()
    for sku in skus:
        codigo_entry.delete(0, tk.END)  # Limpar o campo de entrada
        codigo_entry.insert(0, sku)  # Inserir novo SKU
        buscar_item(access_token)

def buscar_item(access_token):
    codigo = codigo_entry.get()
    url = f'{BASE_URL}/produtos?pagina=1&limite=100&criterio=1&tipo=T&codigo={codigo}'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json().get('data', [])
        if not data:
            tk.messagebox.showinfo("Item Não Encontrado", "Nenhum item encontrado com o código fornecido.")
            return

        item = data[0]
        id_item = item['id']
        nome = item['nome']
        sku = item['codigo']  # Aqui estamos pegando o SKU que é representado pelo campo "codigo"

        codigo_item, codigo_cor, cor_final = extrair_cor(nome)
        referencia = extrair_referencia(nome)

        # Verificar se o item já existe na tabela usando o código
        if any(df['SKU'] == sku):  # Aqui também mudamos para verificar o SKU
            tk.messagebox.showinfo("Item Duplicado", "O item já existe na tabela.")
            return

        novo_index, novo_item = adicionar_item(id_item, nome, codigo_item, codigo_cor, cor_final, referencia, sku)
        tree.insert(parent='', index='end', iid=novo_index, text='',
                    values=('', novo_item['ID'], novo_item['Cod. Item'], novo_item['Cod. Cor'], novo_item['Cor'], novo_item['Referência'], novo_item['SKU']))
    else:
        print(response.status_code)
        print("Erro na requisição.")

def extrair_referencia(nome):
    # Extrair os últimos 3-4 dígitos
    referencia = re.search(r'\d{3,4}$', nome)
    return referencia.group(0) if referencia else None

def extrair_cor(nome):
    partes = nome.split(" / ")
    if len(partes) < 2:
        print("Formato inválido do nome do item.")
        return None, None, None

    codigos = partes[0]
    if " | " in codigos:
        codigo_item, codigo_cor = codigos.split(" | ")
    else:
        print("Não foi possível extrair os códigos do item.")
        return None, None, None

    cor_parte = partes[1].split(" - ")[0] if " - " in partes[1] else None

    return codigo_item, codigo_cor, cor_parte

def adicionar_item(id_item, nome, codigo_item, codigo_cor, cor_final, referencia, sku):
    global df

    novo_item = {
        'ID': id_item, 
        'Cod. Item': codigo_item, 
        'Cod. Cor': codigo_cor,
        'Cor': cor_final, 
        'Referência': referencia, 
        'SKU': sku  
    }
    
    novo_index = len(df)
    df.loc[novo_index] = novo_item

    df.to_excel(arquivo, index=False)
    return novo_index, novo_item

def exibir_tabela(root):
    global tree
    global df 

    # Estilo para o Treeview
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", background="gray20", fieldbackground="#e0e0e0", rowheight=25)
    style.configure("Treeview.Heading", font=("Arial", 12, 'bold')) 
    style.map('Treeview', background=[('selected', '#a0a0a0')])

    # Configurar linhas de separação
    style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
    style.configure("Treeview.Treearea", background="black")
    style.configure("Treeview.Cell", padding=(0, 1))

    # Carregar a tabela existente ou criar um novo DataFrame vazio
    if os.path.exists(arquivo):
        df = pd.read_excel(arquivo)
        df['ID'] = df['ID'].astype(str).str.replace(',', '').astype('int64')
        df['Cod. Item'] = df['Cod. Item'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
        df['Cod. Cor'] = df['Cod. Cor'].astype(str).apply(lambda x: re.sub(r'\D', '', x))
    else:
        df = pd.DataFrame(columns=['ID', 'Cod. Item', 'Cod. Cor', 'Cor', 'Referência', 'SKU'])
    
    # Criar um Treeview para exibir a tabela
    tree = ttk.Treeview(root, columns=('Seleção', 'ID', 'Cod. Item', 'Cod. Cor', 'Cor', 'Referência', 'SKU'))

    # Definir as configurações das colunas
    tree.column('#0', width=0, stretch=tk.NO)
    tree.column('Seleção', anchor=tk.W, width=20)
    tree.column('ID', anchor=tk.W, width=80)
    tree.column('Cod. Item', anchor=tk.W, width=90)
    tree.column('Cod. Cor', anchor=tk.W, width=90)
    tree.column('Cor', anchor=tk.W, width=200)
    tree.column('Referência', anchor=tk.W, width=45)
    tree.column('SKU', anchor=tk.W, width=35)

    # Criar os cabeçalhos das colunas
    tree.heading('#0', text='', anchor=tk.W)
    tree.heading('Seleção', text='', anchor=tk.W)
    tree.heading('ID', text='ID', anchor=tk.W)
    tree.heading('Cod. Item', text='Cod. Item', anchor=tk.W)
    tree.heading('Cod. Cor', text='Cod. Cor', anchor=tk.W)
    tree.heading('Cor', text='Cor', anchor=tk.W)
    tree.heading('Referência', text='Ref.', anchor=tk.W)
    tree.heading('SKU', text='SKU', anchor=tk.W)

    # Adicionar os dados à tabela
    for index, row in df.iterrows():
        tree.insert(parent='', index='end', iid=index, text='',
                    values=('', row['ID'], row['Cod. Item'], row['Cod. Cor'], row['Cor'], row['Referência'], row['SKU']))

    tree.pack(side=tk.LEFT)

    # Função para alternar a seleção de um item
    def toggle_selecao(event):
        item = tree.selection()[0]
        if tree.item(item, 'values')[0] == '':
            tree.item(item, values=('✓', *tree.item(item, 'values')[1:]))
        else:
            tree.item(item, values=('', *tree.item(item, 'values')[1:]))

    # Adicionar evento de clique para alternar a seleção
    tree.bind('<Double-1>', toggle_selecao)

def excluir_itens():
    global df, indices_exibidos  # Adicione indices_exibidos aqui
    resposta = messagebox.askyesno("Confirmação", "Tem certeza de que deseja excluir os itens selecionados?")
    if resposta:
        items_to_delete = []  # Lista para armazenar os itens a serem excluídos
        for item in tree.get_children():
            if tree.item(item, 'values')[0] == '✓':
                items_to_delete.append(item)

        if indices_exibidos:
            # Se itens foram filtrados, use os índices reais para excluir
            indices_reais = [indices_exibidos[int(item)] for item in items_to_delete]
            df = df.drop(indices_reais).reset_index(drop=True)
        else:
            # Se não houve filtragem, use os índices da árvore diretamente
            df = df.drop(df.index[[int(item) for item in items_to_delete]]).reset_index(drop=True)
        
        # Recriar o Treeview com os itens restantes
        for item in tree.get_children():
            tree.delete(item)
        for index, row in df.iterrows():
            tree.insert(parent='', index='end', iid=index, text='',
                        values=('', row['ID'], row['Cod. Item'], row['Cod. Cor'], row['Cor'], row['Referência'], row['SKU']))

        # Salvar a tabela atualizada
        df.to_excel(arquivo, index=False)

def buscar_resultado():
    global indices_exibidos
    valor_busca = busca_entry.get()
    resultado_busca = df[(df['SKU'].astype(str).str.contains(valor_busca, na=False)) | 
                         (df['Referência'].astype(str).str.contains(valor_busca, na=False))]
    
    indices_exibidos = resultado_busca.index.tolist()

    # Limpar a árvore antes de inserir os resultados da busca
    for item in tree.get_children():
        tree.delete(item)

    # Adicionar os resultados da busca à árvore
    for index, row in resultado_busca.iterrows():
        tree.insert(parent='', index='end', iid=index, text='',
                    values=('', row['ID'], row['Cod. Item'], row['Cod. Cor'], row['Cor'], row['Referência'], row['SKU']))
        
# Configurando cores escuras
cor_fundo = '#2c2c2c'
cor_texto = '#f0f0f0'

# Interface gráfica
root = tk.Tk()
root.title("Adicionar Itens")
root.configure(bg=cor_fundo)

# Estilo para o Treeview
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background=cor_fundo, foreground=cor_texto, fieldbackground=cor_fundo, rowheight=25)
style.map('Treeview', background=[('selected', '#a0a0a0')])

botao_estilo = {
        'bg': '#555555',       
        'fg': '#f0f0f0',      
        'font': ('Helvetica', 12, 'bold'),
        'relief': 'solid',     
        'borderwidth': 2, 
        'activebackground': '#666666', 
        'activeforeground': '#ffffff',  
        'width': 9,           
        'height': 1           
    }

botao_mais = {
        'bg': '#555555',       
        'fg': '#f0f0f0',      
        'font': ('Helvetica', 12, 'bold'),
        'relief': 'solid',     
        'borderwidth': 2, 
        'activebackground': '#666666', 
        'activeforeground': '#ffffff',  
        'width': 2,           
        'height': 1           
    }

botao_excluir = {
        'bg': '#FF0000',             
        'font': ('Helvetica', 12, 'bold'),
        'relief': 'solid',     
        'borderwidth': 2, 
        'activebackground': '#B22222', 
        'width': 2,           
        'height': 1           
    }

# Código e Botão Buscar
codigo_frame = tk.Frame(root, bg=cor_fundo)
codigo_frame.pack(fill=tk.X)
codigo_label = tk.Label(codigo_frame, text="Código:", bg=cor_fundo, fg=cor_texto, font=("Helvetica", 13, 'bold'))
codigo_label.grid(row=0, column=0)
codigo_entry = tk.Entry(codigo_frame, font=("Helvetica", 15), bg='#404040', fg='white', width=25)
codigo_entry.grid(row=0, column=1, sticky=tk.W + tk.E)
buscar_button = tk.Button(codigo_frame, botao_estilo ,text="Buscar", command=lambda: buscar_item(access_token), fg=cor_texto)
buscar_button.grid(row=0, column=2, padx=2)
buscar_multiplos_button = tk.Button(codigo_frame, botao_mais, text="+", command=buscar_multiplos_skus, fg=cor_texto)
buscar_multiplos_button.grid(row=0, column=3, padx=2)

# Campo de entrada e botão para pesquisa (com tema escuro)
busca_frame = tk.Frame(root, bg=cor_fundo)
busca_frame.pack(fill=tk.X)
busca_label = tk.Label(busca_frame, text="Buscar:", bg=cor_fundo, fg=cor_texto, font=("Helvetica", 13, 'bold'))
busca_label.grid(row=0, column=0)
busca_entry = tk.Entry(busca_frame, font=("Helvetica", 12), bg='#404040', fg=cor_texto, width=25)
busca_entry.grid(row=0, column=1, sticky=tk.W + tk.E)
buscar_resultado_button = tk.Button(busca_frame, botao_estilo, text="Filtrar", command=buscar_resultado, fg=cor_texto)
buscar_resultado_button.grid(row=0, column=2, padx=1)
excluir_button = tk.Button(busca_frame, botao_excluir, text="🗑", command=excluir_itens, fg=cor_texto)
excluir_button.grid(row=0, column=3, padx=2)

# Garante que as colunas se expandam para preencher o espaço disponível
codigo_frame.grid_columnconfigure(1, weight=1)
busca_frame.grid_columnconfigure(1, weight=1)

# Tabela
exibir_tabela(root)

root.mainloop()