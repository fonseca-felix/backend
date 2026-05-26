import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types
from google.genai import errors  # Importado para capturar erros específicos da API Google
from dotenv import load_dotenv

from config import (
    TEXTO_SCHEMA,
    CORRECAO_SCHEMA,
    get_system_instruction_geracao,
    get_system_instruction_correcao,
)

# Carrega as variáveis do arquivo .env local
load_dotenv()
DEFAULT_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
CORS(app)


# ─── FUNÇÃO AUXILIAR PARA OBTER O CLIENTE DO GEMINI ─────────────────────────

def get_gemini_client():
    """
    Verifica se o utilizador enviou uma chave própria no cabeçalho Authorization.
    Caso contrário, tenta utilizar a chave padrão definida no arquivo .env.
    """
    auth_header = request.headers.get("Authorization", "")
    
    # Se vier no formato "Bearer CHAVE", extrai apenas o token
    if auth_header.startswith("Bearer "):
        user_key = auth_header.split(" ")[1].strip()
    else:
        user_key = auth_header.strip()

    # Determina qual chave utilizar (Prioridade absoluta para a do utilizador)
    api_key = user_key if user_key else DEFAULT_GEMINI_API_KEY

    if not api_key:
        raise ValueError("Nenhuma chave de API do Gemini foi configurada no servidor e nem fornecida por si.")

    return genai.Client(api_key=api_key)


# ─── FUNÇÃO PARA TRATAR ERROS DA API GOOGLE ──────────────────────────────────

def handle_gemini_error(e):
    """
    Analisa o erro retornado pelo SDK da Google e gera uma mensagem limpa
    e compreensível para o utilizador final.
    """
    err_msg = str(e)
    
    if "leaked" in err_msg.lower():
        return "A sua chave de API pessoal foi bloqueada pela Google por motivos de segurança (vazamento de credenciais). Por favor, gere uma nova chave no Google AI Studio.", 403
    elif "api key not valid" in err_msg.lower() or "invalid" in err_msg.lower():
        return "A chave de API informada é inválida. Verifique se a copiou corretamente.", 401
    elif "quota" in err_msg.lower() or "limit" in err_msg.lower():
        return "O limite de requisições da sua chave de API foi atingido. Tente novamente mais tarde.", 429
    
    return f"Erro na comunicação com a inteligência artificial: {err_msg}", 500


# ─── GERAÇÃO DE TEXTO ────────────────────────────────────────────────────────

def generate_text(client, tipo: str, tema: str, num_linhas: int, num_paragrafos: int, estilo_extra: str = ""):
    prompt = (
        f"Tipo de texto: {tipo}\n"
        f"Tema: {tema}\n"
        f"Número aproximado de linhas: {num_linhas}\n"
        f"Número aproximado de parágrafos: {num_paragrafos}\n"
    )
    if estilo_extra:
        prompt += f"Instruções e estilo extra do usuário: {estilo_extra}\n"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=get_system_instruction_geracao(tipo),
            response_mime_type="application/json",
            response_schema=TEXTO_SCHEMA,
            temperature=0.7,
        ),
    )
    return response.text


# ─── HUMANIZAÇÃO DE TEXTO ────────────────────────────────────────────────────

def humanize_text(client, texto: str) -> str:
    prompt = f"Por favor, reescreva de forma natural e humana o seguinte texto:\n\n{texto}"
    
    instruction = (
        "Você é um redator humano genial, especialista em fluidez, ritmo e naturalidade textual. "
        "Sua tarefa é receber um texto (geralmente gerado por IA ou duro/artificial) e reescrevê-lo eliminando "
        "repetições viciosas, clichês de IA (como 'em suma', 'ademais', 'no cenário atual'), ajustando o tamanho das sentenças "
        "e adicionando marcas sutis de organicidade humana. "
        "Retorne APENAS o texto modificado final, sem introduções ou explicações."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.8,
        ),
    )
    return response.text


# ─── CORREÇÃO DE REDAÇÃO ─────────────────────────────────────────────────────

