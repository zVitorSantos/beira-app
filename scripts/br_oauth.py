from flask import Flask, request
import json
from etiqueta import load_config, PRODUCTION_MODE

app = Flask(__name__)

AUTH_URL = "https://api.calcadosbeirario.app.br/oauth/grant-code"
TOKEN_URL = "https://api.calcadosbeirario.app.br/oauth/access-token"

# Carregar dados do config.json
environment = "Hom" if PRODUCTION_MODE else "Prod"
config_data = load_config(environment)
CLIENT_ID = config_data.get("config", {}).get("CLIENT_ID")
CLIENT_SECRET = config_data.get("config", {}).get("CLIENT_SECRET")
with open("config.json", "r") as file:
    data = json.load(file)
issued_time = data.get("Beira Rio", {}).get("time", "2000-01-01 00:00:00")

@app.route('/')
def callback():
    try:
        print("Servidor Usado")
    except Exception as e:
        print(f"Exceção: {e}")
        return f"Erro interno do servidor: {e}"

if __name__ == "__main__":
    app.run(debug=False)