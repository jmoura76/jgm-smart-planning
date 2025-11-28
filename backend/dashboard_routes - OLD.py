from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, date
import pandas as pd
import numpy as np
import os
import re

from ia_engine import (
    score_material_criticidade,
    score_order_criticidade,
    score_recurso_criticidade,
)

router = APIRouter()

# --------------------------------------------------------------------
# CONFIGURAÇÃO DE ARQUIVOS
# --------------------------------------------------------------------
DATA_DIR = "../data"
MD04_FILENAME = "md04_uploaded.xlsx"
COHV_FILENAME = "cohv_uploaded.xlsx"
CENTROS_FILENAME = "centros_uploaded.csv"  # gerado no upload de Centros de Trabalho


# --------------------------------------------------------------------
# MODELOS DE RESPOSTA (ENVIADOS PARA O FRONTEND)
# --------------------------------------------------------------------


class KpiSummary(BaseModel):
    # KPIs de materiais (estoque / cobertura)
    total_materiais: int
    materiais_risco: int
    perc_materiais_risco: float
    materiais_excesso: int
    perc_materiais_excesso: float

    # KPIs de ordens (COHV)
    total_ops: int
    ops_atrasadas: int
    perc_ops_atrasadas: float


class CriticalItem(BaseModel):
    material: str
    cobertura_dias: float | None
    criticidade_score: float | None = None


class CriticalOrder(BaseModel):
    ordem: str
    material: str | None
    data_fim: str
    status: str
    criticidade_score: float | None = None


class CapacitySummary(BaseModel):
    total_recursos: int
    recursos_abaixo_90: int
    recursos_90_100: int
    recursos_acima_100: int
    utilizacao_media: float | None


class CriticalResource(BaseModel):
    recurso: str
    planta: str | None = None
    utilizacao_pct: float
    criticidade_score: float | None = None


class DashboardSummary(BaseModel):
    generated_at: str
    kpis: KpiSummary
    criticos: list[CriticalItem]
    ordens_criticas: list[CriticalOrder]
    capacidade: CapacitySummary | None = None
    recursos_criticos: list[CriticalResource] = []


class Insight(BaseModel):
    tipo: str         # "material", "ordem", "recurso", "sistema"
    severidade: str   # "alto", "medio", "baixo", "info"
    titulo: str
    descricao: str
    sugestao: str


class InsightsResponse(BaseModel):
    generated_at: str
    insights: list[Insight]


# --------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE CARGA
# --------------------------------------------------------------------


def _load_md04_df() -> pd.DataFrame:
    """Carrega o MD04 salvo no data/, tratando NaN."""
    file_path = os.path.join(DATA_DIR, MD04_FILENAME)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=400, detail="Arquivo MD04 ainda não foi carregado."
        )

    df = pd.read_excel(file_path)
    df = df.replace({np.nan: None})
    return df


def _load_cohv_df() -> pd.DataFrame | None:
    """Carrega o COHV salvo no data/. Se não existir, retorna None (para não quebrar o dashboard)."""
    file_path = os.path.join(DATA_DIR, COHV_FILENAME)
    if not os.path.exists(file_path):
        return None

    df = pd.read_excel(file_path)
    df = df.replace({np.nan: None})
    return df


def _load_centros_df() -> pd.DataFrame | None:
    """
    Carrega o arquivo de Centros de Trabalho salvo como CSV.
    Se não conseguir ler (encoding estranho, etc.), retorna None
    para não quebrar o dashboard.
    """
    file_path = os.path.join(DATA_DIR, CENTROS_FILENAME)
    if not os.path.exists(file_path):
        return None

    # Tentativas progressivas de leitura, com encodings diferentes
    encodings_to_try = ["latin1", "cp1252", "utf-8"]

    for enc in encodings_to_try:
        # 1ª tentativa: separador flexível ; ou , com engine=python
        try:
            df = pd.read_csv(file_path, sep=";|,", engine="python", encoding=enc)
            df = df.replace({np.nan: None})
            return df
        except Exception:
            pass

        # 2ª tentativa: leitura padrão com esse encoding
        try:
            df = pd.read_csv(file_path, encoding=enc)
            df = df.replace({np.nan: None})
            return df
        except Exception:
            pass

    # Se nada funcionar, não travar o resto do dashboard
    return None


