-- diagnostico
EXPLAIN ANALYZE 
SELECT * FROM servidores_ativos 
WHERE cargo = 'ANALISTA DE TECNOLOGIA DA INFORMACAO' AND uf = 'RS';

EXPLAIN ANALYZE 
SELECT * FROM servidores_ativos 
WHERE orgao = 'UNIVERSIDADE FEDERAL DO RIO GRANDE' AND uf = 'RS';

-- indices compostos
CREATE INDEX idx_servidores_ativos_cargo_uf ON servidores_ativos (cargo, uf);

CREATE INDEX idx_servidores_ativos_orgao_uf ON servidores_ativos (orgao, uf);

-- testando apos os indices
EXPLAIN ANALYZE 
SELECT * FROM servidores_ativos 
WHERE cargo = 'ANALISTA DE TECNOLOGIA DA INFORMACAO' AND uf = 'RS';

EXPLAIN ANALYZE 
SELECT * FROM servidores_ativos 
WHERE orgao = 'UNIVERSIDADE FEDERAL DO RIO GRANDE' AND uf = 'RS';