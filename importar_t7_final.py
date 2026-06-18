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
LOTE = 20

TIPOS = {
    "transformador": "Transformador",
    "disjuntor": "Disjuntor",
    "para-raios": "Para-raio",
    "reator": "Reator",
    "seccionador": "Seccionador",
    "transformador de corrente": "TC",
    "transformador de potencial": "TP",
    "bobina de bloqueio": "Bobina de Bloqueio",
    "dispositivo de prote": "Relé",
    "registrador de perturba": "Registrador de Perturbação",
}


def achar_idx(cab, palavras):
    for i, c in enumerate(cab):
        cl = c.strip().lower()
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


def main():
    total_geral = 0
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
            print(f"[{arq}] Tipo nao reconhecido, pulando")
            continue

        caminho = os.path.join(PASTA, arq)
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
                    ignorados += 1
                    continue

                fabricante = row[idx_fabricante].strip() if idx_fabricante is not None and idx_fabricante < len(row) else ""
                mrid = row[idx_mrid].strip() if idx_mrid is not None and idx_mrid < len(row) else ""
                subestacao = row[idx_subestacao].strip() if idx_subestacao is not None and idx_subestacao < len(row) else ""
                data = row[idx_data].strip() if idx_data is not None and idx_data < len(row) else ""
                status = extrair_status(row[0].strip() if len(row) > 0 else "")

                linhas.append((codigo, fabricante, mrid, subestacao, data, status))

        print(f"[{arq}] {len(linhas)} registros para importar como '{tipo}'...", end=" ")

        qtd = 0
        conn = get_db()
        try:
            for inicio in range(0, len(linhas), LOTE):
                lote = linhas[inicio:inicio + LOTE]
                for codigo, fabricante, mrid, subestacao, data, status in lote:
                    for tentativa in range(3):
                        try:
                            cur = conn.execute("SELECT id FROM equipamentos WHERE codigo = %s", (codigo,))
                            existente = cur.fetchone()
                            if existente:
                                conn.execute("""
                                    UPDATE equipamentos SET tipo=%s, fabricante=%s, local_instalacao=%s,
                                        idbdit=%s, data_cadastro=%s, status=%s, regional=%s
                                    WHERE id=%s
                                """, (tipo, fabricante, subestacao, mrid, data, status, REGIONAL, existente["id"]))
                            else:
                                conn.execute("""
                                    INSERT INTO equipamentos
                                        (codigo, regional, tipo, fabricante, local_instalacao, idbdit, data_cadastro, status)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                                """, (codigo, REGIONAL, tipo, fabricante, subestacao, mrid, data, status))
                            qtd += 1
                            break
                        except Exception as e:
                            if tentativa < 2:
                                time.sleep(2)
                            else:
                                print(f"\n  Erro em {codigo}: {e}")
                conn.commit()
        except Exception as e:
            print(f"\n  ERRO CRITICO: {e}")
            conn.rollback()
        finally:
            conn.close()

        total_geral += qtd
        print(f"{qtd} importados")

    print(f"\n>> FINALIZADO! Total: {total_geral} importados, {ignorados} ignorados")


if __name__ == "__main__":
    main()
