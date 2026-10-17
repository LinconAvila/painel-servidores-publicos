-- procurando por nomes que se repetem
SELECT nome, COUNT(*) AS total 
FROM servidores_ativos 
GROUP BY nome 
HAVING COUNT(*) > 15 
ORDER BY total DESC 
LIMIT 5;

SELECT COUNT(*) AS total_real 
FROM servidores_ativos 
WHERE LOWER(nome) = LOWER('JOSE CARLOS DA SILVA');

SELECT id, nome, cargo, orgao, uf 
FROM servidores_ativos 
WHERE LOWER(nome) = LOWER('JOAO BATISTA DA SILVA')
ORDER BY id
LIMIT 10 OFFSET 0;

SELECT id, nome, cargo, orgao, uf 
FROM servidores_ativos 
WHERE LOWER(nome) = LOWER('MARIA JOSE DA SILVA')
ORDER BY id
LIMIT 10 OFFSET 10;

SELECT id, nome, cargo, orgao, uf 
FROM servidores_ativos 
WHERE LOWER(nome) = LOWER('ANTONIO CARLOS DA SILVA')
ORDER BY id
LIMIT 10 OFFSET 20;