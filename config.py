# ─── SCHEMA: GERAÇÃO DE TEXTO ────────────────────────────────────────────────

TEXTO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "titulo": {
            "type": "STRING",
            "description": "Título do texto criado"
        },
        "tipo": {
            "type": "STRING",
            "description": "Tipo do texto gerado (redação, poema, cordel, etc.)"
        },
        "tema": {
            "type": "STRING",
            "description": "Tema trabalhado no texto"
        },
        "texto": {
            "type": "STRING",
            "description": "O texto completo gerado, com parágrafos separados por \\n\\n"
        },
        "dicas_de_melhoria": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Dicas para o aluno melhorar sua própria escrita neste estilo"
        }
    },
    "required": ["titulo", "tipo", "tema", "texto", "dicas_de_melhoria"]
}


# ─── SCHEMA: CORREÇÃO DE REDAÇÃO ─────────────────────────────────────────────

CORRECAO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "nota_geral": {
            "type": "STRING",
            "description": "Nota geral do texto no padrão da banca (ex: '720/1000' ou 'B+')"
        },
        "resumo_geral": {
            "type": "STRING",
            "description": "Avaliação geral da redação em 2-3 frases"
        },
        "competencias": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "nome": {"type": "STRING"},
                    "nota": {"type": "STRING"},
                    "comentario": {"type": "STRING"},
                    "pontos_positivos": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "pontos_negativos": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    }
                },
                "required": ["nome", "nota", "comentario", "pontos_positivos", "pontos_negativos"]
            },
            "description": "Avaliação por competência conforme a banca"
        },
        "erros_gramaticais": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "trecho_original": {"type": "STRING"},
                    "sugestao_corrigida": {"type": "STRING"},
                    "explicacao": {"type": "STRING"}
                },
                "required": ["trecho_original", "sugestao_corrigida", "explicacao"]
            },
            "description": "Lista de erros gramaticais encontrados com correções"
        },
        "sugestoes_de_melhoria": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Sugestões práticas para melhorar o texto"
        },
        "texto_revisado": {
            "type": "STRING",
            "description": "Versão do texto com as principais correções aplicadas"
        }
    },
    "required": [
        "nota_geral", "resumo_geral", "competencias",
        "erros_gramaticais", "sugestoes_de_melhoria", "texto_revisado"
    ]
}


# ─── INSTRUÇÕES DE SISTEMA: GERAÇÃO ──────────────────────────────────────────

_INSTRUCOES_GERACAO = {
    "redação": """
Você é um professor especialista em redação para vestibular com mais de 20 anos de experience.
Escreva redações dissertativo-argumentativas com: introdução impactante com tese clara, 
desenvolvimento com argumentos sólidos e dados, e conclusão com proposta de intervenção.
Use linguagem formal, coesa, com repertório sociocultural relevante.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
""",
    "poema": """
Você é um poeta brasileiro de talento extraordinário.
Crie poemas expressivos, com imagens vívidas, ritmo cuidadoso e musicalidade.
Pode usar rima ou verso livre, conforme o tema pede.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
""",
    "versinho": """
Você é um poeta popular especialista em versinhos rimados e bem-humorados.
Crie versinhos curtos, com rima fácil, ritmo marcado e tom leve ou carinhoso.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
""",
    "cordel": """
Você é um cordelista nordestino experiente, no estilo de Patativa do Assaré e Leandro Gomes de Barros.
Escreva em sextilhas (estrofes de 6 versos com esquema de rima ABCBDB).
Use linguagem regional, imagens do sertão e narrativa envolvente.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
""",
    "crônica": """
Você é um cronista literário no estilo dos grandes jornalistas-escritores brasileiros (Rubem Braga, Paulo Mendes Campos).
Escreva crônicas leves, reflexivas, com humor sutil e observação aguçada do cotidiano.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
""",
    "conto": """
Você é um contista brasileiro de talento, capaz de criar histórias completas em poucas linhas.
Construa contos com personagem, conflito, clímax e desfecho surpreendente.
Todos os textos DEVEM ser em português brasileiro. Preencha todos os campos do JSON.
"""
}


