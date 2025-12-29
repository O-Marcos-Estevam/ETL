# ETL - Sistema de Automacao QORE

Sistema de ETL (Extract, Transform, Load) para automacao de processos de gestao de fundos de investimento, integrando com a plataforma QORE.

## Estrutura do Projeto

```
ETL/
|-- apps/                    # Aplicacoes e ferramentas
|   |-- db_viewer_3d/        # Visualizador 3D do banco PostgreSQL
|   |-- dash_db_viewer/      # Dashboard Dash/Plotly
|   |-- etl_desktop/         # Aplicacao desktop (em desenvolvimento)
|
|-- core/                    # Scripts principais de producao
|   |-- automacao_qore.py    # Automacao Selenium para download QORE (v11)
|   |-- qore_xml_pipeline.py # Pipeline completo: Download + Upload + Email
|   |-- qore_upload_xml.py   # Upload de XML para banco Access
|   |-- qore_save_excel.py   # Parser de relatorios Excel/XML
|   |-- qore_automation_integrated.py  # Versao integrada
|
|-- utils/                   # Scripts utilitarios
|   |-- config_fundos_web.py # Interface web para configurar fundos
|   |-- migration_access_to_postgres.py  # Migracao Access -> PostgreSQL
|   |-- explore_postgres_db.py           # Exploracao do banco Postgres
|   |-- query_dates.py       # Consulta de datas
|   |-- query_uploaded_data.py  # Consulta dados enviados
|   |-- show_uploaded_data.py   # Visualizacao de dados
|
|-- debug/                   # Scripts de debug e inspecao
|   |-- inspect_*.py         # Diversos scripts de inspecao
|   |-- *.txt                # Logs de debug
|
|-- tests/                   # Testes
|   |-- test_qore_upload.py  # Testes do upload
|   |-- audit_qore_upload.py # Auditoria do upload
|   |-- verify_upload.py     # Verificacao do upload
|
|-- legacy/                  # Versoes antigas (referencia)
|-- docs/                    # Documentacao adicional
|-- README.md                # Este arquivo
```

## Fluxo Principal do ETL

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   QORE Portal   │────>│  Download XML   │────>│  Parse & Upload │
│   (Selenium)    │     │  (automacao)    │     │  (Access DB)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         v
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Email Report   │<────│  PostgreSQL     │
                        │  (Outlook)      │     │  (Migracao)     │
                        └─────────────────┘     └─────────────────┘
