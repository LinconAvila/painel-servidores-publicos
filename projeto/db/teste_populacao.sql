SELECT COUNT(nome)
FROM servidores_aposentados sa ;

SELECT COUNT(nome)
FROM servidores_ativos sa ;

-- Desempenho query em servidores_ativos
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_ativos 
WHERE nome = 'LUCIA DE FREITAS ALMEIDA';

EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_ativos 
WHERE cargo = 'ANALISTA DE SISTEMAS';


EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_ativos 
WHERE uf = 'RS';


EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_ativos 
WHERE orgao = 'MINISTERIO DA EDUCACAO';

-- Desempenho query em servidores_aposentados
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_aposentados
WHERE nome = 'JULIANA NUNES FERREIRA RIOS';

EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_aposentados
WHERE matricula = 262830433391;

EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM servidores_aposentados 
WHERE sigla_orgao = 'FURG';

