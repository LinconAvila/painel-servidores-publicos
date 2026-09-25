from flask import Flask

app = Flask(__name__)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/api/servidores")
def buscar_servidores():
    return {"status": "nao implementado"}, 501
