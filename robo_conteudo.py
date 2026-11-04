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
    """Pool exclusivo de fotos reais de caminhões para garantir a miniatura automática no Blogger"""
    urls_caminhoes = [
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1519003722824-194d4455a60c?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1563720223185-11003d516935?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=1200&q=85",
        "https://images.unsplash.com/photo-1519219788528-76f50567e722?auto=format&fit=crop&w=1200&q=85"
    ]
    return random.choice(urls_caminhoes)

def gerar_conteudo_com_gemini(api_key, transcricao_shorts=None):
    if not genai:
        return None, None
    
    client = genai.Client(api_key=api_key)
    
    if transcricao_shorts:
        # Modo de reescrita anti-plágio de Shorts do YouTube
        prompt = (
            f"Com base nas informações de vagas contidas na seguinte transcrição de um vídeo curto de recrutamento: '{transcricao_shorts}', "
            f"crie um artigo de blog totalmente original, reescrito com outras palavras, sem mencionar de forma alguma a fonte, o vídeo ou o canal de origem[cite: 1]. "
            f"O artigo deve apresentar claramente a oportunidade para motoristas (ex: CNH exigida, requisitos como EAR/MOPP, região e contatos para envio de currículo). "
            f"Estruture o texto em HTML limpo com tags <h3> para os títulos, listas <ul> para os detalhes e <p> para a descrição. "
            f"Retorne APENAS um JSON válido com duas chaves: 'titulo' (título atrativo de vaga de emprego) e 'html' (conteúdo HTML)."
        )
    else:
        # Modo padrão de curadoria diária de vagas
        segmentos = [
            "Agronegócio e Grãos (Bitrem, Rodotrem, Caçamba)",
            "Carga Geral e E-commerce (Baú, Sider, Truck)",
            "Produtos Perigosos e Tanque (Combustíveis - MOPP)",
            "Distribuição Urbana e Carga Leve (Toco, VUC)",
            "Transporte de Cargas Pesadas e Excedentes (Prancha)",
            "Logística Frigorificada e Rodo-fluvial"
        ]
        segmento_sorteado = random.choice(segmentos)
        prompt = (
            f"Você é um especialista em recrutamento rodoviário no Brasil. "
            f"Gere um artigo estruturado em HTML com 4 vagas recentes de emprego para motoristas de caminhão (CNH D e E). "
            f"Dê destaque especial ao setor: '{segmento_sorteado}', mas inclua vagas de outras áreas em diversas regiões do Brasil. "
            f"⚠️ REGRA OBRIGATÓRIA: Para CADA uma das vagas apresentadas, inclua obrigatoriamente os meios de contato diretos "
            f"da empresa anunciante (ex: E-mail específico de RH, WhatsApp corporativo ou site oficial de carreiras). "
            f"Escreva em HTML limpo utilizando tags <h3> para os títulos das vagas, listas <ul> para os detalhes e <p> para a descrição. "
            f"Retorne APENAS um JSON válido com duas chaves: 'titulo' (título atrativo focado em vagas de caminhoneiro) e 'html' (conteúdo HTML)."
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

    # Exemplo de transcrição de Short capturada do canal de referência para teste/execução pontual
    # (Pode definir como None nos dias normais ou injetar a transcrição do vídeo pretendido)
    transcricao_exemplo = (
        "Motorista de distribuição, se você tem a categoria B ou D, a empresa está com oportunidade para você. "
        "Acesse o site oficial indicado no canal para ver os requisitos e fazer a inscrição no processo seletivo."
    )

    # Lógica de seleção: 1 vez por semana (ex: à quarta-feira, dia da semana 2) podemos processar via Shorts
    dia_da_semana = agora.weekday()
    usar_shorts = (dia_da_semana == 2) # Quarta-feira foca no Short do YouTube

    if usar_shorts:
        logging.info("Modo ativado: Convertendo Short do YouTube em postagem original.")
        titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, transcricao_shorts=transcricao_exemplo)
    else:
        titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, transcricao_shorts=None)

    titulo_final = titulo_ia if titulo_ia else f"Vagas Abertas para Caminhoneiros no Brasil - {data_formatada}"
    
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

    botao_grupo = '''
    <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
        <a href="https://www.facebook.com/groups/1162878270485862" target="_blank" style="background-color: #1877f2; color: #ffffff; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
            👉 Participe do Nosso Grupo Oficial de Vagas no Facebook
        </a>
    </div>
    '''

    conteudo_final = aviso_validade + conteudo_hero + (html_ia if html_ia else "<p>Confira as vagas abertas.</p>") + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
