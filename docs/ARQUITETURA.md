# Arquitetura do Sistema ETL QORE

Documentacao tecnica da arquitetura do sistema de automacao para gestao de fundos.

---

## Indice

1. [Visao Geral](#visao-geral)
2. [Diagrama de Arquitetura](#diagrama-de-arquitetura)
3. [Camadas do Sistema](#camadas-do-sistema)
4. [Fluxo de Dados](#fluxo-de-dados)
5. [Componentes Principais](#componentes-principais)
6. [Modelo de Dados](#modelo-de-dados)
7. [Padroes de Design](#padroes-de-design)
8. [Seguranca](#seguranca)
9. [Escalabilidade](#escalabilidade)

---

## Visao Geral

O sistema ETL QORE foi projetado para automatizar a extracao, transformacao e
carga de dados financeiros do portal QORE para bancos de dados locais (Access)
e na nuvem (PostgreSQL).

### Evolucao do Sistema

| Versao | Metodo | Status | Descricao |
|--------|--------|--------|-----------|
| v1.0 | Selenium | Legado | Automacao via browser |
| **v2.0** | **API HTTP** | **Atual** | **Chamadas REST diretas** |

A versao 2.0 (API HTTP) oferece ganhos significativos de performance:

- **10x mais rapido**: 30s vs 5min para 34 fundos
- **10x menos memoria**: 50MB vs 500MB
- **Maior estabilidade**: Sem fragilidade de DOM
- **Menos dependencias**: Sem Chrome/Driver

---

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PORTAL QORE                                       │
│                     hub.qoredtvm.com.br                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         REST API                                     │    │
│  │  POST /api/v1/authorize           (Autenticacao JWT)                │    │
│  │  GET  /api/v1/fundos-posicao/{uuid}/arquivos  (Listagem)            │    │
│  │  GET  /api/v1/fundos-posicao/{uuid}/arquivos/{guid}/download        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    │ HTTPS/JWT
                                    │
┌───────────────────────────────────┴─────────────────────────────────────────┐
│                        CAMADA DE AUTOMACAO                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     automacao_qore_api.py                              │ │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐   │ │
│  │  │QoreAPIClient │  │QoreDownloadMgr   │  │QoreAutomationAPI       │   │ │
│  │  │              │  │                  │  │                        │   │ │
│  │  │- authenticate│  │- ThreadPoolExec  │  │- executar()            │   │ │
│  │  │- get_files   │  │- 10 workers      │  │- carregar_config()     │   │ │
│  │  │- download    │  │- parallelism     │  │- processar_downloads() │   │ │
│  │  └──────────────┘  └──────────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    v               v               v
            ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
            │   PDF Files   │ │  Excel Files  │ │   XML Files   │
            │ (Carteiras)   │ │ (Carteiras)   │ │ (ANBIMA 5.0)  │
            └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                    │               │               │
                    v               v               v
┌───────────────────────────────────────────────────────────────────────────┐
│                       CAMADA DE PROCESSAMENTO                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  FileHandler    │  │  FundoManager   │  │  XML Parser     │            │
│  │                 │  │                 │  │                 │            │
│  │- processar_zip  │  │- carregar_fundos│  │- parse_anbima   │            │
│  │- mover_arquivo  │  │- get_sigla      │  │- extrair_dados  │            │
│  │- versionar      │  │- match_uuid     │  │- validar        │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    v               v               v
┌───────────────────────────────────────────────────────────────────────────┐
│                          CAMADA DE DADOS                                   │
│                                                                            │
│  ┌─────────────────────┐              ┌─────────────────────┐             │
│  │   Microsoft Access  │  migration   │     PostgreSQL      │             │
│  │       (Local)       │ ──────────>  │     (AWS RDS)       │             │
│  │                     │              │                     │             │
│  │ - Cotas_Patrimonio  │              │ - cad.info_fundos   │             │
│  │ - Caixa_Qore        │              │ - pos.pos_cota      │             │
│  │ - RF_Qore           │              │ - pos.pos_caixa     │             │
│  └─────────────────────┘              └─────────────────────┘             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    v
┌────────────────────────────────────────────────────────────────────────────┐
│                       CAMADA DE APRESENTACAO                                │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  db_viewer_3d   │  │  dash_db_viewer │  │  config_web     │             │
│  │   (Three.js)    │  │  (Dash/Plotly)  │  │    (Flask)      │             │
│  │                 │  │                 │  │                 │             │
│  │ - Schema 3D     │  │ - Graficos PL   │  │ - Config fundos │             │
│  │ - Relacoes      │  │ - Cotas         │  │ - Parametros    │             │
│  │ - Navegacao     │  │ - Composicao    │  │ - Datas         │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Camadas do Sistema

### 1. Camada de Origem (Portal QORE)

Interface externa com a plataforma QORE:

- **API REST**: Endpoints para autenticacao e download
- **Formatos**: PDF, Excel, XML (ANBIMA 4.01 e 5.0)
- **Autenticacao**: JWT Bearer token

### 2. Camada de Automacao

Responsavel pela comunicacao com a API:

| Componente | Funcao |
|------------|--------|
| `QoreAPIClient` | Cliente HTTP com retry automatico |
| `QoreDownloadManager` | Orquestracao de downloads paralelos |
| `QoreAutomationAPI` | Classe principal de execucao |

### 3. Camada de Processamento

Tratamento e transformacao dos dados:

| Componente | Funcao |
|------------|--------|
| `FileHandler` | Movimentacao e versionamento de arquivos |
| `FundoManager` | Gerenciamento de lista de fundos |
| `XML Parser` | Parse de XML ANBIMA 5.0/4.01 |

### 4. Camada de Dados

Persistencia dos dados processados:

| Banco | Tipo | Uso |
|-------|------|-----|
| Microsoft Access | Local | Dados operacionais diarios |
| PostgreSQL | Cloud (AWS) | Historico e analytics |

### 5. Camada de Apresentacao

Interfaces para visualizacao e configuracao:

| Aplicacao | Tecnologia | Funcao |
|-----------|------------|--------|
| db_viewer_3d | Three.js | Visualizacao 3D do schema |
| dash_db_viewer | Dash/Plotly | Dashboards interativos |
| config_web | Flask | Configuracao de fundos |

---

## Fluxo de Dados

### Fluxo Principal (ETL)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ CONFIG  │────>│  AUTH   │────>│  LIST   │────>│DOWNLOAD │────>│ PROCESS │
│ (xlsx)  │     │  (JWT)  │     │ (files) │     │ (files) │     │ (parse) │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └────┬────┘
                                                                     │
                                                                     v
                                                              ┌─────────────┐
                                                              │   UPLOAD    │
                                                              │  (Access)   │
                                                              └──────┬──────┘
                                                                     │
                                                                     v
                                                              ┌─────────────┐
                                                              │   NOTIFY    │
                                                              │  (Email)    │
                                                              └─────────────┘
```

### Detalhamento das Etapas

1. **CONFIG**: Carrega configuracoes da planilha DOWNLOADS_AUX.xlsx
   - Credenciais, datas, flags de tipo, caminhos

2. **AUTH**: Autentica na API QORE
   - POST /api/v1/authorize
   - Obtem JWT token

3. **LIST**: Lista arquivos disponiveis
   - GET /api/v1/fundos-posicao/{uuid}/arquivos
   - Filtra por tipo (PDF/Excel/XML) e data

4. **DOWNLOAD**: Baixa arquivos em paralelo
   - ThreadPoolExecutor com 10 workers
   - Retry automatico com backoff

5. **PROCESS**: Processa arquivos baixados
   - Extrai de ZIPs se necessario
   - Move para pastas de destino
   - Aplica versionamento

6. **UPLOAD**: Carrega dados no banco
   - Parse de XML
   - INSERT/UPDATE no Access

7. **NOTIFY**: Envia relatorio
   - Email via Outlook (COM)

---

## Componentes Principais

### QoreAPIClient

Cliente HTTP para comunicacao com a API QORE.

```python
class QoreAPIClient:
    """
    Cliente HTTP com autenticacao JWT e retry automatico.

    Attributes:
        credentials: Credenciais de acesso
        token: JWT token atual
        session: Sessao HTTP com retry configurado

    Methods:
        authenticate() -> bool: Autentica e obtem token
        get_fund_files(uuid, tipo) -> List[Dict]: Lista arquivos
        download_file_by_guid(uuid, guid, path) -> bool: Baixa arquivo
    """
```

Caracteristicas:
- Retry automatico (3 tentativas, backoff 0.5s)
- Timeout configuravel (connect: 10s, read: 60s)
- Headers padrao para JSON

### QoreDownloadManager

Orquestrador de downloads paralelos.

```python
class QoreDownloadManager:
    """
    Gerencia downloads paralelos usando ThreadPoolExecutor.

    Attributes:
        api: Instancia de QoreAPIClient
        file_handler: Instancia de FileHandler
        fundo_manager: Instancia de FundoManager
        fundos_uuid: Mapeamento nome -> UUID

    Methods:
        load_fundos_uuid() -> bool: Carrega UUIDs do JSON
        download_all_funds(tipos) -> Dict: Executa downloads
    """
```

Caracteristicas:
- 10 workers paralelos
- Processamento por tipo (PDF/Excel/XML)
- Resultado agregado por fundo/tipo

### FundoManager

Gerenciador de lista de fundos.

```python
class FundoManager:
    """
    Gerencia lista de fundos e suas siglas.

    Attributes:
        bd_path: Caminho do BD.xlsx
        fundos: Dict {nome: pasta}
        siglas: Dict {nome: sigla_busca}

    Methods:
        carregar_fundos() -> bool: Carrega do BD.xlsx
        get_sigla(nome) -> str: Retorna sigla de busca
        is_bloko(nome) -> bool: Verifica se e fundo BLOKO
    """
```

---

## Modelo de Dados

### Microsoft Access (Local)

**Tabelas de Input QORE:**

```sql
-- Cotas e Patrimonio
CREATE TABLE Cotas_Patrimonio_Qore (
    DATA_INPUT DATE,
    FUNDO VARCHAR(100),
    [PL Posicao] DECIMAL(18,2),
    QtdeCota DECIMAL(18,8),
    [Valor da Cota Bruta] DECIMAL(18,8)
);

-- Caixa
CREATE TABLE Caixa_Qore (
    DATA_INPUT DATE,
    FUNDO VARCHAR(100),
    Descricao VARCHAR(200),
    Moeda_Origem VARCHAR(10),
    Valor DECIMAL(18,2)
);
```

### PostgreSQL (AWS RDS)

**Schema: cad (Cadastro)**

```sql
CREATE TABLE cad.info_fundos (
    id_fundo SERIAL PRIMARY KEY,
    nome_fundo VARCHAR(200),
    cnpj VARCHAR(20),
    tipo_fundo VARCHAR(50),
    status VARCHAR(20),
    data_inicio DATE,
    data_fim DATE
);

CREATE TABLE cad.info_rf (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50),
    emissor VARCHAR(200),
    indexador VARCHAR(50),
    taxa DECIMAL(10,4),
    vencimento DATE
);

CREATE TABLE cad.info_rv (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    nome VARCHAR(200),
    setor VARCHAR(100),
    tipo VARCHAR(50)
);
```

**Schema: pos (Posicao)**

```sql
CREATE TABLE pos.pos_cota (
    id SERIAL PRIMARY KEY,
    id_fundo INTEGER REFERENCES cad.info_fundos,
    data_pos DATE,
    pl_posicao DECIMAL(18,2),
    qtde_cota DECIMAL(18,8),
    valor_cota DECIMAL(18,8),
    UNIQUE(id_fundo, data_pos)
);

CREATE TABLE pos.pos_caixa_2025 (
    id SERIAL PRIMARY KEY,
    id_fundo INTEGER REFERENCES cad.info_fundos,
    data_pos DATE,
    descricao VARCHAR(200),
    moeda VARCHAR(10),
    valor DECIMAL(18,2)
);
```

---

## Padroes de Design

### 1. Strategy Pattern (Parsers)

Permite multiplos parsers para diferentes formatos:

```python
from abc import ABC, abstractmethod

class ReportParser(ABC):
    """Interface base para parsers de relatorio."""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Verifica se o parser pode processar o arquivo."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> pd.DataFrame:
        """Processa o arquivo e retorna DataFrame."""
        pass

class Xml5Parser(ReportParser):
    """Parser para XML ANBIMA 5.0."""
    pass

class LegacyExcelParser(ReportParser):
    """Parser para Excel formato legado."""
    pass

class NewExcelParser(ReportParser):
    """Parser para Excel formato novo."""
    pass
```

### 2. Pipeline Pattern

Execucao sequencial de etapas:

```python
class QorePipeline:
    """Pipeline ETL completo."""

    def run(self):
        self.extract()   # Download do QORE
        self.transform() # Parse dos arquivos
        self.load()      # Upload para banco
        self.notify()    # Email de resultado
```

### 3. Dataclass Configuration

Configuracao tipada e validada:

```python
@dataclass
class QoreCredentials:
    """Credenciais de acesso ao QORE."""
    url: str
    email: str
    senha: str

@dataclass
class QorePaths:
    """Caminhos de destino dos arquivos."""
    pdf: str
    excel: str
    xml: str
    temp_download: str
    bd_path: str

@dataclass
class QoreFlags:
    """Flags de controle."""
    pdf_enabled: bool = False
    excel_enabled: bool = False
    xml_enabled: bool = False

@dataclass
class QoreDatas:
    """Datas de referencia."""
    data_inicial: datetime
    data_final: datetime
```

### 4. Singleton Logger

Logger unico com formatacao customizada:

```python
class LogFormatter(logging.Formatter):
    """Formatter com cores e simbolos."""

    SYMBOLS = {
        'INFO': '[+]',
        'WARNING': '[!]',
        'ERROR': '[X]',
    }

log = setup_logging()  # Singleton
```

---

## Seguranca

### Credenciais

| Tipo | Armazenamento | Recomendacao |
|------|---------------|--------------|
| QORE | Planilha Excel | Migrar para .env |
| PostgreSQL | Arquivo Python | Usar .env |
| Access | Caminho local | OK |

### Boas Praticas Implementadas

1. **Sem credenciais em codigo**: Todas em arquivos externos
2. **Tokens temporarios**: JWT com expiracao
3. **HTTPS**: Toda comunicacao criptografada
4. **Sessao encerrada**: Automaticamente apos uso

### Recomendacoes Futuras

```python
# .env (nao commitado)
QORE_USERNAME=usuario@email.com
QORE_PASSWORD=senha_segura
POSTGRES_URI=postgresql://user:pass@host/db

# Uso
import os
from dotenv import load_dotenv

load_dotenv()
username = os.getenv('QORE_USERNAME')
```

---

## Escalabilidade

### Atual

- **Processamento**: Paralelo (10 workers)
- **Banco local**: Access (~2GB limite)
- **Banco cloud**: PostgreSQL (ilimitado)

### Gargalos Conhecidos

| Gargalo | Impacto | Solucao |
|---------|---------|---------|
| Access 2GB | Limite de dados | Migracao PostgreSQL |
| 10 workers | Limite de paralelismo | Aumentar workers |
| Token unico | Sem refresh | Implementar refresh |

### Evolucoes Planejadas

1. **Migracao completa PostgreSQL**
   - Eliminar dependencia do Access
   - Queries mais performaticas

2. **Cache Redis**
   - UUIDs de fundos
   - Tokens JWT

3. **Fila de Tarefas (Celery)**
   - Processamento assincrono
   - Retry automatico
   - Monitoramento

4. **Containerizacao (Docker)**
   - Deploy padronizado
   - Escalabilidade horizontal

---

## Monitoramento

### Logging Estruturado

```
[+] Autenticacao OK!
[+] Carregados 34 fundos QORE
[+] Iniciando 102 downloads (10 workers)...
[+]   FUNDO_XYZ [PDF]: 1 arquivo(s)
[+]   FUNDO_XYZ [EXCEL]: 1 arquivo(s)
[!]   FUNDO_ABC [XML]: Nenhum arquivo no periodo
[X]   FUNDO_DEF [PDF]: Timeout
```

### Metricas Coletadas

| Metrica | Descricao |
|---------|-----------|
| Total de tarefas | Fundos x Tipos habilitados |
| Processadas | Downloads bem-sucedidos |
| Com erro | Downloads falhos |
| Tempo total | Duracao da execucao |

### Notificacao por Email

Email automatico via Outlook (COM):
- Status geral (sucesso/erro)
- Lista de fundos processados
- Detalhamento de erros
- Estatisticas

---

## Referencias

- [ANBIMA - Padrao XML 5.0](https://www.anbima.com.br)
- [ISO 20022 SEMT.003](https://www.iso20022.org)
- [Requests - HTTP for Humans](https://docs.python-requests.org)
- [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html)

---

*Documentacao atualizada em Dezembro 2025*
*ETL Team*
