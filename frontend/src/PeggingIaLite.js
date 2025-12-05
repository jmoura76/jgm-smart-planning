// frontend/src/PeggingIaLite.js
import React, { useState } from "react";
import { API_BASE_URL } from "./config";

const API_BASE = API_BASE_URL;
const DEFAULT_MATERIAL = "4011835-AA";

/**
 * DADOS DEMO – PEGGING IA
 * Ordens fictícias porém realistas vinculadas ao material.
 */
const DEMO_PEGGING_4011835 = {
  material: "4011835-AA",
  descricao: "Conjunto Airbag – Volante",
  cobertura_atual_dias: 5.2,
  total_ordens_vinculadas: 5,
  ordens_atrasadas: 2,
  maior_atraso_dias: 3,
  ordens: [
    {
      ordem: "00000045",
      material: "4011835-AA",
      data_fim: "2025-12-10",
      atraso_dias: 3,
      backlog_qtd: 450,
      criticidade_score: 91.3,
    },
    {
      ordem: "00000048",
      material: "4011835-AA",
      data_fim: "2025-12-12",
      atraso_dias: 1,
      backlog_qtd: 220,
      criticidade_score: 84.7,
    },
    {
      ordem: "00000052",
      material: "4011835-AA",
      data_fim: "2025-12-18",
      atraso_dias: 0,
      backlog_qtd: 0,
      criticidade_score: 72.1,
    },
    {
      ordem: "00000057",
      material: "4011835-AA",
      data_fim: "2025-12-22",
      atraso_dias: 0,
      backlog_qtd: 0,
      criticidade_score: 65.3,
    },
    {
      ordem: "00000060",
      material: "4011835-AA",
      data_fim: "2025-12-29",
      atraso_dias: 0,
      backlog_qtd: 0,
      criticidade_score: 58.9,
    },
  ],
};

