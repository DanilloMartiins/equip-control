import csv
import re
import os
import sys
import time

_print = print
def print(*a, **kw):
    kw["flush"] = True
    _print(*a, **kw)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db

PASTA = r"C:\Users\Danillo Martins\OneDrive - eletrobras.com\Área de Trabalho\DB\AXIA NORDESTE"
REGIONAL = "AXIA NORDESTE"
LOTE = 50
MAX_TENTATIVAS = 3

TIPOS = {
    "transformador": "Transformador",
    "disjuntor": "Disjuntor",
    "para-raios": "Para-raio",
    "reator em deriva": "Reator",
    "seccionador": "Seccionador",
    "transformador de corrente": "TC",
    "transformador de potencial": "TP",
    "bobina de bloqueio": "Bobina de Bloqueio",
    "dispositivo de prote": "Relé",
    "registrador de perturba": "Registrador de Perturbação",
}


def extrair_status(texto):
    if not texto:
        return "pendente"
    m = re.search(r'title="([^"]+)"', texto)
    if m:
        st = m.group(1).strip().lower()
        if "enviado" in st and "não" not in st:
            return "concluido"
    return "pendente"


def conectar():
    for tentativa in range(MAX_TENTATIVAS):
        try:
            conn = get_db()
            return conn
        except Exception as e:
            print(f"  Erro ao conectar (tentativa {tentativa+1}): {e}")
            time.sleep(2)
    raise Exception("Nao foi possivel conectar ao banco")


def main():
    print(">> Iniciando importacao...")
    print(f">> Pasta: {PASTA}")
    print(f">> Arquivos encontrados: {len([a for a in os.listdir(PASTA) if a.endswith('.csv')])}")

    # Primeiro: limpar registros ja importados
    print(">> Limpando registros anteriores da AXIA NORDESTE...")
    conn = conectar()
    cur = conn.execute("SELECT COUNT(*) AS total FROM equipamentos WHERE regional = %s", (REGIONAL,))
    antes = cur.fetchone()["total"]
    print(f"  Registros encontrados: {antes}")

    conn.execute("DELETE FROM equipamentos WHERE regional = %s", (REGIONAL,))
    conn.commit()
    print(f"  Registros removidos!")
    conn.close()

    # Segundo: importar tudo
    print("\n>> Importando CSVs...")
    total = 0
    ignorados = 0

    for arq in sorted(os.listdir(PASTA)):
        if not arq.endswith(".csv"):
            continue

        nome_base = arq.rsplit(".", 1)[0].lower()
        tipo = None
        for chave, valor in TIPOS.items():
            if chave in nome_base:
                tipo = valor
                break
        if not tipo:
            print(f"  Tipo nao reconhecido: {arq}")
            continue

        caminho = os.path.join(PASTA, arq)
        linhas = []
        with open(caminho, encoding="cp1252") as f:
            reader = csv.reader(f, delimiter=";")
            cab = next(reader)

            idx_codigo = None
            idx_fabricante = None
            idx_mrid = None
            idx_subestacao = None
            idx_data = None

            for i, c in enumerate(cab):
                cl = c.strip().lower()
                if "nome do equipamento" in cl:
                    idx_codigo = i
                elif cl == "fabricante":
                    idx_fabricante = i
                elif cl.strip() == "mrid":
                    idx_mrid = i
                elif "nome da subesta" in cl:
                    idx_subestacao = i
                elif "entrada em opera" in cl:
                    idx_data = i

            for row in reader:
                codigo_raw = row[idx_codigo].strip() if idx_codigo is not None and idx_codigo < len(row) else ""
                codigo = re.sub(r"<[^>]+>", "", codigo_raw).strip()
                if not codigo:
                    ignorados += 1
                    continue

                fabricante = row[idx_fabricante].strip() if idx_fabricante is not None and idx_fabricante < len(row) else ""
                mrid = row[idx_mrid].strip() if idx_mrid is not None and idx_mrid < len(row) else ""
                subestacao = row[idx_subestacao].strip() if idx_subestacao is not None and idx_subestacao < len(row) else ""
                data = row[idx_data].strip() if idx_data is not None and idx_data < len(row) else ""
                status = extrair_status(row[0].strip() if len(row) > 0 else "")

                linhas.append((codigo, REGIONAL, tipo, fabricante, subestacao, mrid, data, status))

        print(f"  {arq}: {len(linhas)} linhas")

        # Importa em lotes
        conn = conectar()
        qtd_ok = 0
        for inicio in range(0, len(linhas), LOTE):
            lote = linhas[inicio:inicio + LOTE]
            for tentativa in range(MAX_TENTATIVAS):
                try:
                    for dados in lote:
                        cod, reg, tip, fab, sub, mrid, dt, st = dados
                        cur = conn.execute("SELECT id FROM equipamentos WHERE codigo = %s", (cod,))
                        existente = cur.fetchone()
                        if existente:
                            conn.execute("""
                                UPDATE equipamentos SET tipo=%s, fabricante=%s, local_instalacao=%s,
                                    idbdit=%s, data_cadastro=%s, status=%s, regional=%s
                                WHERE id=%s
                            """, (tip, fab, sub, mrid, dt, st, reg, existente["id"]))
                        else:
                            conn.execute("""
                                INSERT INTO equipamentos
                                    (codigo, regional, tipo, fabricante, local_instalacao, idbdit, data_cadastro, status)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            """, (cod, reg, tip, fab, sub, mrid, dt, st))
                        qtd_ok += 1
                    conn.commit()
                    break
                except Exception as e:
                    print(f"    Erro no lote {inicio//LOTE +1}, tentativa {tentativa+1}: {e}")
                    if tentativa < MAX_TENTATIVAS - 1:
                        conn.close()
                        time.sleep(3)
                        conn = conectar()
                    else:
                        print(f"    Desistindo do lote apos {MAX_TENTATIVAS} tentativas")
                        conn.rollback()

        conn.close()
        total += qtd_ok

    print(f"\n>> Finalizado!")
    print(f"  Importados: {total}")
    print(f"  Ignorados: {ignorados}")


if __name__ == "__main__":
    main()
