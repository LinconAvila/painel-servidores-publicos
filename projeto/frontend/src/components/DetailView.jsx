import { Avatar } from './Avatar';
import { StatusBadge } from './StatusBadge';
import { formatarMoeda, formatarData } from '../utils/formatters';

function DetailField({ label, value, highlight = false }) {
  if (value === null || value === undefined || value === '') return null;

  return (
    <div className="detail-field-row">
      <span className="detail-field-label">{label}</span>
      <span className={`detail-field-value ${highlight ? 'highlight' : ''}`}>
        {value}
      </span>
    </div>
  );
}

export function DetailView({ servidor, onBack }) {
  const isAtivo = (servidor.status || '').toLowerCase() === 'ativo';

  return (
    <div className="detail-container">
      <button onClick={onBack} className="btn-back">
        ‹ Voltar à busca
      </button>

      <div className="detail-card">
        <div className="detail-header">
          <Avatar nome={servidor.nome} />
          <div className="detail-title-group">
            <div className="detail-name-row">
              <h2>{servidor.nome}</h2>
              <StatusBadge status={servidor.status} />
            </div>
            <p className="detail-cargo">{servidor.cargo}</p>
          </div>
        </div>

        <div className="detail-divider" />

        <div className="detail-fields">
          <DetailField
            label="Remuneração"
            value={formatarMoeda(servidor.remuneracao)}
            highlight
          />
          <DetailField label="Órgão" value={servidor.orgao} />
          {servidor.siglaOrgao && (
            <DetailField label="Sigla do órgão" value={servidor.siglaOrgao} />
          )}
          <DetailField
            label="UF"
            value={isAtivo ? (servidor.uf || 'Não informada') : '— não disponível para aposentados'}
          />
          {servidor.carreira && (
            <DetailField label="Carreira" value={servidor.carreira} />
          )}
          {servidor.matricula && (
            <DetailField label="Matrícula" value={servidor.matricula} />
          )}
          {servidor.tipoIngresso && (
            <DetailField label="Tipo de ingresso" value={servidor.tipoIngresso} />
          )}
          {servidor.dataIngresso && (
            <DetailField label="Data de ingresso" value={formatarData(servidor.dataIngresso)} />
          )}
          {!isAtivo && servidor.tipoAposentadoria && (
            <DetailField label="Tipo de aposentadoria" value={servidor.tipoAposentadoria} />
          )}
          {!isAtivo && servidor.dataAposentadoria && (
            <DetailField label="Data de aposentadoria" value={formatarData(servidor.dataAposentadoria)} />
          )}
        </div>
      </div>
    </div>
  );
}