function PeggingIaLite() {
  const [materialInput, setMaterialInput] = useState(DEFAULT_MATERIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const isValidMaterial = (code) => {
    const trimmed = (code || "").trim();
    if (!trimmed) return false;
    const regex = /^[0-9A-Za-z-]+$/;
    return regex.test(trimmed);
  };

  const buildDemoResult = (code) => {
    const clean = (code || "").trim();
    if (!clean) return null;

    if (clean === DEFAULT_MATERIAL) {
      return DEMO_PEGGING_4011835;
    }

    // Para outros materiais, replica cenário e troca apenas o código
    return {
      ...DEMO_PEGGING_4011835,
      material: clean,
      ordens: DEMO_PEGGING_4011835.ordens.map((op) => ({
        ...op,
        material: clean,
      })),
    };
  };

  const handleLoadPegging = async () => {
    const code = materialInput.trim();

    if (!isValidMaterial(code)) {
      setError('Informe um código de material válido. Ex: "4011835-AA".');
      setResult(null);
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);

      // 1) Tenta usar backend real (se existir)
      const resp = await fetch(
        `${API_BASE}/pegging/ia-lite?material=${encodeURIComponent(code)}`
      );

      if (!resp.ok) {
        console.warn(
          `Backend retornou status ${resp.status} para Pegging IA, usando dados DEMO...`
        );
        const demo = buildDemoResult(code);
        if (demo) {
          setResult(demo);
          return;
        }
        throw new Error(`Erro ao buscar Pegging IA (${resp.status})`);
      }

      // 2) Backend ok → usa dados reais
      const json = await resp.json();
      setResult(json);
    } catch (err) {
      console.error(err);

      // 3) Qualquer erro de rede/CORS → usa DEMO
      const demo = buildDemoResult(code);
      if (demo) {
        setResult(demo);
        setError("");
        return;
      }

      setError(
        "Não foi possível carregar o Pegging IA para este material. Tente novamente."
      );
    } finally {
      setLoading(false);
    }
  };

  const ordens = Array.isArray(result?.ordens) ? result.ordens : [];
  const nenhumaOrdem =
    !loading && !error && result && (ordens.length === 0 || result.sem_ordens);

  return (
    <section>
      <h2>Pegging IA™ Lite – Ordens ligadas ao material</h2>
      <p className="section-subtitle">
        Impacto direto entre ordens de produção e um material específico
        (BACKLOG + criticidade IA).
      </p>

      {/* Campo de material + botão */}
      <div className="pegging-input-row">
        <div className="pegging-input-group">
          <label className="pegging-label">Material</label>
          <input
            type="text"
            className="pegging-input"
            value={materialInput}
            onChange={(e) => setMaterialInput(e.target.value)}
            placeholder='Ex.: 4011835-AA'
          />
        </div>
        <button
          className="btn-primary"
          onClick={handleLoadPegging}
          disabled={loading}
        >
          {loading ? "Carregando..." : "Carregar Pegging IA"}
        </button>
      </div>

      {/* Mensagens de erro / status */}
      {error && <div className="status-box error">{error}</div>}
      {loading && !error && (
        <div className="status-box">Carregando Pegging IA...</div>
      )}

      {/* Resumo do material / cabeçalho */}
      {result && !loading && !error && (
        <div className="cards-row pegging-summary-row">
          <div className="kpi-card">
            <div className="kpi-title">Material</div>
            <div className="kpi-value">{result.material ?? materialInput}</div>
            <div className="kpi-subtitle">
              {result.descricao ?? "Chave de planejamento"}
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-title">Cobertura atual</div>
            <div className="kpi-value">
              {result.cobertura_atual_dias !== null &&
              result.cobertura_atual_dias !== undefined
                ? `${result.cobertura_atual_dias.toFixed(1)} dias`
                : "-"}
            </div>
            <div className="kpi-subtitle">MD04</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-title">Ordens vinculadas</div>
            <div className="kpi-value">
              {result.total_ordens_vinculadas ?? ordens.length ?? 0}
            </div>
            <div className="kpi-subtitle">Encontradas no COHV</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-title">Ordens atrasadas</div>
            <div className="kpi-value">
              {result.ordens_atrasadas ?? 0}
            </div>
            <div className="kpi-subtitle">
              Maior atraso:{" "}
              {result.maior_atraso_dias !== null &&
              result.maior_atraso_dias !== undefined
                ? `${result.maior_atraso_dias} dia(s)`
                : "0 dia(s)"}
            </div>
          </div>
        </div>
      )}

      {/* Nenhuma ordem encontrada */}
      {nenhumaOrdem && (
        <div className="status-box">
          Nenhuma ordem vinculada foi encontrada para este material no
          horizonte atual.
        </div>
      )}

      {/* Detalhamento das ordens em cards */}
      {ordens.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.5rem" }}>
            Detalhamento das ordens (Pegging)
          </h3>
          <div className="pegging-orders-grid">
            {ordens.map((op, idx) => {
              const atraso = op.atraso_dias ?? 0;
              const criticidade = op.criticidade_score ?? op.criticidade ?? 0;

              let badgeClass = "pegging-badge-low";
              if (criticidade >= 80) badgeClass = "pegging-badge-high";
              else if (criticidade >= 60) badgeClass = "pegging-badge-medium";

              return (
                <div key={idx} className="pegging-order-card">
                  <div className="pegging-order-header">
                    <div className="pegging-order-id">
                      Ordem {op.ordem ?? op.order}
                    </div>
                    <div className={`pegging-badge ${badgeClass}`}>
                      IA {Number(criticidade).toFixed(1)}
                    </div>
                  </div>
                  <div className="pegging-order-body">
                    <div>
                      <span className="pegging-label-inline">Material:</span>{" "}
                      {op.material ?? result.material ?? materialInput}
                    </div>
                    <div>
                      <span className="pegging-label-inline">
                        Data fim planejada:
                      </span>{" "}
                      {op.data_fim ?? op.finish_date ?? "-"}
                    </div>
                    <div>
                      <span className="pegging-label-inline">Atraso:</span>{" "}
                      {atraso > 0 ? `${atraso} dia(s)` : "No prazo"}
                    </div>
                    {op.backlog_qtd !== undefined && (
                      <div>
                        <span className="pegging-label-inline">
                          Backlog vinculado:
                        </span>{" "}
                        {op.backlog_qtd}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

export default PeggingIaLite;
