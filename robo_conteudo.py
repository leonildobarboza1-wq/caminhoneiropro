import os
import sys
import re
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
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["access_token"]
    except Exception as e:
        logging.error(f"Erro ao renovar o Access Token: {e}")
        raise e


def obter_imagem_sequencial():
    """Retorna as imagens em ordem sequencial estrita, garantindo que nunca repita a anterior."""
    urls_fixas = [
        "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",
        "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",
        "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg",
    ]

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    dia_do_ano = datetime.now(fuso_br).timetuple().tm_yday
    indice = dia_do_ano % len(urls_fixas)
    return urls_fixas[indice]


def gerar_conteudo_com_gemini(api_key, data_formatada, data_limite):
    if not genai:
        return None, None

    client = genai.Client(api_key=api_key)

    segmentos = [
        "Agronegócio e Grãos (Bitrem, Rodotrem, Caçamba)",
        "Carga Geral e E-commerce (Baú, Sider, Truck)",
        "Produtos Perigosos e Tanque (Combustíveis - MOPP)",
        "Distribuição Urbana e Carga Leve (Toco, VUC)",
        "Transporte de Cargas Pesadas e Excedentes (Prancha)",
    ]
    segmento_sorteado = random.choice(segmentos)

    prompt = f"""
Você é um especialista sênior em RH e logística rodoviária no Brasil.
Hoje é {data_formatada}. Use a Pesquisa Google para encontrar até 10 vagas REAIS e RECENTES (divulgadas entre {data_limite} e {data_formatada}) para motoristas profissionais (CNH C, D ou E: carreteiro, truck, toco, bitrem, cegonheiro, entregas) no Brasil, com foco principal em '{segmento_sorteado}', mas incluindo outras regiões do país para alcançar até 10 oportunidades válidas.

### REGRAS RIGOROSAS
1. **Apenas vagas reais e recentes:** Priorize transportadoras reais, Gupy, PandaPé, InfoJobs, Catho, Vagas.com, LinkedIn, Indeed e páginas oficiais de recrutamento. Descarte vagas antigas, expiradas, links suspeitos ou golpes com cobrança de taxa.
2. **Zero invenção de dados:** NUNCA invente salários, valores, benefícios, e-mails, telefones ou links. Se o salário ou benefício não aparecer na fonte, omita a linha de ganhos/benefícios daquela vaga.
3. **Estrutura de cada vaga (igual ao modelo):**
   - Título da vaga em `<h3>`: `N. Empresa – Cargo / Tipo de Caminhão (Cidade - UF ou Região)`
   - Lista `<ul>` com itens `<li>` usando `<strong>`:
     * `<strong>Base / Rotas:</strong> ...` (apenas se houver base específica ou rotas citadas na vaga)
     * `<strong>Requisitos:</strong> CNH, escolaridade, cursos (MOPP, EAR, direção defensiva), experiência e disponibilidade`
     * `<strong>Ganhos e Benefícios:</strong> ...` (apenas se constar na vaga encontrada)
     * `<strong>Candidatura:</strong> E-mail, WhatsApp, portal ou link oficial encontrado na busca`

### FORMATO DE SAÍDA OBRIGATÓRIO
Retorne APENAS um JSON estrito com exatamente duas chaves: "titulo" e "html".
- "titulo": Ex: "10 Oportunidades para Motoristas – Brasil (Atualizado {data_formatada})"
- "html": Comece com um `<p>` curto de introdução (2 a 3 linhas), liste as vagas encontradas (até 10) no formato `<h3>` + `<ul><li>`, e finalize com um `<p>` curto orientando a conferir os dados oficiais no canal de candidatura e colocar o nome da vaga e cidade no assunto ou primeira mensagem.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2,
            ),
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
        logging.error(f"Erro ao gerar com Gemini: {e}. Usando conteúdo padrão robusto.")
        titulo_fallback = f"Oportunidades e Grandes Frotas para Motoristas – {data_formatada}"
        html_fallback = (
            "<p>Confira canais oficiais de recrutamento de transportadoras com operação ativa no Brasil:</p>"
            "<h3>1. Tegma Gestão Logística – Brasil</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH Categoria E com EAR e experiência comprovada.</li>"
            "<li><strong>Candidatura:</strong> Portal oficial em <code>tegma.gupy.io</code>.</li></ul>"
            "<h3>2. JBS Transportes – Várias Regiões</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH Categoria D ou E e disponibilidade para viagens.</li>"
            "<li><strong>Candidatura:</strong> Portal Trabalhe Conosco oficial da JBS ou Gupy.</li></ul>"
            "<h3>3. Transpanorama Transportes – Brasil</h3>"
            "<ul><li><strong>Requisitos:</strong> CNH Categoria E com EAR e experiência em carreta/bitrem.</li>"
            "<li><strong>Candidatura:</strong> Portal oficial em <code>transpanorama.gupy.io</code>.</li></ul>"
        )
        return titulo_fallback, html_fallback


def postar_no_blogger(blog_id, access_token, titulo, conteudo):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/?isDraft=false"
    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo,
        "labels": ["Guia de Carreira", "Motoristas", "Caminhoneiros", "Grandes Frotas"],
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            logging.info(f"Post publicado com sucesso! ID: {res_data.get('id')}")
            return True
    except Exception as e:
        logging.error(f"Erro ao postar no Blogger: {e}")
        raise e


def main():
    blog_id = os.getenv("BLOG_ID")
    api_key_gemini = os.getenv("GOOGLE_API_KEY")
    client_id = os.getenv("BLOGGER_CLIENT_ID")
    client_secret = os.getenv("BLOGGER_CLIENT_SECRET")
    refresh_token = os.getenv("BLOGGER_REFRESH_TOKEN")

    if not all([blog_id, api_key_gemini, client_id, client_secret, refresh_token]):
        logging.error("Secrets em falta nas configurações do GitHub.")
        sys.exit(1)

    fuso_br = zoneinfo.ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    data_formatada = agora.strftime("%d/%m/%Y")
    data_limite = (agora - timedelta(days=7)).strftime("%d/%m/%Y")

    titulo_ia, html_ia = gerar_conteudo_com_gemini(api_key_gemini, data_formatada, data_limite)

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

    aviso_validade = f"""
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 12px; margin-bottom: 20px; font-size: 14px; color: #856404;">
        <strong>⚠️ Aviso importante sobre os prazos:</strong> Guia de oportunidades referente à semana de <strong>{data_limite}</strong> a <strong>{data_formatada}</strong>. Oportunidades em grandes frotas possuem fluxo constante de captação de talentos.
    </div>
    """

    conteudo_hero = f"""
    <div class="article-hero" style="margin-bottom: 20px;">
        <img src="{imagem_url}" alt="{titulo_final}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 8px;" />
    </div>
    """

    botao_grupo = """
    <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
        <a href="https://www.facebook.com/groups/1162878270485862" target="_blank" style="background-color: #1877f2; color: #ffffff; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
            👉 Participe do Nosso Grupo Oficial de Vagas no Facebook
        </a>
    </div>
    """

    conteudo_final = aviso_validade + conteudo_hero + html_ia + botao_grupo

    access_token = obter_access_token(client_id, client_secret, refresh_token)
    postar_no_blogger(blog_id, access_token, titulo_final, conteudo_final)


if __name__ == "__main__":
    main()
