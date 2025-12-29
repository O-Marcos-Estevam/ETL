import xml.etree.ElementTree as ET
import re

file_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo\XML5.xml'
output_file = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\xml_subacct_inspect.txt'

def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)

try:
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Navigate directly to SctiesBalAcctgRpt -> SubAcctDtls
        def find_child(node, name):
            for child in node:
                if strip_ns(child.tag) == name:
                    return child
            return None

        doc = find_child(root, 'Document')
        rpt = find_child(doc, 'SctiesBalAcctgRpt') if doc else None
        subacct = find_child(rpt, 'SubAcctDtls') if rpt else None
        
        if subacct:
            f.write(f"SubAcctDtls Found. Children count: {len(list(subacct))}\n")
            
            # Print first few children of SubAcctDtls
            count = 0
            for child in subacct:
                if count < 5:
                    f.write(f"\n--- SUB ITEM {count+1}: {strip_ns(child.tag)} ---\n")
                    def print_r(n, l=0):
                         text = (n.text or "").strip()
                         f.write("  "*l + f"{strip_ns(n.tag)}: {text[:50]}\n")
                         for c in n: print_r(c, l+1)
                    print_r(child)
                count += 1
        else:
             f.write("SubAcctDtls NOT found.\n")

except Exception as e:
    with open(output_file, 'w') as f: f.write(str(e))
