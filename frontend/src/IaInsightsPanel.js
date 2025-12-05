// frontend/src/IaInsightsPanel.js
import React from "react";

/**
 * Painel de Insights Avançados da IA Engine™
 * 
 * Opcionalmente recebe um objeto `summary` com métricas da tela principal,
 * por exemplo:
 * {
 *   materiais_em_risco: 4,
 *   recursos_sobrecarga: 2,
 *   ordens_atrasadas: 6
 * }
 *
 * Caso não seja passado, o painel funciona com textos genéricos.
 */
function IaInsightsPanel({ summary }) {
  const materiaisRisco =
    summary && summary.materiais_em_risco != null
      ? summary.materiais_em_risco
      : null;
  const recursosSobrecarga =
    summary && summary.recursos_sobrecarga != null
      ? summary.recursos_sobrecarga
      : null;
  const ordensAtrasadas =
    summary && summary.ordens_atrasadas != null
      ? summary.ordens_atrasadas
      : null;

  return (
    <div className="ia-alert-panel">
      <div className="ia-alert-header">
        <span className="ia-engine-pill">IA ENGINE™</span>
        <span className="ia-alert-title">Insights avançados</span>
      </div>

      <ul className="ia-alert-list">
        <li>
          <strong>Focus hoje:</strong>{" "}
          {materiaisRisco != null && recursosSobrecarga != null ? (
            <>
              {materiaisRisco} materiais com cobertura &lt; 7 dias e{" "}
              {recursosSobrecarga} recurso(s) acima de 100% de utilização.
            </>
          ) : (
            <>
              materiais com cobertura &lt; 7 dias e recursos acima de 100% de
              utilização.
            </>
          )}
        </li>
        <li>
          <strong>Materiais em risco:</strong> priorizar revisão de MRP, estoque
          de segurança e sequência de produção na próxima reunião de PCP.
        </li>
        <li>
          <strong>Capacidade:</strong> usar os recursos em sobrecarga como pauta
          fixa no S&amp;OP/MPS (D-1 / semanal) para redistribuir carga entre
          linhas, turnos e plantas.
        </li>
        <li>
          <strong>Ordens críticas:</strong>{" "}
          {ordensAtrasadas != null ? (
            <>
              acompanhar de perto as {ordensAtrasadas} ordem(ns) atrasada(s),
              alinhando impactos com Comercial / Customer Service para evitar
              problemas em clientes chave.
            </>
          ) : (
            <>
              alinhar atrasos relevantes com times de Comercial / Customer
              Service para evitar impacto em clientes chave.
            </>
          )}
        </li>
      </ul>
    </div>
  );
}

export default IaInsightsPanel;
