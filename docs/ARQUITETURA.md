# Arquitetura do Sistema ETL

## Visao Geral

O sistema ETL foi projetado para automatizar a extracao, transformacao e carga de dados financeiros do portal QORE para bancos de dados locais (Access) e na nuvem (PostgreSQL).

## Camadas do Sistema

```
┌────────────────────────────────────────────────────────────────┐
│                     CAMADA DE APRESENTACAO                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ db_viewer_3d │  │ dash_viewer  │  │ config_web   │          │
│  │  (Three.js)  │  │ (Dash/Plotly)│  │   (Flask)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                      CAMADA DE API REST                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Flask REST API (server.py)               │  │
│  │  /api/stats, /api/funds, /api/nav, /api/portfolio, ...   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                    CAMADA DE PROCESSAMENTO                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ automacao    │  │ xml_pipeline │  │ save_excel   │          │
│  │   _qore.py   │  │     .py      │  │    .py       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                       CAMADA DE DADOS                           │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │   Access     │   ──migration──>   │  PostgreSQL  │          │
│  │  (Local)     │                    │   (AWS RDS)  │          │
│  └──────────────┘                    └──────────────┘          │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                      CAMADA DE ORIGEM                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Portal QORE                            │  │
│  │  XML (ANBIMA 5.0) / Excel / PDF                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### 1. Extracao (Extract)

**Fonte:** Portal QORE via Selenium

```python
# automacao_qore.py
class QoreAutomation:
    def login() -> bool
    def download_xml(fund_id, date) -> str
    def download_excel(fund_id) -> str
```

**Formatos de Arquivo:**
- XML: ANBIMA 5.0 / ISO 20022 SEMT.003
- Excel: Carteira Diaria, Posicao
- PDF: Relatorios

### 2. Transformacao (Transform)

**Parsers Implementados:**

| Parser | Formato | Saida |
|--------|---------|-------|
| Xml5Parser | XML ANBIMA 5.0 | DataFrame |
| LegacyExcelParser | Excel antigo | DataFrame |
| NewExcelParser | Excel novo | DataFrame |

**Estrutura do XML:**
```xml
<Document>
  <SctiesBalAcctgRpt>
    <StmtGnlDtls>
      <StmtDtTm><Dt>2025-12-08</Dt></StmtDtTm>
    </StmtGnlDtls>
    <BalForAcct>
      <AcctBaseCcyAmts>
        <HldgVal><Amt>1000000.00</Amt></HldgVal>
      </AcctBaseCcyAmts>
    </BalForAcct>
    <SubAcctDtls>
      <BalForSubAcct>...</BalForSubAcct>
    </SubAcctDtls>
  </SctiesBalAcctgRpt>
</Document>
```

### 3. Carga (Load)

**Destino Primario:** Microsoft Access
```python
# qore_upload_xml.py
def upload_xml_data(data: dict, conn) -> bool:
    # DELETE duplicatas
    # INSERT novos registros
```

**Destino Secundario:** PostgreSQL (AWS RDS)
```python
# migration_access_to_postgres.py
def migrate_table(table_name: str) -> bool:
    # Leitura do Access
    # Transformacao de tipos
    # INSERT no PostgreSQL
```

## Modelo de Dados

### Access (Local)

**Tabelas de Input QORE:**
- Cotas_Patrimonio_Qore
- Caixa_Qore
- RF_Qore
- RV_Qore
- CPR_Qore
- Dir_Cred_Qore

### PostgreSQL (Nuvem)

**Schema: cad (Cadastro)**
```sql
-- Fundos
CREATE TABLE cad.info_fundos (
    id_fundo SERIAL PRIMARY KEY,
    nome_fundo VARCHAR(200),
    cnpj VARCHAR(20),
    tipo_fundo VARCHAR(50),
    status VARCHAR(20)
);

-- Ativos
CREATE TABLE cad.info_rf (...);
CREATE TABLE cad.info_rv (...);
CREATE TABLE cad.info_cpr (...);
CREATE TABLE cad.info_dir_cred (...);
CREATE TABLE cad.info_contas (...);
```

**Schema: pos (Posicao)**
```sql
-- Cotas e PL
CREATE TABLE pos.pos_cota (
    id_fundo INTEGER REFERENCES cad.info_fundos,
    data_pos DATE,
    pl_posicao NUMERIC(18,2),
    qtde_cota NUMERIC(18,8),
    valor_cota NUMERIC(18,8)
);

-- Posicoes por tipo de ativo
CREATE TABLE pos.pos_caixa_2025 (...);
CREATE TABLE pos.pos_rf_2025 (...);
CREATE TABLE pos.pos_rv_2025 (...);
CREATE TABLE pos.pos_cpr_2025 (...);
CREATE TABLE pos.pos_dir_cred_2025 (...);
```

## Padroes de Design

### Strategy Pattern (Parsers)
```python
class ReportParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: str) -> bool

    @abstractmethod
    def parse(self, file_path: str) -> bool

class Xml5Parser(ReportParser): ...
class LegacyExcelParser(ReportParser): ...
class NewExcelParser(ReportParser): ...
```

### Pipeline Pattern
```python
class QorePipeline:
    def run(self):
        self.extract()   # Download do QORE
        self.transform() # Parse dos arquivos
        self.load()      # Upload para banco
        self.notify()    # Email de resultado
```

### Dataclass Config
```python
@dataclass
class Timeouts:
    page_load: int = 30
    element_wait: int = 10
    download_wait: int = 60

@dataclass
class Paths:
    xml_output: str
    temp_download: str
    db_path: str
```

## Integracao com Calendario ANBIMA

Para calculo de D-1 (dia util anterior):

```python
from bizdays import Calendar

class CalendarioANBIMA:
    def __init__(self):
        self.cal = Calendar.load('ANBIMA')

    def d_minus_1(self, data: date) -> date:
        return self.cal.offset(data, -1)

    def is_business_day(self, data: date) -> bool:
        return self.cal.isbusday(data)
```

## Seguranca

### Credenciais
- Armazenadas em planilha Excel (nao em codigo)
- Recomendacao: Migrar para variaveis de ambiente

### Banco de Dados
- Access: Arquivo local com permissoes de sistema
- PostgreSQL: Credenciais em arquivo .env (gitignore)

### Selenium
- ChromeDriver deve estar atualizado
- Sessao automaticamente encerrada apos uso

## Escalabilidade

### Atual
- Execucao sequencial por fundo
- Banco Access local (limite ~2GB)

### Futuro (Recomendacoes)
- Processamento paralelo com ThreadPoolExecutor
- Migracao completa para PostgreSQL
- Adicionar cache Redis para consultas frequentes
- Implementar fila de tarefas (Celery/RQ)

## Monitoramento

### Logging
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
```

### Email de Notificacao
- Enviado automaticamente via Outlook (COM)
- Contem: Status, fundos processados, erros

## Referencias

- [ANBIMA - Padrao XML 5.0](https://www.anbima.com.br)
- [ISO 20022 SEMT.003](https://www.iso20022.org)
- [Selenium Python](https://selenium-python.readthedocs.io)
- [Three.js](https://threejs.org)
