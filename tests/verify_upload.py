import pyodbc, pandas as pd, os, glob

# Paths
DB_PATH = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\09. Base_de_Dados\\Base Fundos_v2.accdb'
XML_FOLDER = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\XML_QORE'

conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + DB_PATH
conn = pyodbc.connect(conn_str)

# Row counts
cp_count = pd.read_sql('SELECT COUNT(*) AS cnt FROM Cotas_Patrimonio_Qore', conn).iloc[0]['cnt']
caixa_count = pd.read_sql('SELECT COUNT(*) AS cnt FROM Caixa_Qore', conn).iloc[0]['cnt']
print('Rows in Cotas_Patrimonio_Qore:', cp_count)
print('Rows in Caixa_Qore:', caixa_count)

# Distinct dates
dates_cp = pd.read_sql('SELECT DISTINCT DATA_INPUT FROM Cotas_Patrimonio_Qore ORDER BY DATA_INPUT', conn)
print('Distinct dates in Cotas_Patrimonio_Qore:', dates_cp['DATA_INPUT'].tolist())

dates_cx = pd.read_sql('SELECT DISTINCT DATA_INPUT FROM Caixa_Qore ORDER BY DATA_INPUT', conn)
print('Distinct dates in Caixa_Qore:', dates_cx['DATA_INPUT'].tolist())

# Sample rows (first 5) for each table
sample_cp = pd.read_sql('SELECT TOP 5 * FROM Cotas_Patrimonio_Qore', conn)
print('Sample rows from Cotas_Patrimonio_Qore:')
print(sample_cp.to_string(index=False))

sample_cx = pd.read_sql('SELECT TOP 5 * FROM Caixa_Qore', conn)
print('Sample rows from Caixa_Qore:')
print(sample_cx.to_string(index=False))

# Verify XML files count
xml_files = [f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')]
print('XML files count:', len(xml_files))
print('XML files sample:', xml_files[:5])

conn.close()
