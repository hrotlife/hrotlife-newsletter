# 🍄 Hrotlife Newsletter Agent

AI agent pre generovanie Hrotlife newslettrov s A/B predmetmi.

## Lokálne spustenie

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment na Streamlit Cloud (zadarmo)

1. Nahraj tento folder na GitHub (nový privátny repo)
2. Choď na [share.streamlit.io](https://share.streamlit.io)
3. Klikni **New app** → vyber repo → `app.py`
4. V sekcii **Secrets** pridaj:

```toml
# Toto je len fallback — API kľúč môžeš zadať aj priamo v UI
ANTHROPIC_API_KEY = "sk-ant-..."
```

5. Klikni **Deploy** — hotovo za ~2 minúty

## Použitie

1. **Sidebar vľavo:**
   - Vlož ukážky z minulých newslettrov (tone of voice)
   - Zadaj produkty vo formáte: `Názov — URL`
   - Zadaj Anthropic API kľúč

2. **Hlavná plocha:**
   - Téma mesiaca (napr. "Imunita")
   - Typ: Brandový alebo Konverzný
   - Podtémy — nechaj prázdne, agent navrhne sám

3. **Klikni Generovať** → dostaneš:
   - 2× predmet emailu (A/B test)
   - Preview text
   - Kompletný HTML email
   - Download tlačidlo

## Roadmap — fáza 2

- [ ] Napojenie na Ecomail API → priamy draft kampaň
- [ ] A/B test nastavenie priamo v Ecomail
- [ ] História vygenerovaných emailov
- [ ] Bulk generovanie pre celý kvartál
