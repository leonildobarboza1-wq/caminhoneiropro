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
    """Pool diversificado de fotos de caminhões e estradas brasileiras"""
    ids_caminhoes = [
        "1586528116311-ad8dd3c8310d", # Carreta na estrada
        "1544620347-c4fd4a3d5957",    # Caminhão pesado de carga
        "1519003722824-194d4455a60c", # Rodovia de escoamento
        "1563720223185-11003d516935", # Caminhão em viagem
        "1508873696983-2df5c92063c7", # Logística de transporte
        "1601584115197-04ecc0da31d7"  # Bitrem / Carreta
    ]
    foto_id = random.choice(ids_caminhoes)
    rand_seed = random.randint(100, 9999)
    return f"https://images.unsplash.com/photo-{foto_id}?auto=format&fit=crop&w=1200&q=85&sig={rand_seed}"

def gerar_conteudo_com_gemini(api_key):
    if not genai:
        return None, None
    
    # Lista de segmentos para diversificar as postagens
    segmentos = [
        "Agronegócio e Grãos (Bitrem, Rodotrem, Caçamba)",
        "Carga Geral e E-commerce (Baú, Sider, Truck e 3/4)",
        "Produtos Perigosos e Tanque (Combustíveis e Químicos - MOPP)",
        "Distribuição Urbana e Carga Leve (Toco, Accelo, VUC)",
        "Transporte de Veículos e Cargas Excedentes (Cegonheiro, Prancha)",
        "Construção Civil e Mineração (Caçamba, Traçado)"
    ]
    
    segmento_sorteado = random.choice(segmentos)
    
    client = genai.Client(api_key=api_key)
    prompt = (
        f"Você é um especialista em recrutamento para o setor de transporte rodoviário de cargas no Brasil. "
        f"Gere um artigo estruturado em HTML com 4 vagas recentes de emprego para motoristas de caminhão. "
        f"Dê destaque especial ao segmento: '{segmento_sorteado}', mas inclua também oportunidades de outras categorias. "
        f"Abranja diferentes regiões do Brasil (ex: SP, MG, PR, MT, GO, BA, SC, RS, etc.). "
        f"Para cada vaga, informe: Cargo/Função, Categoria de CNH (C, D ou E), Requisitos (MOPP, EAR, experiência), "
        f"Tipo de Rota (Estadual, Interestadual ou Urbana) e Benefícios/Média Salarial. "
        f"Escreva em HTML limpo com tags <h3> para os títulos das vagas, listas <ul> para os detalhes e <p> para a descrição. "
        f"Retorne APENAS um JSON válido com duas chaves: 'titulo' (título chamativo focado em vagas de caminhoneiro) e 'html' (o conteúdo HTML)."
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
    data_formatada = agora.strftime("%d/%m/%Y")
    data_limite = (agora - timedelta(days=7)).strftime("%d/%m/%Y")

    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini)
    titulo_final = titulo_ia if titulo_ia else f"Vagas de Emprego para Caminhoneiros no Brasil - {data_formatada}"
    
    imagem_url = obter_imagem_hd_caminhao()

    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Oportunidades referentes à semana de <strong>{data_limite}</strong> a <strong>{data_formatada}</strong>. Vagas no setor de transportes preenchem-se rapidamente; caso o prazo tenha expirado, consulte as publicações mais recentes do portal.
    </div>
    '''

    conteudo_hero = f'''
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    '''

    # Botão de chamada para redes sociais / grupos de vagas
    botao_grupo = '''
    <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
        <a href="https://facebook.com" target="_blank" style="background-color: #0d6efd; color: #ffffff; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
            👉 Mantenha-se Atualizado no Nosso Grupo de Vagas
        </a>
    </div>
    '''

    conteudo_final = aviso_validade + conteudo_hero + (html_ia if html_ia else "<p>Confira as vagas abertas.</p>") + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