# --------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE TRATAMENTO
# --------------------------------------------------------------------


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    """
    Tenta localizar uma coluna usando possíveis nomes (ignora acentos, espaços e maiúsculas).
    Ex: ['CoberEstq', 'Cobertura', 'CoberEstq.']
    """
    normalized: dict[str, str] = {}

    for col in df.columns:
        if col is None:
            continue  # ignora colunas sem nome
        col_str = str(col)
        key = re.sub(r"[^a-z0-9]", "", col_str.lower())
        normalized[key] = col_str

    for cand in candidates:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        if key in normalized:
            return normalized[key]

    raise HTTPException(
        status_code=500,
        detail=(
            f"Não encontrei nenhuma coluna compatível com {candidates} no arquivo. "
            f"Colunas atuais: {list(df.columns)}"
        ),
    )


def _normalize_centros_header(df: pd.DataFrame) -> pd.DataFrame:
    """
    Alguns arquivos de Centros de Trabalho chegam com as colunas 'Unnamed: 0'...'Unnamed: N'
    e a primeira linha contém o cabeçalho real ('Recurso', 'Descrição breve', etc).

    Esta função detecta esse padrão e transforma a primeira linha em cabeçalho.
    """
    if df is None or df.empty:
        return df

    if all(str(c).startswith("Unnamed") for c in df.columns):
        first_row = df.iloc[0]

        if any(
            str(v).strip().lower()
            in ["recurso", "work center", "centro de trabalho"]
            for v in first_row.values
            if pd.notna(v)
        ):
            df = df.copy()
            df.columns = first_row  # primeira linha vira cabeçalho
            df = df[1:].reset_index(drop=True)

    return df


# --------------------------------------------------------------------
# LÓGICA DE KPI DE ESTOQUE / COBERTURA (MD04)
# --------------------------------------------------------------------


def _build_material_kpis(df_md04: pd.DataFrame):
    col_material = _find_column(df_md04, ["Material", "material"])
    col_cobertura = _find_column(
        df_md04, ["CoberEstq", "CoberEstq.", "Cobertura", "Coverage"]
    )

    # total bruto (linhas de material)
    total_bruto = int(len(df_md04))

    df_valid = df_md04[[col_material, col_cobertura]].copy()
    df_valid[col_cobertura] = pd.to_numeric(df_valid[col_cobertura], errors="coerce")
    df_valid = df_valid.dropna(subset=[col_cobertura])

    total = int(len(df_valid))
    if total == 0:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma linha válida de cobertura encontrada no MD04.",
        )

    materiais_sem_cobertura = max(0, total_bruto - total)

    # Risco: cobertura < 7 dias
    df_risco = df_valid[df_valid[col_cobertura] < 7]
    materiais_risco = int(len(df_risco))

    # Excesso: cobertura > 45 dias
    df_excesso = df_valid[df_valid[col_cobertura] > 45]
    materiais_excesso = int(len(df_excesso))

    perc_risco = round(materiais_risco / total * 100, 2)
    perc_excesso = round(materiais_excesso / total * 100, 2)

    # Top 10 materiais mais críticos (menor cobertura)
    df_top = df_valid.sort_values(by=col_cobertura, ascending=True).head(10)

    criticos: list[CriticalItem] = []
    for _, row in df_top.iterrows():
        cobertura_val = float(row[col_cobertura])
        # Monta uma Series com o nome de coluna esperado pelo motor de IA
        row_for_score = pd.Series({"Cobertura (dias)": cobertura_val})
        score = score_material_criticidade(row_for_score)

        criticos.append(
            CriticalItem(
                material=str(row[col_material]),
                cobertura_dias=cobertura_val,
                criticidade_score=score,
            )
        )

    return {
        "total_materiais": total,
        "materiais_risco": materiais_risco,
        "perc_materiais_risco": perc_risco,
        "materiais_excesso": materiais_excesso,
        "perc_materiais_excesso": perc_excesso,
        "materiais_sem_cobertura": materiais_sem_cobertura,
        "criticos": criticos,
    }


# --------------------------------------------------------------------
# LÓGICA DE KPI DE ORDENS (COHV)
# --------------------------------------------------------------------


