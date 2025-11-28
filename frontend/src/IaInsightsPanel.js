// src/IaInsightsPanel.js
import React from "react";
import "./App.css";

/**
 * Painel de Insights IA (estático para DEMO)
 * - Não chama backend
 * - Evita erro na Visão Geral
 * - Apenas exibe mensagens de boas práticas / contexto da IA
 */
function IaInsightsPanel() {
  return (
    <div className="ia-insights-panel">
      <div className="ia-insights-header">
        <span className="ia-insights-pill">IA Engine™</span>
        <span className="ia-insights-title">Insights avançados</span>
      </div>

      <ul className="ia-insights-list">
        <li>
          <strong>Focus hoje:</strong> materiais com cobertura &lt; 7 dias e
          recursos acima de 100% de utilização.
        </li>
        <li>
          <strong>Materiais em risco:</strong> priorizar revisão de MRP,
          estoque de segurança e sequência de produção na próxima reunião de
          PCP.
        </li>
        <li>
          <strong>Capacidade:</strong> usar os recursos em sobrecarga como
          pauta fixa no S&amp;OP/MPS (D-1 / semanal) para redistribuir carga.
        </li>
        <li>
          <strong>Ordens críticas:</strong> alinhar atrasos relevantes com
          times de Comercial / Customer Service para evitar impacto em clientes
          chave.
        </li>
      </ul>
    </div>
  );
}

export default IaInsightsPanel;
