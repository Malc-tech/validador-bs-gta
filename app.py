import streamlit as st
import anthropic
import fitz
import json

st.set_page_config(page_title="Validador BS e GTA — LAR", page_icon="✅")
st.title("Validador de BS e GTA")
st.caption("LAR Cooperativa Agroindustrial — SIF 797")

MEDICATION_LIST = """
ANTICOCCIDIANOS NAS RAÇÕES - carência em dias antes do abate:
- Aviax Plus (Semduramicina+Nicarbazina): 10 dias
- Maxiban (Narasina+Nicarbazina): 8 dias
- Monimax (Monensina+Nicarbazina): 9 dias
- Nicarmix 25 (Nicarbazina): 10 dias
- Monteban G100 (Narasina): 8 dias
- Linco-Spectin 440 (Lincomicina+Espectinomicina): 0 dias
- Spectomix (Lincomicina+Espectinomicina): 4 dias
- Coxifarm M40 (Monensina): 0 dias
- Avatec 20 (Lasalocida): 5 dias
- Zoocox (Dinitolmida): 0 dias
- Salinacox 240 (Salinomicina): 0 dias
- Coxifarm S (Salinomicina): 0 dias
- Coxifarm Plus (Salinomicina+Diclazuril): 0 dias
MEDICAMENTOS VIA ORAL:
- Diatrim: 5 dias
- Linco-Spectin: 2 dias
- Lincofarm TI: 2 dias
- Spectomix: 4 dias
- Trimelor 75: 4 dias
- Farmaflor, Neobase, Acquaneutra, Activo Liquido, Biohidract, Bronk Clean, Ceitz E.F. Plus, Neoflora, Oligoacid, Perform-Max, Polimeve, Mentovest: 0 dias
NEBULIZAÇÃO (todos 0 dias): AVT 450, AVT-40, Farmasept Plus, Farmasept 40, Germon Plus, Timsen, Virkon, VirukIII
REGRA: 0 dias = data_fim pode ser igual ao abate. N dias = data_fim + N <= data_abate, senão ERRO.
"""

SYSTEM_PROMPT = """Você é especialista em documentos veterinários de frigoríficos de frango da LAR Cooperativa Agroindustrial.
Analise o BS e as GTAs. Retorne APENAS problemas encontrados. Itens corretos NÃO aparecem.

MEDICAMENTOS:""" + MEDICATION_LIST + """

VALIDAÇÕES:
1. CRUZAMENTO BS x GTA (só GTAs fornecidas): compare aves programadas, aviário e SIF. Se diferente: ERRO. Se GTA do BS não fornecida: ALERTA.
2. MORTALIDADE: (total_pintos - remanescentes_1o - programadas_1o) / total_pintos * 100. Se diferença > 0.05% do declarado: ERRO. Se mortalidade<=5% mas tem observação de acima de 5%: ALERTA.
3. MEDICAMENTOS: se não está na lista: ALERTA. Se data_fim + carencia > data_abate: ERRO.
4. CAMPOS OBRIGATÓRIOS ausentes: ERRO.

Retorne SOMENTE JSON sem markdown:
{"produtor":"","lote":"","data_abate":"","tem_problemas":false,"erros":[{"categoria":"GTA|Mortalidade|Medicamento|Campo","item":"","detalhe":""}],"alertas":[{"categoria":"GTA|Mortalidade|Medicamento|Campo","item":"","detalhe":""}]}"""

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
            raw = message.content[0].text.replace("```json","").replace("```","").strip()
            result = json.loads(raw)

            erros = result.get("erros", [])
            alertas = result.get("alertas", [])
            produtor = result.get("produtor", "")
            lote = result.get("lote", "")
            data_abate = result.get("data_abate", "")

            st.divider()

            if not result.get("tem_problemas") or (not erros and not alertas):
                st.success(f"✅ Documento aprovado\n\n**{produtor}** — Lote {lote} — Abate {data_abate}\n\nNenhuma inconsistência encontrada.")
            else:
                if erros:
                    st.error(f"**{produtor}** — Lote {lote} — Abate {data_abate}")
                    for cat in set(e["categoria"] for e in erros):
                        st.markdown(f"**❌ {cat}**")
                        for e in [x for x in erros if x["categoria"] == cat]:
                            st.markdown(f"- **{e['item']}**: {e['detalhe']}")
                if alertas:
                    if not erros:
                        st.warning(f"**{produtor}** — Lote {lote} — Abate {data_abate}")
                    for cat in set(a["categoria"] for a in alertas):
                        st.markdown(f"**⚠️ {cat}**")
                        for a in [x for x in alertas if x["categoria"] == cat]:
                            st.markdown(f"- **{a['item']}**: {a['detalhe']}")

        except json.JSONDecodeError:
            st.error("Erro ao interpretar resposta da IA. Tente novamente.")
        except Exception as e:
            st.error(f"Erro: {str(e)}")
