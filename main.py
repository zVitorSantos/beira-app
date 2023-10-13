from datetime import datetime, timedelta
import os
import subprocess
import base64
import customtkinter as tk
import requests
import subprocess
import threading
import webbrowser
import time
import json

if not os.environ.get("LAUNCHED_FROM_LAUNCH_PY"):
    print("Por favor, inicie o programa pelo launch.py")
    exit()

# Carregando dados consolidados do arquivo JSON
with open("config.json", "r") as file:
    consolidated_data = json.load(file)

# Recuperando a empresa selecionada do arquivo temporário
try:
    with open("sel.json", "r") as file:
        selected_company_data = json.load(file)
    selected_company = selected_company_data.get("sel", None)
except FileNotFoundError:
    print("Arquivo de empresa selecionada não encontrado.")
    exit(1)

# Recuperando tokens e configurações com base na empresa selecionada
ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
REFRESH_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("REFRESH_TOKEN", None)
CLIENT_ID = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_ID", None)
CLIENT_SECRET = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_SECRET", None)
STATE = consolidated_data.get(selected_company, {}).get("config", {}).get("STATE", None)
SCOPES = consolidated_data.get(selected_company, {}).get("config", {}).get("SCOPES", None)
LAST_UPDATED_TIME = consolidated_data.get(selected_company, {}).get("time", None)

# Recuperando o tempo da última atualização com base na empresa selecionada
LAST_UPDATED_TIME_STR = consolidated_data.get(selected_company, {}).get("time", None)
if LAST_UPDATED_TIME_STR:
    LAST_UPDATED_TIME = datetime.strptime(LAST_UPDATED_TIME_STR, '%Y-%m-%d %H:%M:%S')
else:
    LAST_UPDATED_TIME = None  

# Quando você receber novos tokens, atualize o arquivo JSON
def update_tokens(new_access_token, new_refresh_token):
    consolidated_data[selected_company]["tokens"]["ACCESS_TOKEN"] = new_access_token
    consolidated_data[selected_company]["tokens"]["REFRESH_TOKEN"] = new_refresh_token
    with open("config.json", "w") as file:
        json.dump(consolidated_data, file, indent=4)
print("====================================================================")

# URL de autorização (ajuste os parâmetros conforme necessário)
AUTH_URL = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&state={STATE}&scopes={SCOPES}"

BASE_URL = 'https://www.bling.com.br/Api/v3'

VERIFY_URL = f'{BASE_URL}/produtos'

TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'

console_manager = None
token_expiry_time = None

EXPIRES_IN = 21600

def update_time_remaining(time_remaining_label, refresh_token, client_credentials_base64):
    global token_expiry_time
    
    remaining_time = None

    if isinstance(token_expiry_time, datetime):
        remaining_time = token_expiry_time - datetime.now()
    else:
        print(f"token_expiry_time is not a datetime object: {token_expiry_time}")
        return

    if remaining_time and remaining_time.total_seconds() <= 0:
        
        # Atualizando o rótulo do relógio com o novo tempo de expiração
        if isinstance(token_expiry_time, datetime):
            remaining_time = token_expiry_time - datetime.now()
        else:
            print(f"token_expiry_time is not a datetime object: {token_expiry_time}")
            return

    # Verificar se o tempo restante é uma instância válida
    if remaining_time:
        remaining_hours, remainder = divmod(remaining_time.total_seconds(), 3600)
        remaining_minutes, remaining_seconds = divmod(remainder, 60)

        # Formatando o tempo para sempre ter dois dígitos
        time_string = f"{str(int(remaining_hours)).zfill(2)}:{str(int(remaining_minutes)).zfill(2)}:{str(int(remaining_seconds)).zfill(2)}"
    else:
        time_string = "00:00:00"

    time_remaining_label.configure(text=time_string)
    root.update_idletasks()
    time_remaining_label.after(1000, update_time_remaining, time_remaining_label, refresh_token, client_credentials_base64)

