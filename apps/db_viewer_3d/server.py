"""
Database 3D Viewer - Flask API Backend
Cyberpunk-style Three.js visualization
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager

app = Flask(__name__, static_folder='static')
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'prod-db2.c5kgei88itd4.sa-east-1.rds.amazonaws.com',
    'database': 'nscapital',
    'user': 'nscapitaladmin',
    'password': '7lV5Juj0wsgoUmub',
    'port': 5432
}

VISIBLE_SCHEMAS = ['cad', 'pos', 'aux', 'stage']


@contextmanager
def get_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn:
            conn.close()


# ============================================================================
# STATIC FILES
# ============================================================================

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory('static/css', filename)


@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory('static/js', filename)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/test')
def test():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return jsonify({'status': 'ok', 'message': 'Database connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get overall database statistics"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total funds
            cursor.execute("SELECT COUNT(*) FROM cad.info_fundos WHERE is_active = true")
            stats['total_funds'] = cursor.fetchone()[0]

            # Total investors
            cursor.execute("SELECT COUNT(*) FROM cad.info_cotistas WHERE is_active = true")
            stats['total_investors'] = cursor.fetchone()[0]

            # Date range
            cursor.execute("SELECT MIN(data_pos), MAX(data_pos) FROM pos.pos_cota")
            result = cursor.fetchone()
            stats['date_start'] = str(result[0]) if result[0] else None
            stats['date_end'] = str(result[1]) if result[1] else None

            # Total PL (latest date)
            cursor.execute("""
                SELECT SUM(pl_fechamento)
                FROM pos.pos_cota
                WHERE data_pos = (SELECT MAX(data_pos) FROM pos.pos_cota)
            """)
            stats['total_pl'] = float(cursor.fetchone()[0] or 0)

            return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schemas')
def get_schemas():
    """Get all schemas with table counts"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    s.schema_name,
                    COUNT(t.table_name) as table_count
                FROM information_schema.schemata s
                LEFT JOIN information_schema.tables t ON t.table_schema = s.schema_name
                WHERE s.schema_name = ANY(%s)
                GROUP BY s.schema_name
                ORDER BY s.schema_name
            """, (VISIBLE_SCHEMAS,))

            schemas = []
            for row in cursor.fetchall():
                schemas.append({
                    'name': row[0],
                    'table_count': row[1]
                })

            return jsonify(schemas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tables/<schema>')
def get_tables(schema):
    """Get tables for a schema"""
    if schema not in VISIBLE_SCHEMAS:
        return jsonify({'error': 'Invalid schema'}), 400

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name
            """, (schema,))

            tables = []
            for row in cursor.fetchall():
                # Get row count estimate
                cursor.execute("""
                    SELECT reltuples::bigint
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relname = %s
                """, (schema, row[0]))
                count_result = cursor.fetchone()
                row_count = count_result[0] if count_result else 0

                tables.append({
                    'name': row[0],
                    'type': row[1],
                    'row_count': max(0, row_count)
                })

            return jsonify(tables)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/columns/<schema>/<table>')
def get_columns(schema, table):
    """Get columns for a table"""
    if schema not in VISIBLE_SCHEMAS:
        return jsonify({'error': 'Invalid schema'}), 400

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table))

            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3]
                })

            return jsonify(columns)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/foreign-keys')
def get_foreign_keys():
    """Get all foreign key relationships"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
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
            """, (VISIBLE_SCHEMAS,))

            fks = []
            for row in cursor.fetchall():
                fks.append({
                    'source_schema': row[0],
                    'source_table': row[1],
                    'source_column': row[2],
                    'target_schema': row[3],
                    'target_table': row[4],
                    'target_column': row[5]
                })

            return jsonify(fks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/funds')
def get_funds():
    """Get active funds"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_fundo, nome_fundo, nome_curto, tipo_fundo
                FROM cad.info_fundos
                WHERE is_active = true
                ORDER BY nome_fundo
            """)

            funds = []
            for row in cursor.fetchall():
                funds.append({
                    'id': row[0],
                    'name': row[1],
                    'short_name': row[2] or row[1],
                    'type': row[3]
                })

            return jsonify(funds)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/nav/<int:fund_id>')
