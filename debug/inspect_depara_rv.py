import pandas as pd
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

depara_path = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\DE PARA.xlsx"

try:
    df = pd.read_excel(depara_path, sheet_name='QORE')
    # Column B is Table Name, Column D is Keyword
    # We want to find the row where Col D matches 'renda_variável' (ignoring case/accents?)
    
    print(f"Searching DE PARA for 'cpr'...")
    found = False
    for i, row in df.iterrows():
        keyword = str(row.iloc[3]).strip().lower() # Col D (index 3)
        table = str(row.iloc[1]).strip() # Col B (index 1)
        
        if 'cpr' in keyword:
            print(f"Match Row {i}: Keyword='{keyword}' -> Table='{table}'")
            found = True

    if not found:
        print("No match found for cpr")

except Exception as e:
    print(f"Error: {e}")
