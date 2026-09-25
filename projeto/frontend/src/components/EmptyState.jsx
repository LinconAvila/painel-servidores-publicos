import React from 'react';

export function EmptyState({ onClear }) {
  return (
    <div className="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" className="empty-icon">
        <circle cx="11" cy="11" r="7.5" stroke="currentColor" strokeWidth="1.2"/>
        <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
        <path d="M8 11h6M11 8v6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
      </svg>
      <h3 className="empty-title">Nenhum servidor encontrado</h3>
      <p className="empty-desc">
        Nenhum resultado corresponde aos filtros aplicados. Tente termos mais amplos ou limpe os filtros.
      </p>
      <button onClick={onClear} className="btn-clear-empty">
        Limpar filtros
      </button>
    </div>
  );
}