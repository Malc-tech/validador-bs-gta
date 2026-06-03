import streamlit as st
import anthropic
import fitz
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Validador BS e GTA — LAR", page_icon="✅")
st.title("Validador de BS e GTA")
st.caption("LAR Cooperativa Agroindustrial — SIF 797")

# Carências oficiais (dias + 1 extra)
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
    """Recebe lista de dicts {nome, data_fim} e data do abate. Retorna lista de erros."""
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
        # Encontrar carência
        dias = None
        for key, val in CARENCIAS.items():
            if key in nome or nome in key:
                dias = val
                break
        if dias is None:
            continue  # medicamento não reconhecido, IA vai alertar
        if dias <= 1:
            continue  # carência 0 dias (+ 1 extra = 1), data_fim pode ser igual ao abate
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
   - Se GTA listada no BS não foi fornecida nos arquivos enviados: SEMPRE retornar ALERTA informando o número da GTA faltante. Isso é obrigatório independente de qualquer outra validação.

2. MORTALIDADE:
   Fórmula: (total_pintos_alojados - remanescentes_1o_carregamento - programadas_1o_carregamento) / total_pintos_alojados * 100
   - Se mortalidade calculada > 5% E a mensagem "MORTALIDADE ACIMA DE 5%" NÃO constar no BS: ERRO simples sem mostrar cálculos.
   - Se mortalidade calculada <= 5% E a mensagem "MORTALIDADE ACIMA DE 5%" CONSTAR no BS: ALERTA simples sem mostrar cálculos.
   - Se o valor calculado divergir do declarado (considerando arredondamentos): ALERTA simples sem mostrar cálculos.
   - Se tudo correto: não retornar nada sobre mortalidade.

3. MEDICAMENTOS — APENAS:
   - Se medicamento não estiver na lista oficial: ALERTA.
   - NÃO calcule carência — isso já foi calculado pelo sistema. Apenas liste os medicamentos presentes para que o sistema possa verificar.

4. CAMPOS OBRIGATÓRIOS ausentes: ERRO.
   Campos: nome estabelecimento, georreferenciamento, município/UF, cadastro SVO, lote/núcleo, nº galpões, médico veterinário CRMV, data alojamento, GTA pintos, nº pintos alojados, data carregamento, resultado salmonela.

5. EXTRAÇÃO DE MEDICAMENTOS — inclua no JSON todos os medicamentos encontrados no BS com nome e data_fim (se houver).

ORGANIZAÇÃO: agrupe por núcleo informando os aviários relacionados.

Retorne SOMENTE JSON sem markdown:
{
  "produtor": "",
  "lote": "",
  "data_abate": "",
  "tem_problemas": false,
  "medicamentos_encontrados": [{"nome": "", "data_fim": "dd/mm/aaaa ou null"}],
  "nucleos": [
    {
      "nucleo": "",
      "aviarios": "",
      "erros": [{"categoria": "GTA|Mortalidade|Campo", "item": "", "detalhe": ""}],
      "alertas": [{"categoria": "GTA|Mortalidade|Medicamento|Campo", "item": "", "detalhe": ""}]
    }
  ]
}"""

def extract_text(uploaded_file):
    data = uploaded_file.read()
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

col1, col2 = st.columns(2)
with col1:
    bs_files = st.file_uploader("📄 Boletim Sanitário (BS)", type="pdf", accept_multiple_files=True)
with col2:
    gta_files = st.file_uploader("📋 GTAs", type="pdf", accept_multiple_files=True)

if st.button("🔍 Analisar documentos", disabled=not (bs_files and gta_files), use_container_width=True, type="primary"):
    with st.spinner("Extraindo texto dos PDFs..."):
        bs_text = "\n\n".join(f"--- BS: {f.name} ---\n{extract_text(f)}" for f in bs_files)
        gta_text = "\n\n".join(f"--- GTA: {f.name} ---\n{extract_text(f)}" for f in gta_files)

    with st.spinner("Analisando com IA..."):
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Analise:\n{bs_text}\n{gta_text}"}]
            )
            raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            # Verificar carências no Python (confiável)
            meds = result.get("medicamentos_encontrados", [])
            data_abate = result.get("data_abate", "")
            erros_carencia = verificar_carencias(meds, data_abate)

            nucleos = result.get("nucleos", [])
            produtor = result.get("produtor", "")
            lote = result.get("lote", "")

            # Adicionar erros de carência ao primeiro núcleo ou criar um geral
            if erros_carencia:
                result["tem_problemas"] = True
                erro_msgs = []
                for ec in erros_carencia:
                    erro_msgs.append({
                        "categoria": "Medicamento",
                        "item": ec["nome"],
                        "detalhe": f"Carência não cumprida. Liberado a partir de {ec['data_limite']}, abate em {ec['data_abate']}."
                    })
                if nucleos:
                    nucleos[0]["erros"] = nucleos[0].get("erros", []) + erro_msgs
                else:
                    nucleos.append({"nucleo": "Geral", "aviarios": "-", "erros": erro_msgs, "alertas": []})

            st.divider()

            if not result.get("tem_problemas") or not any(n.get("erros") or n.get("alertas") for n in nucleos):
                st.success(f"✅ Documento aprovado — **{produtor}** — Lote {lote} — Abate {data_abate}")
                st.markdown(                    """
                    <div style="text-align:center; padding: 2rem 0;">
                        <p style="font-size:3rem; font-weight:900; color:#15803d; margin:0; line-height:1.1;">TUDO OK!</p>
                        <p style="font-size:1.4rem; font-weight:700; color:#15803d; margin-top:0.5rem;">PODE ASSINAR A PROGRAMAÇÃO ✅</p>
                    </div>
                    """, unsafe_allow_html=True)
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
