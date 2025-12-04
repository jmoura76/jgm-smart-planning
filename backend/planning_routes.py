from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

from .ia_engine import (
    score_material_criticidade,
    score_order_criticidade,
)

# Reutilizamos as funções de carga e utilidades do dashboard
from .dashboard_routes import (
    _load_md04_df,
    _load_cohv_df,
    _find_column,
)

router = APIRouter()

# --------------------------------------------------------------------
# MODELOS Pydantic
# --------------------------------------------------------------------


class PlanningSeries(BaseModel):
    labels: list[str]
    demanda: list[float]
    estoque_natural: list[float]
    estoque_pos_ia: list[float]
    producao_existente: list[float]
    producao_ia: list[float]


class IaRecommendation(BaseModel):
    titulo: str
    categoria: str
    severidade: str  # "alto", "medio", "baixo", "info"
    descricao: str
    justificativa: str | None = None


class PeggingOrder(BaseModel):
    ordem: str
    data_fim: str
    status: str
    dias_atraso: int | None = None
    criticidade_score: float | None = None


class PlanningBoardResponse(BaseModel):
    material: str
    cobertura_atual_dias: float | None
    criticidade_ia: float | None
    rupturas_previstas: int
    horizonte_semanas: int
    series: PlanningSeries
    recomendacoes: list[IaRecommendation]
    pegging_ordens: list[PeggingOrder]


# --------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# --------------------------------------------------------------------


def _get_material_row(df_md04: pd.DataFrame, material: str) -> pd.Series:
    """Retorna a primeira linha do MD04 para o material informado."""
    col_material = _find_column(df_md04, ["Material", "material"])
    df_sel = df_md04[df_md04[col_material].astype(str) == str(material)]

    if df_sel.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Material {material} não encontrado no MD04.",
        )

    return df_sel.iloc[0]


def _get_material_cobertura(row: pd.Series) -> float | None:
    """Busca a coluna de cobertura no MD04 e retorna o valor em dias."""
    try:
        col_cobertura = _find_column(
            row.to_frame().T,
            ["CoberEstq", "CoberEstq.", "Cobertura", "Coverage", "Cobertura (dias)"],
        )
    except HTTPException:
        return None

    val = row[col_cobertura]
    try:
        val_f = float(val)
    except (TypeError, ValueError):
        return None

    if np.isnan(val_f):
        return None

    return val_f


def _build_week_labels(horizonte: int) -> list[str]:
    return [f"S+{i}" for i in range(1, horizonte + 1)]


