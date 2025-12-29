import os

base_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL'

print(f"--- LISTING DIR: {base_path} ---")
try:
    if os.path.exists(base_path):
        for f in os.listdir(base_path):
            print(f"FOUND: {f}")
    else:
        print("Base path does not exist!")
except Exception as e:
    print(f"Error listing dir: {e}")

print("\n--- CHECKING SUBDIRS ---")
relatorios_path = os.path.join(base_path, 'Relatórios')
if os.path.exists(relatorios_path):
    print("Relatórios folder exists.")
    for root, dirs, files in os.walk(relatorios_path):
        for name in files:
            print(f"FILE IN SUBDIR: {os.path.join(root, name)}")
else:
    print("Relatórios folder NOT found.")
