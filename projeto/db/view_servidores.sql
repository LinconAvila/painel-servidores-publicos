CREATE OR REPLACE VIEW servidores AS
SELECT
    id,
    nome,
    cpf,
    cargo,
    uf,
    orgao,
    remuneracao,
    codigo_carreira,
    NULL::varchar AS sigla_orgao,
    NULL::varchar AS matricula,
    NULL::varchar AS tipo_aposentadoria,
    NULL::date AS data_aposentadoria,
    NULL::varchar AS tipo_ingresso,
    NULL::date AS data_ingresso,
    'ativo' AS status
FROM servidores_ativos
UNION ALL
SELECT
    id,
    nome,
    cpf,
    cargo,
    NULL::varchar(2) AS uf,
    orgao,
    remuneracao,
    NULL::varchar AS codigo_carreira,
    sigla_orgao,
    matricula::varchar AS matricula,
    tipo_aposentadoria,
    data_aposentadoria,
    tipo_ingresso,
    data_ingresso,
    'aposentado' AS status
FROM servidores_aposentados;
