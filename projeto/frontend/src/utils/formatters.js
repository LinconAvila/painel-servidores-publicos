export function formatarMoeda(valor) {
  if (valor === null || valor === undefined || valor === '' || isNaN(Number(valor))) {
    return '—';
  }
  return Number(valor).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

export function formatarData(dataStr) {
  if (!dataStr) return null;
  const apenasData = String(dataStr).split('T')[0];
  const partes = apenasData.split('-');
  if (partes.length === 3 && partes[0].length === 4) {
    const [ano, mes, dia] = partes;
    return `${dia.padStart(2, '0')}/${mes.padStart(2, '0')}/${ano}`;
  }
  return dataStr;
}
