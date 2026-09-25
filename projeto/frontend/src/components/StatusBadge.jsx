import React from 'react';

export function StatusBadge({ status }) {
  const isAtivo = status === 'Ativo';
  return (
    <span
      className="status-badge"
      style={{
        backgroundColor: isAtivo ? '#D1FAE5' : '#F3F4F6',
        color: isAtivo ? '#065F46' : '#374151',
      }}
    >
      {status}
    </span>
  );
}