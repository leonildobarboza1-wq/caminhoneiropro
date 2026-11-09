
import os
import sys
import logging
import urllib.request
import urllib.parse
import urllib.error
import json
import random
from datetime import datetime, timedelta
import zoneinfo

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

FUSO_BR = zoneinfo.ZoneInfo("America/Sao_Paulo")
MODELO_GEMINI = "gemini-2.5-flash"


# ============================================================
# AUTENTICAÇÃO BLOGGER
# ============================================================

def obter_access_token(client_id, client_secret, refresh_token):

    url = "https://oauth2.googleapis.com/token"

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    data = urllib.parse.urlencode(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:

            res_data = json.loads(
                response.read().decode("utf-8")
            )

            access_token = res_data.get("access_token")

            if not access_token:
                raise ValueError(
                    "O Google não retornou um Access Token."
                )

            logging.info("Access Token renovado com sucesso.")

            return access_token

    except urllib.error.HTTPError as e:

        detalhe = e.read().decode("utf-8", errors="replace")

        logging.error(
            f"Erro HTTP na autenticação Blogger: {e.code} - {detalhe}"
        )

        raise


# ============================================================
# IMAGENS SEQUENCIAIS
# ============================================================

def obter_imagem_sequencial():

    urls_fixas = [
        "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",

        "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",

        "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg"
    ]

    dia_do_ano = datetime.now(FUSO_BR).timetuple().tm_yday

    indice = dia_do_ano % len(urls_fixas)

    return urls_fixas[indice]


# ============================================================
# EXTRAÇÃO E VALIDAÇÃO DO JSON
# ============================================================

def extrair_json_resposta(texto):

    if not texto or not texto.strip():

        raise ValueError("A IA retornou uma resposta vazia.")

    texto = texto.strip()

    # Remove blocos Markdown, se existirem.

    if texto.startswith("```json"):

        texto = texto[7:]

    elif texto.startswith("```"):

        texto = texto[3:]

    if texto.endswith("```"):

        texto = texto[:-3]

    texto = texto.strip()

    # Localiza o objeto JSON.

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio == -1 or fim == -1 or fim <= inicio:

        raise ValueError(
            "Não foi encontrado um objeto JSON válido na resposta."
        )

    texto_json = texto[inicio:fim + 1]

    dados = json.loads(texto_json)

    if not isinstance(dados, dict):

        raise ValueError("A resposta não é um objeto JSON.")

    if set(dados.keys()) != {"titulo", "html"}:

        raise ValueError(
            "O JSON deve possuir exatamente as chaves titulo e html."
        )

    titulo = dados.get("titulo")
    html = dados.get("html")

    if not isinstance(titulo, str) or not titulo.strip():

        raise ValueError("Título inválido ou vazio.")

    if not isinstance(html, str) or not html.strip():

        raise ValueError("HTML inválido ou vazio.")

    return titulo.strip(), html.strip()


# ============================================================
# GERAÇÃO DE CONTEÚDO COM GEMINI + PESQUISA GOOGLE
# ============================================================

def gerar_conteudo_com_gemini(api_key):

    if not genai or not types:

        logging.error(
            "Biblioteca google-genai não instalada."
        )

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

    agora = datetime.now(FUSO_BR)

    data_pesquisa = agora.strftime("%d/%m/%Y")

    logging.info(
        f"Segmento selecionado: {segmento_sorteado}"
    )

    logging.info(
        "Iniciando pesquisa de oportunidades com Google Search..."
    )

    # --------------------------------------------------------
    # PROMPT EDITORIAL MASTER
    # --------------------------------------------------------

    prompt = f"""
ATUE COMO UM JORNALISTA INVESTIGATIVO SÊNIOR,
ESPECIALISTA EM RECRUTAMENTO, TRANSPORTE RODOVIÁRIO,
LOGÍSTICA E MERCADO DE TRABALHO NO BRASIL.

Você é responsável pela produção editorial de um portal
especializado em oportunidades de emprego para motoristas
profissionais e caminhoneiros.

DATA ATUAL DA PESQUISA: {data_pesquisa}

SEGMENTO DESTA PUBLICAÇÃO:
{segmento_sorteado}

OBJETIVO:

Produzir uma reportagem jornalística completa, original,
aprofundada e confiável sobre oportunidades profissionais
relacionadas ao segmento selecionado.

ATENÇÃO: UTILIZE A PESQUISA GOOGLE DISPONÍVEL PARA
CONSULTAR INFORMAÇÕES ATUAIS NA INTERNET.

============================================================
ETAPA 1 - PESQUISA REAL
============================================================

Pesquise empresas brasileiras relacionadas ao segmento.

Priorize:

- Grandes transportadoras nacionais.
- Empresas de logística.
- Operadores de transporte rodoviário.
- Indústrias com frota própria.
- Empresas de distribuição.
- Transportadoras especializadas.

Consulte prioritariamente:

1. Sites oficiais das empresas.
2. Páginas oficiais Trabalhe Conosco.
3. Gupy e outras plataformas oficiais de recrutamento.
4. Anúncios de emprego identificados e verificáveis.
5. Publicações oficiais de recrutamento.

Não utilize apenas o conhecimento interno do modelo.

Procure informações atuais e considere a data da pesquisa.

============================================================
ETAPA 2 - VERACIDADE DAS VAGAS
============================================================

Identifique até 3 empresas com oportunidades relacionadas
ao segmento.

Diferencie obrigatoriamente:

VAGA ATIVA:
Existe anúncio específico e verificável de contratação.

RECRUTAMENTO ABERTO:
A empresa recebe currículos, mas não existe confirmação
de uma vaga específica em aberto.

OPORTUNIDADE NÃO CONFIRMADA:
Não foi possível verificar a situação atual.

Não apresente recrutamento genérico como vaga ativa.

Não invente:

- Vagas de emprego.
- Cidades de contratação.
- Salários.
- Benefícios.
- Telefones.
- E-mails.
- Requisitos.
- Links de candidatura.
- Datas de processos seletivos.

Se não encontrar três oportunidades verificáveis,
utilize somente as empresas que conseguir confirmar.

Nunca invente informações para completar a quantidade.

============================================================
ETAPA 3 - INFORMAÇÕES DE CADA EMPRESA
============================================================

Para cada empresa, procure levantar:

- Nome oficial.
- Cidade e estado da oportunidade.
- Cargo disponível.
- Tipo de veículo utilizado.
- Tipo de operação.
- Categoria de CNH exigida.
- Necessidade de EAR.
- Exigência de MOPP, quando aplicável.
- Experiência profissional.
- Qualificações adicionais.
- Salário, somente quando divulgado.
- Benefícios, somente quando confirmados.
- Regime de contratação, quando informado.
- Situação atual da vaga.
- Link direto para candidatura.
- Canal oficial de recrutamento.

Preserve exatamente os dados encontrados nas fontes.

Não presuma que toda vaga para carreta exige MOPP.

Não presuma que toda empresa contrata motoristas CNH D e E.

Cada requisito deve corresponder à oportunidade pesquisada.

Se determinada informação não estiver disponível,
informe que ela não foi divulgada.

============================================================
ETAPA 4 - ORIGINALIDADE JORNALÍSTICA
============================================================

Escreva uma reportagem completamente original.

Não copie textos de outros sites.

Não faça simples substituição de palavras por sinônimos.

Não reproduza a sequência de parágrafos de matérias
encontradas na internet.

Não copie títulos de outras publicações.

Utilize os fatos comprovados para construir uma nova
reportagem, com abordagem editorial independente.

Produza:

- Introdução jornalística própria.
- Contextualização do mercado de trabalho.
- Análise das operações de transporte.
- Apresentação organizada das oportunidades.
- Explicação dos requisitos.
- Orientações práticas para candidatura.
- Conclusão original.

Não invente entrevistas, depoimentos ou declarações.

Não altere o sentido das informações verificadas.

============================================================
ETAPA 5 - CONTEÚDO ROBUSTO E SEO
============================================================

O artigo deve ser aprofundado, informativo e agradável
de ler.

Utilize linguagem profissional, natural e acessível.

O conteúdo deve ajudar efetivamente o motorista
que procura uma oportunidade de trabalho.

Otimize naturalmente para pesquisas como:

- Vagas para caminhoneiros.
- Vagas para motoristas.
- Motorista carreteiro.
- Emprego para motorista CNH E.
- Vagas para motorista CNH D.
- Vagas para motorista bitrem.
- Vagas para motorista sider.
- Empresas contratando motoristas.
- Oportunidades no transporte rodoviário.

Utilize somente palavras-chave pertinentes ao conteúdo.

Não faça repetição artificial de termos.

Evite títulos sensacionalistas.

Não prometa contratação garantida.

O artigo deve apresentar conteúdo relevante e substancial,
sem utilizar parágrafos genéricos apenas para aumentar
o tamanho da publicação.

============================================================
ETAPA 6 - ESTRUTURA DA REPORTAGEM
============================================================

Organize o artigo nesta sequência:

1. Introdução atrativa e jornalística.

2. Contextualização das oportunidades no segmento.

3. Apresentação individual das empresas pesquisadas.

4. Detalhamento das vagas e operações.

5. Requisitos profissionais e qualificações.

6. Informações sobre candidatura e recrutamento.

7. Orientações para evitar golpes em falsas vagas.

8. Conclusão incentivando a consulta dos canais oficiais.

Seção de fontes e referências ao final do artigo.

Utilize subtítulos claros e parágrafos bem distribuídos.

============================================================
ETAPA 7 - LINKS E CONTATOS
============================================================

Os links devem ser reais e relacionados à empresa correta.

Priorize links diretos de candidatura.

Quando não houver vaga específica, utilize o portal oficial
de recrutamento e deixe claro que se trata de cadastro
ou consulta de oportunidades.

Não crie URLs fictícias.

Não utilize links de terceiros como se fossem canais oficiais.

Não invente contatos telefônicos ou endereços de e-mail.

Inclua links das fontes utilizadas na apuração, sempre que
estiverem disponíveis.

============================================================
ETAPA 8 - HTML PARA BLOGGER
============================================================

Produza HTML limpo e compatível com Blogger.

Utilize:

<h2> para seções principais.
<h3> para nomes das empresas.
<p> para parágrafos.
<ul> e <li> para listas.
<strong> para destaques.
<a href="URL"> para links.

Utilize links clicáveis para candidatura.

Inclua uma seção final de fontes e canais oficiais.

Não utilize JavaScript, scripts, iframes ou CSS externo.

============================================================
ETAPA 9 - REVISÃO EDITORIAL
============================================================

Antes de responder, confira:

- As empresas existem?
- As informações são atuais?
- As vagas foram realmente encontradas?
- Os requisitos correspondem às fontes?
- Os links estão relacionados às empresas?
- O artigo possui redação independente?
- O HTML está organizado?
- Não existem informações inventadas?
- A matéria oferece utilidade real ao candidato?

Se não conseguir confirmar uma informação,
não a apresente como fato.

============================================================
FORMATO FINAL OBRIGATÓRIO
============================================================

Retorne somente um objeto JSON válido.

O objeto deve possuir exatamente duas chaves:

"titulo": título principal otimizado para SEO.

"html": artigo completo em HTML.

Não escreva explicações fora do JSON.

Não utilize blocos Markdown.

Não adicione outras chaves.

Garanta que as aspas internas e os caracteres especiais
estejam corretamente escapados para JSON.

PRIORIDADE ABSOLUTA:

VERACIDADE DAS OPORTUNIDADES.
AUTENTICIDADE DOS CONTATOS.
ORIGINALIDADE JORNALÍSTICA.
UTILIDADE PARA OS MOTORISTAS.
QUALIDADE EDITORIAL E SEO.
"""

    try:

        # Pesquisa Google habilitada no Gemini.
        ferramenta_pesquisa = types.Tool(
            google_search=types.GoogleSearch()
        )

        configuracao = types.GenerateContentConfig(
            tools=[ferramenta_pesquisa],
            temperature=0.4,
            max_output_tokens=8192
        )

        response = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt,
            config=configuracao
        )

        texto_resposta = response.text

        titulo, html = extrair_json_resposta(
            texto_resposta
        )

        logging.info(
            f"Conteúdo gerado com sucesso: {titulo}"
        )

        return titulo, html

    except Exception as e:

        logging.exception(
            f"Erro ao gerar conteúdo com Gemini: {e}"
        )

        return None, None


