import React, { useEffect, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = "http://127.0.0.1:8000";

const DEFAULT_MATERIAL = "4011835-AA";

function PlanningBoardIa() {
  const [materialCode, setMaterialCode] = useState(DEFAULT_MATERIAL);
  const [board, setBoard] = useState(null);
  const [loadingBoard, setLoadingBoard] = useState(false);
  const [error, setError] = useState("");

  const loadBoard = async (code) => {
    if (!code) return;

    try {
      setLoadingBoard(true);
      setError("");

      const resp = await fetch(`${API_BASE}/planning/board/${code}`);
      if (!resp.ok) {
        throw new Error(`Erro ao buscar Planning Board (${resp.status})`);
      }
      const json = await resp.json();
      setBoard(json);
    } catch (err) {
      console.error(err);
      setError("Não foi possível carregar o Planning Board IA.");
      setBoard(null);
    } finally {
      setLoadingBoard(false);
    }
  };

  useEffect(() => {
    loadBoard(materialCode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!materialCode) return;
    loadBoard(materialCode.trim());
  };

  // Monta dados para o gráfico de linha do tempo
  let chartData = [];
  if (board && board.series && board.series.labels) {
    const labels = board.series.labels || [];
    const demanda = board.series.demanda || [];
    const estoqueNatural = board.series.estoque_natural || [];
    const estoquePosIa = board.series.estoque_pos_ia || [];
    const producaoIa = board.series.producao_ia || [];

    chartData = labels.map((label, idx) => ({
      semana: label,
      demanda: demanda[idx] ?? 0,
      estoque_natural: estoqueNatural[idx] ?? 0,
      estoque_pos_ia: estoquePosIa[idx] ?? 0,
      producao_ia: producaoIa[idx] ?? 0,
    }));
  }

  const peggingOrdens = board?.pegging_ordens || [];

  return (
    <section className="planning-section">
      <h2>Planning Board IA™ (Backend)</h2>
      <p className="section-subtitle">
        Projeção real de demanda, estoque e produção com recomendações IA,
        utilizando MD04 + COHV + IA Engine.
      </p>

      {/* Filtro de material */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "0.5rem",
          marginBottom: "0.75rem",
        }}
      >
        <label
          htmlFor="mat-code"
          style={{
            color: "#e5e7eb",
            fontSize: 14,
            alignSelf: "center",
          }}
        >
          Material
        </label>
        <input
          id="mat-code"
          type="text"
          value={materialCode}
          onChange={(e) => setMaterialCode(e.target.value)}
          style={{
            padding: "0.3rem 0.5rem",
            borderRadius: 6,
            border: "1px solid #4b5563",
            background: "#020617",
            color: "#e5e7eb",
            minWidth: 140,
            fontSize: 13,
          }}
        />
        <button type="submit" className="alert-cta">
          Carregar Planning IA
        </button>
      </form>

      {loadingBoard && (
        <div className="status-box">Carregando materiais...</div>
      )}
      {error && <div className="status-box error">{error}</div>}

      {board && !loadingBoard && (
        <>
          {/* CARD RESUMO – agora em destaque, ocupando largura */}
          <div
            className="cards-row"
            style={{ marginBottom: "1rem", flexWrap: "wrap" }}
          >
            <KpiSmall
              title="Material"
              value={board.material || "-"}
              subtitle="Chave de planejamento"
            />
            <KpiSmall
              title="Cobertura atual"
              value={
                board.cobertura_atual_dias != null
                  ? `${board.cobertura_atual_dias} dias`
                  : "-"
              }
              subtitle="MD04"
            />
            <KpiSmall
              title="Criticidade IA"
              value={
                board.criticidade_ia != null
                  ? board.criticidade_ia.toFixed(1)
                  : "-"
              }
              subtitle="Score calculado pela IA"
            />
            <KpiSmall
              title="Rupturas previstas"
              value={board.rupturas_previstas ?? 0}
              subtitle="Ao longo do horizonte"
            />
            <KpiSmall
              title="Horizonte"
              value={board.horizonte_semanas ?? 0}
              subtitle="semanas"
            />
          </div>

          {/* MAIN ROW: gráfico maior + recomendações ao lado */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 2.3fr) minmax(0, 1.2fr)",
              gap: "1.5rem",
              alignItems: "stretch",
            }}
          >
            {/* Gráfico grande */}
            <div className="chart-card">
              <div className="chart-title">
                Estoque x Demanda x Produção – linha do tempo IA
              </div>
              <div className="chart-body">
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="semana" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar
                      dataKey="demanda"
                      name="Demanda"
                      fill="#f97316"
                      barSize={16}
                    />
                    <Bar
                      dataKey="producao_ia"
                      name="Produção planejada (OPs)"
                      fill="#a855f7"
                      barSize={16}
                    />
                    <Line
                      type="monotone"
                      dataKey="estoque_natural"
                      name="Estoque natural"
                      stroke="#38bdf8"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="estoque_pos_ia"
                      name="Estoque pós-ação IA"
                      stroke="#22c1c3"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="planning-note">
                *Simulação baseada nas séries calculadas pelo IA Engine™ com
                base no MD04 (estoque/cobertura) e COHV (ordens).
              </div>
            </div>

            {/* Recomendações IA ao lado do gráfico */}
            <div className="planning-right">
              <div className="planning-right-title">Recomendações IA</div>
              <div className="ia-suggestions-list">
                {board.recomendacoes && board.recomendacoes.length > 0 ? (
                  board.recomendacoes.map((rec, idx) => (
                    <div
                      key={idx}
                      className="ia-suggestion-card ia-suggestion-high"
                    >
                      <div className="ia-suggestion-title">{rec.titulo}</div>
                      <div className="ia-suggestion-body">
                        {rec.justificativa}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-msg">
                    Nenhuma recomendação IA retornada para este material.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Pegging resumido – card largo embaixo */}
          <div
            style={{
              marginTop: "2rem",
            }}
          >
            <h3>Pegging resumido – Ordens ligadas ao material</h3>
            <p className="section-subtitle">
              Visão rápida das ordens de produção relacionadas ao material, útil
              para discussão de backlog e priorização.
            </p>

            <div className="chart-card" style={{ marginTop: "0.75rem" }}>
              <div className="chart-body">
                {peggingOrdens.length === 0 ? (
                  <div className="empty-msg">
                    Nenhuma ordem de produção ligada encontrada para o material{" "}
                    <strong>{board.material}</strong> no horizonte atual.
                  </div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ordem</th>
                        <th>Tipo</th>
                        <th>Data fim</th>
                        <th>Status</th>
                        <th>Backlog (dias)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {peggingOrdens.map((op, idx) => (
                        <tr key={idx}>
                          <td>{op.ordem}</td>
                          <td>{op.tipo ?? "-"}</td>
                          <td>{op.data_fim ?? "-"}</td>
                          <td>{op.status ?? "-"}</td>
                          <td>{op.backlog_dias ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function KpiSmall({ title, value, subtitle }) {
  return (
    <div className="kpi-card">
      <div className="kpi-title" style={{ fontSize: 12 }}>
        {title}
      </div>
      <div className="kpi-value" style={{ fontSize: 20 }}>
        {value}
      </div>
      {subtitle && (
        <div className="kpi-subtitle" style={{ fontSize: 11 }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

export default PlanningBoardIa;