def get_nav(fund_id):
    """Get NAV history for a fund with optional date filter"""
    from flask import request
    from datetime import datetime, timedelta

    try:
        # Get period filter (30d, 90d, 180d, 365d, all)
        period = request.args.get('period', '365')

        with get_connection() as conn:
            cursor = conn.cursor()

            if period == 'all':
                cursor.execute("""
                    SELECT data_pos, pl_fechamento, cota_fechamento, qt_cotas_fech
                    FROM pos.pos_cota
                    WHERE id_fundo = %s
                    ORDER BY data_pos DESC
                """, (fund_id,))
            else:
                days = int(period)
                start_date = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    SELECT data_pos, pl_fechamento, cota_fechamento, qt_cotas_fech
                    FROM pos.pos_cota
                    WHERE id_fundo = %s AND data_pos >= %s
                    ORDER BY data_pos DESC
                """, (fund_id, start_date.date()))

            data = []
            for row in cursor.fetchall():
                data.append({
                    'date': str(row[0]),
                    'pl': float(row[1]) if row[1] else 0,
                    'quota': float(row[2]) if row[2] else 0,
                    'shares': float(row[3]) if row[3] else 0
                })

            # Reverse to chronological order
            data.reverse()

            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview/<schema>/<table>')
def get_preview(schema, table):
    """Get sample data from a table (10 rows)"""
    if schema not in VISIBLE_SCHEMAS:
        return jsonify({'error': 'Invalid schema'}), 400

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get column names
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table))
            columns = [row[0] for row in cursor.fetchall()]

            # Get sample data (safely using identifier quoting)
            query = sql.SQL("SELECT * FROM {}.{} LIMIT 10").format(
                sql.Identifier(schema),
                sql.Identifier(table)
            )
            cursor.execute(query)

            rows = []
            for row in cursor.fetchall():
                row_data = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert to serializable format
                    if value is None:
                        row_data[col] = None
                    elif isinstance(value, (int, float, str, bool)):
                        row_data[col] = value
                    else:
                        row_data[col] = str(value)
                rows.append(row_data)

            return jsonify({
                'columns': columns,
                'rows': rows,
                'total': len(rows)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<schema>/<table>')
def export_table(schema, table):
    """Export table data as CSV"""
    from flask import Response
    import csv
    import io

    if schema not in VISIBLE_SCHEMAS:
        return jsonify({'error': 'Invalid schema'}), 400

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get column names
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (schema, table))
            columns = [row[0] for row in cursor.fetchall()]

            # Get all data (limit to 10000 rows for safety)
            query = sql.SQL("SELECT * FROM {}.{} LIMIT 10000").format(
                sql.Identifier(schema),
                sql.Identifier(table)
            )
            cursor.execute(query)
            rows = cursor.fetchall()

            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([str(v) if v is not None else '' for v in row])

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={schema}_{table}.csv'}
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/funds-comparison')
def get_funds_comparison():
    """Get PL comparison for all active funds (latest date)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get latest PL for each active fund (only funds with PL > 0)
            cursor.execute("""
                SELECT
                    f.id_fundo,
                    f.nome_curto,
                    f.tipo_fundo,
                    pc.pl_fechamento,
                    pc.data_pos
                FROM cad.info_fundos f
                JOIN pos.pos_cota pc ON f.id_fundo = pc.id_fundo
                WHERE f.is_active = true
                    AND pc.pl_fechamento > 0
                    AND pc.data_pos = (
                        SELECT MAX(data_pos)
                        FROM pos.pos_cota
                        WHERE id_fundo = f.id_fundo
                    )
                ORDER BY pc.pl_fechamento DESC
            """)

            funds = []
            for row in cursor.fetchall():
                funds.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'pl': float(row[3]) if row[3] else 0,
                    'date': str(row[4]) if row[4] else None
                })

            return jsonify(funds)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolio/<int:fund_id>')
