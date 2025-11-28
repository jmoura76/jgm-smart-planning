import React, { useEffect, useState } from "react";

function IaInsightsPanel({ filterTipo }) {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        setLoading(true);
        setError(null);

        // se seu frontend tem "proxy" no package.json, use apenas "/dashboard/insights"
        const res = await fetch("http://127.0.0.1:8000/dashboard/insights");
        if (!res.ok) {
          throw new Error(`Erro ao buscar insights: ${res.status}`);
        }

        const data = await res.json();
        let items = data.insights || [];

        if (filterTipo) {
          items = items.filter((i) => i.tipo === filterTipo);
        }

        setInsights(items);
      } catch (err) {
        console.error(err);
        setError(err.message || "Erro inesperado ao carregar insights.");
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, [filterTipo]);

  const getSeverityClass = (sev) => {
    switch (sev) {
      case "alto":
        return "bg-red-900/40 border-red-500 text-red-100";
      case "medio":
        return "bg-yellow-900/40 border-yellow-400 text-yellow-100";
      case "baixo":
        return "bg-emerald-900/40 border-emerald-500 text-emerald-100";
      default:
        return "bg-sky-900/40 border-sky-500 text-sky-100";
    }
  };

  const getTipoLabel = (tipo) => {
    switch (tipo) {
      case "material":
        return "Materiais";
      case "ordem":
        return "Ordens";
      case "recurso":
        return "Recursos";
      case "sistema":
        return "Sistema";
      default:
        return tipo;
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {loading && (
        <div className="text-slate-300 text-sm">Carregando insights IA...</div>
      )}

      {error && (
        <div className="text-red-400 text-sm">
          Falha ao carregar insights IA: {error}
        </div>
      )}

      {!loading && !error && insights.length === 0 && (
        <div className="text-slate-300 text-sm">
          Nenhum insight IA disponível no momento.
        </div>
      )}

      {!loading &&
        !error &&
        insights.map((insight, idx) => (
          <div
            key={idx}
            className={`border rounded-xl px-4 py-3 shadow-sm ${getSeverityClass(
              insight.severidade
            )}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs uppercase tracking-wide opacity-80">
                {getTipoLabel(insight.tipo)}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full border border-current uppercase tracking-wider">
                {insight.severidade === "alto"
                  ? "Crítico"
                  : insight.severidade === "medio"
                  ? "Atenção"
                  : insight.severidade === "baixo"
                  ? "Monitorar"
                  : "Informativo"}
              </span>
            </div>

            <h4 className="text-sm font-semibold mb-1">{insight.titulo}</h4>

            <p className="text-xs mb-1 opacity-90">{insight.descricao}</p>

            <p className="text-[11px] italic opacity-80">
              <span className="font-semibold not-italic mr-1">
                Sugestão IA:
              </span>
              {insight.sugestao}
            </p>
          </div>
        ))}
    </div>
  );
}

export default IaInsightsPanel;
