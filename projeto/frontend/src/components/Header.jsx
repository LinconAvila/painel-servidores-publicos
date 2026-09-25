import React from 'react';

export function Header() {
  return (
    <header className="main-header">
      <div className="header-content">
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          className="header-icon"
        >
          <path
            d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v4M12 14v4M16 14v4"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div>
          <span className="header-title">
            Painel de Servidores Públicos
          </span>
        </div>
        <div className="header-badge">
          <span>SIAPE</span>
        </div>
      </div>
    </header>
  );
}