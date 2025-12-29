"""
Conexao e queries para o banco PostgreSQL
"""

import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import pandas as pd

from config import DB_CONFIG, VISIBLE_SCHEMAS

# Re-export for convenience
__all__ = ['DatabaseManager', 'SchemaIntrospector', 'FinancialQueries',
           'db_manager', 'schema_introspector', 'financial_queries', 'VISIBLE_SCHEMAS']


class DatabaseManager:
    """Gerenciador de conexao com PostgreSQL"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @contextmanager
    def get_connection(self):
        """Context manager para conexao"""
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            yield conn
        finally:
            if conn:
                conn.close()

    def test_connection(self) -> bool:
        """Testa a conexao com o banco"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Erro de conexao: {e}")
            return False


class SchemaIntrospector:
    """Queries de introspeccao do banco"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_schemas(self) -> pd.DataFrame:
        """Retorna lista de schemas com contagem de tabelas"""
        query = """
            SELECT
                s.schema_name,
                COUNT(t.table_name) as table_count
            FROM information_schema.schemata s
            LEFT JOIN information_schema.tables t
                ON t.table_schema = s.schema_name
            WHERE s.schema_name = ANY(%s)
            GROUP BY s.schema_name
            ORDER BY s.schema_name
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=(VISIBLE_SCHEMAS,))

    def get_tables(self, schema: str) -> pd.DataFrame:
        """Retorna tabelas de um schema"""
        query = """
            SELECT
                t.table_name,
                t.table_type,
                pg_size_pretty(pg_total_relation_size(
                    quote_ident(t.table_schema) || '.' || quote_ident(t.table_name)
                )) as size
            FROM information_schema.tables t
            WHERE t.table_schema = %s
            ORDER BY t.table_name
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=(schema,))

    def get_columns(self, schema: str, table: str) -> pd.DataFrame:
        """Retorna colunas de uma tabela"""
        query = """
            SELECT
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.numeric_precision,
                c.is_nullable,
                c.column_default
            FROM information_schema.columns c
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql(query, conn, params=(schema, table))
            # Formatar tipo
            df['full_type'] = df.apply(self._format_type, axis=1)
            return df

    def _format_type(self, row) -> str:
        """Formata o tipo de dados"""
        dtype = row['data_type']
        if row['character_maximum_length']:
            return f"{dtype}({int(row['character_maximum_length'])})"
        elif row['numeric_precision']:
            return f"{dtype}({int(row['numeric_precision'])})"
        return dtype

    def get_table_row_count(self, schema: str, table: str) -> int:
        """Retorna contagem de linhas (estimativa)"""
        query = """
            SELECT reltuples::bigint as row_estimate
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (schema, table))
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_sample_data(self, schema: str, table: str, limit: int = 10) -> pd.DataFrame:
        """Retorna amostra de dados"""
        with self.db.get_connection() as conn:
            query = sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                sql.Identifier(schema),
                sql.Identifier(table)
            )
            return pd.read_sql(query.as_string(conn), conn, params=(limit,))

    def get_foreign_keys(self) -> pd.DataFrame:
        """Retorna todas as foreign keys"""
        query = """
            SELECT
                tc.table_schema as source_schema,
                tc.table_name as source_table,
                kcu.column_name as source_column,
                ccu.table_schema as target_schema,
                ccu.table_name as target_table,
                ccu.column_name as target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = ANY(%s)
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=(VISIBLE_SCHEMAS,))

    def get_indexes(self, schema: str, table: str) -> pd.DataFrame:
        """Retorna indices de uma tabela"""
        query = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=(schema, table))

    def get_primary_keys(self, schema: str, table: str) -> List[str]:
        """Retorna colunas da primary key"""
        query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (schema, table))
            return [row[0] for row in cursor.fetchall()]


class FinancialQueries:
    """Queries de dados financeiros"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_funds(self) -> pd.DataFrame:
        """Retorna lista de fundos ativos"""
        query = """
            SELECT id_fundo, nome_fundo, nome_curto, tipo_fundo
            FROM cad.info_fundos
            WHERE is_active = true
            ORDER BY nome_fundo
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def get_nav_history(self, id_fundo: int, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Retorna historico de PL e cotas de um fundo"""
        query = """
            SELECT data_pos, pl_fechamento, cota_fechamento, qt_cotas_fech,
                   valor_entrada, valor_saida
            FROM pos.pos_cota
            WHERE id_fundo = %s
        """
        params = [id_fundo]

        if start_date:
            query += " AND data_pos >= %s"
            params.append(start_date)
        if end_date:
            query += " AND data_pos <= %s"
            params.append(end_date)

        query += " ORDER BY data_pos"

        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def get_fund_comparison(self, fund_ids: List[int], start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Retorna dados para comparacao de fundos"""
        query = """
            SELECT c.data_pos, c.id_fundo, f.nome_curto, c.pl_fechamento, c.cota_fechamento
            FROM pos.pos_cota c
            JOIN cad.info_fundos f ON f.id_fundo = c.id_fundo
            WHERE c.id_fundo = ANY(%s)
        """
        params = [fund_ids]

        if start_date:
            query += " AND c.data_pos >= %s"
            params.append(start_date)
        if end_date:
            query += " AND c.data_pos <= %s"
            params.append(end_date)

        query += " ORDER BY c.data_pos, c.id_fundo"

        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def get_cash_positions(self, id_fundo: int, data_pos: str) -> pd.DataFrame:
        """Retorna posicoes de caixa"""
        query = """
            SELECT descricao, moeda, saldo_fechamento
            FROM pos.pos_caixa
            WHERE id_fundo = %s AND data_pos = %s
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn, params=(id_fundo, data_pos))

    def get_database_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas gerais do banco"""
        stats = {}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Total de fundos
            cursor.execute("SELECT COUNT(*) FROM cad.info_fundos WHERE is_active = true")
            stats['total_fundos'] = cursor.fetchone()[0]

            # Total de cotistas
            cursor.execute("SELECT COUNT(*) FROM cad.info_cotistas WHERE is_active = true")
            stats['total_cotistas'] = cursor.fetchone()[0]

            # Range de datas
            cursor.execute("SELECT MIN(data_pos), MAX(data_pos) FROM pos.pos_cota")
            result = cursor.fetchone()
            stats['data_inicial'] = result[0]
            stats['data_final'] = result[1]

            # PL total (ultima data)
            cursor.execute("""
                SELECT SUM(pl_fechamento)
                FROM pos.pos_cota
                WHERE data_pos = (SELECT MAX(data_pos) FROM pos.pos_cota)
            """)
            stats['pl_total'] = cursor.fetchone()[0] or 0

        return stats


# Instancias globais
db_manager = DatabaseManager()
schema_introspector = SchemaIntrospector(db_manager)
financial_queries = FinancialQueries(db_manager)
