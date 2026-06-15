import pytest
import tempfile
import os
from flask import Flask
from routes import bp
from db import init_db, padronizar_tipo
import config

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    config.DATABASE_URL = ''
    config.DB_PATH = db_path

    app = Flask(__name__)
    app.secret_key = 'teste'
    app.register_blueprint(bp)

    from db import USING_PG
    if not USING_PG:
        init_db()

    yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

# -----------------------------------------------------------------------

def test_pagina_inicial(client):
    r = client.get('/')
    assert r.status_code == 200

def test_pagina_cadastrar(client):
    r = client.get('/cadastrar')
    assert r.status_code == 200

def test_pagina_importar(client):
    r = client.get('/importar')
    assert r.status_code == 200

def test_pagina_relatorio(client):
    r = client.get('/relatorio')
    assert r.status_code == 200

def test_exportar_excel(client):
    r = client.get('/exportar')
    assert r.status_code == 200
    assert 'spreadsheet' in r.mimetype

def test_api_equipamentos_vazia(client):
    r = client.get('/api/equipamentos')
    assert r.status_code == 200
    dados = r.get_json()
    assert len(dados) == 0

def test_cadastrar_equipamento(client):
    r = client.post('/cadastrar', data={
        'codigo': '888888',
        'regional': 'Nordeste',
        'tipo': 'Disjuntor',
        'data_cadastro': '2026-06-15',
        'data_solicitacao': '2026-06-15',
    }, follow_redirects=True)
    assert r.status_code == 200

    r = client.get('/api/equipamentos')
    dados = r.get_json()
    codigos = [d['codigo'] for d in dados]
    assert '888888' in codigos

def test_cadastrar_codigo_duplicado(client):
    client.post('/cadastrar', data={
        'codigo': '999999', 'regional': 'Sul', 'tipo': 'Relé',
        'data_cadastro': '2026-06-15', 'data_solicitacao': '',
    }, follow_redirects=True)
    r = client.post('/cadastrar', data={
        'codigo': '999999', 'regional': 'Sul', 'tipo': 'Relé',
        'data_cadastro': '2026-06-15', 'data_solicitacao': '',
    }, follow_redirects=True)
    assert r.status_code == 200

def test_deletar_equipamento(client):
    client.post('/cadastrar', data={
        'codigo': '111111', 'regional': 'Norte', 'tipo': 'Chave',
        'data_cadastro': '', 'data_solicitacao': '',
    }, follow_redirects=True)

    r = client.get('/api/equipamentos')
    dados = r.get_json()
    if dados:
        eq_id = dados[0]['id']
        r = client.post(f'/deletar/{eq_id}', follow_redirects=True)
        assert r.status_code == 200

def test_padronizar_tipo():
    assert padronizar_tipo("TRANSFORMADOR DE POTENCIAL") == "Transformador de Potencial"
    assert padronizar_tipo("para-raios") == "Para-Raios"
    assert padronizar_tipo("CHAVE SECCIONADORA") == "Chave Seccionadora"

def test_rota_invalida(client):
    r = client.get('/pagina-que-nao-existe')
    assert r.status_code == 404
