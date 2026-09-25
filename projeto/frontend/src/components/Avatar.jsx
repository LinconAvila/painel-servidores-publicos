import React from 'react';

function getInitials(nome) {
  if (!nome) return '';
  const parts = nome.trim().split(' ');
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({ nome }) {
  return (
    <div className="avatar-circle">
      {getInitials(nome)}
    </div>
  );
}