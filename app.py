from flask import Flask, jsonify, send_from_directory, redirect, request, session, url_for
import json
import requests
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = os.urandom(24)

# Caminho do banco de dados (um nível acima da pasta do site)
CAMINHO_DADOS = os.path.join(os.path.dirname(__file__), "dados.json")

@app.route("/login")
def login():
    scope = "identify"
    return redirect(
        f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={scope}"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    r.raise_for_status()
    access_token = r.json().get("access_token")

    user_res = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    user_data = user_res.json()

    session["user_id"] = user_data["id"]
    return redirect("/perfil.html")

@app.route("/api/me")
def get_user_id():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 401
    return jsonify({"user_id": user_id})

@app.route("/api/usuario/<user_id>")
def pegar_dados_usuario(user_id):
    try:
        with open(CAMINHO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
        usuario = {
            "xp": dados.get("xp", {}).get(user_id, 0),
            "tempo_total": dados.get("tempo_total", {}).get(user_id, 0),
            "nivel": int(dados.get("xp", {}).get(user_id, 0) // 250),
            "xaracoins": dados.get("xaracoins", {}).get(user_id, 0),
            "barra": dados.get("barras", {}).get(user_id, {})
        }
        return jsonify(usuario)
    except FileNotFoundError:
        return jsonify({"erro": "Arquivo de dados não encontrado"}), 404

@app.route("/api/todos")
def pegar_todos_usuarios():
    try:
        with open(CAMINHO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
        resposta = {}
        for user_id in dados.get("xp", {}):
            resposta[user_id] = {
                "xp": dados.get("xp", {}).get(user_id, 0),
                "tempo_total": dados.get("tempo_total", {}).get(user_id, 0),
                "xaracoins": dados.get("xaracoins", {}).get(user_id, 0),
                "nivel": int(dados.get("xp", {}).get(user_id, 0) // 250)
            }
        return jsonify(resposta)
    except FileNotFoundError:
        return jsonify({"erro": "Arquivo de dados não encontrado"}), 404

@app.route("/api/avatar/<user_id>")
def get_avatar(user_id):
    try:
        headers = {"Authorization": f"Bot {BOT_TOKEN}"}
        r = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)

        if r.status_code == 200:
            user_data = r.json()
            avatar = user_data.get("avatar")
            banner = user_data.get("banner")
            username = user_data.get("global_name") or user_data.get("username", "Usuário")

            if avatar:
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
            else:
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"

            banner_url = None
            if banner:
                tipo = "gif" if banner.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner}.{tipo}"

            return jsonify({
                "url": avatar_url,
                "banner": banner_url,
                "name": username
            })

        return jsonify({"error": "Usuário não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route("/api/ranking/xp")
def ranking_xp():
    try:
        with open(CAMINHO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)

        lista = sorted(dados.get("xp", {}).items(), key=lambda x: x[1], reverse=True)
        top30 = lista[:30]

        resultado = []
        headers = {"Authorization": f"Bot {BOT_TOKEN}"}

        for user_id, xp in top30:
            nome_salvo = dados.get("nomes", {}).get(user_id, f"ID: {user_id}")
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"

            try:
                r = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)
                if r.status_code == 200:
                    user_data = r.json()
                    nome_salvo = user_data.get("global_name") or user_data.get("username", nome_salvo)
                    avatar = user_data.get("avatar")
                    if avatar:
                        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
            except:
                pass  # Se falhar, mantém os dados padrão

            resultado.append({
                "nome": nome_salvo,
                "xp": xp,
                "avatar_url": avatar_url
            })

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    from waitress import serve
    import os
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

