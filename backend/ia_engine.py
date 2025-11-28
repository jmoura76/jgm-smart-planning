# ia_engine.py
"""
IA Engine™ – módulo de inteligência do JGM SmartPlanning™

Responsabilidades principais:
- Calcular criticidade de materiais, ordens e recursos
- Gerar resumos consolidados para o dashboard
- Gerar TOP 10 críticos
- Simular o Planning Board IA™ para um material específico
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Utilitários genéricos
# ---------------------------------------------------------------------------

def _to_date(value) -> Optional[date]:
    """Converte string/objeto em date, retornando None se não conseguir."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y.%m.%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _safe_get(row: pd.Series, candidates: Sequence[str], default=None):
    """
    Recupera o primeiro campo existente na Series dentre os nomes em candidates.
    Ignora NaN. Se nada existir, retorna default.
    """
    for c in candidates:
        if c in row.index:
            v = row[c]
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                return v
    return default


def _first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ---------------------------------------------------------------------------
# Modelos simples
# ---------------------------------------------------------------------------

@dataclass
class PlanningRecommendation:
    titulo: str
    descricao: str
    tipo: str  # "primary", "warning", "danger", etc.


@dataclass
class PlanningBoardResult:
    semanas: List[str]
    demanda: List[float]
    estoque_natural: List[float]
    estoque_pos_ia: List[float]
    producao_ia: List[float]
    rupturas_previstas: int
    crit_ia: float
    cobertura_atual_dias: float
    recomendacoes: List[PlanningRecommendation]


# ---------------------------------------------------------------------------
# 1) Criticidade de Materiais
# ---------------------------------------------------------------------------

def score_material_criticidade(row: pd.Series) -> float:
    """
    Calcula criticidade IA do material (0–100).

    Lógica base:
    - Cobertura <= 0 dias  -> 100 (já em ruptura / atraso)
    - 0 < cobertura <= 7   -> muito crítico (90–100)
    - 7 < cobertura <= 15  -> crítico (70–90)
    - 15 < cobertura <= 45 -> ok (30–70)
    - > 45 dias            -> excesso / baixo risco (0–30)
    """
    cobertura = _safe_get(
        row,
        ["Cobertura (dias)", "cobertura_dias", "Cobertura_dias", "coverage_days"],
        default=None,
    )

    try:
        cobertura = float(cobertura)
    except (TypeError, ValueError):
        return 50.0

    if cobertura <= 0:
        return 100.0

    if cobertura <= 7:
        score = 90 + (7 - cobertura) * (10 / 7.0)
    elif cobertura <= 15:
        score = 70 + (15 - cobertura) * (20 / 8.0)
    elif cobertura <= 45:
        score = 30 + (45 - cobertura) * (40 / 30.0)
    else:
        score = max(0.0, 30.0 - (cobertura - 45) * 0.3)

    return float(round(max(0.0, min(100.0, score)), 1))