def _build_orders_kpis(df_cohv: pd.DataFrame | None):
    if df_cohv is None or df_cohv.empty:
        return {
            "total_ops": 0,
            "ops_atrasadas": 0,
            "perc_ops_atrasadas": 0.0,
            "ordens_criticas": [],
        }

    col_ordem = _find_column(df_cohv, ["Ordem", "Ordem de produção", "Order"])
    col_material = _find_column(
        df_cohv, ["Material", "Material da ordem", "Matéria"]
    )
    col_data_fim = _find_column(
        df_cohv,
        [
            "Data de conclusão base",
            "D.conclusão base",
            "Data fim",
            "Finish date",
        ],
    )
    col_status = _find_column(
        df_cohv, ["Status do sistema", "Status do sist.", "Status"]
    )

    df_valid = df_cohv[[col_ordem, col_material, col_data_fim, col_status]].copy()

    df_valid[col_data_fim] = pd.to_datetime(
        df_valid[col_data_fim], errors="coerce", dayfirst=True
    )
    df_valid = df_valid.dropna(subset=[col_data_fim])

    total_ops = int(len(df_valid))
    if total_ops == 0:
        return {
            "total_ops": 0,
            "ops_atrasadas": 0,
            "perc_ops_atrasadas": 0.0,
            "ordens_criticas": [],
        }

    today = date.today()

    def is_atrasada(row):
        data_fim: datetime = row[col_data_fim]
        status_str = str(row[col_status]) if row[col_status] is not None else ""
        return (
            data_fim.date() < today
            and "TECO" not in status_str
            and "CLSD" not in status_str
        )

    df_valid["atrasada"] = df_valid.apply(is_atrasada, axis=1)
    df_atrasadas = df_valid[df_valid["atrasada"] == True]

    ops_atrasadas = int(len(df_atrasadas))
    perc_ops_atrasadas = round(ops_atrasadas / total_ops * 100, 2)

    df_top_ord = df_atrasadas.sort_values(by=col_data_fim, ascending=True).head(10)

    ordens_criticas: list[CriticalOrder] = []
    for _, row in df_top_ord.iterrows():
        data_fim_val: datetime = row[col_data_fim]
        data_fim_date = data_fim_val.date()
        data_fim_str = data_fim_date.strftime("%Y-%m-%d")
        status_str = str(row[col_status]) if row[col_status] is not None else ""

        # calcula DIAS de atraso para enviar ao motor de IA
        dias_atraso = (today - data_fim_date).days
        if dias_atraso < 0:
            dias_atraso = 0

        # Monta uma Series parecida com a estrutura de uma ordem
        row_for_score = row.copy()
        row_for_score["Dias Atraso"] = dias_atraso
        # usa o motor IA (ordens) – material_crit_map fica None por enquanto
        score = score_order_criticidade(row_for_score)

        ordens_criticas.append(
            CriticalOrder(
                ordem=str(row[col_ordem]),
                material=str(row[col_material])
                if row[col_material] is not None
                else None,
                data_fim=data_fim_str,
                status=status_str,
                criticidade_score=score,
            )
        )

    return {
        "total_ops": total_ops,
        "ops_atrasadas": ops_atrasadas,
        "perc_ops_atrasadas": perc_ops_atrasadas,
        "ordens_criticas": ordens_criticas,
    }


# --------------------------------------------------------------------
# LÓGICA DE KPI DE CAPACIDADE (CENTROS DE TRABALHO)
# --------------------------------------------------------------------


