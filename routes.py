from io import BytesIO
from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl import load_workbook

from config import REGIONAIS
from db import get_db, padronizar_tipo, IntegrityError

bp = Blueprint('routes', __name__)

# -----------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------
@bp.route('/')
def index() -> str:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM equipamentos").fetchone()[0]
    por_regional = conn.execute("""
        SELECT regional, COUNT(*) as qtd FROM equipamentos
        GROUP BY regional ORDER BY qtd DESC
    """).fetchall()
    por_tipo = conn.execute("""
        SELECT tipo, COUNT(*) as qtd FROM equipamentos
        GROUP BY tipo ORDER BY qtd DESC
    """).fetchall()
    recentes = conn.execute("""
        SELECT * FROM equipamentos ORDER BY created_at DESC LIMIT 10
    """).fetchall()
    conn.close()

    return render_template('index.html',
        total=total, por_regional=por_regional, por_tipo=por_tipo,
        recentes=recentes, regionais=REGIONAIS)

# -----------------------------------------------------------------------
# CADASTRAR
# -----------------------------------------------------------------------
@bp.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar() -> str:
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        regional = request.form['regional']
        tipo = padronizar_tipo(request.form['tipo'])
        data_cad = request.form.get('data_cadastro') or None
        data_sol = request.form.get('data_solicitacao') or None

        if not codigo or not regional or not tipo:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('routes.cadastrar'))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO equipamentos (codigo, regional, tipo, data_cadastro, data_solicitacao) VALUES (%s, %s, %s, %s, %s)",
                (codigo, regional, tipo, data_cad, data_sol)
            )
            conn.commit()
            flash('Equipamento cadastrado com sucesso!', 'success')
            return redirect(url_for('routes.index'))
        except IntegrityError:
            flash(f'Código {codigo} já existe no sistema.', 'danger')
        finally:
            conn.close()

    return render_template('cadastrar.html', regionais=REGIONAIS, hoje=date.today().isoformat())

# -----------------------------------------------------------------------
# IMPORTAR EXCEL
# -----------------------------------------------------------------------
@bp.route('/importar', methods=['GET', 'POST'])
def importar() -> str:
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo enviado.', 'danger')
            return redirect(url_for('routes.importar'))

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Selecione um arquivo.', 'danger')
            return redirect(url_for('routes.importar'))

        try:
            wb = load_workbook(arquivo)
            ws = wb.active

            importados = 0
            ignorados = 0
            conn = get_db()

            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
                raw_id = row[0]
                raw_regional = str(row[1]).strip() if row[1] else ''
                raw_tipo = str(row[2]).strip() if row[2] else ''
                raw_cad = row[3]
                raw_env = row[4]

                if raw_id is None or raw_regional.lower() not in [r.lower() for r in REGIONAIS]:
                    ignorados += 1
                    continue

                codigo = str(int(raw_id)) if isinstance(raw_id, float) else str(raw_id)
                regional = raw_regional
                tipo = padronizar_tipo(raw_tipo)

                data_cad = str(raw_cad)[:10] if raw_cad else None
                data_env = str(raw_env)[:10] if raw_env else None

                try:
                    conn.execute(
                        "INSERT INTO equipamentos (codigo, regional, tipo, data_cadastro, data_solicitacao) VALUES (%s, %s, %s, %s, %s)",
                        (codigo, regional, tipo, data_cad, data_env)
                    )
                    importados += 1
                except IntegrityError:
                    ignorados += 1

            conn.commit()
            conn.close()
            flash(f'Importação concluída! {importados} importados, {ignorados} ignorados.', 'success')
            return redirect(url_for('routes.index'))
        except Exception as e:
            flash(f'Erro ao importar: {str(e)}', 'danger')
            return redirect(url_for('routes.importar'))

    return render_template('importar.html')