def correct_text(client, texto: str, banca: str) -> str:
    prompt = f"Aqui está a minha redação para você corrigir conforme os critérios da banca {banca}:\n\n{texto}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=get_system_instruction_correcao(banca),
            response_mime_type="application/json",
            response_schema=CORRECAO_SCHEMA,
            temperature=0.3,
        ),
    )
    return response.text


# ─── ROTAS DA API (FLASK) ────────────────────────────────────────────────────

@app.route("/generate-text", methods=["POST"])
def api_generate_text():
    data = request.get_json() or {}
    tipo = data.get("tipo", "").strip()
    tema = data.get("tema", "").strip()
    
    if not tipo or not tema:
        return jsonify({"status": "error", "message": "Envie 'tipo' e 'tema' obrigatoriamente."}), 400

    try:
        num_linhas = int(data.get("num_linhas", 30))
        num_paragrafos = int(data.get("num_paragrafos", 4))
    except ValueError:
        return jsonify({"status": "error", "message": "As linhas e parágrafos devem ser números inteiros."}), 400

    estilo_extra = data.get("estilo_extra", "").strip()

    try:
        client = get_gemini_client()
        resultado_str = generate_text(client, tipo, tema, num_linhas, num_paragrafos, estilo_extra)
        resultado = json.loads(resultado_str)
        return jsonify({"status": "success", "dados": resultado}), 200
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except errors.APIError as api_err:
        msg, code = handle_gemini_error(api_err)
        return jsonify({"status": "error", "message": msg}), code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro interno no servidor: {str(e)}"}), 500


@app.route("/humanize", methods=["POST"])
def api_humanize():
    data = request.get_json() or {}
    texto = data.get("texto", "").strip()

    if not texto:
        return jsonify({"status": "error", "message": "Envie o 'texto' que deseja humanizar."}), 400

    try:
        client = get_gemini_client()
        texto_humanizado = humanize_text(client, texto)
        return jsonify({
            "status": "success",
            "dados": {
                "texto_humanizado": texto_humanizado,
                "observacoes": "Texto reestruturado para eliminar cadências robóticas, melhorando a escolha lexical e o ritmo das transições."
            }
        }), 200
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except errors.APIError as api_err:
        msg, code = handle_gemini_error(api_err)
        return jsonify({"status": "error", "message": msg}), code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro interno ao humanizar: {str(e)}"}), 500


@app.route("/correct", methods=["POST"])
def api_correct():
    data = request.get_json() or {}
    if "texto" not in data or "banca" not in data:
        return jsonify({"status": "error", "message": "Envie 'texto' e 'banca'."}), 400

    texto = data["texto"].strip()
    banca = data["banca"].strip()

    BANCAS_VALIDAS = [
        "ENEM", "FUVEST", "UNICAMP", "UFMG", "UFRJ", "UFPR",
        "UFSC", "UFG", "UFBA", "UFRGS", "UNB", "UFPE"
    ]

    if banca not in BANCAS_VALIDAS:
        return jsonify({
            "status": "error",
            "message": f"Banca inválida. Disponíveis: {', '.join(BANCAS_VALIDAS)}"
        }), 400

    if len(texto) < 100:
        return jsonify({"status": "error", "message": "Texto demasiado curto para correção (mínimo 100 caracteres)."}), 400

    try:
        client = get_gemini_client()
        resultado_str = correct_text(client, texto, banca)
        resultado = json.loads(resultado_str)
        return jsonify({"status": "success", "banca": banca, "dados": resultado}), 200
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except errors.APIError as api_err:
        msg, code = handle_gemini_error(api_err)
        return jsonify({"status": "error", "message": msg}), code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro interno ao corrigir: {str(e)}"}), 500


@app.route("/")
def root():
    return jsonify({
        "status": "success",
        "message": "API TextMaster com Gemini AI — a funcionar!",
        "rotas": {
            "POST /generate-text": "Gera textos estruturados",
            "POST /humanize": "Modifica o ritmo de textos artificiais",
            "POST /correct": "Corrige redações com base em bancas de vestibulares"
        }
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)