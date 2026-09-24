import React from 'react';

export function Header() {
  return (
    <header className="app-header">
      <div className="header-container">
        <svg
          className="header-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 21h18" />
          <path d="M3 10h18" />
          <path d="M5 6l7-3 7 3" />
          <path d="M4 10v11" />
          <path d="M20 10v11" />
          <path d="M8 10v11" />
          <path d="M12 10v11" />
          <path d="M16 10v11" />
        </svg>
        <h1 className="header-title">Painel de Servidores Públicos</h1>
      </div>
    </header>
  );
}