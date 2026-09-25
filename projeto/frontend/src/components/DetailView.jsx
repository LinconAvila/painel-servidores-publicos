import React from 'react';
import { Avatar } from './Avatar';
import { StatusBadge } from './StatusBadge';

function DetailField({ label, value }) {
  return (
    <div className="detail-field-row">
      <span className="detail-field-label">{label}</span>
      <span className="detail-field-value">{value ?? '—'}</span>
    </div>
  );
}

export function DetailView({ servidor, onBack }) {
  const isAtivo = servidor.status === 'Ativo';

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
          <DetailField label="Órgão" value={servidor.orgao} />
          {servidor.siglaOrgao && (
            <DetailField label="Sigla do órgão" value={servidor.siglaOrgao} />
          )}
          <DetailField
            label="UF"
            value={isAtivo ? servidor.uf : '— não disponível para aposentados'}
          />
          {servidor.carreira && (
            <DetailField label="Carreira" value={servidor.carreira} />
          )}
          <DetailField label="Matrícula" value={servidor.matricula} />
          {servidor.dataIngresso && (
            <DetailField label="Data de ingresso" value={servidor.dataIngresso} />
          )}
          {servidor.tipoAposentadoria && (
            <DetailField label="Tipo de aposentadoria" value={servidor.tipoAposentadoria} />
          )}
        </div>
      </div>
    </div>
  );
}