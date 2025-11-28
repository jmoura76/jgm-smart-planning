from fastapi import APIRouter, UploadFile, File
import pandas as pd
import numpy as np
import os

router = APIRouter()

DATA_DIR = "../data"   # Onde salvamos os arquivos da Wave 1

# Garantir pasta data/
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def save_and_read_excel(upload_file: UploadFile, name: str):
    """Salva o arquivo recebido e retorna um dataframe pandas (preview) em formato JSON-safe."""
    file_path = os.path.join(DATA_DIR, f"{name}")

    # salvar arquivo
    with open(file_path, "wb") as f:
        content = upload_file.file.read()
        f.write(content)

    # ler arquivo
    if name.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    elif name.endswith(".csv"):
        df = pd.read_csv(file_path, sep=";|,", engine="python")
    else:
        raise ValueError("Formato de arquivo não suportado")

    # substituir NaN por None para o JSON não quebrar
    df = df.replace({np.nan: None})

    # devolver só as 10 primeiras linhas como preview
    return df.head(10).to_dict(orient="records")


# ================= ROTAS ======================

@router.post("/upload/md04")
async def upload_md04(file: UploadFile = File(...)):
    rows = save_and_read_excel(file, "md04_uploaded.xlsx")
    return {"status": "MD04 recebido", "preview": rows}


@router.post("/upload/cohv")
async def upload_cohv(file: UploadFile = File(...)):
    rows = save_and_read_excel(file, "cohv_uploaded.xlsx")
    return {"status": "COHV recebido", "preview": rows}


@router.post("/upload/edi")
async def upload_edi(file: UploadFile = File(...)):
    rows = save_and_read_excel(file, "edi_uploaded.xlsx")
    return {"status": "EDI recebido", "preview": rows}


@router.post("/upload/centro_trabalho")
async def upload_centro_trabalho(file: UploadFile = File(...)):
    rows = save_and_read_excel(file, "centros_uploaded.xlsx")
    return {"status": "Centros de Trabalho recebido", "preview": rows}
