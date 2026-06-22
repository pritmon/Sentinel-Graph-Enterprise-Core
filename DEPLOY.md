# Deploying Sentinel-Graph to a public URL (Streamlit Community Cloud)

The app is already deploy-ready. Streamlit Cloud can't reach your laptop's Neo4j, so the
hosted app needs a **cloud Neo4j (Aura free tier)** plus your API key — both supplied as
secrets. Three steps, ~10 minutes.

## 1. Create a free cloud Neo4j (Neo4j Aura)
1. Go to https://console.neo4j.io → sign in → **Create instance** → **AuraDB Free**.
2. When it provisions, **download / copy the credentials** — you get:
   - Connection URI like `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - Username `neo4j` and a generated password.
   Save these; the password is shown only once.

## 2. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io → **Sign in with GitHub** (authorize it to read your repos).
2. **Create app → Deploy a public app from GitHub** and set:
   - Repository: `pritmon/Sentinel-Graph-Enterprise-Core`
   - Branch: `main`
   - Main file path: `src/dashboard.py`
3. Open **Advanced settings → Python version → 3.11** (matches the pinned requirements).
4. In **Advanced settings → Secrets**, paste (using your real Aura values + Anthropic key):

   ```toml
   GEMINI_MODEL = "anthropic:claude-haiku-4-5"
   ANTHROPIC_API_KEY = "sk-ant-..."
   NEO4J_URI = "neo4j+s://xxxxxxxx.databases.neo4j.io"
   NEO4J_USERNAME = "neo4j"
   NEO4J_PASSWORD = "your-aura-password"
   ```
5. Click **Deploy**. First build takes a couple of minutes. You'll get a public URL like
   `https://sentinel-graph-enterprise-core.streamlit.app`.

## 3. Seed data and test
The Aura database starts empty. In the deployed app's sidebar, click
**⚡ Seed sample fraud dataset** once — it ingests the demo document via the Cartographer.
Then ask an audit question (sample buttons are provided), e.g.
*"List every company ranked by risk_score, with its jurisdiction."*

## Notes
- `.streamlit/secrets.toml` is gitignored — secrets live only in Streamlit Cloud, never in git.
  `.streamlit/secrets.toml.example` shows the expected keys.
- Anyone with the public URL can run audits, which spends your Anthropic quota. Streamlit
  Cloud apps can be password-gated under **Settings → Sharing** if you want it private.
- To run locally instead: `streamlit run src/dashboard.py` with a `.env` (or
  `.streamlit/secrets.toml`) holding the same keys, against any reachable Neo4j.
