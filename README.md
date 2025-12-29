# ETL QORE - Sistema de Automacao para Gestao de Fundos

<p align="center">
  <strong>Sistema de automacao para download, processamento e upload de dados financeiros do portal QORE</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/status-production-green.svg" alt="Status: Production">
  <img src="https://img.shields.io/badge/license-proprietary-red.svg" alt="License: Proprietary">
</p>

---

## Indice

- [Visao Geral](#visao-geral)
- [Arquitetura](#arquitetura)
- [Instalacao](#instalacao)
- [Uso Rapido](#uso-rapido)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Modulos Principais](#modulos-principais)
- [Configuracao](#configuracao)
- [API QORE](#api-qore)
- [Banco de Dados](#banco-de-dados)
- [Troubleshooting](#troubleshooting)

---

## Visao Geral

O **ETL QORE** e um sistema completo de automacao para gestao de fundos de investimento que integra com a plataforma QORE (hub.qoredtvm.com.br). O sistema permite:

- **Download automatizado** de relatorios (PDF, Excel, XML ANBIMA 5.0)
- **Processamento paralelo** de dados de multiplos fundos
- **Upload automatico** para bancos de dados Access e PostgreSQL
- **Notificacao por email** via Microsoft Outlook
- **Dashboards interativos** para visualizacao de dados

### Principais Caracteristicas

| Caracteristica | Descricao |
|----------------|-----------|
| **Velocidade** | Versao API e ~10x mais rapida que Selenium |
| **Paralelismo** | Downloads simultaneos com ThreadPoolExecutor (10 workers) |
| **Formatos** | Suporte a PDF, Excel e XML (ANBIMA 4.01 e 5.0) |
| **Robustez** | Retry automatico com backoff exponencial |
| **Monitoramento** | Logging estruturado com cores e simbolos |

---

## Arquitetura

```
                                    ┌─────────────────────────────────┐
                                    │         PORTAL QORE             │
                                    │   hub.qoredtvm.com.br           │
                                    └──────────────┬──────────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        │                          │                          │
                        v                          v                          v
               ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
               │  PDF Downloads │        │ Excel Downloads│        │  XML Downloads │
               │ CARTEIRA_PDF   │        │ CARTEIRA_EXCEL │        │    XML_5_0     │
               └───────┬────────┘        └───────┬────────┘        └───────┬────────┘
                       │                         │                         │
                       └─────────────────────────┼─────────────────────────┘
                                                 │
                                                 v
                                    ┌─────────────────────────────────┐
                                    │      AUTOMACAO QORE API         │
                                    │   core/automacao_qore_api.py    │
                                    │                                 │
                                    │  - Autenticacao JWT             │
                                    │  - Downloads paralelos          │
                                    │  - Processamento de arquivos    │
                                    └──────────────┬──────────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        │                          │                          │
                        v                          v                          v
               ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
               │  Pasta Fundos  │        │  Monitoramento │        │  Access DB     │
               │  (Carteiras)   │        │   (Arquivos)   │        │  (Upload)      │
               └────────────────┘        └────────────────┘        └────────────────┘
```

### Comparativo: Selenium vs API

| Aspecto | Selenium (v1) | API HTTP (v2) |
|---------|---------------|---------------|
| Velocidade | 5-10 min (34 fundos) | 30s-1min |
| Memoria | ~500MB (Chrome) | ~50MB |
| Dependencias | Chrome + Driver | Apenas `requests` |
| Estabilidade | Fragil (DOM) | Robusto (REST) |
| Manutencao | Alta | Baixa |

---

## Instalacao

### Pre-requisitos

- Python 3.9 ou superior
- Microsoft Access Database Engine (para conexao ODBC)
- Acesso ao portal QORE

### Instalacao de Dependencias

```bash
# Clonar repositorio
git clone https://github.com/O-Marcos-Estevam/ETL.git
cd ETL

# Criar ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias Principais

```
requests>=2.31.0      # Cliente HTTP para API
pandas>=2.0.0         # Manipulacao de dados
openpyxl>=3.0.0       # Leitura/escrita Excel
pyodbc>=4.0.0         # Conexao com Access
selenium>=4.0.0       # Automacao web (backup)
bizdays>=1.0.0        # Calendario ANBIMA
flask>=3.0.0          # Aplicacoes web
```

---

## Uso Rapido

### 1. Automacao via API (Recomendado)

```bash
# Executar automacao completa
python core/automacao_qore_api.py
```

### 2. Pipeline Completo (Download + Upload + Email)

```bash
# Pipeline D-1 automatico
python core/qore_xml_pipeline.py
```

### 3. Apenas Upload de XMLs

```bash
# Upload de XMLs existentes para Access
python core/qore_upload_xml.py
```

### Exemplo de Uso Programatico

```python
from core.automacao_qore_api import QoreAutomationAPI, carregar_config_planilha

# Carregar configuracoes da planilha
paths, credentials, flags, datas = carregar_config_planilha(
    r'C:\...\DOWNLOADS_AUX.xlsx'
)

# Criar e executar automacao
bot = QoreAutomationAPI(paths, credentials, flags, datas)
bot.executar()
```

---

## Estrutura do Projeto

```
ETL/
├── core/                           # Modulos principais de producao
│   ├── automacao_qore_api.py       # Automacao via HTTP/REST (PRINCIPAL)
│   ├── automacao_qore.py           # Automacao via Selenium (backup)
│   ├── qore_xml_pipeline.py        # Pipeline completo D-1
│   ├── qore_upload_xml.py          # Upload XML para Access
│   ├── qore_save_excel.py          # Parser de relatorios Excel/XML
│   └── qore_automation_integrated.py
│
├── apps/                           # Aplicacoes auxiliares
│   ├── dash_db_viewer/             # Dashboard Dash/Plotly
│   ├── db_viewer_3d/               # Visualizador 3D PostgreSQL
│   └── etl_desktop/                # Interface desktop (em desenvolvimento)
│
├── debug/                          # Ferramentas de debug e descoberta
│   ├── test_api_qore.py            # Teste de endpoints da API
│   ├── captura_xml_endpoint.py     # Captura de chamadas de rede
│   ├── captura_qore_cdp.py         # Captura via Chrome DevTools
│   └── inspect_*.py                # Scripts de inspecao
│
├── utils/                          # Utilitarios
│   ├── config_fundos_web.py        # Interface web para configuracao
│   ├── migration_access_to_postgres.py
│   └── query_*.py                  # Scripts de consulta
│
├── tests/                          # Testes automatizados
├── docs/                           # Documentacao adicional
├── dump_qore/                      # Dados capturados (debug)
└── requirements.txt
```

---

## Modulos Principais

### 1. `automacao_qore_api.py` - Automacao via API HTTP

Modulo principal que substitui Selenium por chamadas HTTP diretas, oferecendo:

- **Autenticacao JWT**: Login via `/api/v1/authorize`
- **Downloads paralelos**: ThreadPoolExecutor com 10 workers
- **Suporte completo**: PDF, Excel e XML (ANBIMA 4.01 e 5.0)
- **Retry automatico**: Backoff exponencial em caso de falhas

**Classes Principais:**

| Classe | Responsabilidade |
|--------|------------------|
| `QoreAPIClient` | Cliente HTTP com autenticacao JWT |
| `QoreDownloadManager` | Orquestracao de downloads paralelos |
| `QoreAutomationAPI` | Classe principal de execucao |
| `FundoManager` | Gerenciamento de lista de fundos |
| `FileHandler` | Processamento e movimentacao de arquivos |

**Configuracao via Dataclasses:**

```python
@dataclass
class QoreCredentials:
    url: str      # URL do portal
    email: str    # Usuario
    senha: str    # Senha

@dataclass
class QoreFlags:
    pdf_enabled: bool     # Habilita download PDF
    excel_enabled: bool   # Habilita download Excel
    xml_enabled: bool     # Habilita download XML

@dataclass
class QoreDatas:
    data_inicial: datetime  # Data inicial do periodo
    data_final: datetime    # Data final do periodo
```

### 2. `qore_xml_pipeline.py` - Pipeline D-1

Pipeline automatizado para execucao diaria:

1. Calcula D-1 usando calendario ANBIMA
2. Baixa XMLs do QORE
3. Faz upload para banco Access
4. Envia email de relatorio via Outlook

### 3. `qore_upload_xml.py` - Upload para Access

Parser de XML ANBIMA 5.0 com upload para Microsoft Access:

- Parse de estrutura ISO 20022 SEMT.003
- Extracao de: Data, Fundo, Patrimonio, Caixa
- Upload para tabelas `Cotas_Patrimonio_Qore` e `Caixa_Qore`

---

## Configuracao

### Planilha DOWNLOADS_AUX.xlsx

A configuracao e feita via planilha Excel na aba "Downloads":

| Celula | Configuracao | Exemplo |
|--------|--------------|---------|
| C4 | Data inicial | 01/12/2025 |
| C5 | Data final | 31/12/2025 |
| C24 | QORE habilitado | SIM/NAO |
| C25 | PDF habilitado | SIM/NAO |
| C27 | Excel habilitado | SIM/NAO |
| C29 | XML habilitado | SIM/NAO |
| M10 | URL portal | https://hub.qoredtvm.com.br |
| N10 | Email/Usuario | usuario@email.com |
| O10 | Senha | ******** |
| I19 | Caminho BD.xlsx | C:\...\BD.xlsx |
| I20 | Pasta temporaria | C:\...\temp |

### Arquivo BD.xlsx

Lista de fundos configurados para download:

| Coluna | Campo | Descricao |
|--------|-------|-----------|
| B | Apelido | Nome curto do fundo |
| C | Pasta | Caminho da pasta do fundo |
| J | Flag QORE | SIM para incluir no download |

---

## API QORE

### Endpoints Descobertos

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/v1/authorize` | POST | Autenticacao (retorna JWT) |
| `/api/v1/fundos-posicao/{uuid}` | GET | Dados do fundo |
| `/api/v1/fundos-posicao/{uuid}/arquivos` | GET | Lista arquivos |
| `/api/v1/fundos-posicao/{uuid}/arquivos/{guid}/download` | GET | Download arquivo |

### Parametros de Tipo (`tipo`)

| Valor | Descricao | Status |
|-------|-----------|--------|
| `CARTEIRA_PDF` | Carteira em PDF | Confirmado |
| `CARTEIRA_EXCEL` | Carteira em Excel | Confirmado |
| `XML_5_0` | XML ANBIMA 5.0 | Confirmado |
| `XML_4_01` | XML ANBIMA 4.01 | Confirmado |

### Exemplo de Requisicao

```python
import requests

# Autenticacao
response = requests.post(
    'https://hub.qoredtvm.com.br/api/v1/authorize',
    json={'username': 'user@email.com', 'password': 'senha'}
)
token = response.json()['access_token']

# Listar arquivos
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(
    'https://hub.qoredtvm.com.br/api/v1/fundos-posicao/{uuid}/arquivos',
    params={'tipo': 'XML_5_0', 'p': 0},
    headers=headers
)
arquivos = response.json()['content']
```

Para documentacao completa da API, consulte [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Banco de Dados

### Microsoft Access (Local)

**Tabelas de Destino:**

| Tabela | Campos Principais |
|--------|-------------------|
| `Cotas_Patrimonio_Qore` | DATA_INPUT, FUNDO, PL Posicao, QtdeCota, Valor da Cota Bruta |
| `Caixa_Qore` | DATA_INPUT, FUNDO, Descricao, Moeda_Origem, Valor |

### PostgreSQL (AWS RDS)

**Schemas:**

| Schema | Descricao |
|--------|-----------|
| `cad` | Cadastros (fundos, cotistas, ativos) |
| `pos` | Posicoes (cotas, carteira) |
| `aux` | Tabelas auxiliares |
| `stage` | Staging area |

---

## Troubleshooting

### Erro de Autenticacao

```
[X] Falha na autenticacao: 401
```

**Solucao:** Verifique credenciais na planilha DOWNLOADS_AUX.xlsx (celulas N10 e O10)

### Erro de Conexao com Access

```
[X] Erro ODBC: [Microsoft][ODBC Driver Manager]
```

**Solucao:** Instale o Microsoft Access Database Engine 2016

### Nenhum UUID Encontrado

```
[!] UUID nao encontrado para: FUNDO_XYZ
```

**Solucao:** Execute `debug/captura_qore_cdp.py` para atualizar a lista de UUIDs

### Timeout em Downloads

```
[X] Timeout ao baixar arquivo
```

**Solucao:** Aumente os valores em `APIConfig`:
```python
CONNECT_TIMEOUT: int = 20   # Default: 10
READ_TIMEOUT: int = 120     # Default: 60
```

---

## Execucao Automatica

### Task Scheduler (Windows)

```
Nome: ETL QORE Pipeline
Trigger: Diario, 08:00
Acao: python "C:\...\ETL\core\qore_xml_pipeline.py"
```

### Log de Execucao

Os logs sao exibidos no console com cores e simbolos:

```
[+] Info     - Operacao bem-sucedida
[!] Warning  - Atencao necessaria
[X] Error    - Erro que precisa correcao
[.] Debug    - Informacao de debug
```

---

## Contribuicao

Este e um projeto interno proprietario. Para contribuir:

1. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
2. Commit suas mudancas: `git commit -m 'feat: Adiciona nova funcionalidade'`
3. Push para a branch: `git push origin feature/nova-funcionalidade`
4. Abra um Pull Request

---

## Licenca

Projeto proprietario - Uso interno apenas.

---

<p align="center">
  <strong>ETL QORE</strong> - Automacao para Gestao de Fundos<br>
  Desenvolvido por ETL Team - Dezembro 2025
</p>
