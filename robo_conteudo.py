import os
import sys
import logging
import urllib.request
import urllib.parse
import json
import random
from datetime import datetime, timedelta
import zoneinfo

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

logging.basicConfig(level=logging.INFO)

def obter_access_token(client_id, client_secret, refresh_token):
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['access_token']
    except Exception as e:
        logging.error("Erro ao renovar o Access Token.")
        raise e

def obter_imagem_hd_caminhao():
    """IDs validados estritamente de camiões, carretas e transportadoras na estrada"""
    ids_caminhoes = [
        "1586528116311-ad8dd3c8310d", # Cadeira/Carreta na estrada
        "1544620347-c4fd4a3d5957",    # Camião pesado de carga
        "1519003722824-194d4455a60c", # Estrada rodovia
        "1563720223185-11003d516935", # Camião em rodovia
        "1508873696983-2df5c92063c7", # Logística e transporte pesado
        "1601584115197-04ecc0da31d7"  # Camião de grande porte
    ]
    foto_id = random.choice(ids_caminhoes)
    rand_seed = random.randint(100, 9999)
    return f"https://images.unsplash.com/photo-{foto_id}?auto=format&fit=crop&w=1200&q=85&sig={rand_seed}"

def gerar_conteudo_com_gemini(api_key):
    if not genai:
        return None, None
    
    client = genai.Client(api_key=api_key)
    prompt = (
        "Crie um artigo estruturado em HTML focado em vagas de emprego recentes para motoristas de caminhão no Brasil. "
        "Apresente 3 oportunidades reais e detalhadas para motoristas CNH D e E (ex: rotas interestaduais, bitrem, frigorificado), "
        "informando requisitos (MOPP, experiência) e faixa salarial estimada. "
        "Escreva em HTML limpo utilizando tags <h3> para os cargos, listas <ul> para os requisitos e parágrafos <p>. "
        "Retorne APENAS um JSON com duas chaves: 'titulo' (título atrativo) e 'html' (conteúdo em HTML)."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        dados = json.loads(response.text)
        return dados.get("titulo"), dados.get("html")
    except Exception as e:
        logging.error(f"Erro no Gemini: {e}")
        return None, None

def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/?isDraft=false"
    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo,
        "labels": ["Vagas de Emprego", "Motoristas", "Caminhoneiros", "Emprego BR"]
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            logging.info(f"Post publicado com sucesso! ID: {res_data.get('id')}")
            return True
    except Exception as e:
        logging.error("Erro ao postar no Blogger.")
        raise e

def main():
    blog_id = os.getenv('BLOG_ID')
    api_key_gemini = os.getenv('GOOGLE_API_KEY')
    client_id = os.getenv('BLOGGER_CLIENT_ID')
    client_secret = os.getenv('BLOGGER_CLIENT_SECRET')
    refresh_token = os.getenv('BLOGGER_REFRESH_TOKEN')
    
    if not all([blog_id, api_key_gemini, client_id, client_secret, refresh_token]):
        logging.error("Secrets em falta.")
        sys.exit(1)

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    data_formatada = agora.strftime("%d/%m/%Y")
    data_limite = (agora - timedelta(days=7)).strftime("%d/%m/%Y")

    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini)
    titulo_final = titulo_ia if titulo_ia else f"Plantão de Vagas para Motoristas - {data_formatada}"
    
    imagem_url = obter_imagem_hd_caminhao()

    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Oportunidades referéntes à semana de <strong>{data_limite}</strong> a <strong>{data_formatada}</strong>. Vagas no transporte preenchem-se rápido; caso o prazo tenha expirado, consulte as publicações mais recentes do portal.
    </div>
    '''

    conteudo_hero = f'''
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    '''

    conteudo_final = aviso_validade + conteudo_hero + (html_ia if html_ia else "<p>Confira as vagas abertas.</p>")

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
