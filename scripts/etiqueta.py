import requests
import json
import os
import socket
import time
import base64
from datetime import datetime
import subprocess
import customtkinter as tk
import tkinter.messagebox as messagebox
from tkinter import filedialog
from PIL import Image, ImageTk
from pdf2image import convert_from_path
from xml.dom.minidom import parseString
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree as ET
import sqlite3

if not os.environ.get("LAUNCHED_FROM_MAIN"):
    print("Por favor, inicie o programa pelo launch.py")
    exit()

print("=============================================================================================================")

# Inicializar banco de dados SQLite para armazenar EPCs
conn = sqlite3.connect('data/epc_codes.db')
c = conn.cursor()

# Criar a tabela com duas colunas, uma para cada empresa
c.execute("""
CREATE TABLE IF NOT EXISTS epc_codes (
    cnpj TEXT PRIMARY KEY,
    epc TEXT
)""")
conn.commit()

# Carregar dados de configuração
with open("config.json", "r") as file:
    consolidated_data = json.load(file)

# Dicionário para mapear a empresa selecionada ao CNPJ e nome do fornecedor
empresa_mapping = {
    "Brilha Natal": {"CNPJ_EPC": "00699893000105", "Fornecedor": "BRILHA NATAL M"},
    "Maggiore Modas": {"CNPJ_EPC": "24914470000129", "Fornecedor": "MAGGIORE ACESS"},
    "Maggiore Pecas": {"CNPJ_EPC": "10000000000001", "Fornecedor": "MAGGIORE TESTE"}
}

# Recuperar a empresa selecionada
try:
    with open("sel.json", "r") as file:
        selected_company_data = json.load(file)
    selected_company = selected_company_data.get("sel", None)
    CNPJ_EPC = empresa_mapping[selected_company]["CNPJ_EPC"]
    Fornecedor = empresa_mapping[selected_company]["Fornecedor"]
except FileNotFoundError:
    print("Arquivo de empresa selecionada não encontrado.")
    exit(1)

# Recuperar o ACCESS_TOKEN
BASE_URL = 'https://www.bling.com.br/Api/v3'

def get_nfe(nfe_id, BASE_URL):
    ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
    url = f"{BASE_URL}/nfe/{nfe_id}"  
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    print(url,"\n", headers)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            print("Erro ao decodificar a resposta JSON.")
            return None
    except Exception as e:
        print(f"Erro ao fazer a requisição: {e}")
        print(response.text)
        return None
    
def get_xml(data):
    xml_url = data.get('data', {}).get('xml', '')
    namespaces = {'ns0': 'http://www.portalfiscal.inf.br/nfe'}
    
    if not xml_url:
        print("URL do XML vazia ou inválida.")
        return None, None, None  
    
    xml_response = requests.get(xml_url)

    print(xml_response)

    if xml_response.status_code == 200:
        xml_data = xml_response.text
        if xml_data:
            root = ET.fromstring(xml_data)
        else:
            print("XML vazio.")
            return None, None, None
        
        nNF_elem = root.find('.//ns0:nNF', namespaces)
        if nNF_elem is not None:
            nNF = nNF_elem.text
        else:
            nNF = 'Número da NF não disponível'

        # Capturar a chave da NFe
        infNFe_elem = root.find('.//ns0:infNFe', namespaces)
        if infNFe_elem is not None and 'Id' in infNFe_elem.attrib:
            nfe_chave = infNFe_elem.attrib['Id'][3:]
        else:
            nfe_chave = 'Chave da NFe não disponível'
        
        # Verificar se a pasta com o nNF já existe
        nfe_dir = f'etiquetas/{Fornecedor}/{nNF}'
        if os.path.exists(nfe_dir):
            print(f"A Nota Fiscal {nNF} já foi consultada.")
            messagebox.showwarning("Aviso", f"Essa Nota Fiscal {nNF} já foi consultada. Por favor, insira um novo ID.")
            return None, None, None, None

        data_emissao_elem = root.find('.//ns0:dhEmi', namespaces)

        if data_emissao_elem is not None:
            original_data = data_emissao_elem.text.split('T')[0]
            formatted_data = datetime.strptime(original_data, '%Y-%m-%d').strftime('%d/%m/%Y')
            data_emissao = formatted_data
        else:
            data_emissao = 'N/A'

        return xml_data, data_emissao, nNF, nfe_chave 
    else:
        print("Erro ao tentar acessar o XML. Código de status:", xml_response.status_code)
        return None, None, None, None
    
