# para usar o shell do postgres
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# deleta o banco
docker compose down -v
# sobre o banco
docker compose up --build -d
# insere os dados
docker compose run --rm etl

-Ps os csvs tao zipados 

SELECT 'ativo' AS situacao, nome, cpf, cargo, orgao, remuneracao
FROM servidores_ativos
WHERE LOWER(nome) = LOWER('MARCIO KOYA SHIMABUKURO')
UNION ALL
SELECT 'aposentado', nome, cpf, cargo, orgao, remuneracao
FROM servidores_aposentados
WHERE LOWER(nome) = LOWER('MARCIO KOYA SHIMABUKURO')
ORDER BY situacao;