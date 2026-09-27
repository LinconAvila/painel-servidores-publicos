import React from 'react';
import { StatusBadge } from './StatusBadge';
import { EmptyState } from './EmptyState';
import { Pagination } from './Pagination';

export function ResultsArea({
  resultados,
  totalResultados,
  submitted,
  loading,
  page,
  totalPages,
  onPageChange,
  onSelectServidor,
  onClear,
  mensagemErro,
}) {
  if (!submitted) return null;

  if (loading) {
    return (
      <div className="results-container">
        <div className="skeleton-list">
          <div className="skeleton-item" />
          <div className="skeleton-item" />
          <div className="skeleton-item" />
        </div>
      </div>
    );
  }

  if (resultados.length === 0) {
    return <EmptyState mensagem={mensagemErro} onClear={onClear} />;
  }

  return (
    <div className="results-container">
      <div className="results-meta">
        <span className="results-count">
          {totalResultados} {totalResultados === 1 ? 'resultado' : 'resultados'}
        </span>
        {totalPages > 1 && (
          <span className="results-pages-info">
            Página {page} de {totalPages}
          </span>
        )}
      </div>

      <div className="results-card">
        {resultados.map((item, index) => (
          <button
            key={item.id}
            onClick={() => onSelectServidor(item)}
            className={`result-item ${index < resultados.length - 1 ? 'has-border' : ''}`}
          >
            <div className="result-info">
              <p className="result-name">{item.nome}</p>
              <p className="result-sub">
                {item.cargo}
                {item.uf ? ` · ${item.uf}` : ''}
                {` · ${item.orgao}`}
              </p>
            </div>
            <div className="result-right">
              <StatusBadge status={item.status} />
              <span className="chevron">›</span>
            </div>
          </button>
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onChange={onPageChange} />
      )}
    </div>
  );
}