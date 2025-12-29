import pandas as pd
import os

depara_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\DE PARA.xlsx'

if os.path.exists(depara_path):
    try:
        df = pd.read_excel(depara_path, sheet_name='QORE')
        print("--- DE PARA (QORE Sheet) ---")
        print(df.head(20).to_string())
    except Exception as e:
        print(f"Error reading DE PARA: {e}")
else:
    print(f"DE PARA not found at {depara_path}")
