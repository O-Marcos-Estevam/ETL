"""
Explorador de Banco PostgreSQL - AWS RDS
Conecta e analisa a estrutura do banco nscapital
"""

import sys
import os

# Fix encoding para Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Tenta importar psycopg2
try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("psycopg2 não instalado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2 import sql

# Configuração de conexão
DB_CONFIG = {
    'host': 'prod-db2.c5kgei88itd4.sa-east-1.rds.amazonaws.com',
    'database': 'nscapital',
    'user': 'nscapitaladmin',
    'password': '7lV5Juj0wsgoUmub',
    'port': 5432
}

def connect():
    """Estabelece conexão com o banco"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("[OK] Conexao estabelecida com sucesso!")
        return conn
    except Exception as e:
        print(f"[ERRO] Erro de conexao: {e}")
        return None

def list_schemas(conn):
    """Lista todos os schemas do banco"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """)
    schemas = cursor.fetchall()
    print("\n" + "="*60)
    print("SCHEMAS DISPONÍVEIS")
    print("="*60)
    for s in schemas:
        print(f"  - {s[0]}")
    return [s[0] for s in schemas]

def list_tables(conn, schema='public'):
    """Lista todas as tabelas de um schema"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_type, table_name
    """, (schema,))
    tables = cursor.fetchall()

    print(f"\n" + "="*60)
    print(f"TABELAS NO SCHEMA: {schema}")
    print("="*60)

    for t in tables:
        tipo = "VIEW" if t[1] == 'VIEW' else "TABLE"
        print(f"  [{tipo:5}] {t[0]}")

    return [t[0] for t in tables]

def describe_table(conn, table_name, schema='public'):
    """Mostra estrutura detalhada de uma tabela"""
    cursor = conn.cursor()

    # Colunas
    cursor.execute("""
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table_name))
    columns = cursor.fetchall()

    print(f"\n" + "-"*60)
    print(f"TABELA: {schema}.{table_name}")
    print("-"*60)
    print(f"{'COLUNA':<30} {'TIPO':<20} {'NULL':<5} {'DEFAULT'}")
    print("-"*60)

    for col in columns:
        nome = col[0]
        tipo = col[1]
        if col[2]:  # varchar length
            tipo = f"{tipo}({col[2]})"
        elif col[3]:  # numeric precision
            tipo = f"{tipo}({col[3]})"
        nullable = "YES" if col[4] == 'YES' else "NO"
        default = str(col[5])[:20] if col[5] else ""
        print(f"{nome:<30} {tipo:<20} {nullable:<5} {default}")

    # Contagem de registros
    try:
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table_name)
        ))
        count = cursor.fetchone()[0]
        print(f"\nTotal de registros: {count:,}")
    except:
        print("\n(Não foi possível contar registros)")

    return columns

def sample_data(conn, table_name, schema='public', limit=5):
    """Mostra amostra dos dados"""
    cursor = conn.cursor()
    try:
        cursor.execute(sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
            sql.Identifier(schema),
            sql.Identifier(table_name)
        ), (limit,))
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        print(f"\nAMOSTRA DE DADOS ({limit} registros):")
        print("-"*60)

        if rows:
            # Mostra cabeçalho
            print(" | ".join(col_names[:6]))  # Limita a 6 colunas
            print("-"*60)
            for row in rows:
                values = [str(v)[:15] if v else "NULL" for v in row[:6]]
                print(" | ".join(values))
        else:
            print("(Tabela vazia)")

    except Exception as e:
        print(f"Erro ao buscar amostra: {e}")

def full_analysis(conn):
    """Análise completa do banco"""
    schemas = list_schemas(conn)

    all_tables = {}
    for schema in schemas:
        tables = list_tables(conn, schema)
        all_tables[schema] = tables

    # Pergunta qual schema explorar em detalhe
    print("\n" + "="*60)
    print("ANÁLISE DETALHADA")
    print("="*60)

    for schema in schemas:
        if all_tables[schema]:
            print(f"\n>>> Schema: {schema} ({len(all_tables[schema])} tabelas)")
            for table in all_tables[schema][:10]:  # Limita a 10 tabelas por schema
                describe_table(conn, table, schema)

def interactive_mode(conn):
    """Modo interativo para explorar o banco"""
    print("\n" + "="*60)
    print("MODO INTERATIVO")
    print("="*60)
    print("Comandos disponíveis:")
    print("  schemas        - Lista schemas")
    print("  tables <schema> - Lista tabelas do schema")
    print("  desc <schema.table> - Descreve tabela")
    print("  sample <schema.table> - Amostra de dados")
    print("  sql <query>    - Executa SQL")
    print("  quit           - Sair")
    print("-"*60)

    cursor = conn.cursor()

    while True:
        try:
            cmd = input("\nDB> ").strip()

            if not cmd:
                continue

            if cmd.lower() == 'quit':
                break

            elif cmd.lower() == 'schemas':
                list_schemas(conn)

            elif cmd.lower().startswith('tables'):
                parts = cmd.split()
                schema = parts[1] if len(parts) > 1 else 'public'
                list_tables(conn, schema)

            elif cmd.lower().startswith('desc'):
                parts = cmd.split()
                if len(parts) > 1:
                    if '.' in parts[1]:
                        schema, table = parts[1].split('.', 1)
                    else:
                        schema, table = 'public', parts[1]
                    describe_table(conn, table, schema)

            elif cmd.lower().startswith('sample'):
                parts = cmd.split()
                if len(parts) > 1:
                    if '.' in parts[1]:
                        schema, table = parts[1].split('.', 1)
                    else:
                        schema, table = 'public', parts[1]
                    sample_data(conn, table, schema)

            elif cmd.lower().startswith('sql'):
                query = cmd[4:].strip()
                if query:
                    try:
                        cursor.execute(query)
                        if cursor.description:
                            cols = [d[0] for d in cursor.description]
                            print(" | ".join(cols))
                            print("-"*60)
                            for row in cursor.fetchall()[:20]:
                                print(" | ".join(str(v)[:20] for v in row))
                        else:
                            print(f"Comando executado. Linhas afetadas: {cursor.rowcount}")
                    except Exception as e:
                        print(f"Erro SQL: {e}")
                        conn.rollback()

            else:
                print("Comando não reconhecido. Digite 'quit' para sair.")

        except KeyboardInterrupt:
            break
        except EOFError:
            break

if __name__ == "__main__":
    print("="*60)
    print("EXPLORADOR DE BANCO POSTGRESQL - AWS RDS")
    print("="*60)
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    print("="*60)

    conn = connect()

    if conn:
        # Análise inicial
        full_analysis(conn)

        # Modo interativo (opcional)
        # interactive_mode(conn)

        conn.close()
        print("\n[OK] Conexao fechada.")
