from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from upload_routes import router as upload_router
from dashboard_routes import router as dashboard_router
from planning_routes import router as planning_router


app = FastAPI(
    title="JGM SmartPlanning - Wave 1",
    description="Backend inicial do projeto SmartPlanning da JGM.",
    version="0.1",
)

# --------------------------------------------------------------------
# CORS – permite o frontend React acessar a API
# --------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # em produção você pode restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
# ROTAS
# --------------------------------------------------------------------
app.include_router(upload_router)
app.include_router(dashboard_router)
app.include_router(planning_router)   # <- novo router do Planning Board IA™


@app.get("/")
def root():
    return {"message": "SmartPlanning API - Online"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