# Função para salvar o XML
def save_xml(xml_data, nNF, force_nNF=None):
    nNF_to_use = force_nNF if force_nNF else nNF 
    empresa_path = f'etiquetas/{Fornecedor}'  
    if not os.path.exists(empresa_path):
        os.makedirs(empresa_path)

    nfe_path = f'{empresa_path}/{nNF_to_use}'
    if not os.path.exists(nfe_path):
        os.makedirs(nfe_path)

    # Formatar o XML para torná-lo legível
    dom = parseString(xml_data)
    pretty_xml_str = dom.toprettyxml(indent="\t")

    with open(f"{nfe_path}/{nNF_to_use}.xml", 'w', encoding='utf-8') as f:
        f.write(pretty_xml_str)
    
def xml_item_info(xml_data):
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        print("Erro na análise do XML.")
        return []

    namespaces = {'ns0': 'http://www.portalfiscal.inf.br/nfe'}  
    items = []
    ordem_compra = None

    for det in root.findall(".//ns0:det", namespaces):
        item = {}
        
        nItem = det.get('nItem')
        item['nItem'] = nItem

        prod = det.find("ns0:prod", namespaces)

        if prod is not None:
            xProd_elem = prod.find("ns0:xProd", namespaces)
            uCom_elem = prod.find("ns0:uCom", namespaces)
            qCom_elem = prod.find("ns0:qCom", namespaces)
            xPed_elem = prod.find("ns0:xPed", namespaces)

            if xProd_elem is not None and uCom_elem is not None and qCom_elem is not None:
                xProd = xProd_elem.text.strip()
                uCom = uCom_elem.text
                qCom = qCom_elem.text

                # Divida xProd em partes
                partes = xProd.split(" - ")

                # Assegure-se de que há pelo menos 2 partes
                if len(partes) >= 2:
                    codigo_item, codigo_cor = partes[:2]
                    material = " - ".join(partes[2:])
                    
                    max_por_volume = 1

                    item["Código de Item"] = codigo_item
                    item["Código de Cor"] = codigo_cor
                    item["Material"] = material
                    item["Unidade"] = "MIL" if uCom.lower() == "mil" else "PAR"

                    if item["Unidade"] == "PAR":
                        max_por_volume *= 1000

                    item["Qtde"] = qCom
                    item["Max por Volume"] = max_por_volume  

                    if xPed_elem is not None:
                        item["Pedido"] = xPed_elem.text
                        ordem_compra = xPed_elem.text 
                    else:
                        item["Pedido"] = 'SEM O.C'
                        messagebox.showwarning("Aviso", f"NF sem O.C. definida!")
                        return None, None, None, None

                    items.append(item)
                    print(f"Item coletado: {item}")
                else:
                    print("Formato de xProd inválido")
            else:
                print("Elemento 'prod' não encontrado")

    return items, ordem_compra

def insert_epc(cnpj, epc):
    # Verificar se já existe um registro para o CNPJ fornecido
    c.execute("SELECT * FROM epc_codes WHERE cnpj = ?", (cnpj,))
    existing_record = c.fetchone()
    
    if existing_record:
        # Atualizar o EPC para o CNPJ existente
        c.execute("UPDATE epc_codes SET epc = ? WHERE cnpj = ?", (epc, cnpj))
    else:
        # Inserir novo registro
        c.execute("INSERT INTO epc_codes (cnpj, epc) VALUES (?, ?)", (cnpj, epc))
    
    conn.commit()

def generate_epc(cnpj, last_serial):
    return f"{cnpj}{str(last_serial).zfill(10)}"
    
def save_epc(c, CNPJ_EPC):
    c.execute("SELECT * FROM epc_codes WHERE cnpj = ? ORDER BY ROWID DESC LIMIT 1", (CNPJ_EPC,))
    last_epc_record = c.fetchone()
    last_serial = int(last_epc_record[1][-10:]) if last_epc_record else 0
    new_serial = last_serial + 1
    epc_code = generate_epc(CNPJ_EPC, new_serial)
    
    # Salvar novo EPC no banco de dados
    insert_epc(CNPJ_EPC, epc_code)
    
    return epc_code

