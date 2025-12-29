import xml.etree.ElementTree as ET
import re

file_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo\XML5.xml'
output_file = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\xml_deep_inspect_v2.txt'

def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)

try:
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Navigate directly to SctiesBalAcctgRpt (Securities Balance Accounting Report)
        # BsnsMsg -> Document -> SctiesBalAcctgRpt
        
        # Helper to find child ignoring NS
        def find_child(node, name):
            for child in node:
                if strip_ns(child.tag) == name:
                    return child
            return None

        doc = find_child(root, 'Document')
        rpt = find_child(doc, 'SctiesBalAcctgRpt') if doc else None
        
        if rpt:
            f.write(f"Report Found: {strip_ns(rpt.tag)}\n")
            
            # List ALL children types of Report to find which one holds the assets
            child_tags = {}
            for child in rpt:
                tag = strip_ns(child.tag)
                child_tags[tag] = child_tags.get(tag, 0) + 1
            
            f.write(f"Children of Report: {child_tags}\n")

            # Inspect the one that appears multiple times or looks like 'FinInstrm...'
            target_tag = 'FinInstrmDtls' # Common in semt.003
            if target_tag not in child_tags:
                # Try to guess - pick key with multiple counts
                pass
            
            # Print content of first 2 'FinInstrmDtls' (or whatever holds position)
            count = 0
            for child in rpt:
                tag = strip_ns(child.tag)
                if tag == 'FinInstrmDtls' or 'Bal' in tag: # Broad check
                    if count < 3:
                        f.write(f"\n--- ITEM {count+1}: {tag} ---\n")
                        # Print full structure of this item
                        def print_r(n, l=0):
                             f.write("  "*l + f"{strip_ns(n.tag)}: {n.text.strip() if n.text else ''}\n")
                             for c in n: print_r(c, l+1)
                        print_r(child)
                    count += 1
                    
except Exception as e:
    with open(output_file, 'w') as f: f.write(str(e))