def write_to_console(console, message, newline=False, **kwargs):
    try:
        if root and console.winfo_exists():  # Verifica o root e console
            padded_message = f"  {message}  "
            if kwargs:
                for key, value in kwargs.items():
                    extra_info = f"{value}"
                    if newline:
                        padded_message += "\n  " + extra_info
                    else:
                        padded_message += " " + extra_info
            console.insert(tk.END, padded_message + "\n")
            console.see(tk.END)
            root.update()
    except Exception as e:
        print(f"Erro ao escrever no console: {e}")

def on_closing():
    try:
        os.remove("sel.json")
        print("Arquivo sel.json excluído com sucesso.")
    except FileNotFoundError:
        print("Arquivo sel.json não encontrado.")
    root.quit()
    root.destroy()

def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def main():
    global time_remaining_label
    global token_expiry_time
    global write_to_console
    global console
    global root

    # Criando a janela principal
    root = tk.CTk()
    root.title("Autenticação")
    root.geometry("450x420")
    root.configure(bg="gray20")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", on_closing)

    center_window(root, 450, 420)

    # Frame para conter os elementos alinhados horizontalmente
    top_frame = tk.CTkFrame(root, fg_color='transparent')
    top_frame.pack(fill="x", anchor="n")

    # Botão para voltar à seleção de empresa
    def go_back():
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.quit()
        root.destroy()
        subprocess.run(["python", "launch.py"])

    btn_back = tk.CTkButton(top_frame, fg_color="black", text="<", font=("Lucida Sans", 14, 'bold'), border_width=2, border_color='#4d7cff', command=go_back, width=20, height=20)
    btn_back.grid(row=0, column=0, padx=0, pady=12)

    # Label para mostrar a empresa selecionada
    company_label = tk.CTkLabel(top_frame, text_color="white", fg_color='transparent', font=("Lucida Sans", 20, 'bold'), text=f"{selected_company}")
    company_label.grid(row=0, column=1)  

    # Label para mostrar o tempo restante
    time_remaining_label = tk.CTkLabel(top_frame, text='00:00:00', text_color='white', fg_color='transparent', font=("Lucida Sans", 14, 'bold'), width=10)
    time_remaining_label.grid(row=0, column=2, padx=0) 

    # Ajustando o comportamento de expansão das colunas
    top_frame.grid_columnconfigure(0, weight=1)
    top_frame.grid_columnconfigure(1, weight=2)  
    top_frame.grid_columnconfigure(2, weight=1)

    console_frame = tk.CTkFrame(root) 
    console_frame.pack(pady=10)

    console = tk.CTkTextbox(console_frame, height=280, width=410, text_color="white", fg_color="black", font=("Lucida Sans", 14, 'bold'), border_width=2, border_color="#4d7cff")
    console.pack()

    refresh_token = REFRESH_TOKEN
    client_credentials_base64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode('ascii')).decode('ascii')

    if not ACCESS_TOKEN and not REFRESH_TOKEN:
        access_token, refresh_token = initiate_authorization_flow()
    else:
        access_token = ACCESS_TOKEN
        refresh_token = REFRESH_TOKEN

    token_capture_time_str = consolidated_data.get(selected_company, {}).get("time", None)
    token_capture_time = datetime.strptime(token_capture_time_str, '%Y-%m-%d %H:%M:%S')

    # Calcule o tempo restante
    token_expiry_time = token_capture_time + timedelta(seconds=int(EXPIRES_IN))
    time_remaining = token_expiry_time - datetime.now()

    def clear_console(console):
        console.delete(1.0, tk.END)
    
    def clear_last(console):
        last_line_index = console.index(tk.END + "-2l linestart")
        console.delete(last_line_index, tk.END)
    
    print("Captura", token_capture_time)
    print("Expiry:", token_expiry_time)
    print("Tempo restante:", time_remaining)

    write_to_console(console, "\n  Verificando chave de acesso")
    
    if not verify_access_token(access_token) or time_remaining.total_seconds() <= 0:
        access_token, refresh_token, _ = refresh_access_token(refresh_token, client_credentials_base64)
        if access_token:
            write_to_console(console, "A chave de acesso está expirada ou inválida.\n")
            time.sleep(1)
            write_to_console(console, "\n  Atualizando")
            time.sleep(1)
            write_to_console(console, "Chave de acesso atualizada com sucesso.")
            time.sleep(1)
            clear_console(console)
        else:
            time.sleep(1)
            write_to_console(console, "Falha ao atualizar a chave de acesso. \nTentando novamente...")
            return

    else:
        time.sleep(1)
        write_to_console(console, "A chave de acesso está ativa.")
        time.sleep(1)
        clear_console(console)

    def open_envio():
        os.environ["LAUNCHED_FROM_MAIN"] = "True"
        subprocess.Popen(["python", "scripts/coleta.py"])
        write_to_console(console, "Abrindo importação de pedidos.")
        time.sleep(3)
        clear_last(console)

    def open_etiqueta():
        os.environ["LAUNCHED_FROM_MAIN"] = "True"
        subprocess.Popen(["python", "scripts/etiqueta.py"])
        
    def mask_token(token):
        return token[:13] + "*****"

    masked_ACCESS_TOKEN = mask_token(ACCESS_TOKEN)
    masked_REFRESH_TOKEN = mask_token(REFRESH_TOKEN)

    write_to_console(console, "Access:", newline=False, ACCESS_TOKEN=masked_ACCESS_TOKEN)
    write_to_console(console, "Refresh:", newline=False, REFRESH_TOKEN=masked_REFRESH_TOKEN)
    write_to_console(console, "Captura:", newline=False, token_capture_time=token_capture_time)
    write_to_console(console, "Expiração:", newline=False, token_expiry_time=token_expiry_time)
    write_to_console(console, "==========================================")

    # Estilo para os botões usando CustomTkinter
    botao_estilo = {
        'width': 100,  # Largura em pixels
        'height': 50,  # Altura em pixels
        'fg_color': ('', '#000000'),  # Cores de fundo
        'border_width': 2,  # Largura da borda em pixels
        'border_color':('#4d7cff'),
        'text_color': '#ffffff',  # Cor do texto
        'font': ('Lucida Sans', 16, 'bold')  # Fonte e tamanho
    }

    buttons_frame = tk.CTkFrame(root, fg_color='transparent')
    buttons_frame.pack()

    btn_etiqueta = tk.CTkButton(buttons_frame, text="Gerar\nEtiqueta", command=open_etiqueta, **botao_estilo)

    btn_etiqueta.grid(row=0, column=1, padx=10)

    threading.Thread(target=update_time_remaining, args=(time_remaining_label, refresh_token, client_credentials_base64)).start()

    root.mainloop()

