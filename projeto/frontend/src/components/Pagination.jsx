import React from 'react';

export function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;

  const pages = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push('…');
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < totalPages - 2) pages.push('…');
    pages.push(totalPages);
  }

  return (
    <div className="pagination-container" role="navigation" aria-label="Paginação">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="pagination-btn"
        aria-label="Página anterior"
      >
        ‹
      </button>

      {pages.map((p, idx) =>
        p === '…' ? (
          <span key={`ellipsis-${idx}`} className="pagination-ellipsis" style={{ padding: '0 4px', color: '#9CA3AF', fontSize: '0.75rem' }}>
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`pagination-btn ${p === page ? 'active' : ''}`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="pagination-btn"
        aria-label="Próxima página"
      >
        ›
      </button>
    </div>
  );
}