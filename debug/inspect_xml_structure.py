import xml.etree.ElementTree as ET
import re

file_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo\XML5.xml'
output_file = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\xml_deep_inspect.txt'

def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)

try:
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Root: {strip_ns(root.tag)}\n")
        
        # Traverse
        # Expecting Document -> SctiesBal (SecuritiesBalance) -> FinInstrmDtls (FinancialInstrumentDetails)?
        
        # Let's find specific nodes of interest usually found in ISO 20022 semt.003
        # FinInstrmAttributes, AggtBal, etc.
        
        nodes_to_list = []
        
        # Helper to print recursivelly up to depth 4
        def print_node(node, level=0):
            indent = "  " * level
            tag = strip_ns(node.tag)
            text = (node.text or "").strip()
            short_text = (text[:40] + '...') if len(text) > 40 else text
            
            f.write(f"{indent}{tag}: {short_text}\n")
            
            # Print attributes if any
            if node.attrib:
                 f.write(f"{indent}  ATTRS: {node.attrib}\n")

            if level < 5:
                # Limit children to avoid HUGE output if it's a list of thousands of assets
                # Print first 2 children, then ... then last child
                children = list(node)
                if len(children) > 5:
                    for child in children[:2]:
                        print_node(child, level + 1)
                    f.write(f"{indent}  ... ({len(children)-3} more) ...\n")
                    print_node(children[-1], level + 1)
                else:
                    for child in children:
                        print_node(child, level + 1)

        print_node(root)
        
    print(f"Inspection saved to {output_file}")

except Exception as e:
    print(f"Error: {e}")
