import streamlit as st
import anthropic
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="Hrotlife Newsletter Agent",
    page_icon="🍄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: #0f1a10;
    border-right: 1px solid #2a3d2b;
}
section[data-testid="stSidebar"] * {
    color: #c8d8c0 !important;
}
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stTextInput input {
    background: #1a2e1b !important;
    border: 1px solid #2a3d2b !important;
    color: #e8f0e0 !important;
    border-radius: 6px;
}
section[data-testid="stSidebar"] label {
    color: #8aad80 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* main */
.main .block-container {
    padding-top: 2rem;
    max-width: 900px;
}

/* header strip */
.header-strip {
    background: linear-gradient(135deg, #0f1a10 0%, #1a3020 100%);
    border: 1px solid #2a4030;
    border-radius: 12px;
    padding: 1.6rem 2rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.header-strip h1 {
    color: #d4e8c0;
    margin: 0;
    font-size: 1.6rem;
}
.header-strip p {
    color: #7a9870;
    margin: 0;
    font-size: 0.85rem;
}

/* email type cards */
.type-card {
    border: 1px solid #e0e8d8;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    cursor: pointer;
    transition: all 0.15s;
}
.type-card:hover { border-color: #5a8a40; background: #f5faf0; }
.type-card.selected { border-color: #3a6a20; background: #eef7e4; }

/* output sections */
.output-box {
    background: #fafdf7;
    border: 1px solid #d8e8c8;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.output-box h4 {
    font-family: 'DM Serif Display', serif;
    color: #2a4a18;
    margin: 0 0 0.8rem;
    font-size: 1rem;
}
.subject-pill {
    background: #e8f5d8;
    border: 1px solid #b0d890;
    border-radius: 20px;
    padding: 0.4rem 1rem;
    display: inline-block;
    margin: 0.3rem 0.3rem 0.3rem 0;
    font-size: 0.88rem;
    color: #2a4a18;
    font-weight: 500;
}
.subject-pill.b { background: #fef5e0; border-color: #f0c860; color: #4a3800; }

.badge {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    margin-right: 0.4rem;
}
.badge-brand { background: #d8efc8; color: #2a5010; }
.badge-conv  { background: #fde8d0; color: #6a2800; }

.spinner-text {
    color: #5a8a40;
    font-style: italic;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ── sidebar — tone of voice + produkty ────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🍄 Hrotlife Agent")
    st.markdown("---")

    st.markdown("**Tone of voice**")
    tone_examples = st.text_area(
        "Vlož ukážky z minulých newslettrov",
        height=220,
        placeholder="Vlož sem 2–3 odseky z predchádzajúcich newslettrov. Agent sa podľa nich naučí tvoj štýl písania...",
        key="tone_input",
    )

    st.markdown("---")
    st.markdown("**Produkty mesiaca**")
    products_raw = st.text_area(
        "Produkt — URL (každý na nový riadok)",
        height=130,
        placeholder="Hrotlife Lev mohutný — https://hrotlife.sk/...\nHrotlife Maitake — https://hrotlife.sk/...",
        key="products_input",
    )

    st.markdown("---")
    api_key = st.text_input("Anthropic API kľúč", type="password", key="api_key")
    if not api_key:
        st.info("Zadaj API kľúč pre spustenie generovania.")


# ── helpers ───────────────────────────────────────────────────────────────────
def parse_products(raw: str) -> list[dict]:
    items = []
    for line in raw.strip().splitlines():
        if "—" in line:
            parts = line.split("—", 1)
            items.append({"name": parts[0].strip(), "url": parts[1].strip()})
        elif "http" in line:
            items.append({"name": line.strip(), "url": line.strip()})
    return items


def build_system_prompt(tone_examples: str) -> str:
    base = """Si Martin Máša — periodontológ, zakladateľ Hrotlife a tvorca obsahu @dr.fungitarian.
Píšeš po slovensky. Tvoj štýl je: odborný ale prístupný laikom, vždy mechanistický (vysvetľuješ prečo, nie len čo),
bez prázdnych klišé, s osobným hlasom — ako keby si písal kamarátovi, ktorý ťa rešpektuje pre tvoje znalosti.
Nikdy nepoužívaš clickbait. Buduješ autoritu Hrotlife cez edukáciu."""

    if tone_examples.strip():
        base += f"\n\nUkážky tvojho štýlu z minulých newslettrov:\n---\n{tone_examples.strip()}\n---"
    return base


def generate_email(client, email_type: str, topic: str, subtopics: list[str],
                   products: list[dict], tone_examples: str) -> dict:
    system = build_system_prompt(tone_examples)

    products_str = "\n".join([f"- {p['name']}: {p['url']}" for p in products]) if products else "žiadne produkty"

    if email_type == "brand":
        type_instruction = """Píšeš BRANDOVÝ newsletter dlhovekosti.
Cieľ: zvýšiť odbornosť Hrotlife, nie predávať.
Štruktúra:
1. Úvodný hook (1 prekvapivý fakt alebo otázka)
2. Mechanizmus — vysvetli prečo (nie len čo), s odkazom na štúdie
3. Praktický záver — čo môže čitateľ urobiť dnes
4. Soft CTA — môže byť odkaz na blog alebo produkt, ale nie agresívny

Produkty prelinkuj prirodzene ak to dáva zmysel, nie ako reklamu."""
    else:
        type_instruction = """Píšeš KONVERZNÝ newsletter.
Cieľ: predať produkty cez edukáciu — nie cez nátlak.
Štruktúra:
1. Problém/bolák čitateľa (1–2 vety)
2. Mechanizmus prečo bežné riešenia nefungujú
3. Predstavenie produktov ako riešenia — s URL odkazmi
4. Jasné CTA s urgenciou (akcia, limitovaná ponuka alebo dátum)

Produkty: {products}"""
        type_instruction = type_instruction.format(products=products_str)

    subtopics_str = "\n".join([f"- {s}" for s in subtopics if s.strip()])

    user_prompt = f"""Téma newslettera: {topic}

Podtémy / kľúčové otázky na pokrytie:
{subtopics_str}

{type_instruction}

Formát výstupu — odpovedz VÝLUČNE v JSON (bez markdown backticks):
{{
  "subject_a": "predmet emailu — curiosity/mechanizmus (max 55 znakov)",
  "subject_b": "predmet emailu — benefit/výsledok (max 55 znakov)",
  "preview_text": "preview text (45–85 znakov)",
  "email_html": "kompletný HTML email s inline štýlmi, vhodný pre Ecomail"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=6000,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def research_subtopics(client, topic: str, tone_examples: str) -> list[str]:
    system = build_system_prompt(tone_examples)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": f"""Pre tému "{topic}" navrhni 3 najpálčivejšie podotázky,
ktoré ľudia skutočne vyhľadávajú a ktoré sa dajú vysvetliť cez mechanizmy.
Každá podotázka by mala byť konkrétna a zaujímavá pre laika.
Odpovedz VÝLUČNE v JSON (bez backticks): {{"subtopics": ["...", "...", "..."]}}"""}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    return json.loads(raw).get("subtopics", [])


# ── main UI ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-strip">
  <div style="font-size:2.2rem">🍄</div>
  <div>
    <h1>Hrotlife Newsletter Agent</h1>
    <p>Zadaj tému → agent navrhne podotázky → vygeneruje email + A/B predmety</p>
  </div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("#### Téma mesiaca")
    topic = st.text_input("", placeholder="napr. Imunita, Stres a kortizol, Spánok...", label_visibility="collapsed")

    st.markdown("#### Typ newslettera")
    email_type = st.radio(
        "",
        options=["brand", "conversion"],
        format_func=lambda x: "🌿 Brandový — edukácia & autorita" if x == "brand" else "🎯 Konverzný — produkty & akcia",
        label_visibility="collapsed",
    )

    st.markdown("#### Podtémy / kľúčové otázky")
    st.caption("Nechaj prázdne → agent navrhne sám | Alebo uprav po vygenerovaní")

    if "subtopics" not in st.session_state:
        st.session_state.subtopics = ["", "", ""]

    sub1 = st.text_input("Podtéma 1", value=st.session_state.subtopics[0], placeholder="napr. Prečo stres oslabuje imunitu?")
    sub2 = st.text_input("Podtéma 2", value=st.session_state.subtopics[1], placeholder="napr. Spánok a imunitná pamäť")
    sub3 = st.text_input("Podtéma 3", value=st.session_state.subtopics[2], placeholder="napr. Odporúčanie produktu")

with col_right:
    st.markdown("#### Produkty v tomto emaili")
    products = parse_products(products_raw)
    if products:
        for p in products:
            st.markdown(f"✅ **{p['name']}**  \n`{p['url']}`")
    else:
        st.caption("Žiadne produkty — pridaj ich v sidebari vľavo.")

    st.markdown("---")

    can_generate = bool(topic and api_key)

    if st.button("🚀 Generovať email", disabled=not can_generate, use_container_width=True, type="primary"):
        client = anthropic.Anthropic(api_key=api_key)
        subtopics_input = [s for s in [sub1, sub2, sub3] if s.strip()]

        # auto-research if empty
        if not subtopics_input:
            with st.spinner("Hľadám najlepšie podtémy..."):
                subtopics_input = research_subtopics(client, topic, tone_examples)
            st.session_state.subtopics = subtopics_input
            st.rerun()

        with st.spinner("Generujem email..."):
            result = generate_email(
                client,
                email_type=email_type,
                topic=topic,
                subtopics=subtopics_input,
                products=products,
                tone_examples=tone_examples,
            )
            st.session_state.result = result
            st.session_state.generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    if not can_generate and not api_key:
        st.caption("⚠️ Zadaj API kľúč v sidebari.")
    if not can_generate and not topic:
        st.caption("⚠️ Zadaj tému mesiaca.")


# ── results ───────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    r = st.session_state.result
    st.markdown("---")
    st.markdown(f"### Výsledok — vygenerované {st.session_state.get('generated_at', '')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="output-box"><h4>📧 Predmet A — Curiosity</h4>', unsafe_allow_html=True)
        st.markdown(f'<span class="subject-pill">{r.get("subject_a", "–")}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="output-box"><h4>📧 Predmet B — Benefit</h4>', unsafe_allow_html=True)
        st.markdown(f'<span class="subject-pill b">{r.get("subject_b", "–")}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if r.get("preview_text"):
        st.markdown(f'<div class="output-box"><h4>👁 Preview text</h4><p style="color:#4a6a38;margin:0">{r["preview_text"]}</p></div>', unsafe_allow_html=True)

    tab_preview, tab_html = st.tabs(["👀 Preview emailu", "💾 HTML kód"])

    with tab_preview:
        if r.get("email_html"):
            st.components.v1.html(r["email_html"], height=700, scrolling=True)

    with tab_html:
        if r.get("email_html"):
            st.code(r["email_html"], language="html")
            st.download_button(
                "⬇️ Stiahnuť HTML",
                data=r["email_html"],
                file_name=f"hrotlife_{topic.lower().replace(' ', '_')}_{email_type}.html",
                mime="text/html",
            )
