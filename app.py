from datetime import datetime
from flask import Flask, session
from config import SECRET_KEY
from db import init_db
from routes import bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(bp)

@app.context_processor
def inject_now():
    return {'now': datetime.now}

@app.context_processor
def inject_usuario():
    usuario = session.get('usuario')
    nome = usuario or ''
    foto = ''
    if usuario:
        try:
            from db import get_db
            conn = get_db()
            row = conn.execute(
                "SELECT nome, foto FROM usuarios WHERE usuario = %s", (usuario,)
            ).fetchone()
            conn.close()
            if row:
                nome = row['nome'] or usuario
                foto = row['foto'] or ''
        except Exception:
            pass
    return {'usuario': usuario, 'usuario_nome': nome, 'usuario_foto': foto}

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