def get_portfolio(fund_id):
    """Get portfolio composition for a fund (latest date)"""
    from flask import request

    try:
        date_param = request.args.get('date')

        with get_connection() as conn:
            cursor = conn.cursor()

            # Get latest date for this fund if not specified
            if not date_param:
                cursor.execute("""
                    SELECT MAX(data_pos) FROM pos.pos_cota WHERE id_fundo = %s
                """, (fund_id,))
                result = cursor.fetchone()
                target_date = result[0] if result else None
            else:
                target_date = date_param

            if not target_date:
                return jsonify({'error': 'No data found'}), 404

            portfolio = {
                'date': str(target_date),
                'fund_id': fund_id,
                'composition': []
            }

            # Get fund name
            cursor.execute("""
                SELECT nome_curto FROM cad.info_fundos WHERE id_fundo = %s
            """, (fund_id,))
            fund_result = cursor.fetchone()
            portfolio['fund_name'] = fund_result[0] if fund_result else f'Fund {fund_id}'

            # Caixa (Cash) - using saldo_fechamento with details
            cursor.execute("""
                SELECT
                    COALESCE(c.banco, 'Conta ' || p.id_conta::text, 'Caixa') as nome,
                    p.saldo_fechamento
                FROM pos.pos_caixa_2025 p
                LEFT JOIN cad.info_contas c ON p.id_conta = c.id_conta
                WHERE p.id_fundo = %s AND p.data_pos = %s AND p.saldo_fechamento > 0
                ORDER BY p.saldo_fechamento DESC
            """, (fund_id, target_date))
            caixa_rows = cursor.fetchall()
            caixa = sum(float(r[1] or 0) for r in caixa_rows)
            if caixa > 0:
                assets = [{'name': r[0] or 'N/A', 'value': float(r[1])} for r in caixa_rows[:10]]
                portfolio['composition'].append({
                    'category': 'Caixa',
                    'value': caixa,
                    'color': '#58a6ff',
                    'assets': assets,
                    'asset_count': len(caixa_rows)
                })

            # Renda Fixa (Fixed Income) with details
            cursor.execute("""
                SELECT
                    COALESCE(i.nome_ativo, i.cod_ativo, 'N/A') as nome,
                    i.tipo_titulo,
                    i.indexador,
                    p.valor_mercado
                FROM pos.pos_rf_2025 p
                LEFT JOIN cad.info_rf i ON p.id_ativo_rf = i.id_ativo_rf
                WHERE p.id_fundo = %s AND p.data_pos = %s AND p.valor_mercado > 0
                ORDER BY p.valor_mercado DESC
            """, (fund_id, target_date))
            rf_rows = cursor.fetchall()
            rf = sum(float(r[3] or 0) for r in rf_rows)
            if rf > 0:
                assets = [{
                    'name': r[0],
                    'type': r[1] or '',
                    'index': r[2] or '',
                    'value': float(r[3])
                } for r in rf_rows[:10]]
                portfolio['composition'].append({
                    'category': 'Renda Fixa',
                    'value': rf,
                    'color': '#3fb950',
                    'assets': assets,
                    'asset_count': len(rf_rows)
                })

            # Renda Variável (Equities) with details
            cursor.execute("""
                SELECT
                    COALESCE(i.cod_papel, i.nome_papel, 'N/A') as nome,
                    i.tipo_papel,
                    p.valor_mercado
                FROM pos.pos_rv_2025 p
                LEFT JOIN cad.info_rv i ON p.id_ativo_rv = i.id_ativo_rv
                WHERE p.id_fundo = %s AND p.data_pos = %s AND p.valor_mercado > 0
                ORDER BY p.valor_mercado DESC
            """, (fund_id, target_date))
            rv_rows = cursor.fetchall()
            rv = sum(float(r[2] or 0) for r in rv_rows)
            if rv > 0:
                assets = [{
                    'name': r[0],
                    'type': r[1] or '',
                    'value': float(r[2])
                } for r in rv_rows[:10]]
                portfolio['composition'].append({
                    'category': 'Renda Variável',
                    'value': rv,
                    'color': '#f85149',
                    'assets': assets,
                    'asset_count': len(rv_rows)
                })

            # Direitos Creditórios with details
            cursor.execute("""
                SELECT
                    COALESCE(i.nome_sacado, i.cod_ativo_dc, 'N/A') as nome,
                    i.tipo_recebivel,
                    p.valor_presente
                FROM pos.pos_dir_cred_2025 p
                LEFT JOIN cad.info_dir_cred i ON p.id_ativo_dc = i.id_ativo_dc
                WHERE p.id_fundo = %s AND p.data_pos = %s AND p.valor_presente > 0
                ORDER BY p.valor_presente DESC
            """, (fund_id, target_date))
            dc_rows = cursor.fetchall()
            dc = sum(float(r[2] or 0) for r in dc_rows)
            if dc > 0:
                assets = [{
                    'name': r[0],
                    'type': r[1] or '',
                    'value': float(r[2])
                } for r in dc_rows[:10]]
                portfolio['composition'].append({
                    'category': 'Dir. Creditórios',
                    'value': dc,
                    'color': '#a371f7',
                    'assets': assets,
                    'asset_count': len(dc_rows)
                })

            # CPR with details
            cursor.execute("""
                SELECT
                    COALESCE(i.descricao, i.contraparte, 'CPR') as nome,
                    i.tipo_cpr,
                    p.valor_presente
                FROM pos.pos_cpr_2025 p
                LEFT JOIN cad.info_cpr i ON p.id_cpr = i.id_cpr
                WHERE p.id_fundo = %s AND p.data_pos = %s AND p.valor_presente > 0
                ORDER BY p.valor_presente DESC
            """, (fund_id, target_date))
            cpr_rows = cursor.fetchall()
            cpr = sum(float(r[2] or 0) for r in cpr_rows)
            if cpr > 0:
                assets = [{
                    'name': r[0],
                    'type': r[1] or '',
                    'value': float(r[2])
                } for r in cpr_rows[:10]]
                portfolio['composition'].append({
                    'category': 'CPR',
                    'value': cpr,
                    'color': '#d29922',
                    'assets': assets,
                    'asset_count': len(cpr_rows)
                })

            # Calculate total and percentages
            total = sum(item['value'] for item in portfolio['composition'])
            portfolio['total'] = total

            for item in portfolio['composition']:
                item['percentage'] = (item['value'] / total * 100) if total > 0 else 0

            return jsonify(portfolio)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/quota-evolution/<int:fund_id>')
