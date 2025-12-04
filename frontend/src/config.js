// frontend/src/config.js

// URL base da API do backend (Render)
// Se existir variável de ambiente REACT_APP_API_BASE, usa ela;
// senão, usa direto a URL pública do Render.
export const API_BASE_URL =
  process.env.REACT_APP_API_BASE ||
  "https://jgm-smartplanning-api.onrender.com";

// Export default opcional, só para manter compatibilidade
const API_BASE = API_BASE_URL;
export default API_BASE;