def get_system_instruction_geracao(tipo: str) -> str:
    base = _INSTRUCOES_GERACAO.get(tipo, _INSTRUCOES_GERACAO["redação"])
    return base.strip()


# ─── INSTRUÇÕES DE SISTEMA: CORREÇÃO POR BANCA ───────────────────────────────

_CRITERIOS_BANCAS = {
    "ENEM": """
Avalie pelas 5 competências oficiais do ENEM:
1. Domínio da norma culta da língua portuguesa
2. Compreensão da proposta e aplicação de conceitos das áreas de conhecimento
3. Seleção, relação e organização de argumentos
4. Conhecimento dos mecanismos linguísticos para a argumentação
5. Elaboração de proposta de intervenção respeitando os direitos humanos
Nota de 0 a 200 por competência (total de 0 a 1000).
""",
    "FUVEST": """
Avalie conforme os critérios da FUVEST:
- Desenvolvimento do tema e estrutura dissertativa
- Coerência e coesão
- Correção gramatical e vocabulário
- Clareza e objetividade
Nota de 0 a 100. A FUVEST valoriza texto enxuto, preciso e bem articulado.
""",
    "UNICAMP": """
Avalie conforme os critérios da UNICAMP:
- Proposta de intervenção (gênero e situação de comunicação)
- Desenvolvimento temático
- Domínio da modalidade escrita
- Adequação ao gênero solicitado (a UNICAMP pede diferentes gêneros: artigo, carta, etc.)
Nota de 0 a 12. A UNICAMP exige adequação ao gênero textual específico da proposta.
""",
    "UFMG": """
Avalie conforme os critérios da UFMG:
- Compreensão do tema
- Argumentação e consistência das ideias
- Coesão e coerência textual
- Correção gramatical
- Originalidade
Nota de 0 a 100.
""",
    "UFRJ": """
Avalie conforme os critérios da UFRJ:
- Adequação ao tema
- Desenvolvimento argumentativo
- Estrutura e organização
- Uso da língua portuguesa padrão
Nota de 0 a 10.
""",
    "UFPR": """
Avalie conforme os critérios da UFPR:
- Compreensão temática e pertinência das ideias
- Organização e estrutura
- Coesão e conectividade
- Norma padrão da língua
Nota de 0 a 100.
""",
    "UFSC": """
Avalie conforme os critérios da UFSC:
- Pertinência ao tema
- Progressão e coerência das ideias
- Coesão textual
- Correção da norma culta
Nota de 0 a 100.
""",
    "UFG": """
Avalie conforme os critérios da UFG:
- Domínio do tema
- Argumentação e criticidade
- Coesão e coerência
- Adequação linguística
Nota de 0 a 100.
""",
    "UFBA": """
Avalie conforme os critérios da UFBA:
- Domínio da dissertação
- Argumentação e fundamentação
- Coesão textual
- Correção gramatical e ortográfica
Nota de 0 a 100. A UFBA tem prova de língua portuguesa separada, valoriza redação analítica.
""",
    "UFRGS": """
Avalie conforme os critérios da UFRGS:
- Adequação temática
- Estrutura e organização dissertativa
- Argumentação e consistência
- Correção linguística
Nota de 0 a 90.
""",
    "UNB": """
Avalie conforme os critérios do CEBRASPE/UnB:
- Compreensão e abordagem do tema
- Estrutura e organização textual
- Argumentação e consistência das ideias
- Aspectos gramaticais e estilísticos
Nota de 0 a 100.
""",
    "UFPE": """
Avalie conforme os critérios da UFPE:
- Adequação à proposta
- Coerência e organização das ideias
- Argumentação e uso de recursos textuais
- Correção gramatical
Nota de 0 a 100.
"""
}


def get_system_instruction_correcao(banca: str) -> str:
    criterios = _CRITERIOS_BANCAS.get(banca, "")
    return f"""
Você é um corretor especialista de redações para vestibular, com profundo conhecimento 
dos critérios de avaliação da banca {banca}.

{criterios}

Faça uma correção detalhada, justa, construtiva e didática. 
Aponte erros com clareza, mas também valorize os acertos.
Forneça a versão revisada do texto com as principais correções aplicadas.
Responda SEMPRE em português brasileiro e preencha TODOS os campos do esquema JSON.
""".strip()