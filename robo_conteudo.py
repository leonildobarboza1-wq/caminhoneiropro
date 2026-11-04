import os
import sys
import logging
import urllib.request
import urllib.parse
import json
import random
from datetime import datetime, timedelta
import zoneinfo

# Tenta importar o SDK do Gemini
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

logging.basicConfig(level=logging.INFO)

def obter_access_token(client_id, client_secret, refresh_token):
    """Gera um Access Token válido via OAuth2"""
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

def obter_imagem_hd_caminhao():
    """Pool exclusivo de fotos de alta definição focadas em caminhões, carretas e estradas brasileiras"""
    ids_imagens = [
        "1519003722824-194d4455a60c",
        "1586528116311-ad8dd3c8310d",
        "1544620347-c4fd4a3d5957",
        "1506015391300-4802dc74de2e",
        "1563720223185-11003d516935",
        "1508873696983-2df5c92063c7",
        "1511919884226-fd3cad34687c",
        "1559297436-26f18a8cf444"
    ]
    foto_id = random.choice(ids_imagens)
    rand_seed = random.randint(100, 9999)
    return f"https://images.unsplash.com/photo-{foto_id}?auto=format&fit=crop&w=1200&q=85&sig={rand_seed}"

def gerar_conteudo_com_gemini(api_key):
    """Utiliza o Gemini para gerar um boletim completo de vagas recentes para motoristas"""
    if not genai:
        return None, None
    
    client = genai.Client(api_key=api_key)
    prompt = (
        "Crie um artigo estruturado em HTML para um portal de empregos para motoristas de caminhão no Brasil. "
        "O artigo deve simular uma curadoria recente de oportunidades (com até 1 semana de validade) recolhidas de portais e grupos de transporte. "
        "Inclua 3 vagas fictícias detalhadas para motoristas CNH D e E (ex: rotas Sudeste/Sul, transporte frigorificado ou graneleiro), "
        "destacando requisitos como MOPP, experiência e faixa salarial estimada. "
        "Escreva em HTML limpo utilizando tags <h3> para os cargos, listas <ul> para os requisitos e parágrafos <p> explicativos. "
        "Retorne APENAS um JSON com duas chaves: 'titulo' (título chamativo para a postagem) e 'html' (o conteúdo completo em HTML)."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        dados = json.loads(response.text)
        return dados.get("titulo"), dados.get("html")
    except Exception as e:
        logging.error(f"Erro ao gerar conteúdo com o Gemini: {e}")
        return None, None

def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    """Publica a postagem na API do Blogger mantendo o layout intacto"""
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
        logging.error("Erro ao postar na API do Blogger.")
        if hasattr(e, 'read'):
            logging.error(f"Resposta: {e.read().decode('utf-8')}")
        raise e

def main():
    blog_id = os.getenv('BLOG_ID')
    api_key_gemini = os.getenv('GOOGLE_API_KEY')
    client_id = os.getenv('BLOGGER_CLIENT_ID')
    client_secret = os.getenv('BLOGGER_CLIENT_SECRET')
    refresh_token = os.getenv('BLOGGER_REFRESH_TOKEN')
    
    if not all([blog_id, api_key_gemini, client_id, client_secret, refresh_token]):
        logging.error("ERRO CRÍTICO: Secrets em falta no GitHub.")
        sys.exit(1)

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    data_formatada = agora.strftime("%d/%m/%Y")
    data_limite = (agora - timedelta(days=7)).strftime("%d/%m/%Y")

    # Gera título e conteúdo rico com IA
    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini)
    
    titulo_final = titulo_ia if titulo_ia else f"Plantão de Vagas para Motoristas Profissionais - Semana de {data_formatada}"
    
    # Imagem exclusiva de caminhão sem repetição
    imagem_url = obter_imagem_hd_caminhao()

    # Aviso obrigatório de validade (limite de 1 semana)
    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Estas oportunidades foram curadas com referência à semana entre <strong>{data_limite}</strong> e <strong>{data_formatada}</strong>. Vagas no setor de transportes preenchem-se rapidamente; caso o prazo tenha expirado, recomendamos consultar as publicações mais recentes do portal.
    </div>
    '''

    conteudo_hero = f'''
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    '''

    conteudo_final = aviso_hero = aviso_validade + conteudo_hero + (html_ia if html_ia else "<p>Confira abaixo as oportunidades abertas para motoristas em todo o Brasil.</p>")

    # Publicar no Blogger
    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
