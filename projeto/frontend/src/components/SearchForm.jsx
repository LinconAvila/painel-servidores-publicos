import React from 'react';

const UFS = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA',
  'MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN',
  'RO','RR','RS','SC','SE','SP','TO'
];

export function SearchForm({
  nome, setNome,
  cargo, setCargo,
  uf, setUf,
  orgao, setOrgao,
  similaridade, setSimilaridade,
  onBuscar, onClear
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onBuscar();
  };

  return (
    <div className="filter-card">
      <h2 className="filter-card-title">Filtros de busca</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field-group">
            <label className="field-label" htmlFor="nome">Nome</label>
            <input
              id="nome"
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="João da Silva"
              className="field-input"
            />
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="cargo">Cargo</label>
            <input
              id="cargo"
              type="text"
              value={cargo}
              onChange={(e) => setCargo(e.target.value)}
              placeholder="Analista"
              className="field-input"
            />
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="uf">UF</label>
            <select
              id="uf"
              value={uf}
              onChange={(e) => setUf(e.target.value)}
              className="field-select"
              style={{ color: uf ? '#1C1C1E' : '#9CA3AF' }}
            >
              <option value="">Todas</option>
              {UFS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="orgao">Órgão</label>
            <input
              id="orgao"
              type="text"
              value={orgao}
              onChange={(e) => setOrgao(e.target.value)}
              placeholder="Ministério da Fazenda"
              className="field-input"
            />
          </div>
        </div>

        <div className="form-actions">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={similaridade}
              onChange={(e) => setSimilaridade(e.target.checked)}
              className="checkbox-input"
            />
            <span className="checkbox-text">Busca por similaridade</span>
          </label>

          <div className="button-group">
            <button type="button" onClick={onClear} className="btn-clear">
              Limpar
            </button>
            <button type="submit" className="btn-submit">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <circle cx="7" cy="7" r="5.5" stroke="white" strokeWidth="1.4" />
                <path d="M11 11l3 3" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
              Buscar
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}