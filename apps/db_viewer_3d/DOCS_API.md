# Database 3D Viewer - Documentacao Tecnica de APIs e Queries

## Sumario

1. [Configuracao do Banco](#configuracao-do-banco)
2. [Endpoints de Conexao](#endpoints-de-conexao)
3. [Endpoints de Schema](#endpoints-de-schema)
4. [Endpoints de Fundos](#endpoints-de-fundos)
5. [Endpoints de Portfolio](#endpoints-de-portfolio)
6. [Endpoints de Export](#endpoints-de-export)
7. [Modelo de Dados](#modelo-de-dados)

---

## Configuracao do Banco

### Conexao PostgreSQL

```python
DB_CONFIG = {
    'host': 'prod-db2.c5kgei88itd4.sa-east-1.rds.amazonaws.com',
    'database': 'nscapital',
    'user': 'nscapitaladmin',
    'password': '********',
    'port': 5432
}

VISIBLE_SCHEMAS = ['cad', 'pos', 'aux', 'stage']
```

### Context Manager de Conexao

```python
@contextmanager
def get_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn:
            conn.close()
```

---

## Endpoints de Conexao

### GET /api/test

**Descricao**: Testa conectividade com o banco de dados.

**Query SQL**:
```sql
SELECT 1
```

**Response (200)**:
```json
{
    "status": "ok",
    "message": "Database connected"
}
```

**Response (500)**:
```json
{
    "status": "error",
    "message": "connection refused..."
}
```

---

### GET /api/stats

**Descricao**: Retorna estatisticas gerais do banco de dados.

**Queries SQL**:

```sql
-- Total de fundos ativos
SELECT COUNT(*) FROM cad.info_fundos WHERE is_active = true

-- Total de cotistas ativos
SELECT COUNT(*) FROM cad.info_cotistas WHERE is_active = true

-- Range de datas dos dados
SELECT MIN(data_pos), MAX(data_pos) FROM pos.pos_cota

-- PL total na data mais recente
SELECT SUM(pl_fechamento)
FROM pos.pos_cota
WHERE data_pos = (SELECT MAX(data_pos) FROM pos.pos_cota)
```

**Response (200)**:
```json
{
    "total_funds": 45,
    "total_investors": 90,
    "date_start": "2020-01-02",
    "date_end": "2025-12-17",
    "total_pl": 15234567890.50
}
```

---

## Endpoints de Schema

### GET /api/schemas

**Descricao**: Lista todos os schemas visiveis com contagem de tabelas.

**Query SQL**:
```sql
SELECT
    s.schema_name,
    COUNT(t.table_name) as table_count
FROM information_schema.schemata s
LEFT JOIN information_schema.tables t ON t.table_schema = s.schema_name
WHERE s.schema_name = ANY(ARRAY['cad', 'pos', 'aux', 'stage'])
GROUP BY s.schema_name
ORDER BY s.schema_name
```

**Response (200)**:
```json
[
    {"name": "aux", "table_count": 6},
    {"name": "cad", "table_count": 14},
    {"name": "pos", "table_count": 84},
    {"name": "stage", "table_count": 7}
]
```

---

### GET /api/tables/{schema}

**Descricao**: Lista tabelas de um schema especifico com contagem de linhas.

**Parametros**:
| Param | Tipo | Descricao |
|-------|------|-----------|
| schema | path | Nome do schema (cad, pos, aux, stage) |

**Queries SQL**:
```sql
-- Lista de tabelas
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = :schema
ORDER BY table_name

-- Contagem de linhas (estimativa rapida)
SELECT reltuples::bigint
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :schema AND c.relname = :table_name
```

**Response (200)**:
```json
[
    {"name": "info_fundos", "type": "BASE TABLE", "row_count": 81},
    {"name": "info_cotistas", "type": "BASE TABLE", "row_count": 90},
    {"name": "info_rf", "type": "BASE TABLE", "row_count": 57}
]
```

**Response (400)**:
```json
{"error": "Invalid schema"}
```

---

### GET /api/all-tables

**Descricao**: Lista todas as tabelas de todos os schemas visiveis.

**Queries SQL**:
```sql
-- Para cada schema em VISIBLE_SCHEMAS:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = :schema AND table_type = 'BASE TABLE'
ORDER BY table_name

-- Contagem de colunas
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_schema = :schema AND table_name = :table_name

-- Contagem de linhas (estimativa)
SELECT reltuples::bigint
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :schema AND c.relname = :table_name
```

**Response (200)**:
```json
[
    {
        "schema": "cad",
        "name": "info_fundos",
        "full_name": "cad.info_fundos",
        "columns": 15,
        "rows": 81
    },
    {
        "schema": "pos",
        "name": "pos_cota",
        "full_name": "pos.pos_cota",
        "columns": 12,
        "rows": 125000
    }
]
```

---

### GET /api/columns/{schema}/{table}

**Descricao**: Lista colunas de uma tabela especifica.

**Parametros**:
| Param | Tipo | Descricao |
|-------|------|-----------|
| schema | path | Nome do schema |
| table | path | Nome da tabela |

**Query SQL**:
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = :schema AND table_name = :table
ORDER BY ordinal_position
```

**Response (200)**:
```json
[
    {
        "name": "id_fundo",
        "type": "integer",
        "nullable": false,
        "default": "nextval('cad.info_fundos_id_fundo_seq'::regclass)"
    },
    {
        "name": "nome_fundo",
        "type": "character varying",
        "nullable": false,
        "default": null
    },
    {
        "name": "is_active",
        "type": "boolean",
        "nullable": false,
        "default": "true"
    }
]
```

---

### GET /api/foreign-keys

**Descricao**: Lista todas as foreign keys entre tabelas dos schemas visiveis.

**Query SQL**:
```sql
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
    AND tc.table_schema = ANY(ARRAY['cad', 'pos', 'aux', 'stage'])
```

**Response (200)**:
```json
[
    {
        "source_schema": "pos",
        "source_table": "pos_cota",
        "source_column": "id_fundo",
        "target_schema": "cad",
        "target_table": "info_fundos",
        "target_column": "id_fundo"
    }
]
```

---

## Endpoints de Fundos

### GET /api/funds

**Descricao**: Lista todos os fundos ativos.

**Query SQL**:
```sql
SELECT id_fundo, nome_fundo, nome_curto, tipo_fundo
FROM cad.info_fundos
WHERE is_active = true
ORDER BY nome_fundo
```

**Response (200)**:
```json
[
    {
        "id": 3,
        "name": "AJAX FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "short_name": "AJAX FIDC",
        "type": "FIDC"
    },
    {
        "id": 39,
        "name": "BLOKO FIM CREDITO PRIVADO",
        "short_name": "BLOKO FIM",
        "type": "FIM"
    }
]
```

---

### GET /api/nav/{fund_id}

**Descricao**: Retorna historico de NAV (Net Asset Value) de um fundo.

**Parametros**:
| Param | Tipo | Descricao |
|-------|------|-----------|
| fund_id | path | ID do fundo |
| period | query | Periodo: 30, 90, 180, 365, all (default: 365) |

**Queries SQL**:

```sql
-- Com filtro de periodo
SELECT data_pos, pl_fechamento, cota_fechamento, qt_cotas_fech
FROM pos.pos_cota
WHERE id_fundo = :fund_id AND data_pos >= :start_date
ORDER BY data_pos DESC

-- Sem filtro (all)
SELECT data_pos, pl_fechamento, cota_fechamento, qt_cotas_fech
FROM pos.pos_cota
WHERE id_fundo = :fund_id
ORDER BY data_pos DESC
```

**Response (200)**:
```json
[
    {
        "date": "2025-01-02",
        "pl": 520569211.22,
        "quota": 1.234567,
        "shares": 421500000.00
    },
    {
        "date": "2025-01-03",
        "pl": 521234567.89,
        "quota": 1.235678,
        "shares": 421500000.00
    }
]
```

---

### GET /api/funds-comparison

**Descricao**: Comparacao de PL entre todos os fundos ativos (ultima data disponivel de cada um).

**Query SQL**:
```sql
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
```

**Response (200)**:
```json
[
    {
        "id": 81,
        "name": "FIM SOMME",
        "type": "FIM",
        "pl": 2172532803.60,
        "date": "2025-12-17"
    },
    {
        "id": 75,
        "name": "MARNE FIDC NP",
        "type": "FIDC",
        "pl": 2167897996.67,
        "date": "2025-12-04"
    }
]
```

---

### GET /api/quota-evolution/{fund_id}

**Descricao**: Evolucao da cota com metricas de performance.

**Parametros**:
| Param | Tipo | Descricao |
|-------|------|-----------|
| fund_id | path | ID do fundo |
| period | query | Periodo: 30, 90, 180, 365, all (default: 365) |

**Query SQL**:
```sql
SELECT data_pos, cota_fechamento
FROM pos.pos_cota
WHERE id_fundo = :fund_id AND data_pos >= :start_date
ORDER BY data_pos ASC
```

**Calculo de Metricas (Python)**:
```python
first_quota = data[0]['quota']
last_quota = data[-1]['quota']
total_return = ((last_quota / first_quota) - 1) * 100
max_quota = max(quotas)
min_quota = min(quotas)
```

**Response (200)**:
```json
{
    "data": [
        {"date": "2025-01-02", "quota": 1.234567},
        {"date": "2025-01-03", "quota": 1.235678}
    ],
    "metrics": {
        "total_return": 15.23,
        "first_quota": 1.234567,
        "last_quota": 1.422789,
        "max_quota": 1.450000,
        "min_quota": 1.200000,
        "data_points": 250
    }
}
```

---

## Endpoints de Portfolio

### GET /api/portfolio/{fund_id}

**Descricao**: Composicao detalhada da carteira de um fundo com breakdown por categoria de ativo.

**Parametros**:
| Param | Tipo | Descricao |
|-------|------|-----------|
| fund_id | path | ID do fundo |
| date | query | Data especifica (opcional, default: ultima disponivel) |

**Queries SQL**:

#### 1. Obter data mais recente
```sql
SELECT MAX(data_pos) FROM pos.pos_cota WHERE id_fundo = :fund_id
```

#### 2. Nome do fundo
```sql
SELECT nome_curto FROM cad.info_fundos WHERE id_fundo = :fund_id
```

#### 3. Caixa (Cash)
```sql
SELECT
    COALESCE(c.banco, 'Conta ' || p.id_conta::text, 'Caixa') as nome,
    p.saldo_fechamento
FROM pos.pos_caixa_2025 p
LEFT JOIN cad.info_contas c ON p.id_conta = c.id_conta
WHERE p.id_fundo = :fund_id
    AND p.data_pos = :target_date
    AND p.saldo_fechamento > 0
ORDER BY p.saldo_fechamento DESC
```

**Tabelas envolvidas**:
- `pos.pos_caixa_2025`: Posicoes de caixa
- `cad.info_contas`: Cadastro de contas bancarias

#### 4. Renda Fixa (Fixed Income)
```sql
SELECT
    COALESCE(i.nome_ativo, i.cod_ativo, 'N/A') as nome,
    i.tipo_titulo,
    i.indexador,
    p.valor_mercado
FROM pos.pos_rf_2025 p
LEFT JOIN cad.info_rf i ON p.id_ativo_rf = i.id_ativo_rf
WHERE p.id_fundo = :fund_id
    AND p.data_pos = :target_date
    AND p.valor_mercado > 0
ORDER BY p.valor_mercado DESC
```

**Tabelas envolvidas**:
- `pos.pos_rf_2025`: Posicoes de renda fixa
- `cad.info_rf`: Cadastro de ativos de renda fixa

**Campos de cadastro (cad.info_rf)**:
| Campo | Descricao |
|-------|-----------|
| id_ativo_rf | ID unico do ativo |
| cod_ativo | Codigo do ativo |
| nome_ativo | Nome descritivo |
| tipo_titulo | LTN, NTN-B, CDB, LCI, LCA, etc |
| indexador | PREFIXADO, CDI, IPCA, SELIC, etc |

#### 5. Renda Variavel (Equities)
```sql
SELECT
    COALESCE(i.cod_papel, i.nome_papel, 'N/A') as nome,
    i.tipo_papel,
    p.valor_mercado
FROM pos.pos_rv_2025 p
LEFT JOIN cad.info_rv i ON p.id_ativo_rv = i.id_ativo_rv
WHERE p.id_fundo = :fund_id
    AND p.data_pos = :target_date
    AND p.valor_mercado > 0
ORDER BY p.valor_mercado DESC
```

**Tabelas envolvidas**:
- `pos.pos_rv_2025`: Posicoes de renda variavel
- `cad.info_rv`: Cadastro de acoes/papeis

**Campos de cadastro (cad.info_rv)**:
| Campo | Descricao |
|-------|-----------|
| id_ativo_rv | ID unico do ativo |
| cod_papel | Ticker (PETR4, VALE3, etc) |
| nome_papel | Nome da empresa |
| tipo_papel | ON, PN, UNIT, BDR, ETF |
| categoria | Acao, FII, ETF, BDR |

#### 6. Direitos Creditorios
```sql
SELECT
    COALESCE(i.nome_sacado, i.cod_ativo_dc, 'N/A') as nome,
    i.tipo_recebivel,
    p.valor_presente
FROM pos.pos_dir_cred_2025 p
LEFT JOIN cad.info_dir_cred i ON p.id_ativo_dc = i.id_ativo_dc
WHERE p.id_fundo = :fund_id
    AND p.data_pos = :target_date
    AND p.valor_presente > 0
ORDER BY p.valor_presente DESC
```

**Tabelas envolvidas**:
- `pos.pos_dir_cred_2025`: Posicoes de direitos creditorios
- `cad.info_dir_cred`: Cadastro de recebiveis

**Campos de cadastro (cad.info_dir_cred)**:
| Campo | Descricao |
|-------|-----------|
| id_ativo_dc | ID unico do ativo |
| cod_ativo_dc | Codigo do recebivel |
| nome_sacado | Nome do devedor |
| tipo_recebivel | Duplicata, Cheque, CCB, etc |
| cnpj_sacado | CNPJ do devedor |

#### 7. CPR (Cedula de Produto Rural)
```sql
SELECT
    COALESCE(i.descricao, i.contraparte, 'CPR') as nome,
    i.tipo_cpr,
    p.valor_presente
FROM pos.pos_cpr_2025 p
LEFT JOIN cad.info_cpr i ON p.id_cpr = i.id_cpr
WHERE p.id_fundo = :fund_id
    AND p.data_pos = :target_date
    AND p.valor_presente > 0
ORDER BY p.valor_presente DESC
```

**Tabelas envolvidas**:
- `pos.pos_cpr_2025`: Posicoes de CPR
- `cad.info_cpr`: Cadastro de CPRs

**Campos de cadastro (cad.info_cpr)**:
| Campo | Descricao |
|-------|-----------|
| id_cpr | ID unico |
| tipo_cpr | PAGAR, RECEBER |
| descricao | Descricao do lancamento |
| contraparte | Nome da contraparte |

**Response (200)**:
```json
{
    "fund_id": 81,
    "fund_name": "FIM SOMME",
    "date": "2025-12-17",
    "total": 2172564621.72,
    "composition": [
        {
            "category": "Caixa",
            "value": 1896.47,
            "percentage": 0.0001,
            "color": "#58a6ff",
            "asset_count": 1,
            "assets": [
                {"name": "Caixa", "value": 1896.47}
            ]
        },
        {
            "category": "Renda Fixa",
            "value": 2172546816.19,
            "percentage": 99.9991,
            "color": "#3fb950",
            "asset_count": 1,
            "assets": [
                {
                    "name": "CDB BANCO XYZ",
                    "type": "CDB",
                    "index": "CDI",
                    "value": 2172546816.19
                }
            ]
        },
        {
            "category": "CPR",
            "value": 15909.06,
            "percentage": 0.0007,
            "color": "#d29922",
            "asset_count": 4,
            "assets": [
                {"name": "Taxa Adm - Nov/25", "type": "PAGAR", "value": 5000.00},
                {"name": "Taxa Gestao - Nov/25", "type": "PAGAR", "value": 5000.00},
                {"name": "Taxa Adm (Vl Dia)", "type": "PAGAR", "value": 2954.53},
                {"name": "Taxa Gestao (Vl Dia)", "type": "PAGAR", "value": 2954.53}
            ]
        }
    ]
}
```

---

## Endpoints de Export

### GET /api/preview/{schema}/{table}

**Descricao**: Amostra de 10 linhas de uma tabela.

**Query SQL**:
```sql
-- Colunas
SELECT column_name
FROM information_schema.columns
WHERE table_schema = :schema AND table_name = :table
ORDER BY ordinal_position

-- Dados (usando sql.Identifier para seguranca)
SELECT * FROM {schema}.{table} LIMIT 10
```

**Response (200)**:
```json
{
    "columns": ["id_fundo", "nome_fundo", "tipo_fundo", "is_active"],
    "rows": [
        {
            "id_fundo": 1,
            "nome_fundo": "FUNDO EXEMPLO",
            "tipo_fundo": "FIM",
            "is_active": true
        }
    ],
    "total": 10
}
```

---

### GET /api/export/{schema}/{table}

**Descricao**: Exporta tabela como arquivo CSV (maximo 10.000 linhas).

**Query SQL**:
```sql
SELECT * FROM {schema}.{table} LIMIT 10000
```

**Response**: Download de arquivo CSV

**Headers**:
```
Content-Type: text/csv
Content-Disposition: attachment; filename=cad_info_fundos.csv
```

---

## Modelo de Dados

### Diagrama de Relacionamentos

```
cad.info_fundos (1) ----< (N) pos.pos_cota
        |
        +----< (N) pos.pos_caixa_2025
        |
        +----< (N) pos.pos_rf_2025
        |
        +----< (N) pos.pos_rv_2025
        |
        +----< (N) pos.pos_dir_cred_2025
        |
        +----< (N) pos.pos_cpr_2025


cad.info_contas (1) ----< (N) pos.pos_caixa_2025
cad.info_rf (1) ----< (N) pos.pos_rf_2025
cad.info_rv (1) ----< (N) pos.pos_rv_2025
cad.info_dir_cred (1) ----< (N) pos.pos_dir_cred_2025
cad.info_cpr (1) ----< (N) pos.pos_cpr_2025
```

### Tabelas de Cadastro (Schema: cad)

#### cad.info_fundos
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_fundo | integer PK | ID unico |
| nome_fundo | varchar | Nome completo |
| nome_curto | varchar | Nome abreviado |
| tipo_fundo | varchar | FIM, FIDC, FIP, FIA |
| cnpj | varchar | CNPJ do fundo |
| is_active | boolean | Fundo ativo |
| data_criacao | timestamp | Data de cadastro |

#### cad.info_cotistas
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_cotista | integer PK | ID unico |
| nome_cotista | varchar | Nome |
| tipo_cotista | varchar | PF, PJ |
| cpf_cnpj | varchar | Documento |
| is_active | boolean | Ativo |

#### cad.info_contas
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_conta | integer PK | ID unico |
| id_fundo | integer FK | Fundo |
| banco | varchar | Nome do banco |
| agencia | varchar | Agencia |
| conta | varchar | Numero da conta |
| tipo_conta | varchar | CC, Poupanca |

#### cad.info_rf
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_ativo_rf | integer PK | ID unico |
| cod_ativo | varchar | Codigo |
| nome_ativo | varchar | Nome |
| tipo_titulo | varchar | LTN, NTN-B, CDB, etc |
| indexador | varchar | CDI, IPCA, SELIC |
| data_vencimento | date | Vencimento |

#### cad.info_rv
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_ativo_rv | integer PK | ID unico |
| cod_papel | varchar | Ticker |
| nome_papel | varchar | Nome empresa |
| categoria | varchar | Acao, FII, ETF |
| tipo_papel | varchar | ON, PN, UNIT |

#### cad.info_dir_cred
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_ativo_dc | integer PK | ID unico |
| id_fundo | integer FK | Fundo |
| cod_ativo_dc | varchar | Codigo |
| nome_sacado | varchar | Devedor |
| tipo_recebivel | varchar | Duplicata, CCB |
| cnpj_sacado | varchar | CNPJ devedor |

#### cad.info_cpr
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_cpr | integer PK | ID unico |
| id_fundo | integer FK | Fundo |
| tipo_cpr | varchar | PAGAR, RECEBER |
| descricao | varchar | Descricao |
| contraparte | varchar | Contraparte |
| valor_original | numeric | Valor |

### Tabelas de Posicao (Schema: pos)

#### pos.pos_cota
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_cota | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| data_pos | date | Data posicao |
| pl_fechamento | numeric | PL do dia |
| cota_fechamento | numeric | Valor da cota |
| qt_cotas_fech | numeric | Quantidade cotas |

#### pos.pos_caixa_2025
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_caixa | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| id_conta | integer FK | Conta bancaria |
| data_pos | date | Data posicao |
| saldo_fechamento | numeric | Saldo |

#### pos.pos_rf_2025
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_rf | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| id_ativo_rf | integer FK | Ativo RF |
| data_pos | date | Data posicao |
| valor_mercado | numeric | Valor de mercado |
| valor_custo | numeric | Valor de custo |

#### pos.pos_rv_2025
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_rv | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| id_ativo_rv | integer FK | Ativo RV |
| data_pos | date | Data posicao |
| qt_pos | numeric | Quantidade |
| valor_mercado | numeric | Valor de mercado |

#### pos.pos_dir_cred_2025
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_dc | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| id_ativo_dc | integer FK | Ativo DC |
| data_pos | date | Data posicao |
| valor_presente | numeric | Valor presente |
| status | varchar | NORMAL, ATRASO |

#### pos.pos_cpr_2025
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_pos_cpr | bigint PK | ID unico |
| id_fundo | integer FK | Fundo |
| id_cpr | integer FK | CPR |
| data_pos | date | Data posicao |
| valor_presente | numeric | Valor presente |
| status | varchar | Status |

---

## Cores por Categoria

| Categoria | Cor Hex | Uso |
|-----------|---------|-----|
| Caixa | #58a6ff | Azul |
| Renda Fixa | #3fb950 | Verde |
| Renda Variavel | #f85149 | Vermelho |
| Dir. Creditorios | #a371f7 | Roxo |
| CPR | #d29922 | Amarelo |

---

## Codigos de Erro

| Codigo | Descricao |
|--------|-----------|
| 200 | Sucesso |
| 400 | Schema/tabela invalido |
| 404 | Dados nao encontrados |
| 500 | Erro interno (banco/query) |

---

*Documentacao tecnica gerada para o projeto Database 3D Viewer*