def generate_zpl_label(item, Fornecedor, data_emissao, epc_code, nNF, volume_qtde):
    codigo_item = item.get('Código de Item', '')
    codigo_cor = item.get('Código de Cor', 'N/A')  
    qtde = volume_qtde
    unidade = item.get('Unidade', '')
    material = item.get('Material', '').split('/')
    ordem_compra = item.get('Pedido', '')

    material_zpl_lines = []
    initial_y_position = 437
    y_position_increment = 45

    i = 0  

    # Concatena todo o material em uma string
    full_material_line = ' '.join(material)
    
    while len(full_material_line) > 0:
        if len(full_material_line) > 40:
            last_space_index = full_material_line.rfind(' ', 0, 40)
            first_line = full_material_line[:last_space_index]
            full_material_line = full_material_line[last_space_index+1:]
        else:
            first_line = full_material_line
            full_material_line = ""
            
        material_zpl_lines.append(f"^FO170,{initial_y_position + (y_position_increment * i)}^AS^FD{first_line}^FS")
        i += 1

    material_zpl_code_part = '\n'.join(material_zpl_lines)

    zpl_code = f"""
    ^XA
    ^MCY
    ~SD20
    ^PON
    ^CI13
    ^FO050,200^AR^FDFornecedor:^FS
    ^FO210,193^AT^FD{Fornecedor}^FS
    ^FO550,200^AR^FDData:^FS
    ^FO620,193^AT^FD{data_emissao}^FS
    ^FO050,260^AR^FDItem:^FS
    ^FO120,253^AT^FD{codigo_item}^FS
    ^FO550,260^AR^FDCor:^FS
    ^FO620,253^AT^FD{codigo_cor}^FS
    ^FO050,320^AR^FDQtde./Med.:^FS
    ^FO205,313^AT^FD{qtde}^FS
    ^FO620,313^AT^FD{unidade}^FS
    ^FO050,380^AR^FDTam.:^FS
    ^FO122,373^AS^FD^FS
    ^FO550,380^AR^FDLargura:^FS
    ^FO050,440^AR^FDMaterial:^FS
    {material_zpl_code_part}
    ^FO110,632^AR^FDNF:^FS
    ^FO170,625^AT^FD{nNF}^FS
    ^FO530,632^AR^FDO.C.:^FS
    ^FO600,625^AT^FD{ordem_compra}^FS
    ^FO30,790^BY2,,10^BCN,100,Y,N^FD{epc_code}^FS
    ^FO640,760^BQN,2,7^FDLA,{epc_code}^FS
    ^RFW,H^FD{epc_code}^FS
    ^XZ"""

    return zpl_code

def save_zpl(zpl_code, epc_code, nNF):
    empresa_path = f'etiquetas/{Fornecedor}/{nNF}/{epc_code}'  
    if not os.path.exists(empresa_path):
        os.makedirs(empresa_path, exist_ok=True)
        
    with open(f'{empresa_path}/{epc_code}.prn', 'w') as f:
        f.write(zpl_code)

# Variáveis globais para armazenar as imagens e o índice atual
all_images = []
current_index = 0

def update_label(canvas, label):
    global current_index, all_images
    if 0 <= current_index < len(all_images):
        canvas.delete("all")  # Limpa o canvas
        canvas.create_image(0, 0, anchor=tk.NW, image=all_images[current_index])
        label.configure(text=f"{current_index + 1}/{len(all_images)}")

def go_left(canvas, label):
    global current_index
    if current_index > 0:
        current_index -= 1
        update_label(canvas, label)

def go_right(canvas, label):
    global current_index
    if current_index < len(all_images) - 1:
        current_index += 1
        update_label(canvas, label)
        
