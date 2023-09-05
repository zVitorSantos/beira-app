from datetime import datetime, timedelta
import subprocess
import base64
import tkinter as tk
import requests
import subprocess
import threading
import webbrowser
import time
from config import CLIENT_ID, CLIENT_SECRET, SCOPES, STATE, EXPIRES_IN
from tokens import ACCESS_TOKEN, REFRESH_TOKEN

print("ACCESS_TOKEN:", ACCESS_TOKEN)
print("REFRESH_TOKEN:", REFRESH_TOKEN)

# URL de autorização (ajuste os parâmetros conforme necessário)
AUTH_URL = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&state={STATE}&scopes={SCOPES}"

BASE_URL = 'https://www.bling.com.br/Api/v3'

VERIFY_URL = f'{BASE_URL}/contatos'

# URL para o endpoint de token
TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'

console_manager = None
token_expiry_time = None

def update_time_remaining(time_remaining_label, refresh_token, client_credentials_base64):
    global token_expiry_time
    
    remaining_time = None  # Inicializa a variável aqui

    if isinstance(token_expiry_time, datetime):
        remaining_time = token_expiry_time - datetime.now()
    else:
        print(f"token_expiry_time is not a datetime object: {token_expiry_time}")
        return

    if remaining_time and remaining_time.total_seconds() <= 0:
        write_to_console(console, "A chave de acesso está expirada.\n  Atualizando...")
        new_access_token, new_refresh_token, new_expiry_time = refresh_access_token(refresh_token, client_credentials_base64)
        if new_access_token:
            global access_token
            access_token = new_access_token
            token_expiry_time = new_expiry_time
            write_to_console(console, "Chave de acesso atualizada com sucesso.")
            
            # Atualizando o rótulo do relógio com o novo tempo de expiração
            if isinstance(token_expiry_time, datetime):
                remaining_time = token_expiry_time - datetime.now()
            else:
                print(f"token_expiry_time is not a datetime object: {token_expiry_time}")
                return
            
            remaining_hours, remainder = divmod(remaining_time.total_seconds(), 3600)
            remaining_minutes, remaining_seconds = divmod(remainder, 60)
            new_time_string = f"{int(remaining_hours)}:{int(remaining_minutes)}:{int(remaining_seconds)}"
            time_remaining_label.config(text=new_time_string)
        else:
            write_to_console(console, "Falha ao atualizar a chave de acesso. Verifique as credenciais.")
            time_string = "00:00:00"
        return

    # Adicione uma verificação aqui também
    if remaining_time:
        remaining_hours, remainder = divmod(remaining_time.total_seconds(), 3600)
        remaining_minutes, remaining_seconds = divmod(remainder, 60)
        time_string = f"{int(remaining_hours)}:{int(remaining_minutes)}:{int(remaining_seconds)}"
    else:
        time_string = "00:00:00"

    time_remaining_label.config(text=time_string)
    root.update_idletasks()
    time_remaining_label.after(1000, update_time_remaining, time_remaining_label, refresh_token, client_credentials_base64)

def write_to_console(console, message):
    padded_message = f"  {message}  "
    console.insert(tk.END, padded_message + "\n")
    console.see(tk.END)
    root.update()    

