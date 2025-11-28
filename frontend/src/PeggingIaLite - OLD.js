import React, { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function PeggingIaLite({ materialCode }) {
  const [material, setMaterial] = useState(materialCode || "");
  const [effectiveMaterial, setEffectiveMaterial] = useState(materialCode || "");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Atualiza se vier materialCode por prop
  useEffect(() => {
    if (materialCode) {
      setMaterial(materialCode);
      setEffectiveMaterial(materialCode);
      fetchPegging(materialCode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [materialCode]);

  const fetchPegging = async (mat) => {
    if (!mat) return;
    try {
      setLoading(true);
      setError("");
      const resp = await fetch(
        `${API_BASE}/planning/board/${encodeURIComponent(mat)}`
      );
      if (!resp.ok) {
        throw new Error(`Erro ao buscar pegging (${resp.status})`);
      }
      const json = await resp.json();
      setData(json);
    } catch (e) {
      console.error(e);
      setError("Falha ao carregar Pegging IA para o material informado.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadClick = () => {
    setEffectiveMaterial(material);
    fetchPegging(material);
  };

  const ordens = data?.pegging_ordens || [];
  const ordensCriticas = ordens.filter((o) => (o.dias_atraso || 0) > 0);
  const atrasoMax =
    ordensCriticas.length > 0
      ? Math.max(...ordensCriticas.map((o) => o.dias_atraso || 0))
      : 0;

  return (
    <section>
      <h2>Pegging IA™ Lite – Ordens ligadas ao material</h2>
      <p className="section-subtitle">
        Impacto direto entre ordens de produção e um material específico
        (BACKLOG + criticidade IA).
      </p>

      {!materialCode && (
        <div className="planning-filter-row">
          <div>
            <label className="summary-label">Material</label>
            <input
              className="text-input"
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              placeholder="Ex.: 4011835-AA"
              style={{ width: "220px", marginRight: "0.75rem" }}
            />
            <button className="alert-cta" onClick={handleLoadClick}>
              Carregar Pegging IA
            </button>
          </div>
        </div>
      )}

      {materialCode && (
        <div className="planning-chip" style={{ marginBottom: "1rem" }}>
          Material recebido por parâmetro: <strong>{materialCode}</strong>
        </div>
      )}

      {loading && (
        <div className="status-box">Carregando ordens ligadas ao material...</div>
      )}
      {error && <div className="status-box error">{error}</div>}

      {!loading && !error && data && (
        <>
          <div className="cards-row">
            <KpiCard
              title="Material"
              value={data.material}
              subtitle="Chave de planejamento"
            />
            <KpiCard
              title="Cobertura atual"
              value={
                data.cobertura_atual_dias != null
                  ? `${data.cobertura_atual_dias.toFixed(1)} dias`
                  : "-"
              }
              subtitle="MD04"
            />
            <KpiCard
              title="Ordens vinculadas"
              value={ordens.length}
              subtitle="Encontradas no COHV"
            />
            <KpiCard
              title="Ordens atrasadas"
              value={ordensCriticas.length}
              subtitle={`Maior atraso: ${atrasoMax} dia(s)`}
              type={ordensCriticas.length > 0 ? "danger" : ""}
            />
          </div>

          <h3 style={{ marginTop: "1.5rem" }}>Detalhamento das ordens (Pegging)</h3>
          {ordens.length === 0 ? (
            <div className="status-box">
              Nenhuma ordem relevante encontrada para este material.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ordem</th>
                  <th>Data Fim</th>
                  <th>Status</th>
                  <th>Dias Atraso</th>
                  <th>Criticidade IA</th>
                </tr>
              </thead>
              <tbody>
                {ordens.map((op, idx) => (
                  <tr key={idx}>
                    <td>{op.ordem}</td>
                    <td>{op.data_fim}</td>
                    <td>{op.status}</td>
                    <td>{op.dias_atraso ?? 0}</td>
                    <td>
                      {op.criticidade_score != null
                        ? op.criticidade_score.toFixed(1)
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

function KpiCard({ title, value, subtitle, type }) {
  return (
    <div className={`kpi-card ${type ?? ""}`}>
      <div className="kpi-title">{title}</div>
      <div className="kpi-value">{value}</div>
      {subtitle && <div className="kpi-subtitle">{subtitle}</div>}
    </div>
  );
}

export default PeggingIaLite;
