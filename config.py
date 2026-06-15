import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'troque-isso-em-producao')
DATABASE_URL = os.getenv('DATABASE_URL') or ''  # Supabase connection string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'axia.db')  # fallback SQLite

REGIONAIS = ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']