def _build_capacity_kpis(
    df_centros: pd.DataFrame | None,
) -> tuple[CapacitySummary | None, list[CriticalResource]]:
    """
    Gera KPIs de capacidade a partir do arquivo de Centros de Trabalho.
    - Se NÃO houver arquivo => usa um conjunto DEMO de recursos críticos (Joyson).
    - Se houver arquivo => calcula tudo baseado no CSV.
    """

    # ----------------------------------------------------------
    # 1) CENÁRIO DEMO: sem arquivo, usamos recursos fictícios
    # ----------------------------------------------------------
    if df_centros is None or df_centros.empty:
        demo_resources = [
            {"recurso": "3101-LINHA AIRBAG-01", "planta": "3101", "util": 118.0},
            {"recurso": "3101-LINHA AIRBAG-02", "planta": "3101", "util": 105.0},
            {"recurso": "3101-LINHA VOLANTE-01", "planta": "3101", "util": 97.0},
            {"recurso": "3101-LINHA VOLANTE-02", "planta": "3101", "util": 92.0},
            {"recurso": "3101-COSTURA CINTO-01", "planta": "3101", "util": 88.0},
            {"recurso": "3101-CORTE FITA-01", "planta": "3101", "util": 83.0},
        ]

        total_recursos = len(demo_resources)
        recursos_abaixo_90 = sum(1 for r in demo_resources if r["util"] < 90)
        recursos_90_100 = sum(1 for r in demo_resources if 90 <= r["util"] <= 100)
        recursos_acima_100 = sum(1 for r in demo_resources if r["util"] > 100)
        utilizacao_media = round(
            sum(r["util"] for r in demo_resources) / total_recursos, 1
        )

        recursos_criticos: list[CriticalResource] = []
        for r in demo_resources:
            score = score_recurso_criticidade(
                pd.Series({"Utilização (%)": r["util"]})
            )
            recursos_criticos.append(
                CriticalResource(
                    recurso=r["recurso"],
                    planta=r["planta"],
                    utilizacao_pct=r["util"],
                    criticidade_score=score,
                )
            )

        capacidade_summary = CapacitySummary(
            total_recursos=total_recursos,
            recursos_abaixo_90=recursos_abaixo_90,
            recursos_90_100=recursos_90_100,
            recursos_acima_100=recursos_acima_100,
            utilizacao_media=utilizacao_media,
        )

        return capacidade_summary, recursos_criticos

    # ----------------------------------------------------------
    # 2) CENÁRIO REAL: temos arquivo de Centros de Trabalho
    # ----------------------------------------------------------
    df_centros = _normalize_centros_header(df_centros)
    if df_centros is None or df_centros.empty:
        return None, []

    col_recurso = _find_column(
        df_centros, ["Recurso", "Work Center", "Centro de trabalho"]
    )

    try:
        col_planta = _find_column(
            df_centros, ["Unidade gerencial", "Centro", "Plant"]
        )
    except HTTPException:
        col_planta = None

    col_util = _find_column(
        df_centros,
        [
            "Grau utilização em %",
            "Utilização %",
            "Utilização em %",
            "Capacity usage %",
        ],
    )

    cols = [col_recurso, col_util] + ([col_planta] if col_planta else [])
    df = df_centros[cols].copy()

    df[col_util] = pd.to_numeric(df[col_util], errors="coerce")
    df = df.dropna(subset=[col_util])

    if df.empty:
        return None, []

    total_recursos = int(len(df))
    recursos_abaixo_90 = int((df[col_util] < 90).sum())
    recursos_90_100 = int(((df[col_util] >= 90) & (df[col_util] <= 100)).sum())
    recursos_acima_100 = int((df[col_util] > 100).sum())

    utilizacao_media_val = df[col_util].mean()
    utilizacao_media = (
        round(float(utilizacao_media_val), 1)
        if pd.notna(utilizacao_media_val)
        else None
    )

    df_top = df.sort_values(by=col_util, ascending=False).head(10)

    recursos_criticos: list[CriticalResource] = []
    for _, row in df_top.iterrows():
        util_val = float(row[col_util])
        score = score_recurso_criticidade(
            pd.Series({"Utilização (%)": util_val})
        )
        recursos_criticos.append(
            CriticalResource(
                recurso=str(row[col_recurso]),
                planta=(
                    str(row[col_planta])
                    if col_planta and row.get(col_planta) is not None
                    else None
                ),
                utilizacao_pct=util_val,
                criticidade_score=score,
            )
        )

    capacidade_summary = CapacitySummary(
        total_recursos=total_recursos,
        recursos_abaixo_90=recursos_abaixo_90,
        recursos_90_100=recursos_90_100,
        recursos_acima_100=recursos_acima_100,
        utilizacao_media=utilizacao_media,
    )

    return capacidade_summary, recursos_criticos


# --------------------------------------------------------------------
# GERADOR DE INSIGHTS IA ENGINE™
# --------------------------------------------------------------------