def label_zpl(zpl_code, root, epc_code, nNF):
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4.05x4.56/0/'
    files = {'file': ('zpl.zpl', zpl_code)}
    headers = {'Accept': 'application/pdf'}
    try:
        response = requests.post(url, headers=headers, files=files, stream=True)
    except requests.exceptions.ConnectionError:
        messagebox.showerror("Erro de Conexão", "Foi forçado o cancelamento de uma conexão existente pelo host remoto.")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro desconhecido: {e}")

    global all_images, photo

    if response.status_code == 200:
        empresa_path = f'etiquetas/{Fornecedor}/{nNF}/{epc_code}' 
        if not os.path.exists(empresa_path):
            os.makedirs(empresa_path)
            
        pdf_path = f'{empresa_path}/{epc_code}.pdf'
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
            
        # Agora você pode abri-lo
        images = convert_from_path(pdf_path)
        
        if len(images) > 0:
            image = images[0]

            # Redimensiona a imagem para caber na tela
            desired_width = 355 
            desired_height = 400

            image.thumbnail((desired_width, desired_height))

            # Atualize a variável photo aqui
            photo = ImageTk.PhotoImage(image.convert('RGB'))

            # Agora, você pode adicionar a 'photo' à lista de todas as imagens
            all_images.append(photo)

            master_frame = tk.CTkFrame(root)
            master_frame.grid(row=1, column=0, columnspan=3)

            new_frame = tk.CTkFrame(master_frame)
            new_frame.pack()

            desired_width = 355 
            desired_height = 400

            canvas = tk.CTkCanvas(new_frame, width=desired_width, height=desired_height, highlightbackground="#4d7cff", highlightthickness=2)
            canvas_image = canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="current_img")
            canvas.pack()

            # Botões e rótulo para navegação
            left_button = tk.CTkButton(master_frame, text="<", command=lambda: go_left(canvas, index_label))
            left_button.pack(side="left")

            right_button = tk.CTkButton(master_frame, text=">", command=lambda: go_right(canvas, index_label))
            right_button.pack(side="right")

            index_label = tk.CTkLabel(master_frame, text=f"{current_index + 1}/{len(all_images)}")
            index_label.pack(side="bottom")
        else:
            print("PDF não contém páginas.")
    else:
        print(f"Erro na Labelary API. Código de status: {response.status_code}")

