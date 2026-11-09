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

def obter_imagem_sequencial():
    """Retorna as imagens em ordem sequencial estrita, garantindo que nunca repita a anterior."""
    urls_fixas = [
        "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",  # Imagem 1
        "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",  # Imagem 2
        "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg"                           # Imagem 3
    ]
    
    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    dia_do_ano = datetime.now(fuso_br).timetuple().tm_yday
    indice = dia_do_ano % len(urls_fixas)
    return urls_fixas[indice]

def gerar_conteudo_com_gemini(api_key):
    if not genai:
        return None, None
    
    client = genai.Client(api_key=api_key)
    
    segmentos = [
        "Agronegócio e Grãos (Bitrem, Rodotrem, Caçamba)",
        "Carga Geral e E-commerce (Baú, Sider, Truck)",
        "Produtos Perigosos e Tanque (Combustíveis - MOPP)",
        "Distribuição Urbana e Carga Leve (Toco, VUC)",
        "Transporte de Cargas Pesadas e Excedentes (Prancha)"
    ]
    segmento_sorteado = random.choice(segmentos)
    
    prompt = (
        f"Atue como um especialista sênior em RH e logística rodoviária. "
        f"Escreva um guia de oportunidades para motoristas CNH D e E focado no setor de: '{segmento_sorteado}'. "
        f"Você DEVE citar explicitamente 3 grandes empresas REAIS do Brasil neste setor. "
        f"Para cada empresa, escreva o nome real dela, a exigência de frota e o canal oficial de recrutamento (ex: link Gupy ou portal Trabalhe Conosco). "
        f"Retorne APENAS um JSON estrito contendo exatamente duas chaves: 'titulo' e 'html'. "
        f"O valor de 'html' DEVE conter tags <h3> com o nome das empresas e <ul>/<li> detalhando os requisitos e o link de contato oficial."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="json")
        )
        texto_resposta = response.text.strip()
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta[7:]
        if texto_resposta.endswith("```"):
            texto_resposta = texto_resposta[:-3]
            
        dados = json.loads(texto_resposta.strip())
        titulo = dados.get("titulo")
        html = dados.get("html")
        
        # Se a IA retornar vazio, força um conteúdo real estruturado em vez de genérico
        if not html or len(html) < 50:
            raise ValueError("HTML retornado veio vazio ou muito curto.")
            
        return titulo, html
    except Exception as e:
        logging.error(f"Erro ao gerar com Gemini: {e}. Usando conteúdo padrão robusto com empresas reais.")
        # Contingência rica com empresas reais caso a API falhe
        titulo_fallback = f"Guia de Vagas e Grandes Frotas: Setor de {segmento_sorteado}"
        html_fallback = (
            f"<h3>1. Tegma Gestão Logística</h3>"
            f"<p>Referência em transporte de veículos e carga industrial.</p>"
            f"<ul><li><strong>Requisitos:</strong> CNH E com EAR e experiência comprovada.</li>"
            f"<li><strong>Como se candidatar:</strong> Acesse o portal oficial de recrutamento em <code>tegma.gupy.io</code>.</li></ul>"
            f"<h3>2. JBS Transportes</h3>"
            f"<p>Atuação forte no agronegócio, carnes e cargas frigorificadas.</p>"
            f"<ul><li><strong>Requisitos:</strong> CNH D/E e disponibilidade para viagens estaduais/interestaduais.</li>"
            f"<li><strong>Como se candidatar:</strong> Cadastre seu currículo na seção 'Trabalhe Conosco' no site oficial da JBS ou via Gupy.</li></ul>"
            f"<h3>3. Raízen / Logística Rodoviária</h3>"
            f"<p>Transporte de combustíveis, granéis e derivados.</p>"
            f"<ul><li><strong>Requisitos:</strong> CNH E obrigatória e curso MOPP atualizado.</li>"
            f"<li><strong>Como se candidatar:</strong> Envie seus dados através do canal oficial de carreiras da Raízen.</li></ul>"
        )
        return titulo_fallback, html_fallback

def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/?isDraft=false"
    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo,
        "labels": ["Guia de Carreira", "Motoristas", "Caminhoneiros", "Grandes Frotas"]
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

    if not html_ia:
        logging.warning("Conteúdo da IA veio vazio. Aplicando estrutura de contingência.")
        titulo_ia = f"Guia de Oportunidades para Caminhoneiros nas Maiores Frotas - {data_formatada}"
        html_ia = (
            "<h3>Guia de Recrutamento: Grandes Frotas Nacionais</h3>"
            "<p>Grandes transportadoras do país mantêm cadastros abertos para motoristas CNH D e E.</p>"
            "<ul><li><strong>Requisitos Padrão:</strong> CNH válida com EAR e experiência comprovada.</li>"
            "<li><strong>Como se candidatar:</strong> Acesse os portais oficiais de 'Trabalhe Conosco' das transportadoras líderes de mercado.</li></ul>"
        )

    titulo_final = titulo_ia if titulo_ia else f"Guia de Vagas para Caminhoneiros - {data_formatada}"
    
    imagem_url = obter_imagem_sequencial()

    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Guia de oportunidades referente à semana de <strong>{data_limite}</strong> a <strong>{data_formatada}</strong>. Oportunidades em grandes frotas possuem fluxo constante de captação de talentos.
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

    conteudo_final = aviso_validade + conteudo_hero + html_ia + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)

if __name__ == '__main__':
    main()
