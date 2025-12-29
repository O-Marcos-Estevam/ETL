"""
================================================================================
MIGRACAO ACCESS -> POSTGRESQL
================================================================================
Script para migrar dados do banco Access (Base Fundos_v2.accdb) para o
PostgreSQL (nscapital) na AWS RDS.

MAPEAMENTO DE TABELAS:

ACCESS                          -> POSTGRESQL
-----------------------------------------------------------------------
BriTech_Carteiras               -> cad.info_fundos + aux.depara_fundos
BriTech_Cotistas                -> cad.info_cotistas
BriTech_Historico_Cota          -> pos.pos_cota (particionada)
BriTech_Posicao_Cotista         -> pos.pos_passivo (particionada)
BriTech_Passivo_Fundos          -> pos.pos_passivo (agregado)
BriTech_Saldo_Caixa             -> pos.pos_caixa (particionada)
Caixa_Qore                      -> pos.pos_caixa
Cotas_Patrimonio_Qore           -> pos.pos_cota
CPR_QORE                        -> pos.pos_cpr
Renda_Fixa_Qore                 -> pos.pos_rf
Sociedade_Limitada_QORE         -> pos.pos_rv
Direito_Creditorio_Qore         -> pos.pos_dir_cred
FIDC_ESTOQUE                    -> stage.stg_fidc_estoque -> pos.pos_dir_cred
DEPARA                          -> aux.depara_fundos / aux.depara_emissores
DIAS_UTEIS                      -> cad.info_calendario (ja populado)

VOLUME ESTIMADO: ~950.000 registros
================================================================================
"""

import sys
import os

# Fix encoding Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import pyodbc
import psycopg2
from psycopg2 import sql
from datetime import datetime, date
from decimal import Decimal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACOES
# =============================================================================

ACCESS_PATH = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\09. Base_de_Dados\Base Fundos_v2.accdb'

PG_CONFIG = {
    'host': 'prod-db2.c5kgei88itd4.sa-east-1.rds.amazonaws.com',
    'database': 'nscapital',
    'user': 'nscapitaladmin',
    'password': '7lV5Juj0wsgoUmub',
    'port': 5432
}

# =============================================================================
# CONEXOES
# =============================================================================

def connect_access():
    """Conecta ao banco Access"""
    conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCESS_PATH};'
    return pyodbc.connect(conn_str)

def connect_postgres():
    """Conecta ao PostgreSQL"""
    return psycopg2.connect(**PG_CONFIG)

# =============================================================================
# MAPEAMENTO DE FUNDOS (BriTech_Carteiras -> cad.info_fundos)
# =============================================================================