def _build_insights(
    materiais_info: dict,
    ordens_info: dict,
    capacidade_summary: CapacitySummary | None,
    recursos_criticos: list[CriticalResource],
) -> list[Insight]:
    """
    Converte KPIs num conjunto de insights em linguagem de negócio
    para alimentar o Painel de Alertas IA na Visão Geral.
    """
    insights: list[Insight] = []

    # ---------- Materiais (estoque / cobertura) ----------
    total_mat = materiais_info.get("total_materiais", 0)
    mats_risco = materiais_info.get("materiais_risco", 0)
    mats_excesso = materiais_info.get("materiais_excesso", 0)
    perc_risco = materiais_info.get("perc_materiais_risco", 0.0)
    perc_excesso = materiais_info.get("perc_materiais_excesso", 0.0)
    mats_sem_cob = materiais_info.get("materiais_sem_cobertura", 0)

    if mats_risco > 0:
        severidade = "alto" if perc_risco >= 2.0 else "medio"
        insights.append(
            Insight(
                tipo="material",
                severidade=severidade,
                titulo="Materiais em risco de ruptura",
                descricao=(
                    f"{mats_risco} de {total_mat} materiais monitorados "
                    f"estão com cobertura menor que 7 dias."
                ),
                sugestao=(
                    "Priorizar esses itens na reunião de MRP, revisar parâmetros de estoque "
                    "de segurança e verificar possíveis atrasos de fornecedores."
                ),
            )
        )

    if mats_excesso > 0:
        severidade = "medio" if perc_excesso >= 10.0 else "baixo"
        insights.append(
            Insight(
                tipo="material",
                severidade=severidade,
                titulo="Materiais com estoque em excesso",
                descricao=(
                    f"{mats_excesso} materiais com cobertura acima de 45 dias, "
                    "indicando capital empatado em estoque."
                ),
                sugestao=(
                    "Rever política de abastecimento, ajustar lotes mínimos e avaliar "
                    "redução de compras futuras para esses itens."
                ),
            )
        )

    if mats_sem_cob > 0:
        insights.append(
            Insight(
                tipo="sistema",
                severidade="medio",
                titulo="Materiais sem cobertura calculada no MD04",
                descricao=(
                    f"{mats_sem_cob} materiais aparecem no MD04 sem valor de cobertura válido."
                ),
                sugestao=(
                    "Verificar parametrização de MRP, dados mestre de material e estoque "
                    "para garantir cálculo de cobertura correto antes das próximas análises."
                ),
            )
        )

    # ---------- Ordens de Produção ----------
    total_ops = ordens_info.get("total_ops", 0)
    ops_atrasadas = ordens_info.get("ops_atrasadas", 0)
    perc_ops_atrasadas = ordens_info.get("perc_ops_atrasadas", 0.0)
    ordens_criticas = ordens_info.get("ordens_criticas", [])

    if ops_atrasadas > 0:
        severidade = "alto" if perc_ops_atrasadas >= 5.0 else "medio"
        insights.append(
            Insight(
                tipo="ordem",
                severidade=severidade,
                titulo="Ordens de produção em atraso",
                descricao=(
                    f"{ops_atrasadas} de {total_ops} ordens estão atrasadas "
                    f"({perc_ops_atrasadas:.2f}% da carteira)."
                ),
                sugestao=(
                    "Repriorizar fila de produção, revisar restrições de capacidade e "
                    "avaliar necessidade de turnos extras ou realocação de recursos."
                ),
            )
        )

    qtd_ordens_criticas = len(ordens_criticas)
    if qtd_ordens_criticas > 0:
        insights.append(
            Insight(
                tipo="ordem",
                severidade="alto",
                titulo="TOP ordens críticas por atraso",
                descricao=(
                    f"As {qtd_ordens_criticas} ordens mais críticas apresentam maior "
                    "criticidade IA, combinando atraso e importância do material."
                ),
                sugestao=(
                    "Analisar essas ordens na reunião diária de PCP (D-1), focando em "
                    "liberação de materiais, ajustes de sequência e confirmação com clientes."
                ),
            )
        )

    # ---------- Recursos / Capacidade ----------
    if capacidade_summary is not None:
        rec_monitorados = capacidade_summary.total_recursos
        rec_acima_100 = capacidade_summary.recursos_acima_100
        util_media = capacidade_summary.utilizacao_media

        if rec_acima_100 > 0:
            insights.append(
                Insight(
                    tipo="recurso",
                    severidade="alto",
                    titulo="Recursos em sobrecarga",
                    descricao=(
                        f"{rec_acima_100} de {rec_monitorados} recursos estão com utilização "
                        "acima de 100% da capacidade declarada."
                    ),
                    sugestao=(
                        "Avaliar redistribuição de carga entre centros alternativos, "
                        "troca de roteiros ou ajuste temporário de capacidade (hora extra, turnos)."
                    ),
                )
            )

        if util_media is not None and util_media > 0:
            sev = "medio" if 85 <= util_media <= 95 else "info"
            insights.append(
                Insight(
                    tipo="recurso",
                    severidade=sev,
                    titulo="Visão geral da utilização de capacidade",
                    descricao=(
                        f"A utilização média dos recursos está em {util_media:.1f}%."
                    ),
                    sugestao=(
                        "Usar essa visão como referência na reunião S&OP/MPS para balancear "
                        "demanda e capacidade nas próximas semanas."
                    ),
                )
            )

    # Insight rápido baseado no recurso mais crítico (se existir)
    if recursos_criticos:
        recurso_top = recursos_criticos[0]
        insights.append(
            Insight(
                tipo="recurso",
                severidade="alto",
                titulo=f"Recurso gargalo: {recurso_top.recurso}",
                descricao=(
                    f"O recurso {recurso_top.recurso} na planta "
                    f"{recurso_top.planta or '-'} está com {recurso_top.utilizacao_pct:.1f}% de utilização."
                ),
                sugestao=(
                    "Verificar fila de ordens nesse recurso, avaliar possibilidade de "
                    "ativar centros alternativos e revisar sequência de produção."
                ),
            )
        )

    if not insights:
        # fallback para não retornar lista vazia
        insights.append(
            Insight(
                tipo="sistema",
                severidade="info",
                titulo="Nenhum alerta crítico identificado",
                descricao=(
                    "Os principais indicadores de materiais, ordens e recursos estão dentro "
                    "dos limites definidos para o dia."
                ),
                sugestao=(
                    "Manter o monitoramento diário e ajustar parâmetros de MRP e capacidade "
                    "conforme a política da Joyson."
                ),
            )
        )

    return insights