def classify_materials(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    df2["Criticidade_IA"] = df2.apply(score_material_criticidade, axis=1)
    return df2


def top_n_materiais_criticos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if "Criticidade_IA" not in df.columns:
        df = classify_materials(df)

    cobertura_col = _first_existing_column(
        df, ["Cobertura (dias)", "cobertura_dias", "Cobertura_dias", "coverage_days"]
    )

    if cobertura_col is None:
        return df.sort_values("Criticidade_IA", ascending=False).head(n)

    return (
        df.sort_values(
            ["Criticidade_IA", cobertura_col],
            ascending=[False, True],
        )
        .head(n)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# 2) Criticidade de Ordens de Produção
# ---------------------------------------------------------------------------

def score_order_criticidade(
    row: pd.Series,
    material_crit_map: Optional[Dict[str, float]] = None,
    hoje: Optional[date] = None,
) -> float:
    """
    Criticidade da OP considerando atraso + criticidade do material.
    """
    if hoje is None:
        hoje = date.today()

    status = str(_safe_get(row, ["Status", "status"], "") or "")
    status_up = status.upper()
    if any(flag in status_up for flag in ("TECO", "CLSD", "CLOSED")):
        return 0.0

    dias_atraso = _safe_get(row, ["Dias Atraso", "dias_atraso", "delay_days"], None)
    if dias_atraso is None:
        data_fim = _safe_get(row, ["Data Fim", "data_fim", "due_date"], None)
        dt = _to_date(data_fim)
        if dt is not None:
            dias_atraso = (hoje - dt).days
        else:
            dias_atraso = 0

    try:
        dias_atraso = int(dias_atraso)
    except (TypeError, ValueError):
        dias_atraso = 0

    if dias_atraso <= 0:
        base = 20.0
    elif dias_atraso <= 3:
        base = 60.0 + dias_atraso * 5.0
    elif dias_atraso <= 10:
        base = 75.0 + (dias_atraso - 3) * 3.0
    else:
        base = 100.0

    material = str(_safe_get(row, ["Material", "material"], "") or "")
    mat_crit = 0.0
    if material_crit_map and material in material_crit_map:
        mat_crit = material_crit_map[material]

    score = base * 0.6 + mat_crit * 0.4
    return float(round(max(0.0, min(100.0, score)), 1))


def classify_orders(
    df_orders: pd.DataFrame,
    df_materials_with_score: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    mat_map: Optional[Dict[str, float]] = None
    if df_materials_with_score is not None and "Criticidade_IA" in df_materials_with_score.columns:
        id_col = _first_existing_column(
            df_materials_with_score,
            ["Material", "material", "Material ID", "MATNR"],
        )
        if id_col:
            mat_map = df_materials_with_score.set_index(id_col)["Criticidade_IA"].to_dict()

    df2 = df_orders.copy()
    df2["Criticidade_IA"] = df2.apply(
        lambda r: score_order_criticidade(r, material_crit_map=mat_map),
        axis=1,
    )
    return df2


def top_n_ordens_criticas(df_orders: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if "Criticidade_IA" not in df_orders.columns:
        df_orders = classify_orders(df_orders)

    atraso_col = _first_existing_column(df_orders, ["Dias Atraso", "dias_atraso", "delay_days"])

    if atraso_col:
        return (
            df_orders.sort_values(
                ["Criticidade_IA", atraso_col],
                ascending=[False, False],
            )
            .head(n)
            .reset_index(drop=True)
        )

    return (
        df_orders.sort_values("Criticidade_IA", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# 3) Criticidade de Recursos / Capacidade
# ---------------------------------------------------------------------------

def score_recurso_criticidade(row: pd.Series) -> float:
    """Criticidade do recurso baseada na % de utilização."""
    utilizacao = _safe_get(
        row,
        ["Utilização (%)", "Utilizacao (%)", "utilizacao_pct", "Utilization_pct", "UTIL_PCT"],
        default=0,
    )
    try:
        utilizacao = float(utilizacao)
    except (TypeError, ValueError):
        utilizacao = 0.0

    if utilizacao < 70:
        score = 10.0
    elif utilizacao < 90:
        score = 30.0 + (utilizacao - 70) * 1.0
    elif utilizacao <= 100:
        score = 50.0 + (utilizacao - 90) * 2.5
    else:
        score = 75.0 + (utilizacao - 100) * 1.5

    return float(round(max(0.0, min(100.0, score)), 1))


def classify_recursos(df_recursos: pd.DataFrame) -> pd.DataFrame:
    df2 = df_recursos.copy()
    df2["Criticidade_IA"] = df2.apply(score_recurso_criticidade, axis=1)
    return df2


def top_n_recursos_criticos(df_recursos: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if "Criticidade_IA" not in df_recursos.columns:
        df_recursos = classify_recursos(df_recursos)

    util_col = _first_existing_column(
        df_recursos,
        ["Utilização (%)", "Utilizacao (%)", "utilizacao_pct", "Utilization_pct", "UTIL_PCT"],
    )

    if util_col:
        return (
            df_recursos.sort_values(
                ["Criticidade_IA", util_col],
                ascending=[False, False],
            )
            .head(n)
            .reset_index(drop=True)
        )

    return (
        df_recursos.sort_values("Criticidade_IA", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# 4) Resumo consolidado para o Dashboard (Visão Geral)
# ---------------------------------------------------------------------------

def build_dashboard_summary(
    df_materials: pd.DataFrame,
    df_orders: pd.DataFrame,
    df_recursos: pd.DataFrame,
) -> Dict:
    """
    Gera dicionário com os números principais da Visão Geral.
    """

    mats = classify_materials(df_materials)
    orders = classify_orders(df_orders, mats)
    recs = classify_recursos(df_recursos)

    # ---- Materiais ----
    total_mats = len(mats)

    cobertura_col = _first_existing_column(
        mats, ["Cobertura (dias)", "cobertura_dias", "Cobertura_dias", "coverage_days"]
    )
    em_risco = 0
    em_excesso = 0
    if cobertura_col:
        em_risco = int((mats[cobertura_col] < 7).sum())
        em_excesso = int((mats[cobertura_col] > 45).sum())

    mats_alta_crit = int((mats["Criticidade_IA"] >= 80).sum())

    # ---- Ordens ----
    hoje = date.today()
    data_fim_col = _first_existing_column(orders, ["Data Fim", "data_fim", "due_date"])
    atrasadas = 0
    if data_fim_col:
        datas = orders[data_fim_col].apply(_to_date)
        atrasadas = int(datas.apply(lambda d: d is not None and d < hoje).sum())

    ordens_criticas = int((orders["Criticidade_IA"] >= 70).sum())

    # ---- Recursos ----
    util_col = _first_existing_column(
        recs, ["Utilização (%)", "Utilizacao (%)", "utilizacao_pct", "Utilization_pct", "UTIL_PCT"]
    )
    recursos_monitorados = len(recs)
    recursos_sobrecarga = 0
    utilizacao_media = None
    buckets = {"lt_90": 0, "between_90_100": 0, "gt_100": 0}

    if util_col:
        util = recs[util_col].astype(float)
        recursos_sobrecarga = int((util > 100.0).sum())
        utilizacao_media = float(round(util.mean(), 1))
        buckets["lt_90"] = int((util < 90).sum())
        buckets["between_90_100"] = int(((util >= 90) & (util <= 100)).sum())
        buckets["gt_100"] = int((util > 100).sum())

    return {
        "materiais": {
            "total_monitorados": total_mats,
            "em_risco": em_risco,
            "em_excesso": em_excesso,
            "alta_criticidade": mats_alta_crit,
        },
        "ordens": {
            "total": len(orders),
            "atrasadas": atrasadas,
            "alta_criticidade": ordens_criticas,
        },
        "recursos": {
            "monitorados": recursos_monitorados,
            "sobrecarga": recursos_sobrecarga,
            "utilizacao_media": utilizacao_media,
            "buckets_utilizacao": buckets,
        },
    }


# ---------------------------------------------------------------------------
# 5) Planning Board IA™ – simulação simplificada
# ---------------------------------------------------------------------------

def simulate_planning_board_for_material(
    material_row: pd.Series,
    semanas_horizonte: int = 8,
) -> PlanningBoardResult:
    """
    Gera a estrutura de dados para o Planning Board IA™ de um material.
    """

    mat_id = str(
        _safe_get(material_row, ["Material", "material", "Material ID", "MATNR"], default="")
        or ""
    )

    cobertura_dias = _safe_get(
        material_row,
        ["Cobertura (dias)", "cobertura_dias", "Cobertura_dias", "coverage_days"],
        default=-999.9,
    )
    try:
        cobertura_dias = float(cobertura_dias)
    except (TypeError, ValueError):
        cobertura_dias = -999.9

    estoque_atual = _safe_get(
        material_row,
        ["Estoque Atual", "estoque_atual", "Stock", "QTD_ESTOQUE"],
        default=0,
    )
    try:
        estoque_atual = float(estoque_atual)
    except (TypeError, ValueError):
        estoque_atual = 0.0

    consumo_dia = _safe_get(
        material_row,
        ["Consumo Médio Dia", "consumo_medio_dia", "avg_daily_demand"],
        default=None,
    )
    if consumo_dia is not None:
        try:
            consumo_dia = float(consumo_dia)
        except (TypeError, ValueError):
            consumo_dia = None

    if consumo_dia is None or consumo_dia <= 0:
        if cobertura_dias not in (None, 0, -999.9) and estoque_atual > 0:
            consumo_dia = max(1.0, estoque_atual / max(1.0, cobertura_dias))
        else:
            consumo_dia = 25.0  # DEMO

    demanda_semana = consumo_dia * 7.0

    semanas = [f"S+{i}" for i in range(1, semanas_horizonte + 1)]
    demanda = [float(round(demanda_semana, 1)) for _ in semanas]

    estoque_nat: List[float] = []
    estoque_ia: List[float] = []
    producao_ia: List[float] = []

    # Estoque natural – apenas consumo
    estoque = estoque_atual
    for _ in semanas:
        estoque -= demanda_semana
        estoque_nat.append(float(round(estoque, 1)))

    # Estoque com IA – OPs em S+3 e S+5
    estoque = estoque_atual
    rupturas = 0
    for idx, _ in enumerate(semanas):
        prod = 0.0
        if idx in (2, 4):  # S+3 e S+5
            prod = demanda_semana * 2.0

        producao_ia.append(float(round(prod, 1)))

        estoque += prod
        estoque -= demanda_semana
        if estoque < 0:
            rupturas += 1

        estoque_ia.append(float(round(estoque, 1)))

    crit_ia = score_material_criticidade(material_row)

    recs: List[PlanningRecommendation] = []

    if rupturas > 0:
        recs.append(
            PlanningRecommendation(
                titulo=f"Criar OP de {int(demanda_semana * 2)} un. para S+3",
                descricao=(
                    f"Evitar ruptura de estoque prevista a partir da semana S+3 "
                    f"para o material {mat_id}. Ação recomendada ainda nesta semana."
                ),
                tipo="primary",
            )
        )

    recs.append(
        PlanningRecommendation(
            titulo="Rever mix e priorização de demanda",
            descricao=(
                "Demanda projetada acima da média nas semanas S+4 e S+6. "
                "Alinhar com Vendas/Comercial para confirmar picos e ajustar o plano mestre."
            ),
            tipo="warning",
        )
    )

    if cobertura_dias < 0 or crit_ia >= 90:
        recs.append(
            PlanningRecommendation(
                titulo="Avaliar aumento de lote ou antecipação de OP",
                descricao=(
                    "Estoque projetado fica em faixa crítica nas semanas iniciais. "
                    "Planejar produção adicional entre S+2 e S+5 para aumentar robustez."
                ),
                tipo="danger",
            )
        )

    return PlanningBoardResult(
        semanas=semanas,
        demanda=demanda,
        estoque_natural=estoque_nat,
        estoque_pos_ia=estoque_ia,
        producao_ia=producao_ia,
        rupturas_previstas=rupturas,
        crit_ia=float(round(crit_ia, 1)),
        cobertura_atual_dias=float(round(cobertura_dias, 1)),
        recomendacoes=recs,
    )


# ---------------------------------------------------------------------------
# 6) Serialização do PlanningBoardResult
# ---------------------------------------------------------------------------

def planning_board_to_dict(result: PlanningBoardResult) -> Dict:
    return {
        "semanas": result.semanas,
        "demanda": result.demanda,
        "estoque_natural": result.estoque_natural,
        "estoque_pos_ia": result.estoque_pos_ia,
        "producao_ia": result.producao_ia,
        "rupturas_previstas": result.rupturas_previstas,
        "crit_ia": result.crit_ia,
        "cobertura_atual_dias": result.cobertura_atual_dias,
        "recomendacoes": [
            {
                "titulo": r.titulo,
                "descricao": r.descricao,
                "tipo": r.tipo,
            }
            for r in result.recomendacoes
        ],
    }


# ---------------------------------------------------------------------------
# 7) Alias para compatibilidade com código legado
# ---------------------------------------------------------------------------

def score_order(row: pd.Series, hoje: Optional[date] = None) -> float:
    """Alias para compatibilidade."""
    return score_order_criticidade(row, material_crit_map=None, hoje=hoje)
