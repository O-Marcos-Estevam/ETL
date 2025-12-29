"""Mostra dados que subiram para o banco após execução do qore_upload_xml_acess.py"""
import pyodbc

DB_PATH = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\09. Base_de_Dados\\Base Fundos_v2.accdb'
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + DB_PATH
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Fundos e datas que foram processados
fundos = ['AMG', 'ESTOCOLMO', 'OSLO']
datas = ['2025-12-08', '2025-12-09', '2025-12-10', '2025-12-11', '2025-12-12']

print("=" * 80)
print("DADOS INSERIDOS - COTAS_PATRIMONIO_QORE")
print("=" * 80)
print(f"{'DATA':<12} {'FUNDO':<15} {'PL Posição':>18}")
print("-" * 80)

for data in datas:
    for fundo in fundos:
        cursor.execute("""
            SELECT [DATA_INPUT], [FUNDO], [PL Posição] 
            FROM Cotas_Patrimonio_Qore 
            WHERE [DATA_INPUT] = ? AND [FUNDO] = ?
        """, (data, fundo))
        row = cursor.fetchone()
        if row:
            dt = row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0])
            print(f"{dt:<12} {row[1]:<15} {row[2]:>18,.2f}")

print("\n" + "=" * 80)
print("DADOS INSERIDOS - CAIXA_QORE")
print("=" * 80)
print(f"{'DATA':<12} {'FUNDO':<15} {'DESCRIÇÃO':<40} {'VALOR':>12}")
print("-" * 80)

for data in datas:
    for fundo in fundos:
        cursor.execute("""
            SELECT [DATA_INPUT], [FUNDO], [Descrição], [Valor] 
            FROM Caixa_Qore 
            WHERE [DATA_INPUT] = ? AND [FUNDO] = ?
        """, (data, fundo))
        rows = cursor.fetchall()
        for row in rows:
            dt = row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0])
            desc = (row[2][:37] + '...') if len(str(row[2])) > 40 else row[2]
            print(f"{dt:<12} {row[1]:<15} {desc:<40} {row[3]:>12,.2f}")

conn.close()
print("\n[OK] Consulta finalizada.")