def _safe_float(v, default: float = 0.0) -> float:
    try:
        f = float(v)
        if np.isnan(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------
# LÓGICA PRINCIPAL DO PLANNING BOARD IA™
# --------------------------------------------------------------------


@router.get(
    "/planning/board/{material}",
    response_model=PlanningBoardResponse,
)
def get_planning_board(material: str, horizonte_semanas: int = 8):
    """
    Planning Board IA™ para um material:
    - Projeta demanda/estoque por N semanas.
    - Considera cobertura atual do MD04 e OPs do COHV.
    - Gera sugestão de OP IA e recomendações de negócio.
    - Retorna Pegging Lite (ordens do material no COHV).
    """
    if horizonte_semanas < 1:
        horizonte_semanas = 1
    if horizonte_semanas > 12:
        horizonte_semanas = 12

    # 1) Carrega dados
    df_md04 = _load_md04_df()
    df_cohv = _load_cohv_df()

    # 2) Linha do MD04 para o material
    mat_row = _get_material_row(df_md04, material)
    cobertura_dias = _get_material_cobertura(mat_row)

    # 3) Criticidade IA do material (mesma lógica do Dashboard)
    #    Aqui usamos a própria linha do MD04, como no dashboard
    crit_ia = score_material_criticidade(mat_row)

    # 4) Define horizonte de planejamento
    labels = _build_week_labels(horizonte_semanas)

    # ----------------------------------------------------------------
    # DEMANDA (DEMO REALISTA)
    # ----------------------------------------------------------------
    if cobertura_dias is None or cobertura_dias <= 0:
        base_demand = 220.0
    elif cobertura_dias < 7:
        base_demand = 240.0
    elif cobertura_dias < 30:
        base_demand = 210.0
    else:
        base_demand = 180.0

    demanda = []
    for i in range(horizonte_semanas):
        # Pequena variação para dar realismo
        variation = ((i % 3) - 1) * 25  # -25, 0, +25
        demanda.append(base_demand + variation)

    # ----------------------------------------------------------------
    # PRODUÇÃO EXISTENTE (OPs reais do COHV agregadas por semana)
    # ----------------------------------------------------------------
    producao_existente = [0.0 for _ in range(horizonte_semanas)]

    if df_cohv is not None and not df_cohv.empty:
        col_mat_cohv = _find_column(
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
        try:
            col_qtd = _find_column(
                df_cohv,
                [
                    "Quantidade base",
                    "Qtd. base",
                    "Quantidade da ordem",
                    "Quantidade",
                    "Qty",
                ],
            )
        except HTTPException:
            col_qtd = None

        df_mat_ops = df_cohv[df_cohv[col_mat_cohv].astype(str) == str(material)].copy()
        if not df_mat_ops.empty:
            df_mat_ops[col_data_fim] = pd.to_datetime(
                df_mat_ops[col_data_fim], errors="coerce", dayfirst=True
            )
            df_mat_ops = df_mat_ops.dropna(subset=[col_data_fim])

            today = date.today()
            horizon_end = today + timedelta(days=7 * horizonte_semanas)

            df_mat_ops = df_mat_ops[
                (df_mat_ops[col_data_fim].dt.date >= today)
                & (df_mat_ops[col_data_fim].dt.date <= horizon_end)
            ]

            for _, row in df_mat_ops.iterrows():
                data_fim = row[col_data_fim]
                dias_ate = (data_fim.date() - today).days
                if dias_ate < 0:
                    continue
                semana_idx = dias_ate // 7  # 0-based
                if semana_idx >= horizonte_semanas:
                    continue

                qtd = _safe_float(row[col_qtd], default=0.0) if col_qtd else 0.0
                producao_existente[semana_idx] += qtd

    # ----------------------------------------------------------------
    # ESTOQUE NATURAL (sem IA) – cálculo a partir da cobertura
    # ----------------------------------------------------------------
    if cobertura_dias is None:
        estoque_inicial = base_demand * 0.5
    else:
        estoque_inicial = max(0.0, base_demand * (cobertura_dias / 7.0))

    estoque_natural: list[float] = []
    saldo = estoque_inicial
    for i in range(horizonte_semanas):
        saldo += producao_existente[i] - demanda[i]
        estoque_natural.append(round(saldo, 1))

    # ----------------------------------------------------------------
    # IA: identifica semanas com ruptura (estoque < 0)
    # ----------------------------------------------------------------
    semanas_ruptura = [idx for idx, est in enumerate(estoque_natural) if est < 0]
    qtd_rupturas = len(semanas_ruptura)

    # ----------------------------------------------------------------
    # IA: define OP recomendada (producao_ia) para mitigar ruptura
    # ----------------------------------------------------------------
    producao_ia = [0.0 for _ in range(horizonte_semanas)]

    if qtd_rupturas > 0:
        primeira_ruptura_idx = semanas_ruptura[0]
        semana_op_idx = max(0, primeira_ruptura_idx - 1)

        min_saldo = min(estoque_natural[: primeira_ruptura_idx + 1])
        qtd_op_ia = abs(min_saldo) + base_demand

        producao_ia[semana_op_idx] = round(qtd_op_ia, 1)

    # ----------------------------------------------------------------
    # ESTOQUE pós-IA
    # ----------------------------------------------------------------
    estoque_pos_ia: list[float] = []
    saldo = estoque_inicial
    for i in range(horizonte_semanas):
        saldo += producao_existente[i] + producao_ia[i] - demanda[i]
        estoque_pos_ia.append(round(saldo, 1))

    # ----------------------------------------------------------------
    # PEGGING LITE – ordens do material no COHV
    # ----------------------------------------------------------------
    pegging_ordens: list[PeggingOrder] = []
    if df_cohv is not None and not df_cohv.empty:
        col_mat_cohv = _find_column(
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
        col_ordem = _find_column(df_cohv, ["Ordem", "Ordem de produção", "Order"])

        df_mat_ops = df_cohv[df_cohv[col_mat_cohv].astype(str) == str(material)].copy()
        if not df_mat_ops.empty:
            df_mat_ops[col_data_fim] = pd.to_datetime(
                df_mat_ops[col_data_fim], errors="coerce", dayfirst=True
            )
            df_mat_ops = df_mat_ops.dropna(subset=[col_data_fim])

            today = date.today()
            df_mat_ops["Dias_Atraso"] = (
                df_mat_ops[col_data_fim].dt.date.apply(lambda d: (today - d).days)
            )
            df_mat_ops["Dias_Atraso"] = df_mat_ops["Dias_Atraso"].clip(lower=0)

            df_mat_ops = df_mat_ops.sort_values(
                by=["Dias_Atraso", col_data_fim], ascending=[False, True]
            ).head(10)

            for _, row in df_mat_ops.iterrows():
                data_fim_dt = row[col_data_fim]
                data_fim_str = data_fim_dt.date().strftime("%Y-%m-%d")
                status_str = str(row[col_status]) if row[col_status] is not None else ""

                dias_atraso_int = int(row["Dias_Atraso"])
                score_ord = score_order_criticidade(dias_atraso_int, status_str)

                pegging_ordens.append(
                    PeggingOrder(
                        ordem=str(row[col_ordem]),
                        data_fim=data_fim_str,
                        status=status_str,
                        dias_atraso=dias_atraso_int,
                        criticidade_score=score_ord,
                    )
                )

    # ----------------------------------------------------------------
    # RECOMENDAÇÕES IA – Copilot PCP
    # ----------------------------------------------------------------
    recomendacoes: list[IaRecommendation] = []

    # 1) Se houver ruptura → recomendação de criação de OP IA
    if qtd_rupturas > 0:
        primeira_ruptura_semana = semanas_ruptura[0] + 1  # 1-based
        semana_op = max(1, primeira_ruptura_semana - 1)
        qtd_op = producao_ia[semana_op - 1]

        recomendacoes.append(
            IaRecommendation(
                titulo=f"Criar OP IA de {int(qtd_op)} un. para S+{semana_op}",
                categoria="produção",
                severidade="alto",
                descricao=(
                    f"Evitar ruptura de estoque prevista a partir da semana S+{primeira_ruptura_semana} "
                    f"para o material {material}."
                ),
                justificativa=(
                    f"O estoque projetado sem ação IA fica negativo em {qtd_rupturas} semana(s). "
                    f"A OP IA recomendada em S+{semana_op} estabiliza o estoque ao longo do horizonte."
                ),
            )
        )

    # 2) Cobertura muito baixa
    if cobertura_dias is not None and cobertura_dias < 7:
        recomendacoes.append(
            IaRecommendation(
                titulo="Rever parâmetros de MRP e estoque de segurança",
                categoria="planejamento",
                severidade="medio",
                descricao=(
                    f"A cobertura atual do material {material} é de {cobertura_dias:.1f} dias, "
                    "indicando alto risco de ruptura no curto prazo."
                ),
                justificativa=(
                    "Avaliar aumento temporário de estoque de segurança, redução de lead time "
                    "planejado ou antecipação de compras/produção."
                ),
            )
        )

    # 3) Estoque muito alto no final do horizonte (sem ruptura)
    if qtd_rupturas == 0 and estoque_natural[-1] > base_demand * 3:
        recomendacoes.append(
            IaRecommendation(
                titulo="Avaliar redução de lote ou postergação de OPs",
                categoria="planejamento",
                severidade="medio",
                descricao=(
                    "O estoque projetado permanece alto em todo o horizonte, indicando possível excesso "
                    "de produção ou reposição."
                ),
                justificativa=(
                    "Rever tamanhos de lote, frequência de reposição e considerar postergação de "
                    "algumas ordens para liberar capacidade e capital."
                ),
            )
        )

    # 4) Pegging Lite – se tiver ordens atrasadas relevantes
    if pegging_ordens:
        ords_criticas = [o for o in pegging_ordens if (o.dias_atraso or 0) > 0]
        if ords_criticas:
            recomendacoes.append(
                IaRecommendation(
                    titulo="Repriorizar ordens críticas ligadas a este material",
                    categoria="seguimento",
                    severidade="alto",
                    descricao=(
                        f"Foram identificadas {len(ords_criticas)} ordens com atraso para o material "
                        f"{material}. Essas ordens podem gerar ruptura em clientes ou linhas produtivas."
                    ),
                    justificativa=(
                        "Priorizar essas ordens na fila de produção e alinhar prazos com "
                        "Comercial / Atendimento ao Cliente."
                    ),
                )
            )

    if not recomendacoes:
        recomendacoes.append(
            IaRecommendation(
                titulo="Nenhuma ação crítica identificada pela IA",
                categoria="informativo",
                severidade="info",
                descricao=(
                    "Para o horizonte analisado, não foram encontradas rupturas relevantes nem "
                    "excesso significativo de estoque."
                ),
                justificativa=(
                    "Manter o monitoramento semanal e revisar parâmetros de MRP na rotina padrão."
                ),
            )
        )

    # ----------------------------------------------------------------
    # MONTA RESPOSTA FINAL
    # ----------------------------------------------------------------
    series = PlanningSeries(
        labels=labels,
        demanda=[round(x, 1) for x in demanda],
        estoque_natural=estoque_natural,
        estoque_pos_ia=estoque_pos_ia,
        producao_existente=[round(x, 1) for x in producao_existente],
        producao_ia=[round(x, 1) for x in producao_ia],
    )

    return PlanningBoardResponse(
        material=str(material),
        cobertura_atual_dias=cobertura_dias,
        criticidade_ia=crit_ia,
        rupturas_previstas=qtd_rupturas,
        horizonte_semanas=horizonte_semanas,
        series=series,
        recomendacoes=recomendacoes,
        pegging_ordens=pegging_ordens,
    )