def migrate_fundos(acc_conn, pg_conn):
    """Migra cadastro de fundos"""
    log.info("Migrando fundos...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Buscar fundos do Access
    acc_cur.execute("""
        SELECT DISTINCT
            Id_Carteira, Nome, de_para_qore, Tipo_Fundo, de_para_maps
        FROM BriTech_Carteiras
        WHERE Nome IS NOT NULL
    """)

    count = 0
    for row in acc_cur.fetchall():
        id_carteira, nome, codigo_qore, tipo_fundo, codigo_maps = row

        # Verificar se ja existe
        pg_cur.execute(
            "SELECT id_fundo FROM cad.info_fundos WHERE codigo_britech = %s",
            (int(id_carteira) if id_carteira else None,)
        )

        if pg_cur.fetchone():
            continue  # Ja existe

        # Determinar tipo
        tipo = 'FIM'
        if tipo_fundo:
            if 'FIDC' in str(tipo_fundo).upper():
                tipo = 'FIDC'
            elif 'FIP' in str(tipo_fundo).upper():
                tipo = 'FIP'
            elif 'FIA' in str(tipo_fundo).upper():
                tipo = 'FIA'

        # Inserir
        pg_cur.execute("""
            INSERT INTO cad.info_fundos (
                codigo_britech, codigo_qore, codigo_maps, nome_fundo,
                nome_curto, tipo_fundo, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, true)
            ON CONFLICT (codigo_britech) DO UPDATE SET
                nome_fundo = EXCLUDED.nome_fundo,
                codigo_qore = EXCLUDED.codigo_qore
            RETURNING id_fundo
        """, (
            int(id_carteira) if id_carteira else None,
            codigo_qore,
            codigo_maps,
            nome,
            nome[:100] if nome else None,
            tipo
        ))
        count += 1

    pg_conn.commit()
    log.info(f"  Fundos migrados: {count}")
    return count

# =============================================================================
# MAPEAMENTO DE COTISTAS (BriTech_Cotistas -> cad.info_cotistas)
# =============================================================================

def migrate_cotistas(acc_conn, pg_conn):
    """Migra cadastro de cotistas"""
    log.info("Migrando cotistas...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    acc_cur.execute("""
        SELECT DISTINCT ID_COTISTA, NOME, CPF_CNPJ
        FROM BriTech_Cotistas
        WHERE NOME IS NOT NULL
    """)

    count = 0
    for row in acc_cur.fetchall():
        id_cotista, nome, cpf_cnpj = row

        # Verificar se ja existe
        pg_cur.execute(
            "SELECT id_cotista FROM cad.info_cotistas WHERE codigo_britech = %s",
            (int(id_cotista) if id_cotista else None,)
        )

        if pg_cur.fetchone():
            continue

        # Formatar CPF/CNPJ
        doc = None
        tipo_pessoa = 'PJ'
        if cpf_cnpj:
            doc_str = str(int(cpf_cnpj)).zfill(14)
            if len(doc_str) == 11:
                doc = f"{doc_str[:3]}.{doc_str[3:6]}.{doc_str[6:9]}-{doc_str[9:]}"
                tipo_pessoa = 'PF'
            elif len(doc_str) >= 14:
                doc = f"{doc_str[:2]}.{doc_str[2:5]}.{doc_str[5:8]}/{doc_str[8:12]}-{doc_str[12:14]}"
                tipo_pessoa = 'PJ'

        pg_cur.execute("""
            INSERT INTO cad.info_cotistas (
                codigo_britech, nome_cotista, nome_curto, cpf_cnpj, tipo_pessoa, is_active
            ) VALUES (%s, %s, %s, %s, %s, true)
            ON CONFLICT (codigo_britech) DO NOTHING
        """, (
            int(id_cotista) if id_cotista else None,
            nome,
            nome[:100] if nome else None,
            doc,
            tipo_pessoa
        ))
        count += 1

    pg_conn.commit()
    log.info(f"  Cotistas migrados: {count}")
    return count

# =============================================================================
# HISTORICO DE COTAS (BriTech_Historico_Cota -> pos.pos_cota)
# =============================================================================

def migrate_historico_cotas(acc_conn, pg_conn, batch_size=1000):
    """Migra historico de cotas"""
    log.info("Migrando historico de cotas...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Buscar mapeamento de fundos
    pg_cur.execute("SELECT codigo_britech, id_fundo FROM cad.info_fundos WHERE codigo_britech IS NOT NULL")
    fundo_map = {row[0]: row[1] for row in pg_cur.fetchall()}

    acc_cur.execute("""
        SELECT
            Data, Id_Carteira, Cota_Abertura, Cota_Fechamento,
            [PL _Abertura], PL_Fechamento, Quantidade_Fechamento,
            Valor_Entrada, Valor_Saida
        FROM BriTech_Historico_Cota
        WHERE Data IS NOT NULL AND Id_Carteira IS NOT NULL
        ORDER BY Data
    """)

    count = 0
    batch = []

    for row in acc_cur.fetchall():
        data, id_carteira, cota_ab, cota_fech, pl_ab, pl_fech, qt_cotas, entrada, saida = row

        id_fundo = fundo_map.get(int(id_carteira) if id_carteira else None)
        if not id_fundo:
            continue

        # Determinar ano para particao
        if isinstance(data, datetime):
            data_pos = data.date()
        else:
            data_pos = data

        batch.append((
            id_fundo, None, data_pos,
            float(cota_ab) if cota_ab else None,
            float(cota_fech) if cota_fech else None,
            float(qt_cotas) if qt_cotas else None,
            float(qt_cotas) if qt_cotas else None,
            float(pl_ab) if pl_ab else None,
            float(pl_fech) if pl_fech else None,
            float(pl_fech) if pl_fech else None,
            float(entrada) if entrada else None,
            float(saida) if saida else None
        ))

        if len(batch) >= batch_size:
            _insert_pos_cota_batch(pg_cur, batch)
            pg_conn.commit()
            count += len(batch)
            log.info(f"    Cotas processadas: {count}")
            batch = []

    if batch:
        _insert_pos_cota_batch(pg_cur, batch)
        pg_conn.commit()
        count += len(batch)

    log.info(f"  Historico cotas migrado: {count}")
    return count

def _insert_pos_cota_batch(pg_cur, batch):
    """Insere batch de cotas"""
    for row in batch:
        try:
            pg_cur.execute("""
                INSERT INTO pos.pos_cota (
                    id_fundo, id_serie, data_pos,
                    cota_abertura, cota_fechamento,
                    qt_cotas_abert, qt_cotas_fech,
                    pl_abertura, pl_fechamento, pl_contabil,
                    valor_entrada, valor_saida
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id_fundo, COALESCE(id_serie, 0), data_pos) DO UPDATE SET
                    cota_fechamento = EXCLUDED.cota_fechamento,
                    pl_fechamento = EXCLUDED.pl_fechamento
            """, row)
        except Exception as e:
            log.warning(f"Erro ao inserir cota: {e}")

# =============================================================================
# POSICAO CAIXA (Caixa_Qore -> pos.pos_caixa)
# =============================================================================

def migrate_caixa(acc_conn, pg_conn):
    """Migra posicoes de caixa"""
    log.info("Migrando caixa...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Buscar mapeamento de fundos por nome
    pg_cur.execute("SELECT nome_curto, id_fundo FROM cad.info_fundos")
    fundo_map_nome = {row[0]: row[1] for row in pg_cur.fetchall() if row[0]}

    pg_cur.execute("SELECT codigo_qore, id_fundo FROM cad.info_fundos WHERE codigo_qore IS NOT NULL")
    fundo_map_qore = {row[0]: row[1] for row in pg_cur.fetchall()}

    acc_cur.execute("""
        SELECT DATA_INPUT, FUNDO, [Descricao], Moeda_Origem, Valor
        FROM Caixa_Qore
        WHERE DATA_INPUT IS NOT NULL AND FUNDO IS NOT NULL
    """)

    count = 0
    for row in acc_cur.fetchall():
        data, fundo, descricao, moeda, valor = row

        # Encontrar id_fundo
        id_fundo = fundo_map_qore.get(fundo) or fundo_map_nome.get(fundo)
        if not id_fundo:
            continue

        if isinstance(data, datetime):
            data_pos = data.date()
        else:
            data_pos = data

        try:
            pg_cur.execute("""
                INSERT INTO pos.pos_caixa (
                    id_fundo, id_conta, data_pos, banco, descricao, moeda, saldo_fechamento
                ) VALUES (%s, NULL, %s, 'N/D', %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (id_fundo, data_pos, descricao, moeda or 'BRL', float(valor) if valor else 0))
            count += 1
        except Exception as e:
            log.warning(f"Erro caixa: {e}")

    pg_conn.commit()
    log.info(f"  Caixa migrado: {count}")
    return count

# =============================================================================
# CPR (CPR_QORE -> pos.pos_cpr)
# =============================================================================

# Mapeamento de nomes de fundos Access -> id_fundo PostgreSQL
FUNDO_MAP_MANUAL = {
    'AMG': 56, 'BLOKO FIM': 39, 'BLOKO URBANISMO': 47, 'BLOKO URBANISMO NOTE03': 47,
    'ESTOCOLMO': 66, 'FIDC EVOQUE': 79, 'FIDC FORSETI': 80, 'FIDC MARNE': 81,
    'FIDC PLATAO': None, 'FIDC SOA': 72, 'FIDC SOCRATES': 73, 'FIDC SOCRATES NOTE03': 73,
    'FIM BLOKO': 39, 'FIM PES': 39, 'FIP AMG': 56, 'FIP AMG (1)': 56,
    'FIP BENELLI': 53, 'FIP BLOKO MULT': 36, 'FIP BLOKO URBANISMO': 47,
    'FIP CALDAS': 40, 'FIP ESTOCOLMO': 66, 'FIP GEKKO': 54, 'FIP GTB': 46,
    'FIP KAWANA': 41, 'FIP MINAS': 36, 'FIP MURCIELAGO': 62, 'FIP ON': 22,
    'FIP OSLO': 64, 'FIP RAM': 51, 'FIP RENOGRID': 50, 'FIP TERRAVISTA': 38,
    'FIP TURANO': 55, 'FORSETI FIDC': 80, 'OSLO': 64, 'SOA FIDC': 72,
    'TERRAVISTA FIP': 38
}

def migrate_cpr(acc_conn, pg_conn):
    """Migra contas a pagar/receber"""
    log.info("Migrando CPR...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Buscar mapeamentos do banco
    pg_cur.execute("SELECT codigo_qore, id_fundo FROM cad.info_fundos WHERE codigo_qore IS NOT NULL")
    fundo_map = {row[0]: row[1] for row in pg_cur.fetchall()}

    pg_cur.execute("SELECT nome_curto, id_fundo FROM cad.info_fundos")
    fundo_map_nome = {row[0]: row[1] for row in pg_cur.fetchall() if row[0]}

    # Mesclar com mapeamento manual
    fundo_map.update(FUNDO_MAP_MANUAL)
    fundo_map.update(fundo_map_nome)

    # Nomes das colunas tem acentos (Descrição, Lançamento)
    # Usar * e pegar por posicao: 0=DATA_INPUT, 1=FUNDO, 2=Descrição, 3=Lançamento, 4=Vencimento, 5=Valor
    acc_cur.execute("""
        SELECT * FROM CPR_QORE WHERE DATA_INPUT IS NOT NULL
    """)

    count = 0
    skipped = 0
    fundos_nao_mapeados = set()

    for row in acc_cur.fetchall():
        # Posicoes: 0=DATA_INPUT, 1=FUNDO, 2=Descricao, 3=Lancamento, 4=Vencimento, 5=Valor
        data = row[0]
        fundo = row[1]
        descricao = row[2]
        vencimento = row[4]
        valor = row[5]

        id_fundo = fundo_map.get(fundo)
        if not id_fundo:
            fundos_nao_mapeados.add(fundo)
            skipped += 1
            continue

        if isinstance(data, datetime):
            data_pos = data.date()
        else:
            data_pos = data

        # Determinar tipo_cpr baseado no valor
        valor_num = float(valor) if valor else 0
        tipo_cpr = 'PAGAR' if valor_num < 0 else 'RECEBER'
        valor_abs = abs(valor_num)

        try:
            # Primeiro criar registro em cad.info_cpr
            pg_cur.execute("""
                INSERT INTO cad.info_cpr (
                    id_fundo, tipo_cpr, descricao, data_vencimento,
                    valor_original, status
                )
                VALUES (%s, %s, %s, %s, %s, 'PENDENTE')
                ON CONFLICT DO NOTHING
                RETURNING id_cpr
            """, (
                id_fundo,
                tipo_cpr,
                descricao[:255] if descricao else f'CPR {tipo_cpr}',
                vencimento,
                valor_abs
            ))

            result = pg_cur.fetchone()
            if result:
                id_cpr = result[0]

                # Inserir posicao com status obrigatorio
                pg_cur.execute("""
                    INSERT INTO pos.pos_cpr (
                        id_fundo, id_cpr, data_pos, valor_presente, status
                    )
                    VALUES (%s, %s, %s, %s, 'PENDENTE')
                    ON CONFLICT DO NOTHING
                """, (id_fundo, id_cpr, data_pos, valor_abs))

            count += 1

            if count % 5000 == 0:
                pg_conn.commit()
                log.info(f"    CPR processados: {count}")

        except Exception as e:
            log.warning(f"Erro CPR: {e}")
            pg_conn.rollback()

    pg_conn.commit()

    if fundos_nao_mapeados:
        log.warning(f"  Fundos nao mapeados: {fundos_nao_mapeados}")

    log.info(f"  CPR migrado: {count} | Ignorados: {skipped}")
    return count

# =============================================================================
# PASSIVO / COTISTAS (BriTech_Posicao_Cotista -> pos.pos_passivo)
# =============================================================================

def migrate_passivo(acc_conn, pg_conn, batch_size=5000):
    """Migra posicao de cotistas (passivo)"""
    log.info("Migrando passivo (posicao cotistas)...")

    acc_cur = acc_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Mapas PostgreSQL
    pg_cur.execute("SELECT codigo_britech, id_fundo FROM cad.info_fundos WHERE codigo_britech IS NOT NULL")
    fundo_map = {row[0]: row[1] for row in pg_cur.fetchall()}

    pg_cur.execute("SELECT codigo_britech, id_cotista FROM cad.info_cotistas WHERE codigo_britech IS NOT NULL")
    cotista_map = {row[0]: row[1] for row in pg_cur.fetchall()}

    log.info(f"    Fundos mapeados: {len(fundo_map)}")
    log.info(f"    Cotistas mapeados: {len(cotista_map)}")

    # Buscar apenas registros com cotista e fundo cadastrados no Access
    # Isso filtra os 499 cotistas e 492 fundos orfaos
    # Access requer parenteses para multiplos JOINs
    acc_cur.execute("""
        SELECT
            p.DATA_HISTORICO, p.ID_CARTEIRA, p.ID_COTISTA,
            p.VALOR_BRUTO, p.VALOR_LIQUIDO, p.QUANTIDADE, p.COTA_DIA,
            p.VALOR_APLICADO, p.DATA_APLICACAO, p.COTA_APLICACAO,
            p.QUANTIDADE_BLOQUEADA, p.VALOR_IR, p.VALOR_IOF,
            p.VALOR_PERFORMACE, p.VALOR_RENDIMENTO
        FROM (BriTech_Posicao_Cotista p
            INNER JOIN BriTech_Cotistas c ON c.ID_COTISTA = p.ID_COTISTA)
            INNER JOIN BriTech_Carteiras f ON f.Id_Carteira = p.ID_CARTEIRA
        WHERE p.DATA_HISTORICO IS NOT NULL
        ORDER BY p.DATA_HISTORICO
    """)

    count = 0
    skipped_fundo = 0
    skipped_cotista = 0

    for row in acc_cur.fetchall():
        (data, id_carteira, id_cotista, vl_bruto, vl_liq, qtd, cota,
         vl_aplicado, dt_aplicacao, cota_aplicacao, qtd_bloq,
         vl_ir, vl_iof, vl_perf, vl_rend) = row

        id_fundo = fundo_map.get(int(id_carteira) if id_carteira else None)
        id_cot = cotista_map.get(int(id_cotista) if id_cotista else None)

        if not id_fundo:
            skipped_fundo += 1
            continue

        if not id_cot:
            skipped_cotista += 1
            continue

        if isinstance(data, datetime):
            data_pos = data.date()
        else:
            data_pos = data

        # Garantir qt_cotas >= 0 (constraint ck_qt_cotas)
        qt_cotas = max(0, float(qtd) if qtd else 0)

        try:
            pg_cur.execute("""
                INSERT INTO pos.pos_passivo (
                    id_fundo, id_cotista, id_serie, data_pos,
                    qt_cotas, qt_cotas_bloqueadas,
                    cota_aplicacao, cota_dia,
                    valor_aplicado, valor_bruto, valor_liquido,
                    valor_rendimento, valor_ir, valor_iof, valor_performance,
                    data_aplicacao, is_active
                ) VALUES (
                    %s, %s, NULL, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true
                )
                ON CONFLICT DO NOTHING
            """, (
                id_fundo, id_cot, data_pos,
                qt_cotas,
                float(qtd_bloq) if qtd_bloq else 0,
                float(cota_aplicacao) if cota_aplicacao else None,
                float(cota) if cota else None,
                float(vl_aplicado) if vl_aplicado else None,
                float(vl_bruto) if vl_bruto else 0,
                float(vl_liq) if vl_liq else 0,
                float(vl_rend) if vl_rend else 0,
                float(vl_ir) if vl_ir else 0,
                float(vl_iof) if vl_iof else 0,
                float(vl_perf) if vl_perf else 0,
                dt_aplicacao.date() if isinstance(dt_aplicacao, datetime) else dt_aplicacao
            ))
            count += 1

            if count % batch_size == 0:
                pg_conn.commit()
                log.info(f"    Passivo processado: {count:,}")

        except Exception as e:
            log.warning(f"Erro passivo: {e}")
            pg_conn.rollback()

    pg_conn.commit()
    log.info(f"  Passivo migrado: {count:,}")
    log.info(f"  Ignorados - fundo: {skipped_fundo:,} | cotista: {skipped_cotista:,}")
    return count

# =============================================================================
# MAIN
# =============================================================================

def run_migration(steps=None):
    """
    Executa a migracao completa ou parcial.

    Args:
        steps: Lista de etapas a executar. Se None, executa todas.
               Opcoes: ['fundos', 'cotistas', 'cotas', 'caixa', 'cpr', 'passivo']
    """

    all_steps = ['fundos', 'cotistas', 'cotas', 'caixa', 'cpr', 'passivo']
    steps = steps or all_steps

    log.info("="*60)
    log.info("INICIO DA MIGRACAO ACCESS -> POSTGRESQL")
    log.info("="*60)

    # Conectar
    log.info("Conectando aos bancos...")
    acc_conn = connect_access()
    pg_conn = connect_postgres()

    results = {}

    try:
        if 'fundos' in steps:
            results['fundos'] = migrate_fundos(acc_conn, pg_conn)

        if 'cotistas' in steps:
            results['cotistas'] = migrate_cotistas(acc_conn, pg_conn)

        if 'cotas' in steps:
            results['cotas'] = migrate_historico_cotas(acc_conn, pg_conn)

        if 'caixa' in steps:
            results['caixa'] = migrate_caixa(acc_conn, pg_conn)

        if 'cpr' in steps:
            results['cpr'] = migrate_cpr(acc_conn, pg_conn)

        if 'passivo' in steps:
            results['passivo'] = migrate_passivo(acc_conn, pg_conn)

    finally:
        acc_conn.close()
        pg_conn.close()

    # Relatorio
    log.info("="*60)
    log.info("RELATORIO DE MIGRACAO")
    log.info("="*60)
    for step, count in results.items():
        log.info(f"  {step}: {count:,} registros")
    log.info(f"  TOTAL: {sum(results.values()):,} registros")
    log.info("="*60)

    return results

if __name__ == "__main__":
    # Executar migracao completa
    # run_migration()

    # Ou executar apenas algumas etapas:
    # run_migration(['fundos', 'cotistas'])

    # Executar CPR e Passivo (apos ajustes)
    # CPR ja foi migrado (28.137 registros)
    run_migration(['passivo'])
