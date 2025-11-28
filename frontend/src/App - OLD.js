import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import "./App.css";
import IaInsightsPanel from "./IaInsightsPanel";
import PlanningBoardIa from "./PlanningBoardIa";
import CapacityIa from "./CapacityIa";
import PeggingIaLite from "./PeggingIaLite";

const API_BASE = "http://127.0.0.1:8000";

// ---------------------------------------------------------------------
// Label customizado para o donut de capacidade (mostra percentual)
// ---------------------------------------------------------------------
const RADIAN = Math.PI / 180;
const renderCapacityLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.7;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#ffffff"
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
      style={{ fontSize: 12 }}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const resp = await fetch(`${API_BASE}/dashboard/summary`);
        if (!resp.ok) {
          throw new Error(`Erro ao buscar dados (${resp.status})`);
        }
        const json = await resp.json();
        setData(json);
        setError("");
      } catch (err) {
        console.error(err);
        setError("Não foi possível carregar os dados do backend.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const kpis = data?.kpis;
  const capacidade = data?.capacidade;
  const criticos = data?.criticos || [];
  const ordensCriticas = data?.ordens_criticas || [];

  // Dados para gráficos da visão geral
  const inventoryChartData = kpis
    ? [
        {
          name: "Risco",
          value: kpis.materiais_risco,
        },
        {
          name: "Excesso",
          value: kpis.materiais_excesso,
        },
      ]
    : [];

  const ordersChartData = kpis
    ? [
        {
          name: "Total OPs",
          value: kpis.total_ops,
        },
        {
          name: "Atrasadas",
          value: kpis.ops_atrasadas,
        },
      ]
    : [];

  const capacityPieData =
    capacidade && capacidade.total_recursos > 0
      ? [
          {
            name: "< 90%",
            value: capacidade.recursos_abaixo_90,
          },
          {
            name: "90–100%",
            value: capacidade.recursos_90_100,
          },
          {
            name: "> 100%",
            value: capacidade.recursos_acima_100,
          },
        ]
      : [];

  const pieColors = ["#22c55e", "#eab308", "#f97373"];

  // ------------------------------
  // IA – contadores de alertas
  // ------------------------------
  const highRiskMaterials = criticos.filter(
    (m) => (m.criticidade_score ?? 0) >= 80
  ).length;

  const highRiskOrders = ordensCriticas.filter(
    (o) => (o.criticidade_score ?? 0) >= 70
  ).length;

  const overloadedResources = capacidade?.recursos_acima_100 ?? 0;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>JGM SmartPlanning™</h1>
          <p>PCP 360° – Joyson POC</p>
        </div>
        <div className="header-right">
          <span className="env-pill">LOCAL DEV</span>
          <span className="timestamp">
            {data
              ? `Last update: ${new Date(
                  data.generated_at
                ).toLocaleString()}`
              : ""}
          </span>
        </div>
      </header>

      <div className="app-body">
        {/* Sidebar / Menu */}
        <nav className="sidebar">
          <button
            className={
              activeTab === "overview" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("overview")}
          >
            Visão Geral
          </button>
          <button
            className={
              activeTab === "materials" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("materials")}
          >
            Materiais Críticos
          </button>
          <button
            className={
              activeTab === "orders" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("orders")}
          >
            Ordens Críticas
          </button>
          <button
            className={
              activeTab === "resources" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("resources")}
          >
            Recursos / Capacidade
          </button>
          <button
            className={
              activeTab === "planning" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("planning")}
          >
            Planejamento IA
          </button>
          <button
            className={
              activeTab === "pegging" ? "menu-item active" : "menu-item"
            }
            onClick={() => setActiveTab("pegging")}
          >
            Pegging IA
          </button>
        </nav>

        {/* Conteúdo Principal */}
        <main className="main-panel">
          {loading && <div className="status-box">Carregando dados...</div>}
          {error && <div className="status-box error">{error}</div>}

          {/* ------------------------------------------------------------------ */}
          {/* VISÃO GERAL                                                         */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && data && activeTab === "overview" && (
            <>
              <section className="cards-row">
                <KpiCard
                  title="Materiais monitorados"
                  value={kpis.total_materiais}
                  subtitle="Total de itens com cobertura calculada"
                />
                <KpiCard
                  title="Materiais em risco"
                  value={`${kpis.materiais_risco} (${kpis.perc_materiais_risco}%)`}
                  subtitle="Cobertura &lt; 7 dias"
                  type="warning"
                />
                <KpiCard
                  title="Materiais em excesso"
                  value={`${kpis.materiais_excesso} (${kpis.perc_materiais_excesso}%)`}
                  subtitle="Cobertura &gt; 45 dias"
                />
                <KpiCard
                  title="OPs atrasadas"
                  value={`${kpis.ops_atrasadas} (${kpis.perc_ops_atrasadas}%)`}
                  subtitle="Base COHV"
                  type="danger"
                />
              </section>

              {/* Painel de Alertas IA */}
              <section className="alerts-row">
                <div className="alerts-header">
                  <h3>Painel de Alertas IA</h3>
                  <span className="alerts-subtitle">
                    Ações sugeridas hoje com base na criticidade calculada pela
                    IA.
                  </span>

                  {/* Bloco de insights IA avançados */}
                  <IaInsightsPanel />
                </div>
                <div className="alerts-cards">
                  <AlertCard
                    severity="alta"
                    label="Materiais com alta criticidade"
                    value={highRiskMaterials}
                    description="criticidade IA ≥ 80"
                    cta="Ver materiais"
                    onClick={() => setActiveTab("materials")}
                  />
                  <AlertCard
                    severity="media"
                    label="Ordens de produção críticas"
                    value={highRiskOrders}
                    description="criticidade IA ≥ 70"
                    cta="Ver ordens"
                    onClick={() => setActiveTab("orders")}
                  />
                  <AlertCard
                    severity="danger"
                    label="Recursos em sobrecarga"
                    value={overloadedResources}
                    description="utilização &gt; 100%"
                    cta="Ver recursos"
                    onClick={() => setActiveTab("resources")}
                  />
                </div>
              </section>

              <section className="charts-row">
                <ChartCard title="Saúde do Estoque (Risco x Excesso)">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={inventoryChartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar
                        dataKey="value"
                        radius={[8, 8, 0, 0]}
                        fill="#38bdf8"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Situação das Ordens de Produção">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={ordersChartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar
                        dataKey="value"
                        radius={[8, 8, 0, 0]}
                        fill="#a855f7"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Distribuição de Utilização de Recursos">
                  {capacityPieData.length === 0 ? (
                    <div className="empty-msg">
                      Nenhum dado de capacidade carregado.
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={capacityPieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          innerRadius={40}
                          paddingAngle={3}
                          labelLine={false}
                          label={renderCapacityLabel}
                        >
                          {capacityPieData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={pieColors[index % pieColors.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value, name) => [
                            `${value} recursos`,
                            name,
                          ]}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </ChartCard>
              </section>
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* MATERIAIS CRÍTICOS                                                  */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && data && activeTab === "materials" && (
            <section>
              <h2>TOP 10 Materiais Críticos (menor cobertura)</h2>
              <p className="section-subtitle">
                Fonte: MD04 – cobertura em dias. Ideal para discussão de
                reposição / safety stock.
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Cobertura (dias)</th>
                    <th>Criticidade (IA)</th>
                  </tr>
                </thead>
                <tbody>
                  {criticos.map((item, idx) => (
                    <tr key={idx}>
                      <td>{item.material}</td>
                      <td>{item.cobertura_dias ?? "-"}</td>
                      <td>
                        {item.criticidade_score !== null &&
                        item.criticidade_score !== undefined
                          ? item.criticidade_score.toFixed(1)
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* ORDENS CRÍTICAS                                                     */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && data && activeTab === "orders" && (
            <section>
              <h2>TOP 10 Ordens de Produção Atrasadas</h2>
              <p className="section-subtitle">
                Fonte: COHV – ordens com data de fim no passado e sem status
                TECO/CLSD.
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ordem</th>
                    <th>Material</th>
                    <th>Data Fim</th>
                    <th>Status</th>
                    <th>Criticidade (IA)</th>
                  </tr>
                </thead>
                <tbody>
                  {ordensCriticas.map((op, idx) => (
                    <tr key={idx}>
                      <td>{op.ordem}</td>
                      <td>{op.material ?? "-"}</td>
                      <td>{op.data_fim}</td>
                      <td>{op.status}</td>
                      <td>
                        {op.criticidade_score !== null &&
                        op.criticidade_score !== undefined
                          ? op.criticidade_score.toFixed(1)
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* RECURSOS / CAPACIDADE  -> Capacity IA™                             */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && activeTab === "resources" && (
            <section className="planning-section">
              <CapacityIa />
            </section>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* PLANEJAMENTO IA – Planning Board IA™ (backend)                     */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && activeTab === "planning" && (
            <section className="planning-section">
              <PlanningBoardIa />
            </section>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* PEGGING IA – Detalhamento completo                                 */}
          {/* ------------------------------------------------------------------ */}
          {!loading && !error && activeTab === "pegging" && (
            <section className="planning-section">
              <PeggingIaLite />
            </section>
          )}
        </main>
      </div>
    </div>
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

function AlertCard({ severity, label, value, description, cta, onClick }) {
  return (
    <div className={`alert-card alert-${severity}`}>
      <div className="alert-main">
        <div className="alert-value">{value}</div>
        <div className="alert-label">{label}</div>
        <div className="alert-description">{description}</div>
      </div>
      <button className="alert-cta" onClick={onClick}>
        {cta}
      </button>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <div className="chart-title">{title}</div>
      <div className="chart-body">{children}</div>
    </div>
  );
}

export default App;