def update_access_token(new_access_token, new_refresh_token):
    #write_to_console(console,"Atualizando ACCESS_TOKEN:", new_access_token=new_access_token)
    #write_to_console(console,"Atualizando REFRESH_TOKEN:", new_refresh_token=new_refresh_token)
    with open('tokens.py', 'r') as file:
        lines = file.readlines()

    with open('tokens.py', 'w') as file:
        for line in lines:
            if line.startswith('ACCESS_TOKEN'):
                file.write(f'ACCESS_TOKEN = "{new_access_token}"\n')
            elif line.startswith('REFRESH_TOKEN'):
                file.write(f'REFRESH_TOKEN = "{new_refresh_token}"\n')
            else:
                file.write(line)

# Ajustando as funções de verificação e atualização para receber os parâmetros
def verify_access_token(access_token):
    response = requests.get(VERIFY_URL, headers={'Authorization': f'Bearer {access_token}'})
    #print("Código de status da resposta:", response.status_code)
    #print("Token sendo verificado:", access_token)
    return response.status_code == 200

def auto_refresh_token():
    global token_expiry_time
    while True:
        # Recarregue os dados mais recentes da empresa selecionada
        with open("config.json", "r") as file:
            consolidated_data = json.load(file)
        
        try:
            with open("sel.json", "r") as file:
                selected_company_data = json.load(file)
            selected_company = selected_company_data.get("sel", None)
        except FileNotFoundError:
            print("Arquivo de empresa selecionada não encontrado.")
            time.sleep(60)
            continue

        ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
        REFRESH_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("REFRESH_TOKEN", None)
        CLIENT_ID = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_ID", None)
        CLIENT_SECRET = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_SECRET", None)
        
        # Atualize o client_credentials_base64 com base na empresa selecionada
        client_credentials_base64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode('ascii')).decode('ascii')

        LAST_UPDATED_TIME_STR = consolidated_data.get(selected_company, {}).get("time", None)
        if LAST_UPDATED_TIME_STR:
            LAST_UPDATED_TIME = datetime.strptime(LAST_UPDATED_TIME_STR, '%Y-%m-%d %H:%M:%S')
            token_expiry_time = LAST_UPDATED_TIME + timedelta(seconds=EXPIRES_IN)
        else:
            token_expiry_time = None

        if token_expiry_time and datetime.now() >= token_expiry_time:
            new_access_token, new_refresh_token, new_expiry_time = refresh_access_token(REFRESH_TOKEN, client_credentials_base64)
            if new_access_token:
                # Atualize os tokens e o tempo de captura no arquivo JSON
                update_tokens(new_access_token, new_refresh_token)

                # Atualize a variável global
                token_expiry_time = new_expiry_time

        time.sleep(60)

