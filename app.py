import streamlit as st
import anthropic
import fitz
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Validador BS e GTA — LAR", page_icon="🐔", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.lar-header {
    background: linear-gradient(135deg, #003d1a 0%, #006629 50%, #003d1a 100%);
    border-radius: 20px;
    padding: 1.5rem 2rem 1rem 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
    border: 3px solid #FFDF00;
}
.lar-logo {
    font-family: 'Bebas Neue', cursive;
    font-size: 6rem;
    color: #FFDF00;
    letter-spacing: 0.3em;
    line-height: 1;
    text-shadow: 4px 4px 0px #003d1a, 6px 6px 0px rgba(0,0,0,0.3);
    margin: 0;
}
.lar-sub {
    color: #fff;
    font-size: 0.85rem;
    letter-spacing: 0.2em;
    margin-top: -0.3rem;
    margin-bottom: 0.5rem;
    opacity: 0.85;
}
.campo-frangos {
    position: relative;
    width: 100%;
    height: 190px;
    margin: 0.5rem 0;
}
.frango-abs {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
}
.frango-abs:hover .frango-svg {
    animation: acenar 0.5s ease-in-out infinite alternate;
}
@keyframes acenar {
    0%   { transform: rotate(-14deg) translateY(-5px); }
    100% { transform: rotate(14deg) translateY(-5px); }
}
@keyframes chute {
    0%   { transform: rotate(0deg) translateY(0px); }
    20%  { transform: rotate(-25deg) translateY(-10px); }
    45%  { transform: rotate(30deg) translateY(-18px); }
    70%  { transform: rotate(-12deg) translateY(-8px); }
    100% { transform: rotate(0deg) translateY(0px); }
}
@keyframes bola-voo {
    0%   { transform: translateX(0) translateY(0) rotate(0deg); opacity:1; }
    100% { transform: translateX(90px) translateY(-90px) rotate(540deg); opacity:0; }
}
.chutando .frango-svg { animation: chute 0.9s ease-in-out 3; }
.chutando .bola-svg  { animation: bola-voo 0.9s ease-in-out 3 forwards; }