# --------------------------------------------------------------------
# ENDPOINT PRINCIPAL DO DASHBOARD
# --------------------------------------------------------------------


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    # MD04 é obrigatório
    df_md04 = _load_md04_df()
    materiais_info = _build_material_kpis(df_md04)

    # COHV é opcional
    df_cohv = _load_cohv_df()
    ordens_info = _build_orders_kpis(df_cohv)

    # Centros de Trabalho (capacidade) também opcional
    df_centros = _load_centros_df()
    capacidade_summary, recursos_criticos = _build_capacity_kpis(df_centros)

    kpis = KpiSummary(
        total_materiais=materiais_info["total_materiais"],
        materiais_risco=materiais_info["materiais_risco"],
        perc_materiais_risco=materiais_info["perc_materiais_risco"],
        materiais_excesso=materiais_info["materiais_excesso"],
        perc_materiais_excesso=materiais_info["perc_materiais_excesso"],
        total_ops=ordens_info["total_ops"],
        ops_atrasadas=ordens_info["ops_atrasadas"],
        perc_ops_atrasadas=ordens_info["perc_ops_atrasadas"],
    )

    return DashboardSummary(
        generated_at=datetime.utcnow().isoformat() + "Z",
        kpis=kpis,
        criticos=materiais_info["criticos"],
        ordens_criticas=ordens_info["ordens_criticas"],
        capacidade=capacidade_summary,
        recursos_criticos=recursos_criticos,
    )


# --------------------------------------------------------------------
# ENDPOINT DE INSIGHTS AVANÇADOS IA ENGINE™
# --------------------------------------------------------------------


@router.get("/dashboard/insights", response_model=InsightsResponse)
def get_dashboard_insights():
    """
    Endpoint específico para o Painel de Alertas IA.
    Gera insights em linguagem de negócios com base nos mesmos KPIs usados na Visão Geral.
    """
    df_md04 = _load_md04_df()
    materiais_info = _build_material_kpis(df_md04)

    df_cohv = _load_cohv_df()
    ordens_info = _build_orders_kpis(df_cohv)

    df_centros = _load_centros_df()
    capacidade_summary, recursos_criticos = _build_capacity_kpis(df_centros)

    insights = _build_insights(
        materiais_info=materiais_info,
        ordens_info=ordens_info,
        capacidade_summary=capacidade_summary,
        recursos_criticos=recursos_criticos,
    )

    return InsightsResponse(
        generated_at=datetime.utcnow().isoformat() + "Z",
        insights=insights,
    )
