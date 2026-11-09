
import os
import sys
import json
import re
import logging
import urllib.request
import urllib.parse
import urllib.error

from datetime import datetime
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

FUSO_BR = ZoneInfo("America/Sao_Paulo")

MODELO_GEMINI = "gemini-2.5-flash"

URL_OAUTH = "https://oauth2.googleapis.com/token"

URL_BLOGGER = (
    "https://www.googleapis.com/blogger/v3/blogs/"
)

# Imagens utilizadas sequencialmente
IMAGENS = [
    "https://i.postimg.cc/gj3XR5mV/Gemini-Generated-Image-7atb0f7atb0f7atb.jpg",
    "https://i.postimg.cc/kX9DzT7R/Gemini-Generated-Image-ewbdkeewbdkeewbd.jpg",
    "https://i.postimg.cc/s2tgccnX/imagens-caminao.jpg"
]

# Grupo do Facebook
LINK_GRUPO = (
    "https://www.facebook.com/groups/1162878270485862"
)

# Categorias do Blogger
LABELS = [
    "Guia de Carreira",
    "Motoristas",
    "Caminhoneiros",
    "Grandes Frotas",
    "Vagas de Emprego"
]


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# AUTENTICAÇÃO GOOGLE / BLOGGER
# ============================================================

def obter_access_token(
    client_id,
    client_secret,
    refresh_token
):
    """
    Renova o access token usando o refresh token já existente.
    Não cria novas credenciais nem altera os Secrets.
    """

    dados = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    dados_codificados = urllib.parse.urlencode(
        dados
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        URL_OAUTH,
        data=dados_codificados,
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            requisicao,
            timeout=30
        ) as resposta:

            resultado = json.loads(
                resposta.read().decode("utf-8")
            )

            token = resultado.get("access_token")

            if not token:
                raise RuntimeError(
                    "O Google não retornou um access token."
                )

            logging.info(
                "Token de acesso do Blogger renovado."
            )

            return token

    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode(
            "utf-8",
            errors="replace"
        )

        logging.error(
            "Erro HTTP ao renovar token: %s",
            detalhe
        )

        raise

    except Exception:
        logging.exception(
            "Falha na autenticação do Blogger."
        )
        raise


# ============================================================
# IMAGEM SEQUENCIAL
# ============================================================

def obter_imagem_sequencial():
    """
    Seleciona uma imagem conforme o dia do ano.
    Mantém a rotação das imagens já utilizadas.
    """

    agora = datetime.now(FUSO_BR)

    dia_do_ano = agora.timetuple().tm_yday

    indice = (dia_do_ano - 1) % len(IMAGENS)

    return IMAGENS[indice]


# ============================================================
# EXTRAÇÃO E VALIDAÇÃO DO JSON DO GEMINI
# ============================================================


def extrair_json_resposta(texto):
    """
    Localiza e extrai um objeto JSON mesmo quando o Gemini
    acrescenta texto, Markdown ou explicações antes/depois.

    Valida o título e o HTML antes de permitir a publicação.
    """

    if not texto or not texto.strip():
        raise ValueError(
            "O Gemini retornou uma resposta vazia."
        )

    texto = texto.strip().lstrip("\ufeff")

    # Remove cercas Markdown, se existirem.
    texto = re.sub(
        r"```(?:json)?",
        "",
        texto,
        flags=re.IGNORECASE
    )

    texto = texto.strip()

    decoder = json.JSONDecoder()

    dados_validos = None

    # Procura objetos JSON em qualquer posição do texto.
    for posicao, caractere in enumerate(texto):

        if caractere != "{":
            continue

        try:

            dados, tamanho = decoder.raw_decode(
                texto[posicao:]
            )

            if not isinstance(dados, dict):
                continue

            titulo = dados.get("titulo")
            html = dados.get("html")

            if (
                isinstance(titulo, str)
                and titulo.strip()
                and isinstance(html, str)
                and html.strip()
            ):

                dados_validos = {
                    "titulo": titulo.strip(),
                    "html": html.strip()
                }

                break

        except json.JSONDecodeError:
            continue

    if dados_validos is None:

        logging.error(
            "Resposta recebida do Gemini sem JSON válido. "
            "Início da resposta: %r",
            texto[:1200]
        )

        raise ValueError(
            "Não foi encontrado um objeto JSON válido "
            "na resposta do Gemini."
        )

    # Evita publicar um resumo muito curto.
    if len(dados_validos["html"]) < 1500:

        raise ValueError(
            "O artigo gerado está muito curto: "
            f"{len(dados_validos['html'])} caracteres."
        )

    return dados_validos



