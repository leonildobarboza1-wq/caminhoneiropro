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

def gerar_banner_exclusivo(titulo_vaga):
    """Gera um banner visual exclusivo em HTML/CSS para a postagem, evitando plágio e repetições"""
    cores_fundo = [
        "linear-gradient(135deg, #1f2937 0%, #111827 100%)",
        "linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%)",
        "linear-gradient(135deg, #374151 0%, #1f2937 100%)",
        "linear-gradient(135deg, #111827 0%, #030712 100%)"
    ]
    gradiente = random.choice(cores_fundo)
    
    banner_html = f'''
    <div style="background: {gradiente}; color: #ffffff; padding: 35px 20px; border-radius: 8px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
        <span style="background-color: #f59e0b; color: #000; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 4px; text-transform: uppercase;">Portal Emprego para Motorista</span>
        <h2 style="color: #ffffff; font-size: 22px; margin-top: 15px; margin-bottom: 10px; line-height: 1.4;">{titulo_vaga}</h2>
        <p style="color: #9ca3af; font-size: 14px; margin: 0;">Oportunidade Verificada • CNH D / E • Todo o Brasil</p>
    </div>
    '''
    return banner_html

def gerar_conteudo_com_gemini(api_key):
    if not genai:
        return None, None
    
    segmentos = [
        "Agronegócio e Grãos (Bitrem, Rodotrem, Caçamba)",
        "Carga Geral e E-commerce (Baú, Sider, Truck)",
        "Produtos Perigosos e Tanque (Combustíveis - MOPP)",
        "Distribuição Urbana e Carga Leve (Toco, VUC)",
        "Transporte de Cargas Pesadas e Excedentes (Prancha)",
        "Logística Frigorificada e Rodo-fluvial"
    ]
    
    segmento_sorteado = random.choice(segmentos)
    
    client = genai.Client(api_key=api_key)
    prompt = (
        f"Você é um especialista em recrutamento rodoviário no Brasil. "
        f"Gere um artigo estruturado em HTML com 4 vagas recentes de emprego para motoristas de caminhão (CNH D e E). "
        f"Dê destaque especial ao setor: '{segmento_sorteado}', mas inclua vagas de outras áreas. "
        f"Cubra diferentes regiões do Brasil (Sul, Sudeste, Centro-Oeste, Nordeste e Norte). "
        f"Para cada vaga, inclua: Cargo/Função, Categoria de CNH obrigatória, Requisitos (MOPP, EAR, experiência), "
        f"Tipo de Rota (Interestadual, Estadual ou Urbana) e Benefícios / Média Salarial estimada. "
        f"Escreva em HTML limpo utilizando tags <h3> para os títulos das vagas, listas <ul> para os detalhes e <p> para a descrição. "
        f"Retorne APENAS um JSON válido com duas chaves: 'titulo' (título chamativo focado em vagas de caminhoneiro no Brasil) e 'html' (o conteúdo HTML)."
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
        logging.error(f"Erro ao gerar conteúdo com o Gemini: {e}")
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
        logging.error("Secrets em falta nas configurações do GitHub.")
        sys.exit(1)

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    data_formatada = agorar_str = agora.strftime("%d/%m/%Y")
    data_limite = (agora - timedelta(days=7)).strftime("%d/%m/%Y")

    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini)
    titulo_final = titulo_ia if titulo_ia else f"Vagas Abertas para Caminhoneiros no Brasil - {data_formatada}"
    
    # Gera um banner visual exclusivo e único para evitar plágios e repetições
    banner_visual = gerar_banner_exclusivo(titulo_final)

    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Oportunidades referentes à semana de <strong>{data_limite}</strong> a <strong>{data_formatada}</strong>. Vagas no setor de transportes preenchem-se rapidamente; caso o prazo tenha expirado, consulte as publicações mais recentes do portal.
    </div>
    '''

    botao_grupo = '''
    <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
        <a href="https://facebook.com" target="_blank" style="background-color: #0d6efd; color: #ffffff; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
            👉 Aceda ao Nosso Grupo de Vagas para Motoristas
        </a>
    </div>
    '''

    conteudo_final = aviso_validade + banner_visual + (html_ia if html_ia else "<p>Confira as vagas abertas.</p>") + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