```

## Scripts Principais

### 1. automacao_qore.py (core/)
Automacao via Selenium para download de arquivos do portal QORE.

**Funcionalidades:**
- Login automatizado no portal QORE
- Download de XMLs de carteira (formato ANBIMA 5.0)
- Download de relatorios Excel
- Download de PDFs
- Logging estruturado com cores
- Configuracao via dataclasses

**Uso:**
```bash
python core/automacao_qore.py
```

### 2. qore_xml_pipeline.py (core/)
Pipeline completo D-1: Download + Upload + Email.

**Funcionalidades:**
- Calculo automatico de D-1 (dia util anterior) usando calendario ANBIMA
- Download de XMLs do QORE
- Upload para banco Access
- Envio de email de relatorio via Outlook

**Uso:**
```bash
python core/qore_xml_pipeline.py
```

### 3. qore_upload_xml.py (core/)
Upload direto de XMLs para banco Access.

**Funcionalidades:**
- Parse de XML formato ANBIMA 5.0 / ISO 20022
- Extracao de: Data, Fundo, Patrimonio, Caixa
- Upload para tabelas Access (Cotas_Patrimonio_Qore, Caixa_Qore)

**Tabelas de Destino:**
| Tabela | Campos |
|--------|--------|
| Cotas_Patrimonio_Qore | DATA_INPUT, FUNDO, PL Posicao, QtdeCota, Valor da Cota Bruta |
| Caixa_Qore | DATA_INPUT, FUNDO, Descricao, Moeda_Origem, Valor |

### 4. qore_save_excel.py (core/)
Parser de relatorios Excel e XML com estrategia de multiplos parsers.

**Parsers Disponiveis:**
- LegacyExcelParser: Formato antigo QORE
- NewExcelParser: Formato novo QORE (CARTEIRA_DIARIA)
- Xml5Parser: XML formato ANBIMA 5.0

## Aplicacoes (apps/)

### db_viewer_3d
Visualizador 3D interativo do banco PostgreSQL usando Three.js.

**Iniciar:**
```bash
cd apps/db_viewer_3d
pip install -r requirements.txt
python server.py
# Acesse: http://127.0.0.1:8080
```

**Funcionalidades:**
- Visualizacao 3D do schema do banco
- Graficos financeiros (PL, Cotas)
- Composicao de portfolio
- Comparacao entre fundos

### dash_db_viewer
Dashboard interativo usando Dash/Plotly.

**Iniciar:**
```bash
cd apps/dash_db_viewer
pip install -r requirements.txt
python app.py
```

### config_fundos_web (utils/)
Interface web para configurar quais fundos serao baixados do QORE.

**Iniciar:**
```bash
python utils/config_fundos_web.py
# Acesse: http://localhost:5000
```

## Configuracao

### Caminhos Importantes
Os scripts usam caminhos configurados na planilha `DOWNLOADS_AUX.xlsx`:

| Configuracao | Descricao |
|--------------|-----------|
| path_bd | Caminho do banco Access |
| path_xml | Pasta de saida dos XMLs |
| path_temp | Pasta temporaria para downloads |
| path_excel | Pasta de relatorios Excel |
| path_pdf | Pasta de PDFs |

### Credenciais QORE
Configuradas na planilha `DOWNLOADS_AUX.xlsx` na aba "Downloads":
- URL do portal
- Usuario
- Senha

### Banco de Dados
- **Access:** `Base Fundos_v2.accdb`
- **PostgreSQL:** Configurado em `db_viewer_3d/server.py` e `migration_access_to_postgres.py`

## Dependencias

### Principais
```
flask>=3.0.0
flask-cors>=4.0.0
selenium>=4.0.0
pandas>=2.0.0
openpyxl>=3.0.0
pyodbc>=4.0.0
psycopg2-binary>=2.9.9
bizdays>=1.0.0
pywin32>=300
```

### Instalacao
```bash
pip install -r requirements.txt
```

## Banco de Dados PostgreSQL

### Schemas
| Schema | Descricao |
|--------|-----------|
| cad | Cadastros (fundos, cotistas, ativos) |
| pos | Posicoes (cotas, carteira) |
| aux | Tabelas auxiliares |
| stage | Staging area |

### Tabelas Principais

**Cadastro (cad):**
- info_fundos - Cadastro de fundos
- info_cotistas - Cadastro de cotistas
- info_rf - Cadastro renda fixa
- info_rv - Cadastro renda variavel
- info_dir_cred - Cadastro direitos creditorios
- info_cpr - Cadastro CPR
- info_contas - Cadastro contas bancarias

**Posicao (pos):**
- pos_cota - Historico de cotas e PL
- pos_caixa_2025 - Posicao de caixa
- pos_rf_2025 - Posicao renda fixa
- pos_rv_2025 - Posicao renda variavel
- pos_dir_cred_2025 - Posicao direitos creditorios
- pos_cpr_2025 - Posicao CPR

## Execucao Automatica

### Task Scheduler (Windows)
Pipeline pode ser agendado para execucao diaria:
```
Tarefa: QORE ETL Pipeline
Horario: 08:00
Comando: python "C:\...\ETL\core\qore_xml_pipeline.py"
```

## Troubleshooting

### Erro de conexao com QORE
- Verificar se ChromeDriver esta atualizado
- Verificar credenciais na planilha
- Verificar se portal QORE esta acessivel

### Erro de conexao com Access
- Verificar driver ODBC (Microsoft Access Driver)
- Verificar caminho do arquivo .accdb
- Verificar permissoes de escrita

### Erro de conexao com PostgreSQL
- Verificar se servidor esta ativo
- Verificar credenciais em DB_CONFIG
- Verificar regras de firewall

## Autor

ETL Team - Dezembro 2025

---

*Sistema desenvolvido para automacao de processos de gestao de fundos de investimento*
