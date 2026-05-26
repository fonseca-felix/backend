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

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    try:
        import sys
        from pathlib import Path
        parent = Path(__file__).resolve().parent.parent
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        import experimento
        GEMINI_API_KEY = getattr(experimento, "CHAVE_API", None)
        if GEMINI_API_KEY:
            print("GEMINI_API_KEY carregada de experimento.py (CHAVE_API).")
    except Exception:
        pass

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada. Adicione sua chave no arquivo .env")

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)


# ─── GERAÇÃO DE TEXTO ────────────────────────────────────────────────────────

def generate_text(tipo: str, tema: str, num_linhas: int, num_paragrafos: int, estilo_extra: str = ""):
    prompt = (
        f"Tipo de texto: {tipo}\n"
        f"Tema: {tema}\n"
        f"Número de linhas aproximado: {num_linhas}\n"
        f"Número de parágrafos: {num_paragrafos}\n"
    )
    if estilo_extra:
        prompt += f"Instruções extras: {estilo_extra}\n"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=get_system_instruction_geracao(tipo),
            response_mime_type="application/json",
            response_schema=TEXTO_SCHEMA,
        )
    )
    return response.text


@app.route("/generate-text", methods=["POST"])
def generate_text_route():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "JSON inválido."}), 400

    tipo = data.get("tipo", "").strip()
    tema = data.get("tema", "").strip()
    num_linhas = data.get("num_linhas", 20)
    num_paragrafos = data.get("num_paragrafos", 4)
    estilo_extra = data.get("estilo_extra", "")

    TIPOS_VALIDOS = ["redação", "poema", "versinho", "cordel", "crônica", "conto"]
    if tipo not in TIPOS_VALIDOS:
        return jsonify({"status": "error", "message": f"Tipo inválido. Use: {', '.join(TIPOS_VALIDOS)}"}), 400

    if not tema:
        return jsonify({"status": "error", "message": "O campo 'tema' é obrigatório."}), 400

    try:
        resultado_str = generate_text(tipo, tema, num_linhas, num_paragrafos, estilo_extra)
        resultado = json.loads(resultado_str)
        return jsonify({"status": "success", "dados": resultado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao gerar texto: {str(e)}"}), 500


# ─── HUMANIZAÇÃO DE TEXTO ─────────────────────────────────────────────────────

HUMANIZACAO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "texto_humanizado": {"type": "STRING", "description": "O texto reescrito com naturalidade e humanidade"},
        "observacoes": {"type": "STRING", "description": "Breves observações sobre as mudanças feitas"},
    },
    "required": ["texto_humanizado", "observacoes"]
}

HUMANIZACAO_INSTRUCTION = """
Você é um especialista em escrita criativa e comunicação humana. 
Sua tarefa é reescrever textos tornando-os mais naturais, fluidos e autênticos, 
eliminando marcas de escrita artificial ou robótica. 
Preserve a essência e o conteúdo original, mas adicione expressividade, 
variações de ritmo, uso de conectivos naturais e tom conversacional quando adequado.
Responda SEMPRE em português e preencha todos os campos do esquema JSON.
"""

@app.route("/humanize", methods=["POST"])
def humanize():
    data = request.get_json()
    if not data or "texto" not in data:
        return jsonify({"status": "error", "message": "Envie o campo 'texto'."}), 400

    texto = data["texto"].strip()
    if len(texto) < 30:
        return jsonify({"status": "error", "message": "Texto muito curto (mínimo 30 caracteres)."}), 400

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Humanize este texto:\n\n{texto}",
            config=types.GenerateContentConfig(
                system_instruction=HUMANIZACAO_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=HUMANIZACAO_SCHEMA,
            )
        )
        resultado = json.loads(response.text)
        return jsonify({"status": "success", "dados": resultado}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao humanizar texto: {str(e)}"}), 500


# ─── CORREÇÃO DE REDAÇÃO ──────────────────────────────────────────────────────

def correct_text(texto: str, banca: str):
    prompt = f"Banca: {banca}\n\nTexto do aluno:\n{texto}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=get_system_instruction_correcao(banca),
            response_mime_type="application/json",
            response_schema=CORRECAO_SCHEMA,
        )
    )
    return response.text


@app.route("/correct", methods=["POST"])
def correct():
    data = request.get_json()
    if not data or "texto" not in data or "banca" not in data:
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
            "POST /generate-text": "Gera textos (redação, poema, cordel, etc.)",
            "POST /humanize": "Humaniza textos artificiais",
            "POST /correct": "Corrige redações por banca de vestibular"
        },
        "version": "1.0"
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