def refresh_access_token(refresh_token, client_credentials_base64):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0',
        'Authorization': f'Basic {client_credentials_base64}'
    }
    body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    response = requests.post(TOKEN_URL, headers=headers, data=body)

    if response.status_code == 200:
        response_data = response.json()
        new_access_token = response_data['access_token']
        new_refresh_token = response_data['refresh_token']
        new_expiry_time = datetime.now() + timedelta(seconds=EXPIRES_IN)

        # Salve os tokens e o tempo de captura no arquivo config.json
        consolidated_data[selected_company]["tokens"]["ACCESS_TOKEN"] = new_access_token
        consolidated_data[selected_company]["tokens"]["REFRESH_TOKEN"] = new_refresh_token
        consolidated_data[selected_company]["time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('config.json', 'w') as file:
            json.dump(consolidated_data, file, indent=4)

        capture_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Salve o tempo de captura no arquivo config.json
        consolidated_data[selected_company]["time"] = capture_time_str
        with open('config.json', 'w') as file:
            json.dump(consolidated_data, file, indent=4)

        # Atualizar token_expiry_time aqui
        global token_expiry_time
        token_expiry_time = datetime.now() + timedelta(seconds=EXPIRES_IN)

        subprocess.Popen(["python", "launch.py"])

        return new_access_token, new_refresh_token, token_expiry_time
    
    return None, None, None

def initiate_authorization_flow():
    # Inicia o servidor Flask em um processo separado
    flask_process = subprocess.Popen(['python', 'scripts/oauth.py'])
    
    # Aguarda alguns segundos para ter certeza de que o servidor Flask iniciou
    time.sleep(3)
    
    # Abre a URL de autorização no navegador padrão do sistema
    webbrowser.open(AUTH_URL)
    
    # Aguarde o processo Flask capturar e salvar os tokens
    while not os.path.exists("flask_done.tmp"):
        time.sleep(1)
        
    # Remove o arquivo temporário
    if os.path.exists("flask_done.tmp"):
        os.remove("flask_done.tmp")

    # Termina o processo Flask
    flask_process.terminate()
    
    # Carrega os tokens atualizados do arquivo JSON
    with open("config.json", "r") as file:
        consolidated_data = json.load(file)
        
    new_access_token = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
    new_refresh_token = consolidated_data.get(selected_company, {}).get("tokens", {}).get("REFRESH_TOKEN", None)

    # Retorne os novos tokens
    return new_access_token, new_refresh_token

if __name__ == "__main__":
    try:
        expiry_time_str = consolidated_data.get(selected_company, {}).get("time", None)
        if expiry_time_str:
            token_expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
            token_expiry_time += timedelta(seconds=EXPIRES_IN)  
        else:
            token_expiry_time = None
    except FileNotFoundError:
        token_expiry_time = None

    # Inicie a função auto_refresh_token em uma thread separada
    refresh_thread = threading.Thread(target=auto_refresh_token)
    refresh_thread.daemon = True  
    refresh_thread.start()

    main()