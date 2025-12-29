import pyodbc, pandas as pd

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\09. Base_de_Dados\Base Fundos_v2.accdb'
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path
conn = pyodbc.connect(conn_str)
for table in ['Cotas_Patrimonio_Qore', 'Caixa_Qore']:
    df = pd.read_sql(f'SELECT DISTINCT [DATA_INPUT] FROM [{table}] ORDER BY [DATA_INPUT]', conn)
    print('---', table, '---')
    print(df.to_string(index=False))
conn.close()
