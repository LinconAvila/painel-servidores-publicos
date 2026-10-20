FROM python:3.12-slim

WORKDIR /etl


RUN pip install --no-cache-dir psycopg2-binary python-dotenv

# O script e os CSVs vêm do volume montado em /etl (ver docker-compose.yml).
CMD ["python", "importacao.py"]