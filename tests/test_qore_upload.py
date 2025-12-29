"""
Script de teste para analisar o banco e testar o upload do qore_upload_xml_acess.py
"""
import pyodbc
import os

DB_PATH = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\09. Base_de_Dados\\Base Fundos_v2.accdb'
XML_FOLDER = r'C:\\bloko\\Fundos - Documentos\\00. Monitoramento\\01. Rotinas\\03. Arquivos Rotina\\XML_QORE'

def analyze_tables():
    """Analisa estrutura das tabelas Qore no Access"""
    conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + DB_PATH
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    tables = ['Cotas_Patrimonio_Qore', 'Caixa_Qore']
    
    print("=" * 60)
    print("ANÁLISE DAS TABELAS QORE")
    print("=" * 60)
    
    for table in tables:
        print(f"\n>>> Tabela: {table}")
        print("-" * 40)
        
        # Estrutura (colunas)
        try:
            cursor.execute(f"SELECT TOP 1 * FROM [{table}]")
            columns = [desc[0] for desc in cursor.description]
            print(f"Colunas: {columns}")
        except Exception as e:
            print(f"Erro ao ler estrutura: {e}")
            continue
        
        # Contagem total
        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
        total = cursor.fetchone()[0]
        print(f"Total de registros: {total}")
        
        # Contagem por data (últimas 5 datas)
        try:
            cursor.execute(f"""
                SELECT TOP 5 [DATA_INPUT], COUNT(*) as cnt 
                FROM [{table}] 
                GROUP BY [DATA_INPUT] 
                ORDER BY [DATA_INPUT] DESC
            """)
            print("Últimas 5 datas inseridas:")
            for row in cursor.fetchall():
                print(f"   {row[0]} -> {row[1]} registros")
        except Exception as e:
            print(f"Erro ao agrupar por data: {e}")
        
        # Amostra de dados recentes
        try:
            cursor.execute(f"SELECT TOP 3 * FROM [{table}] ORDER BY [DATA_INPUT] DESC")
            print("Amostra (3 registros mais recentes):")
            for row in cursor.fetchall():
                print(f"   {list(row)}")
        except Exception as e:
            print(f"Erro ao ler amostra: {e}")
    
    conn.close()

def list_xml_files():
    """Lista arquivos XML disponíveis"""
    print("\n" + "=" * 60)
    print("ARQUIVOS XML DISPONÍVEIS")
    print("=" * 60)
    
    if not os.path.exists(XML_FOLDER):
        print(f"Pasta não encontrada: {XML_FOLDER}")
        return []
    
    xml_files = [f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')]
    print(f"Total de arquivos: {len(xml_files)}")
    
    for f in xml_files[:10]:  # Primeiros 10
        print(f"   - {f}")
    
    if len(xml_files) > 10:
        print(f"   ... e mais {len(xml_files) - 10} arquivos")
    
    return xml_files

def test_single_upload():
    """Testa o upload de um único arquivo"""
    print("\n" + "=" * 60)
    print("TESTE DE UPLOAD (1 ARQUIVO)")
    print("=" * 60)
    
    # Importar o parser
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from qore_upload_xml_acess import Xml5Parser, get_db_connection, upload_xml_data
    
    xml_files = [f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')]
    if not xml_files:
        print("Nenhum arquivo XML encontrado.")
        return
    
    # Pegar o primeiro arquivo
    test_file = os.path.join(XML_FOLDER, xml_files[0])
    print(f"Arquivo de teste: {xml_files[0]}")
    
    # Parsear
    parser = Xml5Parser()
    data = parser.extract_data(test_file)
    
    if not data:
        print("[ERRO] Falha ao parsear arquivo.")
        return
    
    print(f"\nDados extraídos:")
    print(f"   Fundo: {data['meta'].get('fundo')}")
    print(f"   Data: {data['meta'].get('data_ref')}")
    print(f"   Patrimônio: {data.get('patrimonio')}")
    print(f"   Itens de Caixa: {len(data.get('caixa', []))}")
    print(f"   Itens de RV: {len(data.get('rv', []))}")
    print(f"   Itens de Passivo: {len(data.get('passivo', []))}")
    print(f"   Itens de RF: {len(data.get('rf', []))}")
    
    # Conectar e fazer upload
    conn = get_db_connection()
    if not conn:
        print("[ERRO] Falha na conexão com BD.")
        return
    
    print("\nExecutando upload...")
    upload_xml_data(conn, data)
    
    # Verificar se foi inserido
    cursor = conn.cursor()
    fundo = data['meta']['fundo']
    data_ref = data['meta']['data_ref']
    
    cursor.execute("SELECT COUNT(*) FROM Cotas_Patrimonio_Qore WHERE [DATA_INPUT] = ? AND [FUNDO] = ?", (data_ref, fundo))
    cp_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Caixa_Qore WHERE [DATA_INPUT] = ? AND [FUNDO] = ?", (data_ref, fundo))
    cx_count = cursor.fetchone()[0]
    
    print(f"\nVerificação pós-upload:")
    print(f"   Cotas_Patrimonio_Qore: {cp_count} registro(s)")
    print(f"   Caixa_Qore: {cx_count} registro(s)")
    
    conn.close()
    print("\n[OK] Teste concluído com sucesso!")

if __name__ == "__main__":
    analyze_tables()
    list_xml_files()
    test_single_upload()
