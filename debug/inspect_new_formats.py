import pandas as pd
import os
import xml.etree.ElementTree as ET

base_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL'
excel_name = 'CARTEIRA_DIARIA_55523261_08-12-2025-5d6909a2-64d7-4af2-8ecd-0dba2748e744.xlsx'
xml_name = 'XML5.xml'

print("--- INSPECTING EXCEL ---")
excel_path = os.path.join(base_path, excel_name)
if os.path.exists(excel_path):
    try:
        xls = pd.ExcelFile(excel_path)
        print(f"Sheets: {xls.sheet_names}")
        for sheet in xls.sheet_names:
            print(f"\nSheet: {sheet}")
            df = pd.read_excel(xls, sheet_name=sheet, nrows=5)
            print("Columns:", list(df.columns))
            print("Head:\n", df.head(3).to_string())
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print(f"Excel file not found at: {excel_path}")

print("\n--- INSPECTING XML ---")
xml_path = os.path.join(base_path, xml_name)
if os.path.exists(xml_path):
    try:
        # Try pandas extract first if simple structure
        try:
            df_xml = pd.read_xml(xml_path)
            print("Pandas read_xml columns:", list(df_xml.columns))
            print("Head:\n", df_xml.head(3).to_string())
        except Exception as e:
            print(f"Pandas read_xml failed: {e}. Trying ElementTree.")
            
            tree = ET.parse(xml_path)
            root = tree.getroot()
            print(f"Root tag: {root.tag}")
            # Print first few children structure
            for child in list(root)[:3]:
                print(f"Child: {child.tag} | Attribs: {child.attrib}")
                for sub in list(child)[:3]:
                    print(f"  Sub: {sub.tag} - {sub.text[:50] if sub.text else ''}")
    except Exception as e:
        print(f"Error reading XML: {e}")
else:
    print(f"XML file not found at: {xml_path}")
