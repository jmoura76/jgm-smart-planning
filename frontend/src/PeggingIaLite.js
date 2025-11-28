// frontend/src/PeggingIaLite.js
import React, { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function PeggingIaLite() {
  const [materialInput, setMaterialInput] = useState("4011835-AA");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  // -------------------------------------------------------------
  // Validação simples do código de material
  // Aceita letras, números e hífen. Ex: 4011835-AA
  // -------------------------------------------------------------
  const isValidMaterial = (code) => {
    const trimmed = (code || "").trim();
    if (!trimmed) return false;
    const regex = /^[0-9A-Za-z-]+$/;
    return regex.test(trimmed);
  };

  const handleLoadPegging = async () => {
    const code = materialInput.trim();

    // 1) Validação antes de chamar o backend
    if (!isValidMaterial(code)) {
      setError('Informe um código de material válido. Ex: "4011835-AA".');
      setResult(null);
      return;
    }

    try {
      // 2) Spinner on
      setLoading(true);
      setError("");
      setResult(null);

      // 3) Chamada ao backend (mantenha o endpoint que você já usa)
      const resp = await fetch(
        `${API_BASE}/pegging/ia-lite?material=${encodeURIComponent(code)}`
      );

      if (!resp.ok) {
        throw new Error(`Erro ao buscar Pegging IA (${resp.status})`);
      }

      const json = await resp.json();
      setResult(json);
    } catch (err) {
      console.error(err);
      setError(
        "Não foi possível carregar o Pegging IA para este material. Tente novamente."
      );
    } finally {
      // 4) Spinner off
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
