import React from 'react';

const UFS = [
  'Todas', 'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 
  'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
];

export function SearchForm() {
  return (
    <div className="search-card">
      <h2 className="search-card-title">FILTROS DE BUSCA</h2>
      
      <form onSubmit={(e) => e.preventDefault()} className="search-form">
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="nome">Nome</label>
            <input
              type="text"
              id="nome"
              placeholder="João da Silva"
            />
          </div>

          <div className="form-group">
            <label htmlFor="cargo">Cargo</label>
            <input
              type="text"
              id="cargo"
              placeholder="Analista"
            />
          </div>

          <div className="form-group">
            <label htmlFor="uf">UF</label>
            <select id="uf" defaultValue="Todas">
              {UFS.map((uf) => (
                <option key={uf} value={uf}>
                  {uf}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="orgao">Órgão</label>
            <input
              type="text"
              id="orgao"
              placeholder="Ministério da Fazenda"
            />
          </div>
        </div>

        <div className="form-footer">
          <label className="checkbox-container">
            <input type="checkbox" id="similaridade" />
            <span>Busca por similaridade</span>
          </label>

          <div className="button-group">
            <button type="button" className="btn-secondary">
              Limpar
            </button>
            <button type="submit" className="btn-primary">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              Buscar
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}