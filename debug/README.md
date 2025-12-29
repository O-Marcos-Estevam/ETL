# Debug - Ferramentas de Diagnostico QORE

## captura_qore.py

Script que faz login no portal QORE e captura todas as informacoes possiveis para analise e otimizacao.

### O que captura

| Item | Descricao |
|------|-----------|
| **HTML** | Paginas renderizadas (login, dashboard, fundos) |
| **API Calls** | Todas as chamadas de rede interceptadas |
| **Endpoints** | Lista unica de endpoints descobertos |
| **Cookies** | Cookies de sessao (para usar com requests) |
| **Auth Headers** | Tokens de autenticacao (Authorization, JWT, etc) |
| **Scripts JS** | Arquivos JavaScript do site |
| **Screenshots** | Capturas de tela das paginas |

### Estrutura de Output

```
dump_qore/
├── RELATORIO.json          # Resumo da captura
├── cookies.json            # Cookies da sessao
├── auth_headers.json       # Headers de autenticacao
├── html/
│   ├── 01_login.html
│   ├── 02_dashboard.html
│   └── fundo_01_*.html
├── api/
│   ├── todas_chamadas.json # Todas as requisicoes
│   ├── endpoints_unicos.json
│   └── endpoints_js.json   # Endpoints encontrados no JS
├── js/
│   └── *.js                # Scripts baixados
├── screenshots/
│   └── *.png
└── fundos/
    └── lista_fundos.json
```

### Como usar

```bash
# Executa captura (usa credenciais da planilha DOWNLOADS_AUX.xlsx)
python debug/captura_qore.py

# Ou configure manualmente no prompt
```

### Requisitos

```bash
pip install selenium-wire beautifulsoup4 openpyxl
```

### Usando os dados capturados

#### 1. Fazer requests diretos com cookies

```python
import requests
import json

# Carrega cookies
with open('dump_qore/cookies.json') as f:
    cookies = json.load(f)

session = requests.Session()
for c in cookies:
    session.cookies.set(c['name'], c['value'])

# Agora pode fazer requests diretos
response = session.get('https://hub.qoredtvm.com.br/api/fundos')
```

#### 2. Ver endpoints descobertos

```python
import json

with open('dump_qore/api/endpoints_unicos.json') as f:
    endpoints = json.load(f)

for endpoint, info in endpoints.items():
    print(f"{endpoint} -> {info['status']}")
```

#### 3. Analisar chamadas de API

```python
import json

with open('dump_qore/api/todas_chamadas.json') as f:
    calls = json.load(f)

# Filtra por tipo
downloads = [c for c in calls if 'download' in c['url'].lower()]
for d in downloads:
    print(f"{d['method']} {d['url']}")
```
