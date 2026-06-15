from datetime import datetime
from flask import Flask
from config import SECRET_KEY
from db import init_db
from routes import bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(bp)

@app.context_processor
def inject_now():
    return {'now': datetime.now}

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