def main():
    global time_remaining_label
    global token_expiry_time
    global write_to_console
    global console
    global root

    # Criando a janela principal
    root = tk.Tk()
    root.title("Autenticação")
    root.geometry("505x395")
    root.configure(bg="gray20")

    console_frame = tk.Frame(root, padx=20, pady=20, bg="gray20") # Ajuste o padding conforme necessário
    console_frame.pack()

    console = tk.Text(console_frame, height=15, width=50, bg="black", fg="green", font=("Courier New", 12, 'bold'))
    console.pack()

    refresh_token = REFRESH_TOKEN
    client_credentials_base64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode('ascii')).decode('ascii')

    if not ACCESS_TOKEN and not REFRESH_TOKEN:
        access_token, refresh_token = initiate_authorization_flow()
    else:
        access_token = ACCESS_TOKEN
        refresh_token = REFRESH_TOKEN

    # Leia o horário da captura do access_token de time.txt
    with open('time.txt', 'r') as file:
        token_capture_time_str = file.read().strip()
        token_capture_time = datetime.strptime(token_capture_time_str, '%Y-%m-%d %H:%M:%S')

    # Calcule o tempo restante
    token_expiry_time = token_capture_time + timedelta(seconds=int(EXPIRES_IN))
    time_remaining = token_expiry_time - datetime.now()

    def animate_loading(message):
        for i in range(2):  # Repete a animação 4 vezes
            for j in range(4):  
                dots = '.' * j
                console.delete(tk.END + "-2l", tk.END)
                write_to_console(console, f"{message}{dots}")
                time.sleep(0.3)
        console.delete(tk.END + "-2l", tk.END)
        write_to_console(console, f"{message} ✓")

    def clear_console(console):
        console.delete(1.0, tk.END)
    
    print("Horário de captura do token:", token_capture_time)
    print("EXPIRES_IN:", EXPIRES_IN)
    print("Horário de expiração do token:", token_expiry_time)
    print("Tempo restante:", time_remaining)

    animate_loading("\n  Verificando chave de acesso")
    
    if not verify_access_token(access_token) or time_remaining.total_seconds() <= 0:
        access_token, refresh_token, _ = refresh_access_token(refresh_token, client_credentials_base64)
        if access_token:
            write_to_console(console, "A chave de acesso está expirada ou inválida.\n")
            time.sleep(1)
            animate_loading("\n  Atualizando")
            time.sleep(1)
            write_to_console(console, "Chave de acesso atualizada com sucesso.")
            time.sleep(1)
            clear_console(console)
        else:
            time.sleep(1)
            write_to_console(console, "Falha ao atualizar a chave de acesso. Verifique as credenciais.")
            return
    else:
        time.sleep(1)
        write_to_console(console, "A chave de acesso está ativa.")
        time.sleep(1)

    write_to_console(console, "A aplicação está pronta para ser usada.\n")
    time.sleep(2)
    clear_console(console)

    def open_envio():
        write_to_console(console, "Abrindo a função de Envio!")
        subprocess.Popen(["python", "scripts/coleta.py"])
        time.sleep(2)
        clear_console(console)

    def open_cadastro():
        write_to_console(console, "Abrindo a função de Cadastro!")
        subprocess.Popen(["python", "scripts/tabela.py"])
        time.sleep(2)
        clear_console(console)

    botao_estilo = {
        'bg': '#555555',       
        'fg': '#f0f0f0',      
        'font': ('Helvetica', 12, 'bold'),
        'relief': 'solid',     
        'borderwidth': 2, 
        'activebackground': '#666666', 
        'activeforeground': '#ffffff',  
        'width': 15,           
        'height': 2           
    }

    # Criando um frame para os botões com padding de 1 cm
    buttons_frame = tk.Frame(root, padx=20, pady=3, bg="gray20") # 1 cm padding
    buttons_frame.pack()

    # Botões para escolher entre Envio e Cadastro
    btn_envio = tk.Button(buttons_frame, text="Envio", command=open_envio, **botao_estilo)
    btn_cadastro = tk.Button(buttons_frame, text="Cadastro", command=open_cadastro, **botao_estilo)

    # Usando grid para posicionar os botões lado a lado
    btn_envio.grid(row=0, column=0, padx=10) 
    btn_cadastro.grid(row=0, column=1, padx=10)

    time_remaining_label = tk.Label(root, text='', fg='white', font=("Courier New", 12, 'bold'), bg="gray20")
    time_remaining_label.pack()

    threading.Thread(target=update_time_remaining, args=(time_remaining_label, refresh_token, client_credentials_base64)).start()

    root.mainloop()

def update_access_token(new_access_token, new_refresh_token):
    print("Atualizando ACCESS_TOKEN:", new_access_token)
    print("Atualizando REFRESH_TOKEN:", new_refresh_token)
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
    print("Código de status da resposta:", response.status_code)
    print("Token sendo verificado:", access_token)
    return response.status_code == 200

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

        # Salve os tokens e o tempo de expiração
        with open('tokens.py', 'w') as file:
            file.write(f'ACCESS_TOKEN = "{new_access_token}"\n')
            file.write(f'REFRESH_TOKEN = "{new_refresh_token}"\n')

        capture_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('time.txt', 'w') as file:
            file.write(capture_time_str)

        return new_access_token, new_refresh_token, new_expiry_time

    return None, None, None

def initiate_authorization_flow():
    flask_process = subprocess.Popen(['python', 'scripts/oauth.py'])
    time.sleep(3)

    # Abre a URL de autorização no navegador padrão do sistema
    webbrowser.open(AUTH_URL)

    # Aguarde o processo Flask capturar e salvar os tokens
    time.sleep(10) 

    # Importe os tokens atualizados de tokens.py (ou de onde quer que estejam salvos)
    from tokens import ACCESS_TOKEN as new_access_token, REFRESH_TOKEN as new_refresh_token

    flask_process.terminate()

    # Retorne os tokens capturados
    return new_access_token, new_refresh_token

if __name__ == "__main__":
    try:
        with open('time.txt', 'r') as file:
            expiry_time_str = file.read().strip()
            token_expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
            token_expiry_time += timedelta(seconds=EXPIRES_IN)  
    except FileNotFoundError:
        token_expiry_time = datetime.now()
    main()
