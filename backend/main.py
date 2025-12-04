from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers do projeto (imports relativos, pois o módulo é backend.main)
from .upload_routes import router as upload_router
from .dashboard_routes import router as dashboard_router
from .planning_routes import router as planning_router

app = FastAPI(
    title="JGM SmartPlanning API",
    description="Backend oficial do projeto SmartPlanning™ da JGM.",
    version="1.0.0",
)

# ----------------------------------------------------------------------
# CORS – necessário para o React consumir a API
# ----------------------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://main.d2emdliuimy7ux.amplifyapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# HEALTHCHECK – importante p/ Render e CI/CD
# ----------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ----------------------------------------------------------------------
# ROTAS OFICIAIS DO PROJETO
# ----------------------------------------------------------------------
app.include_router(upload_router, prefix="/upload")
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(planning_router, prefix="/planning")


# ----------------------------------------------------------------------
# ROOT – teste rápido
# ----------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "SmartPlanning API - Online"}