def divide_por_volume(quantidade, max_por_volume):
    volumes = []
    volumes_totais = -(-quantidade // max_por_volume)
    for volume in range(1, int(volumes_totais) + 1):
        if quantidade >= max_por_volume:
            qtd = max_por_volume
        else:
            qtd = round(quantidade, 2)
        volumes.append({'Volume': volume, 'Quantidade': qtd})
        quantidade = round(quantidade - qtd, 2)
    return volumes

api_data_list = []

def process_volume(item, volume, nNF, Fornecedor, data_emissao, nfe_chave, api_data_list):
    # Gerar um único código EPC para o volume do item
    epc_code = save_epc(c, CNPJ_EPC)

    # Gerar o código ZPL para este volume
    zpl_code = generate_zpl_label(item, Fornecedor, data_emissao, epc_code, nNF, volume['Quantidade'])

    # Salvar o arquivo .prn
    save_zpl(zpl_code, epc_code, nNF)

    # Salvar o arquivo .pdf
    label_zpl(zpl_code, root, epc_code, nNF)

    if data_emissao not in [None, 'N/A']:
        data_emissao = datetime.strptime(data_emissao, '%d/%m/%Y').strftime('%Y-%m-%d')
    else:
        data_emissao = datetime.strptime(data_emissao, '%d/%m/%Y').strftime('%Y-%m-%d')

    quantidade = (volume['Quantidade'])

    # Coletar os dados da API
    api_data = {
        "chaveNfe": nfe_chave,
        "cnpj": CNPJ_EPC,
        "codigoEpc": epc_code,
        "dataFabricacao": data_emissao,
        "dataValidade": "",
        "itemNotaFiscal": int(item['nItem']),
        "lote": "0",
        "piID": "0",
        "piIDSequence": 0,
        "quantidade": quantidade,
        "unidadeMedida": item['Unidade']
    }
    api_data_list.append(api_data)

PRODUCTION_MODE = False

# Carregar a configuração com base no ambiente
def load_config(environment="Hom"):
    with open("config.json", "r") as file:
        data = json.load(file)
    return data.get("Beira Rio", {}).get(environment, {})

# Atualizar a configuração
def update_config(new_access_token, new_refresh_token, environment="Hom"):
    with open("config.json", "r") as file:
        data = json.load(file)
    
    data["Beira Rio"][environment]["tokens"]["ACCESS_TOKEN"] = new_access_token
    data["Beira Rio"][environment]["tokens"]["REFRESH_TOKEN"] = new_refresh_token
    data["Beira Rio"][environment]["time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open("config.json", "w") as file:
        json.dump(data, file, indent=4)

# Função para verificar se o token está expirado
def is_token_expired(issued_time_str, expires_in=None):
    if expires_in is None:
        expires_in = 3600
    issued_time = datetime.strptime(issued_time_str, '%Y-%m-%d %H:%M:%S')
    current_time = datetime.now()
    delta = current_time - issued_time
    return delta.total_seconds() >= expires_in

# Carregar chaves do ambiente
def load_environment_keys():
    environment = "Prod" if PRODUCTION_MODE else "Hom"
    config_data = load_config(environment)
    CLIENT_ID = config_data.get("config", {}).get("CLIENT_ID", None)
    CLIENT_SECRET = config_data.get("config", {}).get("CLIENT_SECRET", None)
    ACCESS_TOKEN = config_data.get("tokens", {}).get("ACCESS_TOKEN", None)
    REFRESH_TOKEN = config_data.get("tokens", {}).get("REFRESH_TOKEN", None)
    BASE_64 = config_data.get("config", {}).get("BASE_64", None)
    
    return CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN, BASE_64

# Inicialização de variáveis globais
CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN, BASE_64 = None, None, None, None, None

# Atualizar variáveis globais
def update_global_keys():
    global CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN, BASE_64
    CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN, BASE_64 = load_environment_keys()

def authorization_flow():
    global CLIENT_ID, CLIENT_SECRET  

    # 1. Inicie o servidor Flask em um processo separado
    flask_process = subprocess.Popen(['python', 'scripts/br_oauth.py'])
    time.sleep(3)

    # 2. Obtenha o código de autorização
    response = requests.post("https://api.calcadosbeirario.app.br/oauth/grant-code",
        json={"client_id": CLIENT_ID,
              "redirect_uri": "http://127.0.0.1:5000"
              }
    )

    if response.status_code == 201:
        redirect_uri = response.json().get('redirect_uri')
        parsed_url = urlparse(redirect_uri)
        parsed_qs = parse_qs(parsed_url.query)

        code = parsed_qs.get('code', [None])[0]
        
        if code:
            # Chame a função para obter o token de acesso
            TOKEN_URL = "https://api.calcadosbeirario.app.br/oauth/access-token"
            result = get_access_token(code, TOKEN_URL)  
            flask_process.terminate()
            print(result)

        else:
            print("Código de autorização não encontrado.")
    else:
        print("Erro ao obter o código de autorização.")

def get_access_token(code, TOKEN_URL):
    global CLIENT_ID, CLIENT_SECRET, BASE_64
    environment = "Prod" if PRODUCTION_MODE else "Hom"
    try:
        base64_creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode('utf-8')).decode('utf-8')
        headers = {'Authorization': f'Basic {base64_creds}'}
        data = {
            'grant_type': 'authorization_code',
            'code': code
        }
        response = requests.post(TOKEN_URL, headers=headers, data=data)

        print("Resposta da coleta acess token:", response.json)
        
        if response.status_code == 201:
            tokens = response.json()
            environment = "Prod" if PRODUCTION_MODE else "Hom"
            update_config(tokens["access_token"], tokens["refresh_token"], environment)
            return "Tokens atualizados com sucesso."
        else:
            return f"Erro: {response.json()}"
    except Exception as e:
        return f"Erro interno: {e}"

def verify_token():
    global ACCESS_TOKEN  
    
    # Determinar o ambiente atual baseado no PRODUCTION_MODE
    environment = "Prod" if PRODUCTION_MODE else "Hom"
    
    config_data = load_config(environment)
    
    issued_time = config_data.get("time", "2000-01-01 00:00:00")
    access_token = config_data.get("tokens", {}).get("ACCESS_TOKEN", None)

    print(access_token)

    if is_token_expired(issued_time):
        print("Token expirado. Atualizando...")
        refresh_access_token() 
        config_data = load_config(environment)  
        access_token = config_data.get("tokens", {}).get("ACCESS_TOKEN", None)
        print("isexpired:", access_token)
        ACCESS_TOKEN = access_token  
    
    return access_token

def enviar_para_api(data):
    global ACCESS_TOKEN, CLIENT_ID, PRODUCTION_MODE 

    update_global_keys()
    
    # Verifique o modo do ambiente para ajustar a URL
    if PRODUCTION_MODE:
        url = "https://api.calcadosbeirario.app.br/nota-fiscal/entradas/fornecedores/volumes-itens/lote"
    else:
        url = "https://api.calcadosbeirario.app.br/stg/nota-fiscal/entradas/fornecedores/volumes-itens/lote"

    print(CLIENT_ID)
    print(ACCESS_TOKEN)
    
    headers = {
        'Content-Type': 'application/json',
        'client_id': CLIENT_ID,
        'access_token': ACCESS_TOKEN  
    }

    response = requests.post(url, json=data, headers=headers)

    # Verifique se o token de acesso é inválido ou expirado
    if response.status_code == 401:
        print(response.text)
        print("Token expirado ou inválido. Atualizando...")
        refresh_access_token()
        # Atualize as informações do token
        ACCESS_TOKEN = verify_token() 
        headers['access_token'] = ACCESS_TOKEN  

        response = requests.post(url, json=data, headers=headers)

    try:
        if response.status_code in [200, 201]:
            return response.status_code, response.json()
        else:
            return response.status_code, {}
    except json.JSONDecodeError:
        print("Não foi possível decodificar o JSON")
        return response.status_code, {}

def refresh_access_token():
    global CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN
    
    environment = "Prod " if PRODUCTION_MODE else "Hom "
    refresh_token = REFRESH_TOKEN

    if refresh_token is None:
        print("Sem refresh token. Iniciando novo fluxo de autorização...")
        authorization_flow()
        return

    TOKEN_URL = "https://api.calcadosbeirario.app.br/oauth/access-token"
    base64_creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode('utf-8')).decode('utf-8')
    headers = {'Authorization': f'Basic {base64_creds}'}
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    
    if response.status_code == 201:
        tokens = response.json()
        update_config("Beira Rio", tokens["access_token"], tokens["refresh_token"], environment)
        print("Token atualizado com sucesso.")
    else:
        print(f"Erro ao atualizar token: {response.json()}")
        if 'INVALID' in response.json().get('errors', [{}])[0].get('type', ''):
            print("Sem refresh token válido. Iniciando novo fluxo de autorização...")
            authorization_flow()
            
