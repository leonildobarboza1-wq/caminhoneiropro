import os
import sys
import re
import logging
import urllib.request
import urllib.parse
import json
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
        logging.error(f"Erro ao renovar o Access Token: {e}")
        raise e


def obter_imagem_sequencial():
    """Retorna as imagens em ordem sequencial estrita, garantindo que nunca repita a anterior."""
    urls_fixas = [
        "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",
        "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",
        "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg"
    ]

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    dia_do_ano = datetime.now(fuso_br).timetuple().tm_yday
    indice = dia_do_ano % len(urls_fixas)
    return urls_fixas[indice]


def gerar_conteudo_com_gemini(api_key, data_formatada, data_limite):
    if not genai:
        return None, None

    client = genai.Client(api_key=api_key)

    prompt = f"""
Você é um especialista em recrutamento logístico e redator de conteúdo focado em motoristas profissionais no Brasil (CNH C, D e E, carreteiro, truck, toco, bitrem, cegonheiro, motorista de entrega).

Sua missão hoje ({data_formatada}) é usar a Pesquisa Google para encontrar VAGAS REAIS E ATUAIS para motorista de caminhão no Brasil publicadas recentemente (entre {data_limite} e {data_formatada}).

### REGRAS RIGOROSAS DE BUSCA E FILTRO
1. **Recência obrigatória:** Busque vagas abertas e recentes em transportadoras reais, Gupy, PandaPé, InfoJobs, Catho, Vagas.com, LinkedIn, Indeed e canais oficiais de recrutamento. Descarte vagas antigas, expiradas ou suspeitas.
2. **Dados reais e verificados:** NUNCA invente salários, benefícios, e-mails, telefones ou links. Se um dado (como salário) não estiver explícito na vaga encontrada, simplesmente omita esse item.
3. **Dados mínimos por vaga:** Cada vaga deve conter:
   - Cargo / Tipo de veículo (ex.: Motorista Carreteiro, Truck, Bitrem, Cegonheiro)
   - Cidade e Estado (UF)
   - Nome da Empresa / Transportadora
   - Requisitos principais (ex.: CNH E, EAR, MOPP, experiência)
   - Como se candidatar (e-mail, WhatsApp, site ou link oficial encontrado)
4. **Quantidade:** Selecione de 8 a 12 vagas reais bem distribuídas pelo Brasil.

### FORMATO DE SAÍDA OBRIGATÓRIO
Retorne APENAS um objeto JSON válido (sem markdown ```json) com exatamente duas chaves: "titulo" e "html".
- "titulo": Ex: "Vagas Atualizadas para Motorista de Caminhão no Brasil – {data_formatada}"
- "html": HTML limpo pronto para Blogger contendo:
  1. Um parágrafo `<p>` curto de introdução (2 a 3 linhas).
  2. Para cada vaga, uma tag `<h3>` com `Cargo – Cidade/UF (Empresa)` seguida de `<ul>` com `<li><strong>Requisitos:</strong> ...</li>`, `<li><strong>Benefícios/Salário:</strong> ...</li>` (apenas se constar na fonte) e `<li><strong>Como se candidatar:</strong> ...</li>`.
  3. Um parágrafo `<p>` final lembrando que as vagas podem encerrar a qualquer momento.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2,
            )
        )

        texto_resposta = (response.text or "").strip()

        match_json = re.search(r"\{.*\}", texto_resposta, flags=re.DOTALL)
        if not match_json:
            raise ValueError("Resposta do Gemini não conteve um JSON válido.")

        dados = json.loads(match_json.group(0))
        titulo = dados.get("titulo")
        html = dados.get("html")

        if not html or "<h3>" not in html.lower() or len(html) < 150:
            raise ValueError("HTML retornado veio vazio ou sem estrutura de vagas.")

        return titulo, html

    except Exception as e:
        logging.error(f"Erro ao buscar/gerar vagas reais com Gemini: {e}. Usando contingência.")
        titulo_fallback = f"Oportunidades e Cadastro de Reserva para Motoristas CNH D e E – {data_formatada}"
        html_fallback = (
            "<p>Confira os canais oficiais de recrutamento aberto nas principais transportadoras do país:</p>"
            "<h3>1. Tegma Gestão Logística – Brasil</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH E com EAR e experiência comprovada.</li>"
            "<li><strong>Como se candidatar:</strong> Acesse o portal oficial em <code>tegma.gupy.io</code>.</li></ul>"
            "<h3>2. JBS Transportes – Várias Regiões</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH D ou E e disponibilidade para viagens.</li>"
            "<li><strong>Como se candidatar:</strong> Cadastre seu currículo no portal 'Trabalhe Conosco' da JBS ou via Gupy.</li></ul>"
            "<h3>3. Transpanorama Transportes – Brasil</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH E com EAR e experiência em carreta/bitrem.</li>"
            "<li><strong>Como se candidatar:</strong> Acesse o portal oficial <code>transpanorama.gupy.io</code>.</li></ul>"
        )
        return titulo_fallback, html_fallback


def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    url = f"[https://www.googleapis.com/blogger/v3/blogs/](https://www.googleapis.com/blogger/v3/blogs/){blog_id}/posts/?isDraft=false"
    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo,
        "labels": ["Vagas Motorista", "Caminhoneiros", "Emprego", "Logística"]
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
            logging.info(f"Post publicado com sucesso! ID: {res_data.get('id')} | URL: {res_data.get('url')}")
            return True
    except Exception as e:
        logging.error(f"Erro ao postar no Blogger: {e}")
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
    data_limite = (agora - timedelta(days=3)).strftime("%d/%m/%Y")

    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, data_formatada, data_limite)

    titulo_final = titulo_ia if titulo_ia else f"Vagas para Motorista de Caminhão no Brasil – {data_formatada}"
    imagem_url = obter_imagem_sequencial()

    aviso_validade = f'''
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Levantamento de vagas divulgadas entre <strong>{data_limite}</strong> e <strong>{data_formatada}</strong>. Vagas de motorista preenchem rápido — envie seu currículo o quanto antes e nunca pague taxas para participar de processos seletivos.
    </div>
    '''

    conteudo_hero = f'''
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    '''

    botao_grupo = '''
    <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
        <a href="[https://www.facebook.com/groups/1162878270485862](https://www.facebook.com/groups/1162878270485862)" target="_blank" style="background-color: #1877f2; color: #ffffff; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
            👉 Participe do Nosso Grupo Oficial de Vagas no Facebook
        </a>
    </div>
    '''

    conteudo_final = aviso_validade + conteudo_hero + html_ia + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)


if __name__ == '__main__':
    main()