.stButton > button {
    background: linear-gradient(135deg, #009c3b, #006629) !important;
    color: #FFDF00 !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
    border: 2px solid #FFDF00 !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    letter-spacing: 0.05em !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #FFDF00, #ffc800) !important;
    color: #003d1a !important;
}
.tudo-ok {
    background: linear-gradient(135deg, #003d1a, #006629);
    border: 3px solid #FFDF00;
    border-radius: 16px;
    padding: 3rem;
    text-align: center;
    margin: 1rem 0;
}
.tudo-ok-titulo {
    font-family: 'Bebas Neue', cursive;
    font-size: 5rem;
    color: #FFDF00;
    letter-spacing: 0.2em;
    margin: 0;
    text-shadow: 3px 3px 0px #003d1a;
}
.tudo-ok-sub { font-size: 1.4rem; font-weight: 700; color: #fff; margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)

def frango_svg(nome_id, nome, numero, sexo, fa2=False, flo=False, pintinho=False):
    escala = 0.72 if pintinho else 1.0
    h = int(115 * escala)
    w = int(72 * escala)
    pele = "#FDE68A"
    camisa = "#009c3b"
    faixa = "#FFDF00"
    crista = "#ef4444" if sexo == "galo" else "#f97316"
    fa_esq = "#FFDF00" if fa2 else camisa
    fa_dir = "#FF6B00" if flo else ("#FFDF00" if fa2 else camisa)
    nome_curto = nome[:6]
    fs_nome = 5.5 if len(nome) <= 5 else 4.5

    if sexo == "galo":
        crista_p = f'<path d="M35,18 Q38,10 42,17 Q46,8 49,17 Q44,20 35,21Z" fill="{crista}"/>'
        barb_p   = f'<path d="M33,42 Q28,50 31,56 Q35,60 39,56 Q42,50 37,42Z" fill="{crista}"/>'
    else:
        crista_p = f'<path d="M33,18 Q35,12 37,18 Q39,10 41,18 Q37,20 33,20Z" fill="{crista}"/>'
        barb_p   = f'<path d="M34,42 Q31,47 33,51 Q35,54 37,51 Q39,47 36,42Z" fill="{crista}"/>'

    return f"""<svg class="frango-svg" width="{w}" height="{h}" viewBox="0 0 72 115" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="36" cy="74" rx="22" ry="26" fill="{camisa}"/>
  <ellipse cx="36" cy="62" rx="20" ry="5" fill="{faixa}"/>
  <text x="36" y="71" text-anchor="middle" font-family="Arial" font-size="{fs_nome}" font-weight="700" fill="{faixa}">{nome_curto}</text>
  <text x="36" y="82" text-anchor="middle" font-family="Arial Black" font-size="8" font-weight="900" fill="{faixa}">#{numero}</text>
  {crista_p}
  <rect x="30" y="43" width="12" height="10" fill="{pele}" rx="3"/>
  <ellipse cx="36" cy="34" rx="18" ry="17" fill="{pele}"/>
  <path d="M36,36 L43,39 L36,42Z" fill="#f97316"/>
  <path d="M36,36 L29,39 L36,42Z" fill="#fb923c"/>
  <ellipse cx="28" cy="30" rx="5" ry="5.5" fill="white"/>
  <ellipse cx="29" cy="30" rx="3" ry="3.5" fill="#1e293b"/>
  <ellipse cx="30" cy="28" rx="1.2" ry="1.2" fill="white"/>
  <ellipse cx="44" cy="30" rx="5" ry="5.5" fill="white"/>
  <ellipse cx="45" cy="30" rx="3" ry="3.5" fill="#1e293b"/>
  <ellipse cx="46" cy="28" rx="1.2" ry="1.2" fill="white"/>
  <ellipse cx="21" cy="37" rx="4" ry="3" fill="#fca5a5" opacity="0.6"/>
  <ellipse cx="51" cy="37" rx="4" ry="3" fill="#fca5a5" opacity="0.6"/>
  {barb_p}
  <path d="M14,63 Q6,56 5,47 Q7,41 12,45 Q15,53 19,61Z" fill="{pele}"/>
  <path d="M11,53 Q8,51 7,47 Q9,45 11,48 Q12,51 13,54Z" fill="{fa_esq}"/>
  <path d="M58,63 Q66,56 67,47 Q65,41 60,45 Q57,53 53,61Z" fill="{pele}"/>
  <path d="M61,53 Q64,51 65,47 Q63,45 61,48 Q60,51 59,54Z" fill="{fa_dir}"/>
  <path d="M29,97 Q25,107 23,110" fill="none" stroke="#d97706" stroke-width="5" stroke-linecap="round"/>
  <path d="M43,97 Q51,105 55,109" fill="none" stroke="#d97706" stroke-width="5" stroke-linecap="round"/>
  <ellipse cx="22" cy="110" rx="7" ry="3.5" fill="#1e293b" transform="rotate(-10,22,110)"/>
  <ellipse cx="55" cy="109" rx="7" ry="3.5" fill="#1e293b" transform="rotate(25,55,109)"/>
</svg>"""

def bola_svg(small=False):
    s = 16 if small else 20
    return f"""<svg class="bola-svg" width="{s}" height="{s}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="11" fill="white" stroke="#9ca3af" stroke-width="1"/>
  <polygon points="12,4 16,8 14,13 10,13 8,8" fill="#1e293b"/>
  <polygon points="16,8 21,9 21,15 17,17 14,13" fill="none" stroke="#9ca3af" stroke-width="0.8"/>
  <polygon points="8,8 3,9 3,15 7,17 10,13" fill="none" stroke="#9ca3af" stroke-width="0.8"/>
</svg>"""

colaboradores = [
    {"nome": "Hagatah", "id": "hagatah", "numero": "7",  "sexo": "galinha", "fa2": False, "flo": False, "pintinho": False, "left": 2,  "bottom": 25},
    {"nome": "Sarah",   "id": "sarah",   "numero": "9",  "sexo": "galinha", "fa2": False, "flo": False, "pintinho": False, "left": 13, "bottom": 40},
    {"nome": "Sara",    "id": "sara",    "numero": "11", "sexo": "galinha", "fa2": True,  "flo": False, "pintinho": False, "left": 24, "bottom": 20},
    {"nome": "Michael", "id": "michael", "numero": "10", "sexo": "galo",    "fa2": True,  "flo": False, "pintinho": False, "left": 36, "bottom": 35},
    {"nome": "Edmar",   "id": "edmar",   "numero": "5",  "sexo": "galo",    "fa2": False, "flo": True,  "pintinho": False, "left": 48, "bottom": 20},
    {"nome": "Maria",   "id": "maria_j", "numero": "8",  "sexo": "galinha", "fa2": False, "flo": False, "pintinho": True,  "left": 59, "bottom": 42},
    {"nome": "Maria",   "id": "maria",   "numero": "3",  "sexo": "galinha", "fa2": False, "flo": False, "pintinho": False, "left": 68, "bottom": 22},
    {"nome": "Beatriz", "id": "beatriz", "numero": "6",  "sexo": "galinha", "fa2": False, "flo": False, "pintinho": False, "left": 79, "bottom": 38},
    {"nome": "Vinicius","id": "vinicius","numero": "4",  "sexo": "galo",    "fa2": False, "flo": False, "pintinho": True,  "left": 90, "bottom": 22},
]

campo_html = '<div class="campo-frangos" id="campo-frangos">'
for c in colaboradores:
    campo_html += f'<div class="frango-abs" id="wrap-{c["id"]}" style="left:{c["left"]}%;bottom:{c["bottom"]}px;">'
    campo_html += frango_svg(c["id"], c["nome"], c["numero"], c["sexo"], c["fa2"], c["flo"], c["pintinho"])
    campo_html += bola_svg(c["pintinho"])
    campo_html += '</div>'
campo_html += '</div>'

st.markdown(f"""
<div class="lar-header">
  <p class="lar-logo">LAR</p>
  <p class="lar-sub">COOPERATIVA AGROINDUSTRIAL &nbsp;·&nbsp; VALIDADOR BS e GTA &nbsp;·&nbsp; SIF 797</p>
  {campo_html}
</div>
""", unsafe_allow_html=True)

CARENCIAS = {
    "aviax plus": 11, "maxiban": 9, "monimax": 10, "nicarmix 25": 11,
    "monteban g100": 9, "linco-spectin 440": 1, "spectomix": 5,
    "coxifarm m40": 1, "avatec 20": 6, "zoocox": 1, "salinacox 240": 1,
    "coxifarm s": 1, "coxifarm plus": 1, "diatrim": 6, "linco-spectin": 3,
    "lincofarm ti": 3, "trimelor 75": 5, "farmaflor": 1, "neobase": 1,
    "acquaneutra": 1, "activo liquido": 1, "biohidract": 1, "bronk clean": 1,
    "ceitz e.f. plus": 1, "neoflora": 1, "oligoacid": 1, "perform-max": 1,
    "polimeve": 1, "mentovest": 1, "avt 450": 1, "avt-40": 1,
    "farmasept plus": 1, "farmasept 40": 1, "germon plus": 1,
    "timsen": 1, "virkon": 1, "virukiii": 1,
}

def parse_date(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except:
            pass
    return None

def verificar_carencias(medicamentos_bs, data_abate_str):
    data_abate = parse_date(data_abate_str)
    if not data_abate:
        return []
    erros = []
    for med in medicamentos_bs:
        nome = med.get("nome", "").lower().strip()
        data_fim_str = med.get("data_fim", "")
        if not data_fim_str:
            continue
        data_fim = parse_date(data_fim_str)
        if not data_fim:
            continue
        dias = None
        for key, val in CARENCIAS.items():
            if key in nome or nome in key:
                dias = val
                break
        if dias is None or dias <= 1:
            continue
        data_limite = data_fim + timedelta(days=dias)
        if data_abate < data_limite:
            erros.append({
                "nome": med.get("nome"),
                "data_fim": data_fim_str,
                "data_limite": data_limite.strftime("%d/%m/%Y"),
                "data_abate": data_abate_str
            })
    return erros

SYSTEM_PROMPT = """Você é especialista em documentos veterinários de frigoríficos de frango da LAR Cooperativa Agroindustrial.
Analise o BS e as GTAs. Retorne APENAS problemas encontrados. Itens corretos NÃO aparecem.

VALIDAÇÕES:
1. CRUZAMENTO BS x GTA (só GTAs fornecidas):
   - Compare aves programadas no BS com TOTAL na GTA. Se diferente: ERRO.
   - Compare aviário/núcleo do BS com o da GTA. Se diferente: ERRO.
   - Compare SIF destino. Se diferente: ERRO.
   - Se GTA listada no BS não foi fornecida: SEMPRE retornar ALERTA com número da GTA faltante.

2. MORTALIDADE:
   Fórmula: (total_pintos - remanescentes_1o - programadas_1o) / total_pintos * 100
   - Se > 5% E sem mensagem "MORTALIDADE ACIMA DE 5%" no BS: ERRO simples.
   - Se <= 5% E com a frase "MORTALIDADE ACIMA DE 5%" em qualquer parte do BS (incluindo declarações ou observações): apenas ALERTA simples. NÃO gerar ERRO nesse caso.
   - ATENÇÃO: a frase "MORTALIDADE ACIMA DE 5% NÃO SENDO EM 72 HORAS" também conta como presença da mensagem — não gerar erro.
   - Se valor divergir do declarado (arredondamentos): ALERTA simples.

3. MEDICAMENTOS: se não estiver na lista oficial: ALERTA. NÃO calcule carência.

4. CAMPOS OBRIGATÓRIOS ausentes: ERRO.
   Campos: nome estabelecimento, georreferenciamento, município/UF, cadastro SVO, lote/núcleo, nº galpões, médico veterinário CRMV, data alojamento, GTA pintos, nº pintos alojados, data carregamento, resultado salmonela.

5. EXTRAÇÃO: inclua todos os medicamentos com nome e data_fim.

ORGANIZAÇÃO: agrupe por núcleo com aviários.

Retorne SOMENTE JSON sem markdown:
{"produtor":"","lote":"","data_abate":"","tem_problemas":false,"medicamentos_encontrados":[{"nome":"","data_fim":"dd/mm/aaaa ou null"}],"nucleos":[{"nucleo":"","aviarios":"","erros":[{"categoria":"GTA|Mortalidade|Campo","item":"","detalhe":""}],"alertas":[{"categoria":"GTA|Mortalidade|Medicamento|Campo","item":"","detalhe":""}]}]}"""

def extract_text(f):
    doc = fitz.open(stream=f.read(), filetype="pdf")
    return "\n".join(p.get_text() for p in doc)

col1, col2 = st.columns(2)
with col1:
    bs_files = st.file_uploader("📄 Boletim Sanitário (BS)", type="pdf", accept_multiple_files=True)
with col2:
    gta_files = st.file_uploader("📋 GTAs", type="pdf", accept_multiple_files=True)

analisar = st.button("⚽ Analisar documentos", disabled=not (bs_files and gta_files), use_container_width=True, type="primary")

if analisar:
    with st.spinner("🐔 Os frangos estão analisando..."):
        bs_text = "\n\n".join(f"--- BS: {f.name} ---\n{extract_text(f)}" for f in bs_files)
        gta_text = "\n\n".join(f"--- GTA: {f.name} ---\n{extract_text(f)}" for f in gta_files)

    with st.spinner("🔍 Conferindo medicamentos e GTAs..."):
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Analise:\n{bs_text}\n{gta_text}"}]
            )
            raw = message.content[0].text.replace("```json","").replace("```","").strip()
            result = json.loads(raw)

            meds = result.get("medicamentos_encontrados", [])
            data_abate = result.get("data_abate", "")
            erros_carencia = verificar_carencias(meds, data_abate)
            nucleos = result.get("nucleos", [])
            produtor = result.get("produtor", "")
            lote = result.get("lote", "")

            if erros_carencia:
                result["tem_problemas"] = True
                msgs = [{"categoria": "Medicamento", "item": ec["nome"],
                    "detalhe": f"Carência não cumprida. Liberado a partir de {ec['data_limite']}, abate em {ec['data_abate']}."}
                    for ec in erros_carencia]
                if nucleos:
                    nucleos[0]["erros"] = nucleos[0].get("erros", []) + msgs
                else:
                    nucleos.append({"nucleo": "Geral", "aviarios": "-", "erros": msgs, "alertas": []})

            st.divider()
            tem_problemas = result.get("tem_problemas") and any(n.get("erros") or n.get("alertas") for n in nucleos)

            if not tem_problemas:
                st.success(f"✅ {produtor} — Lote {lote} — Abate {data_abate}")
                st.markdown("""
                <div class="tudo-ok">
                  <p class="tudo-ok-titulo">TUDO OK!</p>
                  <p class="tudo-ok-sub">✅ PODE ASSINAR A PROGRAMAÇÃO ✅</p>
                </div>""", unsafe_allow_html=True)
            else:
                tem_erro = any(n.get("erros") for n in nucleos)
                if tem_erro:
                    st.error(f"**{produtor}** — Lote {lote} — Abate {data_abate}")
                else:
                    st.warning(f"**{produtor}** — Lote {lote} — Abate {data_abate}")

                for nucleo in nucleos:
                    erros = nucleo.get("erros", [])
                    alertas = nucleo.get("alertas", [])
                    if not erros and not alertas:
                        continue
                    n_num = nucleo.get("nucleo", "")
                    aviarios = nucleo.get("aviarios", "")
                    with st.expander(f"🏠 Núcleo {n_num} — Aviários: {aviarios}", expanded=True):
                        if erros:
                            for cat in set(e["categoria"] for e in erros):
                                st.markdown(f"**❌ {cat}**")
                                for e in [x for x in erros if x["categoria"] == cat]:
                                    st.markdown(f"- **{e['item']}**: {e['detalhe']}")
                        if alertas:
                            for cat in set(a["categoria"] for a in alertas):
                                st.markdown(f"**⚠️ {cat}**")
                                for a in [x for x in alertas if x["categoria"] == cat]:
                                    st.markdown(f"- **{a['item']}**: {a['detalhe']}")

        except json.JSONDecodeError:
            st.error("Erro ao interpretar resposta da IA. Tente novamente.")
        except Exception as e:
            st.error(f"Erro: {str(e)}")
