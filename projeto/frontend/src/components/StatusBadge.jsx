
export function StatusBadge({ status }) {
  const isAtivo = (status || '').toLowerCase() === 'ativo';
  return (
    <span
      className={`status-badge ${isAtivo ? 'status-ativo' : 'status-aposentado'}`}
      style={{
        backgroundColor: isAtivo ? '#D1FAE5' : '#F3F4F6',
        color: isAtivo ? '#065F46' : '#374151',
      }}
    >
      {isAtivo ? 'Ativo' : 'Aposentado'}
    </span>
  );
}
