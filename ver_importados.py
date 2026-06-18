import sys
sys.path.insert(0, r"C:\Users\Danillo Martins\OneDrive - eletrobras.com\Projetos - pessoais\sistema-axia")
from db import get_db
conn = get_db()
dados = conn.execute("SELECT tipo, COUNT(*) AS qtd FROM equipamentos WHERE regional = %s GROUP BY tipo ORDER BY qtd DESC", ("AXIA NORDESTE",)).fetchall()
total = conn.execute("SELECT COUNT(*) AS total FROM equipamentos WHERE regional = %s", ("AXIA NORDESTE",)).fetchone()["total"]
conn.close()
print(f"Total AXIA NORDESTE: {total}")
for d in dados:
    print(f"  {d['tipo']}: {d['qtd']}")
