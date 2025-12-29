import pandas as pd
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

depara_path = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\DE PARA.xlsx"

try:
    df = pd.read_excel(depara_path, sheet_name='QORE')
    # Loop manually over rows
    for i, row in df.iterrows():
        table_name = str(row.iloc[1]).strip()
        alias = str(row.iloc[3]).strip()
        
        if 'CPR' in table_name or 'cpr' in alias.lower():
            print(f"Match Row {i}: Table='{table_name}' -> Alias='{alias}'")

except Exception as e:
    print(f"Error: {e}")
