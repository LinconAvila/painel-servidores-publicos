import React from 'react';

export function Pagination({ page, totalPages, onChange }) {
  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    pages.push(i);
  }

  return (
    <div className="pagination-container">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        className="pagination-btn"
      >
        ‹
      </button>
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`pagination-btn ${p === page ? 'active' : ''}`}
        >
          {p}
        </button>
      ))}
      <button
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
        className="pagination-btn"
      >
        ›
      </button>
    </div>
  );
}