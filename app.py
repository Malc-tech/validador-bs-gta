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

REGRA DE CARÊNCIA — LEIA COM ATENÇÃO:
- Medicamentos com 0 dias: sempre OK, nunca retornar erro.
- Medicamentos com N dias: calcule DATA_LIMITE = data_fim + (N + 1) dias.
  Se data_abate >= DATA_LIMITE: APROVADO, não retornar nada.
  Se data_abate < DATA_LIMITE: ERRO.
- ATENÇÃO: compare as datas corretamente considerando mês e ano. Uma data em junho é SEMPRE posterior a uma data em maio do mesmo ano.
- Exemplos corretos:
  Maxiban 8 dias, data_fim 14/05/2026, abate 01/06/2026 → DATA_LIMITE = 14/05 + 9 = 23/05/2026. Abate 01/06/2026 > 23/05/2026 → APROVADO, não retornar.
  Maxiban 8 dias, data_fim 14/05/2026, abate 20/05/2026 → DATA_LIMITE = 23/05/2026. Abate 20/05/2026 < 23/05/2026 → ERRO.
- NUNCA retornar medicamentos aprovados.
"""

SYSTEM_PROMPT = """Você é especialista em documentos veterinários de frigoríficos de frango da LAR Cooperativa Agroindustrial.
Analise o BS e as GTAs. Retorne APENAS problemas encontrados. Itens corretos NÃO aparecem na resposta.

MEDICAMENTOS E CARÊNCIAS:
""" + MEDICATION_LIST + """

VALIDAÇÕES:

1. CRUZAMENTO BS x GTA (só GTAs fornecidas):
   - Compare aves programadas no BS com TOTAL na GTA. Se diferente: ERRO.
   - Compare aviário/núcleo do BS com o da GTA. Se diferente: ERRO.
   - Compare SIF destino. Se diferente: ERRO.
   - Se GTA listada no BS não foi fornecida: ALERTA.

2. MORTALIDADE:
   Fórmula: (total_pintos_alojados - remanescentes_1o_carregamento - programadas_1o_carregamento) / total_pintos_alojados * 100
   - Se mortalidade calculada > 5% E a mensagem de declaração "MORTALIDADE ACIMA DE 5%" NÃO constar no BS: ERRO simples, sem mostrar cálculos.
   - Se mortalidade calculada <= 5% E a mensagem "MORTALIDADE ACIMA DE 5%" CONSTAR no BS: apenas ALERTA simples, sem mostrar cálculos.
   - Se o valor calculado divergir do declarado no BS (considerando arredondamentos): apenas ALERTA simples, sem mostrar os números do cálculo.
   - Se tudo estiver correto: não retornar nada sobre mortalidade.

3. MEDICAMENTOS:
   - Aplicar exatamente a REGRA DE CARÊNCIA descrita acima.
   - Se medicamento não estiver na lista oficial: ALERTA.
   - NUNCA retornar medicamentos OK.

4. CAMPOS OBRIGATÓRIOS ausentes ou em branco: ERRO.
   Campos: nome estabelecimento, georreferenciamento, município/UF, cadastro SVO, lote/núcleo, nº galpões, médico veterinário CRMV, data alojamento, GTA pintos, nº pintos alojados, data carregamento, resultado salmonela.

ORGANIZAÇÃO DA RESPOSTA:
- Agrupe todos os erros e alertas por NÚCLEO.
- Para cada núcleo, informe quais aviários estão relacionados ao problema.
- Seja objetivo: apenas o problema, sem explicações longas.

Retorne SOMENTE JSON sem markdown:
{
  "produtor": "",
  "lote": "",
  "data_abate": "",
  "tem_problemas": false,
  "nucleos": [
    {
      "nucleo": "número do núcleo",
      "aviarios": "aviários relacionados ex: 3015, 3016",
      "erros": [{"categoria": "GTA|Mortalidade|Medicamento|Campo", "item": "", "detalhe": ""}],
      "alertas": [{"categoria": "GTA|Mortalidade|Medicamento|Campo", "item": "", "detalhe": ""}]
    }
  ]
}

Se não houver nenhum problema, retorne nucleos:[] e tem_problemas:false.
"""

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

            nucleos = result.get("nucleos", [])
            produtor = result.get("produtor", "")
            lote = result.get("lote", "")
            data_abate = result.get("data_abate", "")

            st.divider()

            if not result.get("tem_problemas") or not nucleos:
                st.success(f"✅ Documento aprovado\n\n**{produtor}** — Lote {lote} — Abate {data_abate}\n\nNenhuma inconsistência encontrada.")
            else:
                tem_erro = any(n.get("erros") for n in nucleos)
                if tem_erro:
                    st.error(f"**{produtor}** — Lote {lote} — Abate {data_abate}")
                else:
                    st.warning(f"**{produtor}** — Lote {lote} — Abate {data_abate}")

                for nucleo in nucleos:
                    n_num = nucleo.get("nucleo", "")
                    aviarios = nucleo.get("aviarios", "")
                    erros = nucleo.get("erros", [])
                    alertas = nucleo.get("alertas", [])

                    if not erros and not alertas:
                        continue

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