def send_to_printer(prn_path, printer_ip, printer_port):

    with open(prn_path, "rb") as f:
        prn_data = f.read()
        
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((printer_ip, printer_port))
        s.sendall(prn_data)
        s.close()
    except socket.error as e:
        print(f"Erro ao enviar dados para a impressora: {e}")

def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def salvar_xml_apenas(nfe_id):
    nfe_data = get_nfe(nfe_id, BASE_URL)
    if nfe_data is None:
        print("Erro ao buscar dados NFE.")
        return

    xml_data, data_emissao, nNF, nfe_chave = get_xml(nfe_data)
    if xml_data is None:
        print("Erro ao buscar XML.")
        return

    save_xml(xml_data, nNF)

dev_label = None
env_label = None
info_frame = None

DEV_MODE = False

def main():
    global root, nfe_entry, nNF, info_frame, DEV_MODE
    global api_data_object
    all_labels_ready = False
    api_data_object = None

    update_global_keys()

    def print_labels(nNF, printer_ip, printer_port):
        global api_data_object
        nfe_directory_path = f'etiquetas/{Fornecedor}/{nNF}/'
        
        if os.path.exists(nfe_directory_path):
            for epc_code_folder in os.listdir(nfe_directory_path):
                epc_code_path = os.path.join(nfe_directory_path, epc_code_folder)
                
                if os.path.isdir(epc_code_path): 
                    prn_file_path = os.path.join(epc_code_path, f"{epc_code_folder}.prn")
                    
                    if os.path.exists(prn_file_path):
                        try:
                            send_to_printer(prn_file_path, printer_ip, printer_port)
                            print("Etiqueta imprimida!")
                        except Exception as e:
                            print(f"Erro durante a impressão: {e}")
                            return
                    else:
                        print(f"Arquivo .prn não encontrado em {epc_code_path}")
                        return
        else:
            print(f"Nenhuma etiqueta encontrada para a NFe {nNF}")
            return

        global api_data_list
        if api_data_list:
            status, response = enviar_para_api({"list": api_data_list})
            api_list_json = json.dumps(api_data_list, indent=4)
            print(api_list_json)
            if type(response) is dict:
                print(response)
            if status in [200, 201, 204]:
                print("Dados enviados com sucesso para a API.")
                messagebox.showinfo("Sucesso!","Dados enviados com sucesso para a API.")
                api_data_list = []  
            else:
                print(f"Erro ao enviar dados para a API. Código de status: {status}")
                messagebox.showerror("Erro!", f"Erro ao enviar dados para a API. Código de status: {status}")

    def process_xml(xml_data, data_emissao=None, nNF=None, nfe_chave=None):
        items, ordem_compra = xml_item_info(xml_data)
        if not items:
            print("Erro ao extrair informações do XML.")
            return

        for item in items:
            max_por_volume = item.get("Max por Volume", 0.5) 

            volumes = divide_por_volume(float(item['Qtde']), max_por_volume)
            for volume in volumes:
                process_volume(item, volume, nNF, Fornecedor, data_emissao, nfe_chave, api_data_list)

        save_xml(xml_data, nNF)
        all_labels_ready = True
        print_button.configure(state="normal")

    def process_nfe():
        nfe_id = nfe_entry.get()
        global all_labels_ready, nNF

        # Se o ID começa com ".", considere como um comando especial
        if nfe_id.startswith('.'):
            process_special_command(nfe_id[1:])
            return

        nfe_data = get_nfe(nfe_id, BASE_URL)
        if nfe_data is None:
            print("Erro ao buscar dados NFE.")
            return

        xml_data, data_emissao, nNF, nfe_chave = get_xml(nfe_data)
        if xml_data is None:
            print("Erro ao buscar XML.")
            return

        process_xml(xml_data, data_emissao, nNF, nfe_chave)

    ###################################################################################################
    ###################################################################################################

    def update_environment_label():
        global env_label, PRODUCTION_MODE
        if env_label:
            env_label.destroy()
        env_label = tk.CTkLabel(info_frame, text="PROD" if PRODUCTION_MODE else "HOM")
        env_label.grid(row=0, column=0, sticky="w")

    def update_dev_label():
        global dev_label, DEV_MODE
        if dev_label:
            dev_label.destroy()
        if DEV_MODE:
            dev_label = tk.CTkLabel(info_frame, text=" - DEV-ON")
            dev_label.grid(row=0, column=1, sticky="w")
        else:
            dev_label = None

    VALID_DEV_COMMANDS = ['.dev', '.select', '.xml ', '.mode']

    def process_special_command(command):
        global DEV_MODE, PRODUCTION_MODE, dev_label, root
        if command.startswith("xml "):
            nfe_id = command[4:]  
            salvar_xml_apenas(nfe_id)

        elif command == "dev":
            DEV_MODE = not DEV_MODE 
            print(f"Modo desenvolvedor {'ativado' if DEV_MODE else 'desativado'}")
            update_dev_label()
                
        elif command == "select":
            filepath = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
            if filepath:
                with open(filepath, 'r') as f:
                    xml_data = f.read()
                
                # Extrair metadados como data_emissao aqui
                root = ET.fromstring(xml_data)
                namespaces = {'ns0': 'http://www.portalfiscal.inf.br/nfe'}

                nNF_elem = root.find('.//ns0:nNF', namespaces)
                if nNF_elem is not None:
                    nNF = nNF_elem.text
                else:
                    nNF = 'Número da NF não disponível'

                # Verifique se uma pasta com o mesmo número de nNF já existe
                empresa_path = f'etiquetas/{Fornecedor}'
                nfe_path = f'{empresa_path}/{nNF}'
                if os.path.exists(nfe_path):
                    messagebox.showwarning("Aviso", f"Uma pasta com o número de NF {nNF} já existe.")
                    return

                # Capturar a chave da NFe
                infNFe_elem = root.find('.//ns0:infNFe', namespaces)
                if infNFe_elem is not None and 'Id' in infNFe_elem.attrib:
                    nfe_chave = infNFe_elem.attrib['Id'][3:]
                else:
                    nfe_chave = 'Chave da NFe não disponível'
                
                data_emissao_elem = root.find('.//ns0:dhEmi', namespaces)
                if data_emissao_elem is not None:
                    original_data = data_emissao_elem.text.split('T')[0]
                    formatted_data = datetime.strptime(original_data, '%Y-%m-%d').strftime('%d/%m/%Y')
                    data_emissao = formatted_data
                else:
                    data_emissao = None
                
                process_xml(xml_data, data_emissao=data_emissao, nNF=nNF, nfe_chave=nfe_chave)
        elif command == "mode":
            PRODUCTION_MODE = not PRODUCTION_MODE
            print(f"Modo de produção {'ativado' if PRODUCTION_MODE else 'desativado'}")
            update_global_keys()
            update_environment_label()
        else:
            print(f"Comando {command} não reconhecido")  

    # Interface Tkinter
    root = tk.CTk()
    root.geometry("400x510")
    #root.resizable(False, False)
    root.title("Gerar Etiquetas")

    center_window(root, 410, 535)

    update_environment_label()

    def check_entry_length(event):
        global DEV_MODE  # Declarar que você está usando a variável global
        content = nfe_entry.get()
        
        # Ativa o modo de desenvolvedor se o conteúdo for '.dev'
        if content == '.dev':
            buscar_button.configure(state="normal")  # Ative o botão de busca
            return
        
        # Se o modo de desenvolvedor está ativo e a entrada é um comando válido, permita
        if DEV_MODE:
            if content in VALID_DEV_COMMANDS:
                buscar_button.configure(state="normal")
                return
            elif len(content) > 10:  # Se for um ID válido, permita
                buscar_button.configure(state="normal")
                return
            else:  # Se não for nem um comando válido nem um ID, desabilite o botão
                buscar_button.configure(state="disabled")
                return

        # Se o modo de desenvolvedor não está ativo, siga as regras normais
        if not DEV_MODE:
            if len(content) > 20:
                nfe_entry.delete(50, 'end') 
            elif len(content) > 10:
                buscar_button.configure(state="normal")
            else:
                buscar_button.configure(state="disabled")

    # Função para esconder o placeholder
    def hide_placeholder(event):
        if nfe_entry.get() == 'ID da NFe':
            nfe_entry.delete(0, 'end')
            nfe_entry.configure(fg_color='black')

    # Função para mostrar o placeholder
    def show_placeholder(event):
        if nfe_entry.get() == '':
            nfe_entry.insert(0, 'ID da NFe')
            nfe_entry.configure(fg_color='black')

    # Campo de entrada
    nfe_entry = tk.CTkEntry(root)
    nfe_entry.insert(0, 'ID da NFe')
    nfe_entry.configure(fg_color='black')
    nfe_entry.grid(row=0, column=1, sticky='we', padx=5, pady=5)
    nfe_entry.bind("<KeyRelease>", check_entry_length)
    nfe_entry.bind("<FocusIn>", hide_placeholder)
    nfe_entry.bind("<FocusOut>", show_placeholder)

    # Botão de pesquisa
    buscar_button = tk.CTkButton(root, font=('Helvetica', 15, 'bold'), text_color='white', text="🔎", fg_color='black', border_width=2, border_color='#4d7cff', state="disabled", command=process_nfe, width=16, height=25)
    buscar_button.grid(row=0, column=2, padx=5, pady=5)

    # Faz a coluna 1 se expandir para preencher o espaço extra
    root.grid_columnconfigure(1, weight=1)

    # Posicione este frame para conter o botão de impressão
    button_frame = tk.CTkFrame(root)  
    button_frame.grid(row=2, column=0, columnspan=3)  

    # Botão de impressão (inicialmente desativado)
    print_button = tk.CTkButton(button_frame, font=('Helvetica', 15, 'bold'), text_color='white', text="Imprimir Etiquetas", fg_color='black', border_width=2, border_color='#4d7cff', state="disabled", command=lambda: print_labels(nNF, "172.16.101.117", 9100), width=30, height=14)
    print_button.grid(row=0, column=0, padx=5, pady=5, sticky='s')  

    # Posicione este frame para conter os labels HOM/PROD e DEV-ON
    info_frame = tk.CTkFrame(root)  
    info_frame.grid(row=3, column=0, columnspan=3)  # Mudei para row=3

    # Labels de modo e ambiente
    dev_mode_label = tk.CTkLabel(info_frame, text="")
    env_label = tk.CTkLabel(info_frame, text="")
    update_environment_label()

    dev_mode_label.grid(row=0, column=0)
    env_label.grid(row=0, column=1)

    root.mainloop()

if __name__ == "__main__":
    main()