# ============================================================
# GERAÇÃO DE CONTEÚDO COM GEMINI
# ============================================================

def gerar_conteudo_com_gemini(api_key):

    logging.info(
        "Iniciando pesquisa e geração do artigo."
    )

    segmentos = [
        "Agronegócio e transporte de grãos: "
        "bitrem, rodotrem, caçamba e graneleiro",

        "Carga geral e e-commerce: "
        "baú, sider, truck e carreta",

        "Produtos perigosos e transporte em tanque: "
        "combustíveis, cargas químicas e exigência de MOPP",

        "Distribuição urbana e carga leve: "
        "toco, VUC e operações regionais",

        "Cargas pesadas e excedentes: "
        "prancha, transporte especial e equipamentos pesados"
    ]

    import random

    segmento = random.choice(segmentos)

    agora = datetime.now(FUSO_BR)

    data_formatada = agora.strftime(
        "%d/%m/%Y"
    )

    prompt = f"""
Você é um jornalista especializado em transporte rodoviário,
logística, mercado de trabalho e recrutamento de motoristas
profissionais no Brasil.

Sua missão é produzir uma reportagem completa, original,
informativa e profissional para o portal CaminhoneiroPro.

DATA DE REFERÊNCIA: {data_formatada}

SEGMENTO DESTA EDIÇÃO:
{segmento}

============================================================
1. PESQUISA E APURAÇÃO
============================================================

Utilize a pesquisa do Google para procurar informações
atuais e relevantes sobre oportunidades de trabalho para
motoristas profissionais no Brasil.

Dê preferência a:

- Páginas oficiais de recrutamento das transportadoras.
- Sites oficiais das empresas.
- Páginas oficiais de carreiras.
- Comunicados institucionais.
- Canais oficiais de recrutamento.
- Informações publicadas recentemente.

Procure identificar empresas reais relacionadas ao segmento
selecionado.

Não invente empresas, vagas, cidades, salários, benefícios,
datas, telefones, e-mails ou links.

Não transforme uma notícia antiga em uma vaga atual.

Não afirme que uma empresa está contratando quando não
existir confirmação suficiente.

============================================================
2. CLASSIFICAÇÃO DAS OPORTUNIDADES
============================================================

Diferencie claramente:

VAGA CONFIRMADA:
Quando houver anúncio ou página de recrutamento que
comprove a oportunidade.

PROCESSO SELETIVO OU BANCO DE TALENTOS:
Quando a empresa estiver recebendo currículos, mas não
houver confirmação de uma vaga específica.

OPORTUNIDADE NÃO CONFIRMADA:
Quando houver apenas indícios ou informações insuficientes.

Não apresente oportunidades não confirmadas como vagas
abertas.

Se não encontrar vagas atuais comprovadas, produza uma
reportagem útil sobre o mercado de trabalho do segmento,
explicando que não foi possível confirmar oportunidades
específicas na pesquisa realizada.

============================================================
3. INFORMAÇÕES SOBRE AS VAGAS
============================================================

Quando disponíveis nas fontes, apresente:

- Nome da empresa.
- Cargo ou função.
- Cidade e estado.
- Tipo de veículo ou operação.
- Requisitos de CNH.
- Necessidade de EAR.
- Necessidade de MOPP.
- Experiência exigida.
- Benefícios anunciados.
- Salário, somente quando divulgado.
- Forma de candidatura.
- Link oficial para inscrição ou recrutamento.

Não complete informações ausentes com suposições.

Não invente requisitos para tornar a vaga mais atraente.

============================================================
4. TAMANHO E PROFUNDIDADE DO ARTIGO
============================================================

O artigo NÃO deve ser um resumo curto.

Produza uma reportagem completa, preferencialmente entre
1.000 e 1.500 palavras, quando houver informações
suficientes para isso.

Não aumente o texto artificialmente com repetições.

O conteúdo precisa ter profundidade, contexto e utilidade
real para o motorista profissional.

Desenvolva os assuntos em parágrafos completos.

Explique os detalhes importantes em vez de apenas listar
informações.

============================================================
5. ESTRUTURA EDITORIAL OBRIGATÓRIA
============================================================

Organize o artigo com a seguinte estrutura:

1. Introdução jornalística:
Apresente o assunto, o segmento e sua importância para
os profissionais do transporte rodoviário.

2. Panorama do mercado:
Explique o cenário do segmento, a demanda por profissionais
e as características das operações.

3. Empresas e oportunidades:
Apresente as empresas pesquisadas e as oportunidades
que puderam ser verificadas.

4. Detalhes das oportunidades:
Explique funções, requisitos, veículos, localização e
benefícios, respeitando exclusivamente os dados encontrados.

5. Como se candidatar:
Oriente o motorista sobre como acessar os canais oficiais
e realizar a candidatura.

6. Documentação e preparação:
Explique os cuidados com CNH, EAR, MOPP, currículo e
experiência profissional, conforme a função.

7. Orientações importantes:
Inclua cuidados contra golpes de falsas vagas e cobranças
indevidas por processos seletivos.

8. Conclusão:
Finalize com uma análise útil para o profissional e uma
orientação prática.

9. Fontes consultadas:
Apresente os links das fontes oficiais efetivamente
utilizadas na apuração.

============================================================
6. ORIGINALIDADE E QUALIDADE
============================================================

O texto deve ser original.

Não copie notícias, anúncios ou textos de outros sites.

Não faça simples substituição de palavras de uma notícia.

Utilize as informações apuradas para construir uma nova
reportagem, com organização, explicações e abordagem
próprias.

Evite frases genéricas, introduções repetitivas e conteúdo
que não acrescente informação.

Escreva em português brasileiro natural, com linguagem
jornalística profissional, clara e acessível.

O público principal são caminhoneiros e motoristas
profissionais que procuram oportunidades de trabalho.

============================================================
7. SEO
============================================================

Crie um título atrativo, específico e informativo.

Utilize naturalmente expressões relacionadas ao assunto,
como:

- vagas para motoristas;
- vagas para caminhoneiros;
- motorista carreteiro;
- motorista truck;
- oportunidades no transporte;
- empresas de transporte;
- contratação de motoristas.

Não faça excesso de palavras-chave.

Utilize subtítulos claros e parágrafos bem organizados.

============================================================
8. HTML PARA BLOGGER
============================================================

O campo html deve conter o artigo completo em HTML.

Utilize somente elementos compatíveis com o Blogger:

<h2>
<h3>
<p>
<ul>
<li>
<strong>
<a>

Não inclua:
- Markdown.
- Blocos de código.
- Scripts.
- CSS externo.
- Comentários sobre o processo de geração.
- JSON dentro do HTML.

Os links devem ser clicáveis e direcionar para páginas
reais encontradas durante a pesquisa.

Não invente URLs.

============================================================
9. FONTES E TRANSPARÊNCIA
============================================================

Ao final do artigo, crie uma seção:

<h2>Fontes e canais oficiais</h2>

Inclua os links das páginas consultadas que sustentam
as informações publicadas.

Não crie fontes fictícias.

Não apresente como fonte uma página que não foi consultada.

Se não houver fonte oficial suficiente para confirmar
uma vaga, deixe isso claro no texto.

============================================================
10. FORMATO DE SAÍDA
============================================================

Retorne exclusivamente um JSON válido, sem explicações
antes ou depois.

O JSON deve possuir exatamente duas propriedades:

{{
  "titulo": "Título completo da reportagem",
  "html": "<h2>...</h2><p>...</p>"
}}

Não escreva nada fora do JSON.
"""

    try:

        # A pesquisa do Google utilizada como ferramenta
        # requer a versão v1beta neste fluxo.
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                api_version="v1beta"
            )
        )

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

        if not texto_resposta:
            raise ValueError(
                "O Gemini não retornou texto."
            )

        artigo = extrair_json_resposta(
            texto_resposta
        )

        logging.info(
            "Artigo gerado e validado com sucesso."
        )

        logging.info(
            "Título: %s",
            artigo["titulo"]
        )

        logging.info(
            "Tamanho do HTML: %s caracteres",
            len(artigo["html"])
        )

        return artigo["titulo"], artigo["html"]

    
    except Exception as erro:

        logging.exception(
            "Erro ao gerar ou interpretar conteúdo com Gemini: %s",
            erro
        )

        # Registra uma amostra da resposta para facilitar
        # o diagnóstico de problemas futuros.
        try:

            if "response" in locals():

                texto_diagnostico = response.text or ""

                logging.error(
                    "Resposta recebida do Gemini (até 1500 caracteres): %s",
                    texto_diagnostico[:1500]
                )

        except Exception:
            logging.error(
                "Não foi possível recuperar a resposta para diagnóstico."
            )

        return None, None