# ============================================================
# PUBLICAÇÃO NO BLOGGER
# ============================================================

def postar_no_blogger(
    blog_id,
    access_token,
    titulo,
    conteudo
):

    url = (
        f"https://www.googleapis.com/blogger/v3/"
        f"blogs/{blog_id}/posts/?isDraft=false"
    )

    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo,
        "labels": [
            "Guia de Carreira",
            "Motoristas",
            "Caminhoneiros",
            "Grandes Frotas",
            "Vagas de Emprego"
        ]
    }

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=60
        ) as response:

            res_data = json.loads(
                response.read().decode("utf-8")
            )

            logging.info(
                f"Post publicado com sucesso! "
                f"ID: {res_data.get('id')}"
            )

            logging.info(
                f"URL da postagem: {res_data.get('url')}"
            )

            return True

    except urllib.error.HTTPError as e:

        detalhe = e.read().decode(
            "utf-8",
            errors="replace"
        )

        logging.error(
            f"Erro HTTP ao publicar no Blogger: "
            f"{e.code} - {detalhe}"
        )

        raise

    except Exception as e:

        logging.exception(
            f"Erro ao publicar no Blogger: {e}"
        )

        raise


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():

    logging.info("========================================")
    logging.info("INICIANDO ROBO DE CONTEUDO")
    logging.info("========================================")

    # Secrets do GitHub

    blog_id = os.getenv("BLOG_ID")

    api_key_gemini = os.getenv("GOOGLE_API_KEY")

    client_id = os.getenv("BLOGGER_CLIENT_ID")

    client_secret = os.getenv("BLOGGER_CLIENT_SECRET")

    refresh_token = os.getenv("BLOGGER_REFRESH_TOKEN")

    # Verificação das credenciais

    if not all([
        blog_id,
        api_key_gemini,
        client_id,
        client_secret,
        refresh_token
    ]):

        logging.error(
            "Secrets em falta nas configurações do GitHub."
        )

        sys.exit(1)

    agora = datetime.now(FUSO_BR)

    data_formatada = agora.strftime("%d/%m/%Y")

    data_limite = (
        agora - timedelta(days=7)
    ).strftime("%d/%m/%Y")

    # --------------------------------------------------------
    # GERAÇÃO DO ARTIGO
    # --------------------------------------------------------

    titulo_ia, html_ia = gerar_conteudo_com_gemini(
        api_key_gemini
    )

    # Não publicar conteúdo genérico ou sem validação.

    if not titulo_ia or not html_ia:

        logging.error(
            "A geração do conteúdo falhou. "
            "Publicação cancelada para evitar informações "
            "não verificadas."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # IMAGEM DA POSTAGEM
    # --------------------------------------------------------

    imagem_url = obter_imagem_sequencial()

    # --------------------------------------------------------
    # AVISO EDITORIAL
    # --------------------------------------------------------

    aviso_validade = f"""
    <div style="
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 12px;
        margin-bottom: 20px;
        font-size: 14px;
        color: #856404;
    ">
        <strong>⚠️ Atenção aos candidatos:</strong>
        Este conteúdo foi elaborado em {data_formatada}.
        As informações sobre oportunidades podem mudar
        conforme os processos seletivos das empresas.
        Consulte sempre os canais oficiais antes de enviar
        seu currículo.
    </div>
    """

    # --------------------------------------------------------
    # IMAGEM PRINCIPAL
    # --------------------------------------------------------

    conteudo_hero = f"""
    <div class="article-hero"
         style="margin-bottom: 20px;">

        <img
            src="{imagem_url}"
            alt="{titulo_ia}"
            style="
                width: 100%;
                max-height: 480px;
                object-fit: cover;
                border-radius: 8px;
            "
        />

    </div>
    """

    # --------------------------------------------------------
    # BOTÃO DO GRUPO DE VAGAS
    # --------------------------------------------------------

    botao_grupo = """
    <div style="
        text-align: center;
        margin-top: 30px;
        margin-bottom: 20px;
    ">

        <a
            href="https://www.facebook.com/groups/1162878270485862"
            target="_blank"
            rel="noopener noreferrer"
            style="
                background-color: #1877f2;
                color: #ffffff;
                padding: 14px 28px;
                text-decoration: none;
                font-weight: bold;
                border-radius: 5px;
                font-size: 16px;
                display: inline-block;
            "
        >
            👉 Participe do Nosso Grupo de Vagas no Facebook
        </a>

    </div>
    """

    # --------------------------------------------------------
    # MONTAGEM DO CONTEÚDO FINAL
    # --------------------------------------------------------

    conteudo_final = (
        aviso_validade
        + conteudo_hero
        + html_ia
        + botao_grupo
    )

    # --------------------------------------------------------
    # AUTENTICAÇÃO E PUBLICAÇÃO
    # --------------------------------------------------------

    logging.info(
        "Renovando autenticação do Blogger..."
    )

    access_token = obter_access_token(
        client_id,
        client_secret,
        refresh_token
    )

    logging.info(
        "Enviando artigo para o Blogger..."
    )

    sucesso = postar_no_blogger(
        blog_id,
        access_token,
        titulo_ia,
        conteudo_final
    )

    if sucesso:

        logging.info("========================================")
        logging.info("AUTOMAÇÃO FINALIZADA COM SUCESSO")
        logging.info("========================================")


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception:

        logging.exception(
            "A execução do robô foi interrompida."
        )

        sys.exit(1)
