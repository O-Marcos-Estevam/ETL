# Database 3D Viewer - Financial Market

Visualizador 3D interativo de banco de dados PostgreSQL para gestao de fundos de investimento, com tema inspirado em terminais financeiros (Bloomberg).

## Visao Geral

O projeto e uma aplicacao web que combina:
- **Backend**: API REST em Flask/Python conectada a PostgreSQL
- **Frontend**: Visualizacao 3D interativa com Three.js
- **Tema**: Interface profissional estilo terminal financeiro

## Estrutura do Projeto

```
db_viewer_3d/
|-- server.py              # API Flask (backend)
|-- requirements.txt       # Dependencias Python
|-- static/
    |-- index.html         # Pagina principal
    |-- css/
    |   |-- style.css      # Estilos (tema financeiro)
    |-- js/
        |-- api.js         # Cliente API + helpers de formatacao
        |-- effects.js     # Sistema de particulas e efeitos visuais
        |-- panels.js      # Paineis, tooltips e UI
        |-- schema.js      # Visualizacao 3D do schema do banco
        |-- charts.js      # Graficos 3D (financeiro, portfolio, etc)
        |-- main.js        # Aplicacao principal, navegacao e eventos
```

## Instalacao e Execucao

### Requisitos
- Python 3.10+
- PostgreSQL (acesso ao banco de dados)

### Instalacao

```bash
# Instalar dependencias
pip install -r requirements.txt
```

### Execucao

```bash
python server.py
```

O servidor inicia em `http://127.0.0.1:8080`

## API Endpoints

### Conexao e Estatisticas

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/test` | GET | Testa conexao com o banco |
| `/api/stats` | GET | Estatisticas gerais (fundos, cotistas, PL total) |

### Schema e Tabelas

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/schemas` | GET | Lista schemas com contagem de tabelas |
| `/api/tables/<schema>` | GET | Lista tabelas de um schema |
| `/api/all-tables` | GET | Todas as tabelas com metadados |
| `/api/columns/<schema>/<table>` | GET | Colunas de uma tabela |
| `/api/foreign-keys` | GET | Relacionamentos FK entre tabelas |

### Fundos e NAV

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/funds` | GET | Lista de fundos ativos |
| `/api/nav/<fund_id>?period=365` | GET | Historico NAV (30, 90, 180, 365, all) |
| `/api/funds-comparison` | GET | Comparacao PL de todos os fundos |
| `/api/portfolio/<fund_id>` | GET | Composicao da carteira com ativos |
| `/api/quota-evolution/<fund_id>` | GET | Evolucao da cota com metricas |

### Export e Preview

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/preview/<schema>/<table>` | GET | Amostra de 10 linhas |
| `/api/export/<schema>/<table>` | GET | Download CSV (max 10000 linhas) |

## Visualizacoes 3D

### 1. OVERVIEW
Tela inicial com estatisticas gerais do banco de dados:
- Total de fundos ativos
- Total de tabelas
- PL total dos fundos