def get_quota_evolution(fund_id):
    """Get quota evolution with performance metrics"""
    from flask import request
    from datetime import datetime, timedelta

    try:
        period = request.args.get('period', '365')

        with get_connection() as conn:
            cursor = conn.cursor()

            if period == 'all':
                cursor.execute("""
                    SELECT data_pos, cota_fechamento
                    FROM pos.pos_cota
                    WHERE id_fundo = %s
                    ORDER BY data_pos ASC
                """, (fund_id,))
            else:
                days = int(period)
                start_date = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    SELECT data_pos, cota_fechamento
                    FROM pos.pos_cota
                    WHERE id_fundo = %s AND data_pos >= %s
                    ORDER BY data_pos ASC
                """, (fund_id, start_date.date()))

            data = []
            for row in cursor.fetchall():
                data.append({
                    'date': str(row[0]),
                    'quota': float(row[1]) if row[1] else 0
                })

            # Calculate performance metrics
            if len(data) >= 2:
                first_quota = data[0]['quota']
                last_quota = data[-1]['quota']

                if first_quota > 0:
                    total_return = ((last_quota / first_quota) - 1) * 100
                else:
                    total_return = 0

                # Find max and min
                quotas = [d['quota'] for d in data]
                max_quota = max(quotas)
                min_quota = min(quotas)

                return jsonify({
                    'data': data,
                    'metrics': {
                        'total_return': round(total_return, 2),
                        'first_quota': first_quota,
                        'last_quota': last_quota,
                        'max_quota': max_quota,
                        'min_quota': min_quota,
                        'data_points': len(data)
                    }
                })

            return jsonify({
                'data': data,
                'metrics': None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/all-tables')
def get_all_tables():
    """Get all tables with schemas for 3D visualization"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            all_tables = []

            for schema in VISIBLE_SCHEMAS:
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """, (schema,))

                for row in cursor.fetchall():
                    # Get column count
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                    """, (schema, row[0]))
                    col_count = cursor.fetchone()[0]

                    # Get row estimate
                    cursor.execute("""
                        SELECT reltuples::bigint
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s AND c.relname = %s
                    """, (schema, row[0]))
                    row_result = cursor.fetchone()
                    row_count = max(0, row_result[0] if row_result else 0)

                    all_tables.append({
                        'schema': schema,
                        'name': row[0],
                        'full_name': f"{schema}.{row[0]}",
                        'columns': col_count,
                        'rows': row_count
                    })

            return jsonify(all_tables)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("DATABASE 3D VIEWER - Cyberpunk Edition")
    print("=" * 60)
    print("Testing database connection...")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            print("Database connected!")
    except Exception as e:
        print(f"Database error: {e}")

    print("\nStarting server at http://127.0.0.1:8080")
    print("=" * 60)

    app.run(debug=True, host='127.0.0.1', port=8080)
