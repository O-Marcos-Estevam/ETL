import sys
import os

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

pdf_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo\CARTEIRA.pdf'

try:
    full_text = ""
    try:
        # Try pypdf first (modern)
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        print(f"Opened with pypdf. Pages: {len(reader.pages)}")
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
    except ImportError:
        # Try PyPDF2 (older)
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(pdf_path)
            print(f"Opened with PyPDF2. Pages: {len(reader.pages)}")
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
        except ImportError:
            print("No PDF library found (pypdf or PyPDF2).")
            sys.exit(1)

    # SEARCH LOGIC
    keywords = ['cota', 'qtde', 'quantidade', 'bruta', 'líquida', 'liquida', 'patrimônio', 'patrimonio']
    full_text_lower = full_text.lower()
    print(f"--- Full Text Length: {len(full_text)} ---")
    
    for k in keywords:
        if k in full_text_lower:
            print(f"FOUND '{k}':")
            # Find occurrences
            start = 0
            while True:
                idx = full_text_lower.find(k, start)
                if idx == -1: break
                # Print context
                context = full_text[max(0, idx-50):min(len(full_text), idx+50)].replace('\n', ' ')
                print(f"   ...{context}...")
                start = idx + 1
        else:
            print(f"NOT FOUND: {k}")

except Exception as e:
    print(f"Error reading PDF: {e}")