### 2. SCHEMAS
Visualizacao 3D do modelo de dados:
- **Nos**: Tabelas representadas como cubos 3D
- **Cores por schema**:
  - `cad` (cadastro): Azul (#58a6ff)
  - `pos` (posicao): Verde (#3fb950)
  - `aux` (auxiliar): Roxo (#a371f7)
  - `stage` (staging): Amarelo (#d29922)
- **Tamanho**: Proporcional ao numero de linhas (escala log)
- **Linhas**: Relacionamentos FK entre tabelas
- **Interacao**: Hover mostra tooltip, clique abre painel com colunas

### 3. FINANCIAL
Grafico 3D de evolucao PL e cota para um fundo:
- Barras 3D representando PL ao longo do tempo
- Ribbon (fita) mostrando evolucao da cota
- Filtro de periodo: 30D, 90D, 6M, 1Y, ALL
- Seletor de fundo no painel lateral

### 4. PORTFOLIO
Composicao da carteira de um fundo:
- Barras 3D por categoria de ativo
- **Categorias**:
  - Caixa (azul)
  - Renda Fixa (verde)
  - Renda Variavel (vermelho)
  - Dir. Creditorios (roxo)
  - CPR (amarelo)
- **Tooltip**: Top 5 ativos ao passar o mouse
- **Clique**: Painel com lista completa dos top 10 ativos

### 5. COMPARISON
Comparacao de PL entre todos os fundos:
- Barras 3D ordenadas por PL (maior para menor)
- Cores por tipo de fundo
- Labels de valor para os top 10 fundos
- Tooltip com detalhes ao hover

## Componentes Frontend

### api.js - Cliente API
```javascript
API.getStats()           // Estatisticas
API.getAllTables()       // Todas tabelas
API.getNav(fundId)       // NAV de um fundo
API.getPortfolio(fundId) // Composicao carteira
API.getFundsComparison() // Comparacao fundos
```

### Format - Helpers de Formatacao
```javascript
Format.number(1234567)   // "1.2M"
Format.currency(1234.56) // "R$ 1.234,56"
Format.date("2025-01-01") // "01/01/2025"
```

### effects.js - Efeitos Visuais
- **ParticleSystem**: Sistema de particulas de fundo
- **NeonGrid**: Grid de referencia no plano
- **EnergyLine**: Linhas animadas entre tabelas

### schema.js - Visualizacao Schema
- **SchemaVisualization**: Renderiza tabelas como cubos 3D
- Layout radial por schema
- Conexoes FK animadas

### charts.js - Graficos 3D
- **FinancialCharts**: Grafico PL + Cota
- **FundsComparisonChart**: Comparacao entre fundos
- **QuotaEvolutionChart**: Evolucao da cota
- **PortfolioCompositionChart**: Composicao da carteira

### panels.js - Interface UI
- **InfoPanel**: Painel lateral de informacoes
- **Tooltip**: Tooltips contextuais
- **FundSelector**: Seletor de fundo + periodo
- **TableSearch**: Busca de tabelas

## Banco de Dados

### Schemas Visiveis
- `cad`: Cadastros (fundos, cotistas, ativos)
- `pos`: Posicoes (cotas, carteira)
- `aux`: Tabelas auxiliares
- `stage`: Staging area

### Tabelas Principais

#### Cadastro (cad)
| Tabela | Descricao |
|--------|-----------|
| info_fundos | Cadastro de fundos |
| info_cotistas | Cadastro de cotistas |
| info_rf | Cadastro renda fixa |
| info_rv | Cadastro renda variavel |
| info_dir_cred | Cadastro direitos creditorios |
| info_cpr | Cadastro CPR |
| info_contas | Cadastro contas bancarias |

#### Posicao (pos)
| Tabela | Descricao |
|--------|-----------|
| pos_cota | Historico de cotas e PL |
| pos_caixa_2025 | Posicao de caixa |
| pos_rf_2025 | Posicao renda fixa |
| pos_rv_2025 | Posicao renda variavel |
| pos_dir_cred_2025 | Posicao direitos creditorios |
| pos_cpr_2025 | Posicao CPR |

## Tecnologias

### Backend
- **Flask 3.0+**: Framework web Python
- **Flask-CORS**: Suporte a CORS
- **psycopg2**: Driver PostgreSQL

### Frontend
- **Three.js r128**: Renderizacao 3D WebGL
- **CSS2DRenderer**: Labels HTML sobre cena 3D
- **Tween.js**: Animacoes de camera
- **OrbitControls**: Navegacao 3D (rotacao, zoom, pan)

### Estilos
- Tema dark inspirado em GitHub/Bloomberg
- Tipografia: System UI + Orbitron (titulos) + Rajdhani (corpo)
- Cores: Azul primario (#58a6ff), Verde positivo (#3fb950), Vermelho negativo (#f85149)

## Controles de Navegacao

### Mouse
- **Arrastar**: Rotacionar camera
- **Scroll**: Zoom
- **Clique direito + arrastar**: Pan
- **Hover**: Highlight objeto + tooltip
- **Clique**: Abrir painel de detalhes

### Botoes de Controle
- **Reset Camera**: Volta para posicao inicial
- **Toggle Particles**: Liga/desliga particulas
- **Toggle Labels**: Mostra/esconde labels 3D
- **Refresh**: Recarrega dados

## Estrutura de Dados API

### Portfolio Response
```json
{
  "fund_id": 39,
  "fund_name": "BLOKO FIM",
  "date": "2025-12-17",
  "total": 59448.98,
  "composition": [
    {
      "category": "Caixa",
      "value": 617.01,
      "percentage": 1.04,
      "color": "#58a6ff",
      "asset_count": 1,
      "assets": [
        {"name": "Banco XYZ", "value": 617.01}
      ]
    },
    {
      "category": "Renda Fixa",
      "value": 50000.00,
      "percentage": 84.10,
      "color": "#3fb950",
      "asset_count": 3,
      "assets": [
        {"name": "LTN 2026", "type": "LTN", "index": "PREFIXADO", "value": 30000.00},
        {"name": "CDB BANCO", "type": "CDB", "index": "CDI", "value": 20000.00}
      ]
    }
  ]
}
```

### Funds Comparison Response
```json
[
  {
    "id": 81,
    "name": "FIM SOMME",
    "type": "FIM",
    "pl": 2172532803.60,
    "date": "2025-12-17"
  }
]
```

## Versionamento de Cache

Os arquivos estaticos usam query string para cache busting:
```html
<link rel="stylesheet" href="/css/style.css?v=9">
<script src="/js/main.js?v=9"></script>
```

Ao modificar arquivos, incremente o numero da versao.

## Consideracoes de Seguranca

- Credenciais do banco estao hardcoded (apenas para desenvolvimento)
- Em producao, usar variaveis de ambiente
- API nao tem autenticacao (adicionar se exposto externamente)
- Export limitado a 10.000 linhas por seguranca

## Troubleshooting

### Erro de conexao com banco
- Verificar se o PostgreSQL esta acessivel
- Verificar credenciais em `DB_CONFIG`
- Verificar regras de firewall/security groups

### Labels nao aparecem
- Verificar se CSS2DRenderer esta carregado
- Limpar cache do browser (Ctrl+F5)

### Dados nao carregam
- Verificar console do browser para erros de API
- Verificar logs do servidor Flask

---

*Desenvolvido para visualizacao de dados financeiros de gestao de fundos*
