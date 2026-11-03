import os
import sys
import logging
import urllib.request
import urllib.parse
import json
import random
from datetime import datetime
import zoneinfo

# Tenta importar do SDK do Gemini
try:
    from google import genai
except ImportError:
    genai = None

logging.basicConfig(level=logging.INFO)

# Nicho Fixo para a AI Site Factory alimentar este blog
NICHO_ALVO = "Vagas de Emprego para Motoristas de Caminhão, Carreteiros e Logística no Brasil"

def obter_access_token(client_id, client_secret, refresh_token):
    """Gera um Access Token válido a partir do Refresh Token (OAuth2)"""
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
        logging.error("Erro crítico ao renovar o Access Token via OAuth2.")
        if hasattr(e, 'read'):
            logging.error(f"Detalhes: {e.read().decode('utf-8')}")
        raise e

def obter_ultimos_titulos_blogger(blog_id, access_token):
    """Busca os títulos das últimas postagens do blog para evitar duplicidade"""
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?maxResults=20&fetchBodies=false"
    headers = {'Authorization': f'Bearer {access_token}'}
    req = urllib.request.Request(url, headers=headers, method='GET')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            items = res_data.get('items', [])
            return [item['title'].lower().strip() for item in items]
    except Exception as e:
        logging.warning(f"Não foi possível buscar posts antigos do Blogger: {e}")
        return []

def obter_imagem_hd_estrada():
    """Pool de fotos de alta definição focadas em caminhões e estradas brasileiras"""
    ids_imagens = [
        "1519003722824-194d4455a60c",
        "1586528116311-ad8dd3c8310d",
        "1544620347-c4fd4a3d5957",
        "1506015391300-4802dc74de2e",
        "1469854523086-cc02fe5d8800",
        "1512917774080-9991f1c4c750",
        "1511919884226-fd3cad34687c",
        "1563720223185-11003d516935",
        "1559297436-26f18a8cf444",
        "1508873696983-2df5c92063c7"
    ]
    foto_id = random.choice(ids_imagens)
    rand_seed = random.randint(100, 9999)
    return f"https://images.unsplash.com/photo-{foto_id}?auto=format&fit=crop&w=1200&q=85&sig={rand_seed}"

def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    """Envia o artigo formatado para a API do Blogger sem alterar a estrutura do tema"""
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
            logging.info(f"Post publicado com sucesso no Portal! ID: {res_data.get('id')}")
            return True
    except Exception as e:
        logging.error("Erro ao postar na API do Blogger.")
        if hasattr(e, 'read'):
            logging.error(f"Resposta do Blogger: {e.read().decode('utf-8')}")
        raise e

def main():
    blog_id = os.getenv('BLOG_ID')
    api_key_gemini = os.getenv('GOOGLE_API_KEY')
    client_id = os.getenv('BLOGGER_CLIENT_ID')
    client_secret = os.getenv('BLOGGER_CLIENT_SECRET')
    refresh_token = os.getenv('BLOGGER_REFRESH_TOKEN')
    
    if not all([blog_id, api_key_gemini, client_id, client_secret, refresh_token]):
        logging.error("ERRO CRÍTICO: Chaves ou Secrets faltando nas definições do GitHub.")
        sys.exit(1)

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso_br).strftime("%d/%m/%Y às %H:%M")

    # Autenticação OAuth2
    access_token = obter_access_token(client_id, client_secret, refresh_token)
    titulos_publicados = obter_ultimos_titulos_blogger(blog_id, access_token)

    # Injeção da imagem no topo da postagem
    imagem_url = obter_imagem_hd_estrada()
    
    # Exemplo simples de estrutura HTML adaptada para o tema Sora Jobs / Portal
    titulo_final = f"Oportunidades de Emprego para Motoristas Profissionais - {agora.split(' ')[0]}"
    
    conteudo_final = f'''
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    <h2>Vagas em Destaque no Setor de Transporte e Logística</h2>
    <p>Confira as últimas vagas verificadas para motoristas de caminhão, carretas (CNH C, D e E) e entregadores em diversas regiões do Brasil.</p>
    <br><hr>
    <p><small><i>Atualizado automaticamente para o portal em {agora}.</i></small></p>
    '''

    # Publica mantendo o layout do site intocado
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
