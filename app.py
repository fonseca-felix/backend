import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

from config import (
    TEXTO_SCHEMA,
    CORRECAO_SCHEMA,
    get_system_instruction_geracao,
    get_system_instruction_correcao,
)

# Carrega as variáveis do arquivo .env local
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fallback: Tenta buscar a chave no arquivo experimento.py se ela não estiver no ambiente
if not GEMINI_API_KEY:
    try:
        import experimento
        GEMINI_API_KEY = getattr(experimento, "CHAVE_API", None)
        if GEMINI_API_KEY:
            print("GEMINI_API_KEY carregada de experimento.py (CHAVE_API).")
    except (ImportError, AttributeError, Exception):
        # Silencia qualquer erro de importação para não quebrar o ambiente de produção
        pass

# Validação final obrigatória da Chave de API
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY não encontrada. Adicione sua chave no arquivo .env ou no painel da Vercel."
    )

# Inicializa o cliente do Gemini usando o SDK correto
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)


# ─── GERAÇÃO DE TEXTO ────────────────────────────────────────────────────────

def generate_text(tipo: str, tema: str, num_linhas: int, num_paragrafos: int, estilo_extra: str = ""):
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
            system_instruction=get_system_instruction_geracao(),
            response_mime_type="application/json",
            response_schema=TEXTO_SCHEMA,
            temperature=0.7,
        ),
    )
    return response.text


# ─── HUMANIZAÇÃO DE TEXTO ────────────────────────────────────────────────────

def humanize_text(texto: str) -> str:
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

def correct_text(texto: str, banca: str) -> str:
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
        resultado_str = generate_text(tipo, tema, num_linhas, num_paragrafos, estilo_extra)
        resultado = json.loads(resultado_str)
        return jsonify({"status": "success", "dados": resultado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro na geração de conteúdo: {str(e)}"}), 500


@app.route("/humanize", methods=["POST"])
def api_humanize():
    data = request.get_json() or {}
    texto = data.get("texto", "").strip()

    if not texto:
        return jsonify({"status": "error", "message": "Envie o 'texto' que deseja humanizar."}), 400

    try:
        texto_humanizado = humanize_text(texto)
        return jsonify({"status": "success", "texto_humanizado": texto_humanizado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao humanizar texto: {str(e)}"}), 500


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
        return jsonify({"status": "error", "message": "Texto muito curto para correção (mínimo 100 caracteres)."}), 400

    try:
        resultado_str = correct_text(texto, banca)
        resultado = json.loads(resultado_str)
        return jsonify({"status": "success", "banca": banca, "dados": resultado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao corrigir texto: {str(e)}"}), 500


# ─── ROTA RAIZ ────────────────────────────────────────────────────────────────

@app.route("/")
def root():
    return jsonify({
        "status": "success",
        "message": "API TextMaster com Gemini AI — funcionando!",
        "rotas": {
            "POST /generate-text": "Gera textos estruturados",
            "POST /humanize": "Modifica o ritmo de textos artificiais",
            "POST /correct": "Corrige redações com base em bancas de vestibulares"
        }
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)