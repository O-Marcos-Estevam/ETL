import pyodbc

DB_PATH = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\09. Base_de_Dados\\Base Fundos_v2.accdb'
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + DB_PATH
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Row counts
for table in ['Cotas_Patrimonio_Qore', 'Caixa_Qore']:
    cursor.execute(f'SELECT COUNT(*) FROM [{table}]')
    count = cursor.fetchone()[0]
    print(f'Rows in {table}: {count}')

# Distinct dates
for table in ['Cotas_Patrimonio_Qore', 'Caixa_Qore']:
    cursor.execute(f'SELECT DISTINCT [DATA_INPUT] FROM [{table}] ORDER BY [DATA_INPUT]')
    dates = [row[0] for row in cursor.fetchall()]
    print(f'Distinct dates in {table}: {dates}')

# Sample rows (first 5) for each table
for table in ['Cotas_Patrimonio_Qore', 'Caixa_Qore']:
    cursor.execute(f'SELECT TOP 5 * FROM [{table}]')
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    print(f'\nSample rows from {table}:')
    print('\t'.join(cols))
    for r in rows:
        print('\t'.join(str(v) for v in r))

conn.close()
