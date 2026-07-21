"""dashboard_styles.py — CSS estatico extraido do dashboard.py (V17.2).

Constantes injetadas via st.markdown(CONST, unsafe_allow_html=True), nos
mesmos pontos do original. Blocos de CSS DINAMICO (f-string dependente de
key/variaveis: nav_button, stop_button, card 3D do Villa) seguem inline no
dashboard.py. Extracao byte-a-byte -> aparencia identica.
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400..700&display=swap');

:root {
    --lilo-bg:          #FAF9F5;   /* marfim — fundo principal */
    --lilo-bg-soft:     #F0EEE6;   /* creme — sidebar e bolha do usuario */
    --lilo-bg-card:     #FFFFFF;   /* cartoes e composer */
    --lilo-border:      #E3E1D7;
    --lilo-text:        #3D3929;   /* marrom-escuro quente */
    --lilo-text-dim:    #73705F;
    --lilo-accent:      #D97757;   /* coral Claude */
    --lilo-accent-dark: #C96442;
    --lilo-accent-soft: #F5E8E1;
    --lilo-serif: 'Source Serif 4', Georgia, 'Times New Roman', serif;
    --lilo-sans:  'Inter', -apple-system, 'Segoe UI', sans-serif;
}

/* === BASE — fundo marfim, tipografia ===================================== */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--lilo-bg) !important;
    color: var(--lilo-text) !important;
    font-family: var(--lilo-sans) !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }

.main .block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 5rem !important;
    max-width: 100% !important;
}

/* Headings serifados, estilo Claude */
.main h1, .main h2, .main h3 {
    font-family: var(--lilo-serif) !important;
    color: var(--lilo-text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
}
.main h1 {
    font-size: 1.9rem !important;
    border-bottom: none !important;
    padding-bottom: 0.2rem;
    margin-bottom: 0.8rem !important;
}

/* === SIDEBAR — creme, navegacao ghost ==================================== */
section[data-testid="stSidebar"] {
    background: var(--lilo-bg-soft) !important;
    border-right: 1px solid var(--lilo-border) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.6rem !important;
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] small {
    color: var(--lilo-text) !important;
}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small {
    color: var(--lilo-text-dim) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: var(--lilo-border) !important;
    margin: 0.5rem 0 0.4rem 0 !important;
}
/* Rotulos de secao (SUB-AGENTES, FERRAMENTAS...) */
section[data-testid="stSidebar"] .stMarkdown p {
    margin: 0 0 0.2rem 0 !important;
    font-size: 0.68rem !important;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--lilo-text-dim) !important;
    font-weight: 600;
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.15rem !important;
}

/* === BOTOES DA SIDEBAR — ghost (transparente), hover suave ============== */
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    padding: 0.42rem 0.75rem !important;
    margin: 0 !important;
    border: none !important;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.88rem !important;
    line-height: 1.25 !important;
    min-height: 34px !important;
    cursor: pointer;
    transition: background 0.12s ease;
    box-shadow: none !important;
    text-align: left;
    color: var(--lilo-text) !important;
    background: transparent !important;
}
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span,
section[data-testid="stSidebar"] .stButton > button div {
    color: inherit !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(61,57,41,0.07) !important;
}
section[data-testid="stSidebar"] .stButton > button:active {
    background: rgba(61,57,41,0.12) !important;
}

/* Item ativo: tinta coral suave (item selecionado, como no Claude) */
.active-btn button {
    background: var(--lilo-accent-soft) !important;
    color: var(--lilo-accent-dark) !important;
    font-weight: 600 !important;
}

/* === SELECTBOX e INPUT na sidebar ======================================== */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: var(--lilo-bg-card) !important;
    border-color: var(--lilo-border) !important;
    min-height: 36px !important;
    color: var(--lilo-text) !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] span {
    color: var(--lilo-text) !important;
}

/* === LOGO ================================================================ */
.lilo-logo-wrap {
    text-align: center;
    padding: 4px 0 2px 0;
}
.lilo-logo-wrap img {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(61,57,41,0.15);
    background: white;
    padding: 4px;
}
.lilo-title {
    text-align: center;
    font-family: var(--lilo-serif);
    font-size: 1.25rem !important;
    font-weight: 700;
    letter-spacing: 3px;
    color: var(--lilo-text) !important;
    margin: 6px 0 2px 0 !important;
}
.lilo-subtitle {
    text-align: center;
    font-size: 0.68rem !important;
    color: var(--lilo-text-dim) !important;
    margin-bottom: 8px !important;
}

/* === CHAT — bolhas estilo Claude ========================================= */
div[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.4rem 0;
}
/* Mensagem do usuario: bolha creme arredondada */
div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--lilo-bg-soft) !important;
    border-radius: 16px;
    padding: 0.7rem 1rem;
}
div[data-testid="stChatMessage"] p { line-height: 1.65; }

/* Composer: cartao branco arredondado com sombra (como o Claude) */
div[data-testid="stChatInput"],
section[data-testid="stChatInput"] {
    background: var(--lilo-bg-card) !important;
    border: 1px solid var(--lilo-border) !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 18px rgba(61,57,41,0.08) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--lilo-text) !important;
    font-family: var(--lilo-sans) !important;
}
div[data-testid="stChatInput"] button {
    background: var(--lilo-accent) !important;
    border-radius: 10px !important;
    color: #fff !important;
}
div[data-testid="stChatInput"] button:hover {
    background: var(--lilo-accent-dark) !important;
}

/* === BOTOES DA AREA CENTRAL — neutros com borda sutil ==================== */
.main .stButton > button {
    border: 1px solid var(--lilo-border) !important;
    border-radius: 10px !important;
    background: var(--lilo-bg-card) !important;
    color: var(--lilo-text) !important;
    font-weight: 500;
    box-shadow: 0 1px 2px rgba(61,57,41,0.05);
    transition: background 0.12s ease, border-color 0.12s ease;
}
.main .stButton > button:hover {
    border-color: var(--lilo-accent) !important;
    color: var(--lilo-accent-dark) !important;
    background: var(--lilo-bg) !important;
}
.main .stButton > button[kind="primary"],
.main button[data-testid="stBaseButton-primary"] {
    background: var(--lilo-accent) !important;
    border-color: var(--lilo-accent) !important;
    color: #fff !important;
}

/* === STOP BUTTON ========================================================= */
.stop-btn button {
    background: #C0392B !important;
    border-color: #C0392B !important;
    color: white !important;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.75; }
}

/* === TABS — neutras com ativo coral ====================================== */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--lilo-bg-soft);
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 8px;
    color: var(--lilo-text-dim);
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.4rem 1rem;
}
.stTabs [aria-selected="true"] {
    background-color: var(--lilo-bg-card) !important;
    color: var(--lilo-accent-dark) !important;
    box-shadow: 0 1px 3px rgba(61,57,41,0.10);
}

/* === SKILLS POPUP ======================================================== */
.skill-popup {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    width: 500px;
    max-height: 300px;
    overflow-y: auto;
    background: var(--lilo-bg-card);
    border: 1px solid var(--lilo-border);
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(61,57,41,0.14);
    z-index: 1000;
    padding: 8px;
}

/* === CODE/PRE em tom quente ============================================== */
.main code {
    background: var(--lilo-bg-soft);
    color: var(--lilo-accent-dark);
    border-radius: 5px;
}
.main pre {
    background: #FCFBF8 !important;
    border: 1px solid var(--lilo-border) !important;
    border-radius: 10px !important;
}

/* === AJUSTES FINOS (v10.10) ============================================== */
/* Botoes da sidebar alinhados a esquerda (flex, nao so text-align) */
section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start !important;
}
section[data-testid="stSidebar"] .stButton > button p {
    text-align: left !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    font-size: 0.88rem !important;
    font-weight: inherit !important;
    color: inherit !important;
}
/* Caption de status (Ollama | agentes): sem uppercase, com respiro */
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    text-transform: none !important;
    letter-spacing: 0.2px !important;
    font-size: 0.74rem !important;
    font-weight: 400 !important;
    margin: 2px 0 8px 0 !important;
    text-align: center;
}
/* h2/h3 mais contidos (painel direito estreito: "Historico" sem quebrar) */
.main h3 { font-size: 1.12rem !important; }
.main h2 { font-size: 1.45rem !important; }
/* Botoes-pilula nunca quebram linha */
.lilo-mode-bar .stButton > button,
div[class*="st-key-lilo_mode_"] button {
    white-space: nowrap !important;
}

/* ========================================================================
   AJUDA & GLOSSARIO — estilo GenOmics localhost:3838
   ======================================================================== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Header azul (Bootstrap info color) replica do GenOmics */
.help-header {
    background: linear-gradient(135deg, #D97757 0%, #C96442 100%);
    color: white;
    padding: 0.85rem 1.4rem;
    border-radius: 8px 8px 0 0;
    margin-top: 0.5rem;
    margin-bottom: 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.help-header h2 {
    color: white !important;
    margin: 0 !important;
    font-family: 'Inter', sans-serif;
    font-size: 1.15rem !important;
    font-weight: 600;
    letter-spacing: 0.3px;
    border: none !important;
    padding: 0 !important;
}
.help-header.glossario-header {
    background: linear-gradient(135deg, #D97757 0%, #C96442 100%);
}

/* Subtitle abaixo do header — area cinza clara como no GenOmics */
.help-subtitle {
    background: #F0EEE6;
    color: #73705F;
    padding: 0.75rem 1.4rem;
    margin: 0 0 0 0;
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    border-left: 1px solid #E0E0E0;
    border-right: 1px solid #E0E0E0;
}

/* Card branco para conteudo Markdown */
.help-content {
    background: white;
    padding: 1.8rem 2.2rem;
    border-radius: 0 0 8px 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    border: 1px solid #E0E0E0;
    border-top: none;
    font-family: 'Inter', sans-serif;
    font-size: 0.94rem;
    line-height: 1.65;
    color: #2C3E50;
    margin-bottom: 1.5rem;
}
.help-content h1 {
    font-size: 1.55rem !important;
    color: #3D3929 !important;
    border-bottom: 2px solid #D97757 !important;
    padding-bottom: 0.4rem !important;
    margin-bottom: 1rem !important;
    font-weight: 700;
}
.help-content h2 {
    font-size: 1.25rem !important;
    color: #3D3929 !important;
    margin-top: 1.6rem !important;
    margin-bottom: 0.6rem !important;
    border-left: 4px solid #D97757;
    padding-left: 0.6rem;
    font-weight: 600;
}
.help-content h3 {
    font-size: 1.08rem !important;
    color: #3D3929 !important;
    margin-top: 1.2rem !important;
    font-weight: 600;
}
.help-content p {
    margin-bottom: 0.8rem;
}
.help-content ul, .help-content ol {
    margin-left: 1.2rem;
    margin-bottom: 0.8rem;
}
.help-content li { margin-bottom: 0.3rem; }
.help-content table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
    font-size: 0.88rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.help-content table th {
    background: #D97757;
    color: white;
    padding: 0.6rem 0.8rem;
    text-align: left;
    font-weight: 600;
    border: 1px solid #C96442;
}
.help-content table td {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid #E0E0E0;
    border-left: 1px solid #F0F0F0;
    border-right: 1px solid #F0F0F0;
    vertical-align: top;
}
.help-content table tr:nth-child(even) td { background: #FAFBFC; }
.help-content table tr:hover td { background: #F0F8FB; }
.help-content code {
    background: #F0F4F8;
    color: #C0392B;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.87em;
    font-family: 'Consolas', 'Courier New', monospace;
}
.help-content pre {
    background: #F8F9FA;
    border: 1px solid #E0E0E0;
    border-left: 3px solid #D97757;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    overflow-x: auto;
    margin: 0.8rem 0;
}
.help-content pre code {
    background: transparent;
    color: #2C3E50;
    padding: 0;
}
.help-content blockquote {
    border-left: 4px solid #D97757;
    background: #F0F8FB;
    padding: 0.6rem 1rem;
    margin: 0.8rem 0;
    color: #455A64;
    font-style: italic;
}
.help-content hr {
    border: none;
    border-top: 1px solid #E0E0E0;
    margin: 1.5rem 0;
}

/* Tabs do GenOmics — fundo cinza claro com active state azul */
.stTabs [data-baseweb="tab-list"] {
    background: #ECEFF1 !important;
    border: 1px solid #E0E0E0 !important;
    border-radius: 6px !important;
    padding: 4px !important;
    gap: 2px !important;
    margin-bottom: 0.5rem !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border-radius: 4px !important;
    color: #455A64 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    background-color: #D97757 !important;
    color: white !important;
    box-shadow: 0 2px 4px rgba(217,119,87,0.25);
}

/* Glossario — busca e tabela */
.glossario-search input {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}
</style>
"""

