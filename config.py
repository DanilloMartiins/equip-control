import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'troque-isso-em-producao')

LOGIN_USER = os.getenv('LOGIN_USER', 'DanilloMartins')
LOGIN_PASS_HASH = os.getenv('LOGIN_PASS_HASH', 'scrypt:32768:8:1$SbuxQNYQJjV80z85$2325cdd1eadcae679c5365e3c54568c4070d343ad677ef4e522c1f6fe09589b327ae571eaa1e13338f8be84be9b2891fd4e5139dd42fb731dd53aaa9bd39a181')
DATABASE_URL = os.getenv('DATABASE_URL') or ''  # Supabase connection string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'axia.db')  # fallback SQLite

REGIONAIS = ['AXIA Norte', 'AXIA Nordeste', 'AXIA Sudeste', 'AXIA Sul']
