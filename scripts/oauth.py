import requests
import base64
import json
import datetime
import sys
sys.path.append(r'C:\Users\Usuario\Desktop\Bling API')
import main
from config import STATE, CLIENT_ID, CLIENT_SECRET, SCOPES
from tokens import ACCESS_TOKEN, REFRESH_TOKEN
from flask import Flask, request, redirect, Response

app = Flask(__name__)

# Credenciais do cliente (client_id e client_secret)
CLIENT_ID = 'c676d47d13c33a707e1d26f23fa11fcaef5666d2'
CLIENT_SECRET = '614d505dd5ace5383a74cb2358055370e8f3136d5f0f1655454545ea1482'

# URL da página de autorização do provedor OAuth
AUTHORIZE_URL = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&state={STATE}&scopes={SCOPES}"

# URLs para obtenção dos tokens de acesso e novo access token usando o refresh token
ACCESS_TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'
REFRESH_TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'

def write_tokens_to_tokens(access_token, refresh_token):
    with open('tokens.py', 'w') as file:
        file.write(f'ACCESS_TOKEN = "{access_token}"\n')
        file.write(f'REFRESH_TOKEN = "{refresh_token}"\n')

def write_expires_in_to_config(expires_in):
    with open('config.py', 'a') as file:
        file.write(f"EXPIRES_IN = {expires_in}\n")

@app.route('/')
def callback():
    # Obter o código de autorização da URL
    code = request.args.get('code')

    if code:
        # Codificar as credenciais para Base64
        base64_creds = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
        
        # Requisição para obter os tokens de acesso usando o grant type "authorization_code"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '1.0',
            'Authorization': f'Basic {base64_creds}'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code
        }

        response = requests.post(ACCESS_TOKEN_URL, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            expires_in = token_data['expires_in']

            write_expires_in_to_config(expires_in)
            write_tokens_to_tokens(access_token, refresh_token)

            token_capture_time = datetime.now()
            with open('time.txt', 'w') as file:
                file.write(str(token_capture_time))
        
        elif response.status_code == 400:
            error_data = response.json()
            error_type = error_data["error"]["type"]
            error_message = error_data["error"]["message"]
            error_description = error_data["error"]["description"]
            return f'Erro: {error_type}, {error_message}, {error_description}'
        else:
            response = Response('Erro ao obter os tokens de acesso.')
            response.status_code = 500
            return response
    else:
        return 'Erro!'

@app.route('/refresh')
def refresh():
    # Obter o refresh token da URL (neste exemplo, você pode fornecer o refresh token como parâmetro da URL)
    refresh_token = request.args.get('refresh_token')

    if not refresh_token:
        return 'Refresh token não fornecido.', 400

    # Codificar as credenciais para Base64
    base64_creds = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
    
    # Requisição para obter um novo access token usando o refresh token
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0',
        'Authorization': f'Basic {base64_creds}'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(REFRESH_TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        new_access_token = token_data["access_token"]
        return f'Novo token de acesso: {new_access_token}'
    elif response.status_code == 400:
        error_data = response.json()
        error_type = error_data["error"]["type"]
        error_message = error_data["error"]["message"]
        error_description = error_data["error"]["description"]
        return f'Erro: {error_type}, {error_message}, {error_description}'
    else:
        return 'Erro ao obter novo token de acesso.', 500

if __name__ == '__main__':
    app.run()