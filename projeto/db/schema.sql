CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE servidores_ativos (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(11) NOT NULL, -- como o cpf e censurado eu nao posso usar unic pq ele se repete
    codigo_carreira VARCHAR(3) NOT NULL,
    cargo VARCHAR(45) NOT NULL,
    uf VARCHAR(2) NOT NULL,
    orgao VARCHAR(45) NOT NULL,
    remuneracao NUMERIC(20,2) NOT NULL
);

CREATE TABLE servidores_aposentados (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cpf VARCHAR(11) NOT NULL,
    matricula BIGINT NOT NULL,
    orgao VARCHAR(45) NOT NULL,
    sigla_orgao VARCHAR(255) NOT NULL,
    cargo VARCHAR(45) NOT NULL,
    tipo_aposentadoria VARCHAR(255) NOT NULL,
    data_aposentadoria date NOT NULL, -- publicacao_diploma_lega
    tipo_ingresso VARCHAR(255) NOT NULL,
    data_ingresso date NOT NULL, 
    remuneracao NUMERIC(20,2) NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_servidores_ativos_nome ON servidores_ativos USING BTREE (nome);
CREATE INDEX IF NOT EXISTS idx_servidores_ativos_cargo ON servidores_ativos USING BTREE (cargo);
CREATE INDEX IF NOT EXISTS idx_servidores_ativos_uf ON servidores_ativos USING BTREE (uf);
CREATE INDEX IF NOT EXISTS idx_servidores_ativos_orgao ON servidores_ativos USING BTREE (orgao);

CREATE INDEX IF NOT EXISTS idx_servidores_aposentados_nome ON servidores_aposentados USING BTREE (nome);
CREATE INDEX IF NOT EXISTS idx_servidores_aposentados_cargo ON servidores_aposentados USING BTREE (cargo);
CREATE INDEX IF NOT EXISTS idx_servidores_aposentados_orgao ON servidores_aposentados USING BTREE (orgao);

CREATE INDEX IF NOT EXISTS idx_servidores_ativos_nome_lower ON servidores_ativos USING BTREE (LOWER(nome));
CREATE INDEX IF NOT EXISTS idx_servidores_aposentados_nome_lower ON servidores_aposentados USING BTREE (LOWER(nome));

CREATE INDEX IF NOT EXISTS idx_servidores_ativos_cargo_uf ON servidores_ativos USING BTREE (cargo, uf);
CREATE INDEX IF NOT EXISTS idx_servidores_ativos_orgao_uf ON servidores_ativos USING BTREE (orgao, uf);

CREATE INDEX IF NOT EXISTS idx_servidores_ativos_nome_trgm ON servidores_ativos USING GIN (nome gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_servidores_aposentados_nome_trgm ON servidores_aposentados USING GIN (nome gin_trgm_ops);