# -----------------------------------------------------------------------
# RELATORIO WEB
# -----------------------------------------------------------------------
@bp.route('/relatorio')
def relatorio() -> str:
    conn = get_db()
    equipamentos = conn.execute("SELECT * FROM equipamentos ORDER BY regional, tipo, codigo").fetchall()
    por_regional = conn.execute("""
        SELECT regional, COUNT(*) as qtd FROM equipamentos GROUP BY regional ORDER BY qtd DESC
    """).fetchall()
    por_tipo = conn.execute("""
        SELECT tipo, COUNT(*) as qtd FROM equipamentos GROUP BY tipo ORDER BY qtd DESC
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM equipamentos").fetchone()[0]
    conn.close()

    return render_template('relatorio.html',
        equipamentos=equipamentos, por_regional=por_regional, por_tipo=por_tipo, total=total)

# -----------------------------------------------------------------------
# EXPORTAR EXCEL
# -----------------------------------------------------------------------
@bp.route('/exportar')
def exportar():
    conn = get_db()
    dados = conn.execute("""
        SELECT codigo, regional, tipo, data_cadastro, data_solicitacao
        FROM equipamentos ORDER BY regional, tipo, codigo
    """).fetchall()
    por_regional = conn.execute("""
        SELECT regional, COUNT(*) as qtd FROM equipamentos GROUP BY regional ORDER BY qtd DESC
    """).fetchall()
    por_tipo = conn.execute("""
        SELECT tipo, COUNT(*) as qtd FROM equipamentos GROUP BY tipo ORDER BY qtd DESC
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM equipamentos").fetchone()[0]
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Equipamentos Cadastrados"

    AZUL_E = "1F4E79"
    AZUL_M = "2E75B6"
    thin = Border(
        left=Side(style="thin", color="B4C6E7"),
        right=Side(style="thin", color="B4C6E7"),
        top=Side(style="thin", color="B4C6E7"),
        bottom=Side(style="thin", color="B4C6E7"),
    )
    fill_titulo = PatternFill(start_color=AZUL_E, end_color=AZUL_E, fill_type="solid")
    fill_header = PatternFill(start_color=AZUL_M, end_color=AZUL_M, fill_type="solid")
    fill_l1 = PatternFill(start_color="F2F7FB", end_color="F2F7FB", fill_type="solid")
    fill_l2 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    ca = Alignment(horizontal="center", vertical="center")
    cl = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A1:E1")
    ws["A1"].value = "RELATÓRIO DE EQUIPAMENTOS CADASTRADOS - AXIA"
    ws["A1"].font = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = fill_titulo
    ws["A1"].alignment = ca
    ws.row_dimensions[1].height = 40

    ws.merge_cells("A2:E2")
    ws["A2"].value = f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    ws["A2"].font = Font(name="Calibri", size=10, color="B4C6E7")
    ws["A2"].fill = fill_titulo
    ws["A2"].alignment = ca
    ws.row_dimensions[2].height = 22

    card_fill = PatternFill(start_color="F0F4FA", end_color="F0F4FA", fill_type="solid")
    card_border = Border(
        left=Side(style="thin", color="D0D8E8"),
        right=Side(style="thin", color="D0D8E8"),
        top=Side(style="thin", color="D0D8E8"),
        bottom=Side(style="thin", color="D0D8E8"),
    )
    ws.merge_cells("A4:B4")
    ws["A4"].value = "Total de Equipamentos"
    ws["A4"].font = Font(name="Calibri", size=9, color="666666")
    ws["A4"].alignment = ca
    ws.merge_cells("A5:B5")
    ws["A5"].value = total
    ws["A5"].font = Font(name="Calibri", size=14, bold=True, color=AZUL_E)
    ws["A5"].alignment = ca

    ws.merge_cells("C4:C4")
    ws["C4"].value = "Regionais"
    ws["C4"].font = Font(name="Calibri", size=9, color="666666")
    ws["C4"].alignment = ca
    ws["C5"].value = len(por_regional)
    ws["C5"].font = Font(name="Calibri", size=14, bold=True, color=AZUL_E)
    ws["C5"].alignment = ca

    ws.merge_cells("D4:E4")
    ws["D4"].value = "Tipos de Equipamento"
    ws["D4"].font = Font(name="Calibri", size=9, color="666666")
    ws["D4"].alignment = ca
    ws.merge_cells("D5:E5")
    ws["D5"].value = len(por_tipo)
    ws["D5"].font = Font(name="Calibri", size=14, bold=True, color=AZUL_E)
    ws["D5"].alignment = ca

    for col_idx in range(1, 6):
        for row_idx in [4, 5]:
            c = ws.cell(row=row_idx, column=col_idx)
            c.fill = card_fill
            c.border = card_border
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 36

    h_row = 7
    headers = ["Nº Equipamento", "Regional Axia", "Tipo de Equipamento",
               "Data de Cadastro", "Data de Solicitação de Envio"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=h_row, column=col, value=h)
        c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        c.fill = fill_header
        c.alignment = ca
        c.border = thin
    ws.row_dimensions[h_row].height = 30

    for i, d in enumerate(dados):
        r = h_row + 1 + i
        fill = fill_l1 if i % 2 == 0 else fill_l2
        vals = [d['codigo'], d['regional'], d['tipo'], d['data_cadastro'], d['data_solicitacao']]
        for col_idx, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col_idx, value=val)
            c.font = Font(name="Calibri", size=10, color="333333")
            c.fill = fill
            c.border = thin
            c.alignment = ca if col_idx != 3 else cl
        ws.row_dimensions[r].height = 22

    final_row = h_row + 1 + len(dados) + 1
    ws.merge_cells(f"A{final_row}:E{final_row}")
    ws.cell(row=final_row, column=1, value="RESUMO POR REGIONAL")
    ws.cell(row=final_row, column=1).font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.cell(row=final_row, column=1).fill = fill_titulo
    ws.cell(row=final_row, column=1).alignment = ca
    for col_idx in range(2, 6):
        ws.cell(row=final_row, column=col_idx).fill = fill_titulo
        ws.cell(row=final_row, column=col_idx).border = thin
    ws.row_dimensions[final_row].height = 24

    r = final_row + 1
    bg_reg = PatternFill(start_color="E8EEF7", end_color="E8EEF7", fill_type="solid")
    for row_reg in por_regional:
        ws.cell(row=r, column=1, value="").border = thin
        ws.cell(row=r, column=1).fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
        ws.cell(row=r, column=2, value=row_reg['regional'])
        ws.cell(row=r, column=2).font = Font(name="Calibri", size=10, bold=True, color=AZUL_E)
        ws.cell(row=r, column=2).alignment = ca
        ws.cell(row=r, column=2).border = thin
        ws.cell(row=r, column=2).fill = bg_reg
        ws.merge_cells(f"C{r}:D{r}")
        ws.cell(row=r, column=3, value=f"{row_reg['qtd']} equipamento(s)")
        ws.cell(row=r, column=3).font = Font(name="Calibri", size=10, color="333333")
        ws.cell(row=r, column=3).alignment = cl
        ws.cell(row=r, column=3).border = thin
        ws.cell(row=r, column=3).fill = bg_reg
        ws.cell(row=r, column=5, value=row_reg['qtd'])
        ws.cell(row=r, column=5).font = Font(name="Calibri", size=10, bold=True, color=AZUL_E)
        ws.cell(row=r, column=5).alignment = ca
        ws.cell(row=r, column=5).border = thin
        ws.cell(row=r, column=5).fill = bg_reg
        ws.row_dimensions[r].height = 22
        r += 1

    for col_idx in range(1, 6):
        ws.cell(row=r, column=col_idx).border = thin
        ws.cell(row=r, column=col_idx).fill = fill_header
    ws.cell(row=r, column=1, value="")
    ws.cell(row=r, column=2, value="TOTAL GERAL")
    ws.cell(row=r, column=2).font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.cell(row=r, column=2).alignment = ca
    ws.merge_cells(f"C{r}:D{r}")
    ws.cell(row=r, column=3, value=f"{total} equipamento(s) cadastrado(s)")
    ws.cell(row=r, column=3).font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.cell(row=r, column=3).alignment = cl
    ws.cell(row=r, column=5, value=total)
    ws.cell(row=r, column=5).font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws.cell(row=r, column=5).alignment = ca
    ws.row_dimensions[r].height = 24
    r += 2

    ws.merge_cells(f"A{r}:E{r}")
    ws.cell(row=r, column=1, value="RESUMO POR TIPO DE EQUIPAMENTO")
    ws.cell(row=r, column=1).font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.cell(row=r, column=1).fill = fill_titulo
    ws.cell(row=r, column=1).alignment = ca
    for col_idx in range(2, 6):
        ws.cell(row=r, column=col_idx).fill = fill_titulo
        ws.cell(row=r, column=col_idx).border = thin
    ws.row_dimensions[r].height = 24
    r += 1

    bg_tipo = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
    for row_tp in por_tipo:
        ws.cell(row=r, column=1, value="").border = thin
        ws.cell(row=r, column=1).fill = bg_tipo
        ws.merge_cells(f"B{r}:C{r}")
        ws.cell(row=r, column=2, value=row_tp['tipo'])
        ws.cell(row=r, column=2).font = Font(name="Calibri", size=10, color="333333")
        ws.cell(row=r, column=2).alignment = cl
        ws.cell(row=r, column=2).border = thin
        ws.cell(row=r, column=2).fill = bg_tipo
        ws.cell(row=r, column=3).border = thin
        ws.cell(row=r, column=5, value=row_tp['qtd'])
        ws.cell(row=r, column=5).font = Font(name="Calibri", size=10, bold=True, color=AZUL_E)
        ws.cell(row=r, column=5).alignment = ca
        ws.cell(row=r, column=5).border = thin
        ws.cell(row=r, column=5).fill = bg_tipo
        ws.row_dimensions[r].height = 22
        r += 1

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 32
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 24
    ws.sheet_properties.tabColor = AZUL_M
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.paperSize = ws.PAPERSIZE_A4

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output,
        download_name=f"Relatorio_Equipamentos_AXIA_{datetime.now().strftime('%d%m%Y')}.xlsx",
        as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------------------------------------------------------
# API E DELETAR
# -----------------------------------------------------------------------
@bp.route('/api/equipamentos')
def api_equipamentos():
    conn = get_db()
    dados = conn.execute("SELECT * FROM equipamentos ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(d) for d in dados])

@bp.route('/deletar/<int:id>', methods=['POST'])
def deletar(id: int) -> str:
    conn = get_db()
    conn.execute("DELETE FROM equipamentos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Equipamento removido.', 'success')
    return redirect(url_for('routes.index'))
