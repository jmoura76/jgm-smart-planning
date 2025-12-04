# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .upload_routes import router as upload_router
from .dashboard_routes import router as dashboard_router
from .planning_routes import router as planning_router

# Tenta importar o router de ia_insights, se existir
try:
    from .ia_insights import router as ia_insights_router  # type: ignore
    HAS_IA_INSIGHTS = True
except Exception:
    ia_insights_router = None
    HAS_IA_INSIGHTS = False


app = FastAPI(
    title="JGM SmartPlanning API",
    version="1.0.0",
    description="Backend oficial do projeto SmartPlanning™ da JGM.",
)

# --------------------------------------------------------------------
# CORS – libera acesso para o frontend (Amplify) e uso local
# --------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
    "https://main.d2emdliuimy7ux.amplifyapp.com",     # frontend no Amplify
    "https://jgm-smartplanning-api.onrender.com",      # backend no Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
# Rotas básicas
# --------------------------------------------------------------------


@app.get("/health")
def health_check():
    """Endpoint simples de saúde, usado pelo Render e para testes rápidos."""
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "message": "JGM SmartPlanning API – backend oficial da JGM.",
        "docs_url": "/docs",
    }


# --------------------------------------------------------------------
# Inclusão dos módulos de rotas
# --------------------------------------------------------------------

# Upload de arquivos (MD04, COHV, Centros, EDI)
app.include_router(upload_router, prefix="/upload", tags=["upload"])

# Dashboard principal + Capacity IA™
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Planejamento IA (Planning Board, Pegging, etc.)
app.include_router(planning_router, prefix="/planning", tags=["planning"])

# Painel de Insights IA (IA Engine™) – só se o router existir
if HAS_IA_INSIGHTS and ia_insights_router is not None:
    app.include_router(ia_insights_router, prefix="/ia", tags=["ia"])
