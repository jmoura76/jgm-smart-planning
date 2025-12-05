// frontend/src/CapacityIa.js
import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { API_BASE_URL } from "./config";

const API_BASE = API_BASE_URL;

function CapacityIa() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchCapacity = async () => {
      try {
        setLoading(true);
        setError("");

        // Endpoint do backend para capacidade IA
        // Ex.: GET {API_BASE}/dashboard/capacity/ia
        const resp = await fetch(`${API_BASE}/dashboard/capacity/ia`);

        if (!resp.ok) {
          throw new Error(`Erro ao buscar capacidade (status ${resp.status})`);
        }

        const json = await resp.json();
        setData(json || null);
      } catch (err) {
        console.error("Erro ao carregar Capacity IA:", err);
        setError("Não foi possível carregar os dados de capacidade da IA.");
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchCapacity();
  }, []);

  if (loading) {
    return (
      <section className="planning-section">
        <div className="status-box">Carregando dados de capacidade...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="planning-section">
        <div className="status-box error">{error}</div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="planning-section">
        <div className="status-box">
          Nenhuma informação de capacidade foi retornada pelo backend.
        </div>
      </section>
    );
  }

  const {
    total_recursos = 0,
    utilizacao_media = null,
    recursos_acima_100 = 0,
    recursos_abaixo_90 = 0,
    recursos_90_100 = 0,
    insights = [],
    recomendacoes_gerais = [],
  } = data;

  // ------------------------------------------------------------------
  // Ordena recursos por utilização (maior → menor) para gráfico + cards
  // ------------------------------------------------------------------
  const safeInsights = Array.isArray(insights) ? insights : [];
  const sortedResources = [...safeInsights].sort(
    (a, b) => (b?.utilizacao_pct ?? 0) - (a?.utilizacao_pct ?? 0)
  );

  const chartData = sortedResources.map((r) => ({
    recurso: r.recurso,
    utilizacao: r.utilizacao_pct ?? 0,
  }));

  return (
    <section className="planning-section">
      <h2>Capacity IA™ – Utilização de Recursos</h2>
      <p className="section-subtitle">
        Visão consolidada de carga x capacidade, com insights de IA para
        gargalos e ociosidade.
      </p>

      {/* KPIs principais */}
      <div className="cards-row">
        <CapacityKpiCard
          title="Recursos monitorados"
          value={total_recursos}
          subtitle="Centros de trabalho avaliados pela IA"
        />
        <CapacityKpiCard
          title="Utilização média"
          value={
            utilizacao_media !== null && utilizacao_media !== undefined
              ? `${utilizacao_media.toFixed(1)}%`
              : "-"
          }
          subtitle="Média ponderada da carga"
        />
        <CapacityKpiCard
          title="> 100% de utilização"
          value={recursos_acima_100}
          subtitle="Recursos em sobrecarga (gargalos)"
          type="danger"
        />
      </div>

      {/* Gráfico + recomendações gerais lado a lado */}
      <div className="charts-row">
        <div className="chart-card">
          <div className="chart-title">Utilização por Recurso (TOP IA)</div>
          {chartData.length === 0 ? (
            <div className="empty-msg">
              Nenhum recurso foi retornado pela IA para este horizonte.
            </div>
          ) : (
            <div className="chart-body">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="recurso" />
                  <YAxis
                    allowDecimals={false}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    formatter={(value) => [`${value.toFixed(1)}%`, "Utilização"]}
                  />
                  <Bar
                    dataKey="utilizacao"
                    radius={[8, 8, 0, 0]}
                    fill="#a855f7"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-title">Recomendações gerais da IA</div>
          <div className="chart-body">
            {Array.isArray(recomendacoes_gerais) &&
            recomendacoes_gerais.length > 0 ? (
              <ul className="ia-recommendations-list">
                {recomendacoes_gerais.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            ) : (
              <div className="empty-msg">
                Nenhuma recomendação geral foi gerada pela IA.
              </div>
            )}
            <div className="capacity-legend-inline">
              <span>
                <strong>Abaixo de 90%:</strong> possível ociosidade.
              </span>
              <span>
                <strong>90–100%:</strong> faixa saudável.
              </span>
              <span>
                <strong>&gt; 100%:</strong> gargalo ⚠️.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Insights por recurso (cards) */}
      <h3 style={{ marginTop: "2rem" }}>Insights por recurso</h3>
      {sortedResources.length === 0 ? (
        <div className="status-box">
          Nenhum recurso detalhado retornado para análise.
        </div>
      ) : (
        <div className="capacity-insights-list">
          {sortedResources.map((r, idx) => {
            const utilizacao = r.utilizacao_pct ?? 0;
            const isGargalo =
              (r.categoria && r.categoria.toLowerCase() === "gargalo") ||
              utilizacao > 100;

            // cores por faixa de utilização
            let cardClass = "capacity-insight-card capacity-normal";
            if (isGargalo) {
              cardClass = "capacity-insight-card capacity-critical";
            } else if (utilizacao < 90) {
              cardClass = "capacity-insight-card capacity-low";
            }

            return (
              <div key={idx} className={cardClass}>
                <div className="capacity-insight-header">
                  <div className="capacity-insight-title">
                    {r.recurso} –{" "}
                    {utilizacao !== null && utilizacao !== undefined
                      ? `${utilizacao.toFixed(1)}%`
                      : "-"}
                    {r.planta ? ` (planta ${r.planta})` : ""}
                  </div>
                  {isGargalo && (
                    <div className="capacity-insight-badge">
                      <span role="img" aria-label="Gargalo">
                        ⚠️
                      </span>{" "}
                      Gargalo
                    </div>
                  )}
                </div>
                <div className="capacity-insight-body">
                  {r.recomendacao_curta ||
                    "Sem recomendação específica da IA para este recurso."}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ------------------------------------------------------------------
// Pequeno card interno para KPIs (reusa estilos globais de kpi-card)
// ------------------------------------------------------------------
function CapacityKpiCard({ title, value, subtitle, type }) {
  return (
    <div className={`kpi-card ${type ?? ""}`}>
      <div className="kpi-title">{title}</div>
      <div className="kpi-value">{value}</div>
      {subtitle && <div className="kpi-subtitle">{subtitle}</div>}
    </div>
  );
}

export default CapacityIa;