HISTORICO_CSS = """
<style>
.lilo-history-list { margin: 0 0 8px 0; padding: 0; }
.lilo-history-item {
    display: flex; align-items: center;
    padding: 4px 8px; margin: 1px 0;
    border-radius: 8px; cursor: pointer;
    color: var(--lilo-text-dim, #73705F);
    font-size: 0.86rem; line-height: 1.3;
    transition: background 0.15s ease, color 0.15s ease;
    text-decoration: none;
}
.lilo-history-item:hover {
    background: rgba(61,57,41,0.06);
    color: var(--lilo-text, #3D3929);
}
.lilo-history-item.active {
    background: var(--lilo-accent-soft, #F5E8E1);
    color: var(--lilo-accent-dark, #C96442); font-weight: 600;
}
.lilo-history-item .dot { opacity: 0.55; margin-right: 6px; }
.lilo-progress-bar {
    height: 4px; background: rgba(61,57,41,0.10);
    border-radius: 2px; overflow: hidden; margin: 4px 0 8px 0;
}
.lilo-progress-bar > div {
    height: 100%; background: var(--lilo-accent, #D97757);
}
</style>
    """

WELCOME_CSS = """
<style>
.lilo-welcome { text-align:center; max-width:720px; margin:6vh auto 1rem auto; }
.lilo-welcome .lw-logo { font-size:2.6rem; }
.lilo-welcome h1 {
    font-family: var(--lilo-serif, Georgia, serif) !important;
    font-size:2rem !important; font-weight:600; color:var(--lilo-text,#3D3929) !important;
    border:none !important; margin:.4rem 0 .2rem 0 !important;
}
.lilo-welcome .lw-sub {
    color:var(--lilo-text-dim,#73705F); font-size:1rem; line-height:1.6;
    margin:0 auto 1.6rem auto; max-width:620px;
}
.lilo-welcome .lw-sub b { color:var(--lilo-accent-dark,#C96442); }
.lw-cards {
    display:grid; grid-template-columns:repeat(2,1fr); gap:12px;
    text-align:left; margin:0 auto;
}
.lwc {
    background:var(--lilo-bg-card,#fff); border:1px solid var(--lilo-border,#E3E1D7);
    border-radius:12px; padding:12px 14px; transition:border-color .15s ease;
}
.lwc:hover { border-color:var(--lilo-accent,#D97757); }
.lwc b { display:block; color:var(--lilo-text,#3D3929); font-size:.92rem; margin-bottom:3px; }
.lwc span { color:var(--lilo-text-dim,#73705F); font-size:.82rem; line-height:1.45; }
.lw-hint { color:var(--lilo-text-dim,#73705F); font-size:.85rem; margin-top:1.4rem; }
</style>
<div class="lilo-welcome">
  <div class="lw-logo">🧬</div>
  <h1>Olá! Eu sou o LILO</h1>
  <div class="lw-sub">Seu orquestrador de IA local sobre Ollama. Pergunte em
    linguagem natural — no modo <b>Auto</b> eu escolho o melhor especialista pela
    semântica e, se a tarefa exigir, <b>encadeio vários em sequência</b>.</div>
  <div class="lw-cards">
    <div class="lwc"><b>🔎 Pesquisa</b><span>PubMed, OpenAlex, Europe PMC, Google Books, arXiv, Crossref, Wikipedia…</span></div>
    <div class="lwc"><b>📊 Análise</b><span>Estatística (Prism), SQL e dados tabulares</span></div>
    <div class="lwc"><b>📄 Documentos</b><span>Sumarização de PDFs científicos</span></div>
    <div class="lwc"><b>🛠️ Sistema</b><span>Arquivos e shell local (allow-list)</span></div>
  </div>
  <div class="lw-hint">Digite abaixo para começar — ou use <b>/</b> para skills.</div>
</div>
            """

