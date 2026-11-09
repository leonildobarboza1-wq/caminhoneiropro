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
    """Retorna alternadamente uma das três imagens genéricas de emprego/caminhão."""
    urls_fixas = [
        "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",  # Imagem 1: Frotas e Logística
        "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",  # Imagem 2: O Caminhoneiro
        "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg"   # Imagem 3: A Estrada e Vagas
    ]
    
    # Usa a data atual para garantir alternância constante (uma por dia)
    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    dia_do_ano = datetime.now(fuso_br).timetuple().tm_yday
    indice = dia_do_ano % len(urls_fixas)
    
    return urls_fixas[indice]


def gerar_conteudo_com_gemini(api_key, transcricao_shorts=None):
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
        f"Atue como um portal especializado em vagas de emprego para motoristas rodoviários no Brasil. "
        f"Gere um artigo completo em HTML focado no setor de: '{segmento_sorteado}'. "
        f"O artigo DEVE conter exatamente 3 oportunidades de emprego reais/detalhadas para motoristas CNH D ou E. "
        f"Para CADA vaga, você DEVE estruturar as seguintes informações obrigatoriamente: "
        f"1. Nome da Transportadora e Localidade. "
        f"2. Tipo de Veículo / Rota. "
        f"3. Benefícios e Faixa Salarial estimada. "
        f"4. ⚠️ CANAL DE CONTATO DIRETO OBRIGATÓRIO: E-mail específico de recrutamento (ex: rh@transportadora.com.br) ou número de WhatsApp corporativo para envio de currículos. "
        f"Utilize tags <h3> para os títulos das vagas, <ul> e <li> para os detalhes, e <p> para a descrição. "
        f"Retorne APENAS um objeto JSON válido contendo exatamente duas chaves: 'titulo' (título chamativo para o blog) e 'html' (o código HTML completo do post)."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="json")
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



    transcricao_exemplo = (

        "Motorista de distribuição, se você tem a categoria B ou D, a empresa está com oportunidade para você. "

        "Acesse o site oficial indicado no canal para ver os requisitos e fazer a inscrição no processo seletivo."

    )



    dia_da_semana = agora.weekday()

    usar_shorts = (dia_da_semana == 2) # Quarta-feira foca no Short do YouTube



    if usar_shorts:

        logging.info("Modo ativado: Convertendo Short do YouTube em postagem original.")

        titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, transcricao_shorts=transcricao_exemplo)

    else:

        titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, transcricao_shorts=None)



    # 🛡️ Blindagem de Segurança: Se a IA falhar ou retornar vazio, aplica conteúdo estruturado de contingência

    if not html_ia:

        logging.warning("Conteúdo da IA veio vazio. Aplicando estrutura de contingência.")

        titulo_ia = f"Oportunidades e Vagas Urgentes para Caminhoneiros - {data_formatada}"

        html_ia = (

            "<h3>Vagas em Destaque na Região</h3>"

            "<p>As principais transportadoras do país abriram novas oportunidades para motoristas profissionais com CNH D e E. "

            "Há vagas voltadas para o transporte de carga geral, frigorificada e operações rodoviárias de longa distância.</p>"

            "<ul>"

            "<li><strong>Requisitos comuns:</strong> Categoria CNH D ou E válida, experiência comprovada em carteira e curso especializado (MOPP / EAR quando aplicável).</li>"

            "<li><strong>Benefícios:</strong> Salário compatível com a categoria, diárias atrativas, premiações por economia e plano de saúde.</li>"

            "</ul>"

            "<p>Para participar dos processos seletivos e enviar o seu currículo atualizado, entre em contato através dos canais oficiais das empresas ou acompanhe as atualizações diárias em nosso portal.</p>"

        )



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



    conteudo_final = aviso_validade + conteudo_hero + html_ia + botao_grupo



    access_token = obter_access_token(client_id, client_secret, refresh_token)

    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)



if __name__ == '__main__':

    main() 
