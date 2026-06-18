import sys
sys.path.insert(0, r"C:\Users\Danillo Martins\OneDrive - eletrobras.com\Projetos - pessoais\sistema-axia")
from db import get_db
conn = get_db()
conn.execute("DELETE FROM equipamentos WHERE regional = %s AND tipo = 'Transformador'", ("AXIA NORDESTE",))
conn.commit()
conn.close()
print("Registros 'Transformador' da AXIA NORDESTE deletados. Agora reimportar na ordem certa.")
