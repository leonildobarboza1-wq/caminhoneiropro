import os
import random
import time
import requests
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_ID = os.environ.get("BLOG_ID")
B_CLIENT_ID = os.environ.get("B_CLIENT_ID")
B_CLIENT_SECRET = os.environ.get("B_CLIENT_SECRET")
B_REFRESH_TOKEN = os.environ.get("B_REFRESH_TOKEN")

client = genai.Client(api_key=GEMINI_API_KEY)

CATEGORIAS = ['Vagas e Carreiras', 'Notícias do Setor', 'Vida na Estrada', 'Legislação e Treinamento']
TAGS_IMAGEM = ['Professional Truck Driver Career Development', 'Global Logistics Industry Trends', 'Trucker Life Scenic Highway', 'Commercial Truck Driver Training Classroom']

def obter_imagem_hd(index):
    rand_seed = random.randint(100, 9999)
    return f"https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=85&sig={rand_seed}"

def obter_novo_access_token():
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": B_CLIENT_ID,
        "client_secret": B_CLIENT_SECRET,
        "refresh_token": B_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def gerar_artigo():
    cat_escolhida = random.choice(CATEGORIAS)
    idx = CATEGORIAS.index(cat_escolhida)

    prompt = f"""
    Você é um jornalista e editor visual sênior para o portal 'CaminhoneiroPro'.
    Escreva um artigo rico, cativante e altamente informativo sobre '{cat_escolhida}'.

    ESTRUTURA OBRIGATÓRIA (HTML):
    [TITULO] Título impressionante e otimizado para SEO [/TITULO]
    [CONTEUDO]
    <p class="lead"><b>Introdução envolvente destacando o valor visual e a importância do tema...</b></p>
    <h3>Destaques e Análise Técnica</h3>
    <p>Explicação aprofundada com detalhes visuais e contextuais...</p>
    <h3>Conclusão e Tendências</h3>
    <p>Considerações finais para os leitores...</p>
    <br><hr>
    <p><small><i><b>Disclaimer:</b> Conteúdo informativo e educacional.</i></small></p>
    [/CONTEUDO]
    """

    for tentativa in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            texto = response.text
            
            titulo = texto.split("[TITULO]")[1].split("[/TITULO]")[0].strip()
            conteudo = texto.split("[CONTEUDO]")[1].split("[/CONTEUDO]")[0].strip()

            imagem_url = obter_imagem_hd(idx)
            html_final = f'<div class="article-hero"><img src="{imagem_url}" alt="{titulo}" style="width:100%; max-height:500px; object-fit:cover; border-radius:12px; margin-bottom:20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);"/></div>\n' + conteudo

            return titulo, html_final, cat_escolhida
        except Exception as e:
            print(f"⚠️ Servidor ocupado (Tentativa {tentativa+1}/3). A tentar novamente em 10 segundos...")
            time.sleep(10)
    
    raise Exception("Falha ao gerar artigo após 3 tentativas devido à alta demanda do modelo.")

def publicar():
    access_token = obter_novo_access_token()
    if not access_token: return

    titulo, conteudo, etiqueta = gerar_artigo()
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"kind": "blogger#post", "title": titulo, "content": conteudo, "labels": [etiqueta, "CaminhoneiroPro"]}

    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"✅ Publicado com sucesso: [{etiqueta}] {titulo}")
    else:
        print(f"❌ Erro ao publicar: {res.text}")

if __name__ == "__main__":
    publicar()
