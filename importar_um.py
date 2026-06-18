import csv, re, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db

PASTA = r"C:\Users\Danillo Martins\OneDrive - eletrobras.com\Área de Trabalho\DB\AXIA NORDESTE"
REGIONAL = "AXIA NORDESTE"
LOTE = 20

TIPOS = {
    "transformador de corrente": "TC",
    "transformador de potencial": "TP",
    "transformador": "Transformador",
    "disjuntor": "Disjuntor",
    "para-raios": "Para-raio",
    "reator": "Reator",
    "seccionador": "Seccionador",
    "bobina de bloqueio": "Bobina de Bloqueio",
    "dispositivo de prote": "Relé",
    "registrador de perturba": "Registrador de Perturbação",
}

import unicodedata
def remover_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def achar_idx(cab, palavras):
    for i, c in enumerate(cab):
        cl = remover_acentos(c.strip().lower())
        for p in palavras:
            if p in cl:
                return i
    return None

def extrair_status(texto):
    if not texto:
        return "pendente"
    m = re.search(r'title="([^"]+)"', texto)
    if m:
        st = m.group(1).strip().lower()
        if "enviado" in st and "não" not in st:
            return "concluido"
    return "pendente"

arquivo = sys.argv[1] if len(sys.argv) > 1 else ""
if not arquivo:
    arquivos = [a for a in sorted(os.listdir(PASTA)) if a.endswith(".csv")]
    ja_tem = set(r["tipo"] for r in get_db().execute("SELECT DISTINCT tipo FROM equipamentos WHERE regional = %s", (REGIONAL,)).fetchall())
    for a in arquivos:
        nome_base = a.rsplit(".", 1)[0].lower()
        tipo = None
        for chave, valor in TIPOS.items():
            if chave in nome_base:
                tipo = valor
                break
        if tipo and tipo not in ja_tem:
            print(f"  {a} -> {tipo}")
    arquivo = input("\nDigite o nome do arquivo pra importar: ").strip()

caminho = os.path.join(PASTA, arquivo)
if not os.path.exists(caminho):
    print(f"Arquivo nao encontrado: {caminho}")
    sys.exit(1)

nome_base = arquivo.rsplit(".", 1)[0].lower()
tipo = None
for chave, valor in TIPOS.items():
    if chave in nome_base:
        tipo = valor
        break
if not tipo:
    print(f"Tipo nao reconhecido pra: {arquivo}")
    sys.exit(1)

with open(caminho, encoding="cp1252") as f:
    reader = csv.reader(f, delimiter=";")
    cab = next(reader)
    idx_codigo = achar_idx(cab, ["numero equipamento", "numero do equipamento", "nome do equipamento", "nome"])
    idx_fabricante = achar_idx(cab, ["fabricante"])
    idx_mrid = achar_idx(cab, ["mrid"])
    idx_subestacao = achar_idx(cab, ["nome da subesta"])
    idx_data = achar_idx(cab, ["entrada em opera"])

    linhas = []
    for row in reader:
        codigo_raw = row[idx_codigo].strip() if idx_codigo is not None and idx_codigo < len(row) else ""
        codigo = re.sub(r"<[^>]+>", "", codigo_raw).strip()
        if not codigo:
            continue
        fabricante = row[idx_fabricante].strip() if idx_fabricante is not None and idx_fabricante < len(row) else ""
        mrid = row[idx_mrid].strip() if idx_mrid is not None and idx_mrid < len(row) else ""
        subestacao = row[idx_subestacao].strip() if idx_subestacao is not None and idx_subestacao < len(row) else ""
        data = row[idx_data].strip() if idx_data is not None and idx_data < len(row) else ""
        status = extrair_status(row[0].strip() if len(row) > 0 else "")
        linhas.append((codigo, fabricante, mrid, subestacao, data, status))

print(f"Importando {len(linhas)} registros como '{tipo}'...")
qtd = 0
conn = get_db()
for inicio in range(0, len(linhas), LOTE):
    lote = linhas[inicio:inicio + LOTE]
    for codigo, fabricante, mrid, subestacao, data, status in lote:
        for tentativa in range(3):
            try:
                cur = conn.execute("SELECT id FROM equipamentos WHERE codigo = %s", (codigo,))
                existente = cur.fetchone()
                if existente:
                    conn.execute("""UPDATE equipamentos SET tipo=%s, fabricante=%s, local_instalacao=%s,
                        idbdit=%s, data_cadastro=%s, status=%s, regional=%s WHERE id=%s
                    """, (tipo, fabricante, subestacao, mrid, data, status, REGIONAL, existente["id"]))
                else:
                    conn.execute("""INSERT INTO equipamentos
                        (codigo, regional, tipo, fabricante, local_instalacao, idbdit, data_cadastro, status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (codigo, REGIONAL, tipo, fabricante, subestacao, mrid, data, status))
                qtd += 1
                break
            except Exception as e:
                if tentativa < 2:
                    time.sleep(2)
    if inicio % 200 == 0 and inicio > 0:
        conn.commit()
        print(f"  {qtd}/{len(linhas)}...")
conn.commit()
conn.close()
print(f"Finalizado! {qtd} registros importados como '{tipo}'")