# ============================================================
# PUBLICAÇÃO NO BLOGGER
# ============================================================

def postar_no_blogger(
    blog_id,
    access_token,
    titulo,
    html
):

    logging.info(
        "Preparando publicação no Blogger."
    )

    agora = datetime.now(FUSO_BR)

    data_formatada = agora.strftime(
        "%d/%m/%Y"
    )

    imagem = obter_imagem_sequencial()

    # Estrutura visual do artigo
    conteudo_final = f"""
<div style="font-family: Arial, sans-serif;
            font-size: 16px;
            line-height: 1.7;
            color: #333;">

    <div style="margin-bottom: 20px;">
        <img src="{imagem}"
             alt="Transporte rodoviário e oportunidades para motoristas"
             style="width:100%;
                    height:auto;
                    border-radius:8px;">
    </div>

    <p style="font-size:13px;color:#777;">
        Atualizado em {data_formatada}
    </p>

    {html}

    <hr>

    <div style="background:#f2f5f7;
                padding:18px;
                border-radius:8px;
                margin-top:25px;">

        <h3>Continue acompanhando o CaminhoneiroPro</h3>

        <p>
            Acompanhe informações sobre vagas para motoristas,
            oportunidades no transporte rodoviário, empresas
            de logística e orientações para sua carreira.
        </p>

        <p>
            Participe também da nossa comunidade de motoristas:
        </p>

        <p>
            <a href="{LINK_GRUPO}"
               target="_blank"
               rel="noopener noreferrer">
               Acessar grupo CaminhoneiroPro no Facebook
            </a>
        </p>

    </div>

</div>
"""

    url = (
        URL_BLOGGER
        + urllib.parse.quote(str(blog_id))
        + "/posts/"
    )

    dados_postagem = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo_final,
        "labels": LABELS,
        "published": agora.isoformat()
    }

    dados_json = json.dumps(
        dados_postagem,
        ensure_ascii=False
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados_json,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=60
        ) as resposta:

            resultado = json.loads(
                resposta.read().decode("utf-8")
            )

            link_publicacao = resultado.get(
                "url",
                ""
            )

            logging.info(
                "Publicação realizada com sucesso."
            )

            logging.info(
                "URL: %s",
                link_publicacao
            )

            return resultado

    except urllib.error.HTTPError as erro:

        detalhe = erro.read().decode(
            "utf-8",
            errors="replace"
        )

        logging.error(
            "Erro HTTP ao publicar no Blogger: %s",
            detalhe
        )

        raise

    except Exception:

        logging.exception(
            "Falha durante a publicação no Blogger."
        )

        raise


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    logging.info(
        "============================================"
    )

    logging.info(
        "INICIANDO CAMINHONEIROPRO"
    )

    logging.info(
        "============================================"
    )

    # Secrets já utilizados pelo projeto.
    blog_id = os.getenv("BLOG_ID")

    google_api_key = os.getenv("GOOGLE_API_KEY")

    blogger_client_id = os.getenv(
        "BLOGGER_CLIENT_ID"
    )

    blogger_client_secret = os.getenv(
        "BLOGGER_CLIENT_SECRET"
    )

    blogger_refresh_token = os.getenv(
        "BLOGGER_REFRESH_TOKEN"
    )

    # Verificação dos Secrets obrigatórios.
    secrets = {
        "BLOG_ID": blog_id,
        "GOOGLE_API_KEY": google_api_key,
        "BLOGGER_CLIENT_ID": blogger_client_id,
        "BLOGGER_CLIENT_SECRET": blogger_client_secret,
        "BLOGGER_REFRESH_TOKEN": blogger_refresh_token
    }

    ausentes = [
        nome
        for nome, valor in secrets.items()
        if not valor
    ]

    if ausentes:

        logging.error(
            "Secrets ausentes: %s",
            ", ".join(ausentes)
        )

        sys.exit(1)

    # 1. Gerar o conteúdo.
    titulo, html = gerar_conteudo_com_gemini(
        google_api_key
    )

    if not titulo or not html:

        logging.error(
            "A geração do conteúdo falhou. "
            "Publicação cancelada para evitar "
            "informações não verificadas."
        )

        sys.exit(1)

    # 2. Renovar o token do Blogger.
    try:

        access_token = obter_access_token(
            blogger_client_id,
            blogger_client_secret,
            blogger_refresh_token
        )

    except Exception:

        logging.error(
            "Não foi possível autenticar no Blogger."
        )

        sys.exit(1)

    # 3. Publicar o artigo.
    try:

        resultado = postar_no_blogger(
            blog_id,
            access_token,
            titulo,
            html
        )

        if resultado:

            logging.info(
                "PROCESSO FINALIZADO COM SUCESSO."
            )

    except Exception:

        logging.error(
            "Não foi possível concluir a publicação."
        )

        sys.exit(1)


# ============================================================
# INÍCIO
# ============================================================

if __name__ == "__main__":
    main()
