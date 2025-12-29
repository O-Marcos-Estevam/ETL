# API QORE - Referencia Completa

Documentacao tecnica dos endpoints da API REST do portal QORE (hub.qoredtvm.com.br).

> **Nota:** Esta documentacao foi gerada atraves de engenharia reversa usando
> Chrome DevTools Protocol. Os endpoints podem mudar sem aviso previo.

---

## Indice

1. [Visao Geral](#visao-geral)
2. [Autenticacao](#autenticacao)
3. [Endpoints](#endpoints)
   - [Autorizacao](#1-autorizacao)
   - [Informacoes do Fundo](#2-informacoes-do-fundo)
   - [Listagem de Arquivos](#3-listagem-de-arquivos)
   - [Download de Arquivo](#4-download-de-arquivo)
4. [Parametros de Tipo](#parametros-de-tipo)
5. [Estrutura de Resposta](#estrutura-de-resposta)
6. [Codigos de Erro](#codigos-de-erro)
7. [Exemplos de Uso](#exemplos-de-uso)
8. [Rate Limiting](#rate-limiting)

---

## Visao Geral

### Base URL

```
https://hub.qoredtvm.com.br
```

### Headers Padrao

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
```

### Autenticacao

A API utiliza autenticacao JWT (JSON Web Token). O token deve ser enviado
no header `Authorization` com prefixo `Bearer`.

```
Authorization: Bearer eyJhbGciOiJIUzUxMiJ9...
```

---

## Autenticacao

### Fluxo de Autenticacao

```
┌─────────────┐      POST /api/v1/authorize      ┌─────────────┐
│   Cliente   │ ─────────────────────────────────>│   Server    │
│             │                                   │             │
│             │<─────────────────────────────────│             │
└─────────────┘      {access_token, refresh}     └─────────────┘
       │
       │  Authorization: Bearer {token}
       │
       v
┌─────────────────────────────────────────────────────────────┐
│                    Requisicoes Autenticadas                 │
│  GET /api/v1/fundos-posicao/{uuid}                          │
│  GET /api/v1/fundos-posicao/{uuid}/arquivos                 │
│  GET /api/v1/fundos-posicao/{uuid}/arquivos/{guid}/download │
└─────────────────────────────────────────────────────────────┘
```

### Estrutura do Token JWT

```json
{
  "sub": "d1fce4de-97a8-4ed0-a229-9dc3eb6e51ba",
  "exp": 1767044836,
  "guid": "d1fce4de-97a8-4ed0-a229-9dc3eb6e51ba",
  "papeis": ["USER", "GESTOR_READ", "GESTOR", "GESTOR_ADMIN"],
  "permissoes": []
}
```

---

## Endpoints

### 1. Autorizacao

Autentica o usuario e retorna tokens de acesso.

```http
POST /api/v1/authorize
```

#### Request Body

| Campo | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| `username` | string | Sim | Email do usuario |
| `password` | string | Sim | Senha do usuario |

```json
{
  "username": "usuario@email.com",
  "password": "senha123"
}
```

#### Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJkMWZjZTRkZS05N2E4...",
  "refresh_token": "4d264b72-984a-4137-90a7-6abc123def45"
}
```

#### Erros

| Codigo | Mensagem | Descricao |
|--------|----------|-----------|
| 400 | Campo usuario obrigatorio | Username nao informado |
| 401 | Credenciais invalidas | Usuario ou senha incorretos |

---

### 2. Informacoes do Fundo

Retorna dados cadastrais e metricas do fundo.

```http
GET /api/v1/fundos-posicao/{uuid}
```

#### Path Parameters

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `uuid` | string (UUID) | Identificador unico do fundo |

#### Response (200 OK)

```json
{
  "cnpj": "55523261000188",
  "nome": "AMG FIP MULTIESTRATEGIA",
  "guid": "175a9636-5ff2-4b86-85b5-5e12726f9ac7",
  "cota": 1.234567,
  "patrimonioLiquido": 15000000.00,
  "cotaData": "2025-12-26"
}
```

#### Campos de Resposta

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cnpj` | string | CNPJ do fundo (sem formatacao) |
| `nome` | string | Nome completo do fundo |
| `guid` | string | UUID do fundo |
| `cota` | number | Valor da cota atual |
| `patrimonioLiquido` | number | PL do fundo |
| `cotaData` | string | Data da ultima cota (YYYY-MM-DD) |

---

### 3. Listagem de Arquivos

Lista arquivos disponiveis para download de um fundo.

```http
GET /api/v1/fundos-posicao/{uuid}/arquivos
```

#### Path Parameters

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `uuid` | string (UUID) | Identificador unico do fundo |

#### Query Parameters

| Parametro | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `tipo` | string | Sim | Tipo de arquivo (ver tabela abaixo) |
| `p` | integer | Nao | Numero da pagina (default: 0) |

#### Response (200 OK)

```json
{
  "content": [
    {
      "nome": "amg_fip_mult_2025-12-26.pdf",
      "data": "2025-12-26",
      "tamanho": 143042,
      "guid": "f099a421-40d9-4e9c-8ecd-ff4902316687"
    },
    {
      "nome": "amg_fip_mult_2025-12-25.pdf",
      "data": "2025-12-25",
      "tamanho": 142850,
      "guid": "a123b456-78cd-90ef-1234-567890abcdef"
    }
  ],
  "pageable": {
    "pageNumber": 0,
    "pageSize": 50
  },
  "totalElements": 150,
  "totalPages": 3,
  "last": false,
  "first": true,
  "empty": false
}
```

#### Campos do Arquivo

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `nome` | string | Nome do arquivo |
| `data` | string | Data de referencia (YYYY-MM-DD) |
| `tamanho` | integer | Tamanho em bytes |
| `guid` | string | UUID do arquivo (para download) |

---

### 4. Download de Arquivo

Baixa um arquivo especifico pelo seu GUID.

```http
GET /api/v1/fundos-posicao/{fundo_uuid}/arquivos/{arquivo_guid}/download
```

#### Path Parameters

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `fundo_uuid` | string (UUID) | UUID do fundo |
| `arquivo_guid` | string (UUID) | UUID do arquivo |

#### Response (200 OK)

- Content-Type: `application/pdf`, `application/vnd.ms-excel`, ou `application/xml`
- Body: Conteudo binario do arquivo

#### Exemplo com cURL

```bash
curl -X GET \
  "https://hub.qoredtvm.com.br/api/v1/fundos-posicao/175a9636-5ff2-4b86-85b5-5e12726f9ac7/arquivos/f099a421-40d9-4e9c-8ecd-ff4902316687/download" \
  -H "Authorization: Bearer eyJhbGci..." \
  -o "arquivo.pdf"
```

---

## Parametros de Tipo

Valores validos para o parametro `tipo` na listagem de arquivos:

| Valor | Descricao | Formato | Status |
|-------|-----------|---------|--------|
| `CARTEIRA_PDF` | Carteira Diaria em PDF | PDF | Confirmado |
| `CARTEIRA_EXCEL` | Carteira Diaria em Excel | XLSX | Confirmado |
| `XML_5_0` | XML ANBIMA 5.0 | XML | Confirmado |
| `XML_4_01` | XML ANBIMA 4.01 | XML | Confirmado |

### Detalhes dos Formatos

#### CARTEIRA_PDF
- Relatorio visual da carteira do fundo
- Inclui: composicao, rentabilidade, graficos
- Formato: PDF

#### CARTEIRA_EXCEL
- Dados tabulares da carteira
- Inclui: ativos, quantidades, valores, percentuais
- Formato: XLSX (Excel 2007+)

#### XML_5_0 (ANBIMA 5.0)
- Padrao ISO 20022 SEMT.003
- Estrutura hierarquica com namespaces
- Inclui: posicoes, cotas, patrimonio, ativos

#### XML_4_01 (ANBIMA 4.01)
- Versao anterior do padrao ANBIMA
- Estrutura simplificada
- Mantido para compatibilidade

---

## Estrutura de Resposta

### Resposta Paginada

Todas as listagens retornam estrutura paginada:

```json
{
  "content": [...],
  "pageable": {
    "pageNumber": 0,
    "pageSize": 50,
    "sort": {
      "sorted": false,
      "unsorted": true
    }
  },
  "totalElements": 150,
  "totalPages": 3,
  "size": 50,
  "number": 0,
  "sort": {
    "sorted": false,
    "unsorted": true
  },
  "numberOfElements": 50,
  "first": true,
  "last": false,
  "empty": false
}
```

### Campos de Paginacao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `content` | array | Lista de itens da pagina atual |
| `totalElements` | integer | Total de itens em todas as paginas |
| `totalPages` | integer | Numero total de paginas |
| `number` | integer | Numero da pagina atual (0-indexed) |
| `size` | integer | Tamanho da pagina |
| `first` | boolean | Se e a primeira pagina |
| `last` | boolean | Se e a ultima pagina |
| `empty` | boolean | Se a pagina esta vazia |

---

## Codigos de Erro

### Erros HTTP

| Codigo | Status | Descricao |
|--------|--------|-----------|
| 200 | OK | Requisicao bem-sucedida |
| 400 | Bad Request | Parametros invalidos |
| 401 | Unauthorized | Token ausente ou invalido |
| 403 | Forbidden | Sem permissao para o recurso |
| 404 | Not Found | Recurso nao encontrado |
| 429 | Too Many Requests | Rate limit excedido |
| 500 | Internal Server Error | Erro no servidor |

### Estrutura de Erro

```json
{
  "timestamp": "2025-12-26T10:30:00.000+00:00",
  "status": 400,
  "error": "Bad Request",
  "message": "O campo tipo e obrigatorio",
  "path": "/api/v1/fundos-posicao/123/arquivos"
}
```

### Erro de Validacao

```json
{
  "fields": [
    {
      "field": "username",
      "message": "O campo usuario e obrigatorio."
    }
  ]
}
```

---

## Exemplos de Uso

### Python (requests)

```python
import requests

# Configuracao
BASE_URL = 'https://hub.qoredtvm.com.br'
USERNAME = 'usuario@email.com'
PASSWORD = 'senha123'

# 1. Autenticacao
auth_response = requests.post(
    f'{BASE_URL}/api/v1/authorize',
    json={'username': USERNAME, 'password': PASSWORD}
)
token = auth_response.json()['access_token']

# Headers para requisicoes autenticadas
headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json'
}

# 2. Listar fundos (precisa do UUID)
fund_uuid = '175a9636-5ff2-4b86-85b5-5e12726f9ac7'

# 3. Obter info do fundo
fund_info = requests.get(
    f'{BASE_URL}/api/v1/fundos-posicao/{fund_uuid}',
    headers=headers
).json()
print(f"Fundo: {fund_info['nome']}")
print(f"PL: R$ {fund_info['patrimonioLiquido']:,.2f}")

# 4. Listar arquivos XML
files_response = requests.get(
    f'{BASE_URL}/api/v1/fundos-posicao/{fund_uuid}/arquivos',
    params={'tipo': 'XML_5_0', 'p': 0},
    headers=headers
)
files = files_response.json()['content']
print(f"Encontrados {len(files)} arquivos XML")

# 5. Download do primeiro arquivo
if files:
    file_guid = files[0]['guid']
    file_name = files[0]['nome']

    download_response = requests.get(
        f'{BASE_URL}/api/v1/fundos-posicao/{fund_uuid}/arquivos/{file_guid}/download',
        headers=headers,
        stream=True
    )

    with open(file_name, 'wb') as f:
        for chunk in download_response.iter_content(8192):
            f.write(chunk)

    print(f"Arquivo salvo: {file_name}")
```

### cURL

```bash
# 1. Autenticacao
TOKEN=$(curl -s -X POST \
  "https://hub.qoredtvm.com.br/api/v1/authorize" \
  -H "Content-Type: application/json" \
  -d '{"username":"usuario@email.com","password":"senha123"}' \
  | jq -r '.access_token')

# 2. Listar arquivos
curl -X GET \
  "https://hub.qoredtvm.com.br/api/v1/fundos-posicao/175a9636-5ff2-4b86-85b5-5e12726f9ac7/arquivos?tipo=XML_5_0&p=0" \
  -H "Authorization: Bearer $TOKEN"

# 3. Download
curl -X GET \
  "https://hub.qoredtvm.com.br/api/v1/fundos-posicao/175a9636-5ff2-4b86-85b5-5e12726f9ac7/arquivos/f099a421-40d9-4e9c-8ecd-ff4902316687/download" \
  -H "Authorization: Bearer $TOKEN" \
  -o "carteira.xml"
```

---

## Rate Limiting

### Limites Conhecidos

| Endpoint | Limite | Janela |
|----------|--------|--------|
| /api/v1/authorize | 10 req | 1 min |
| /api/v1/fundos-posicao/* | 100 req | 1 min |
| /api/v1/*/download | 50 req | 1 min |

### Headers de Rate Limit

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1703581200
```

### Tratamento de Rate Limit

Quando o limite e excedido, a API retorna:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

### Estrategia de Retry

```python
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504]
)

session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

---

## UUIDs dos Fundos

Os UUIDs dos fundos podem ser obtidos atraves da interface web do portal
ou do arquivo `dump_qore/fundos/lista_fundos.json`.

Exemplo de estrutura:

```json
[
  {
    "nome": "AMG FIP MULT",
    "url": "https://hub.qoredtvm.com.br/portfolios/fundo-posicao/175a9636-5ff2-4b86-85b5-5e12726f9ac7"
  },
  {
    "nome": "ATLAS VALOR FIP",
    "url": "https://hub.qoredtvm.com.br/portfolios/fundo-posicao/b44b10c0-a6d2-436c-9efb-7175ecaef88d"
  }
]
```

Para extrair o UUID da URL:

```python
url = "https://hub.qoredtvm.com.br/portfolios/fundo-posicao/175a9636-5ff2-4b86-85b5-5e12726f9ac7"
uuid = url.split('/fundo-posicao/')[-1]
# uuid = "175a9636-5ff2-4b86-85b5-5e12726f9ac7"
```

---

## Notas Importantes

1. **Tokens JWT expiram** - O token de acesso tem validade limitada. Implemente
   logica de renovacao usando o refresh_token.

2. **UUIDs sao estaticos** - O UUID de um fundo nao muda, pode ser armazenado
   em cache.

3. **Paginacao** - Listagens retornam maximo de 50 itens por pagina. Use o
   parametro `p` para navegar.

4. **Tipos de arquivo** - O parametro `tipo` e case-sensitive. Use exatamente
   como documentado.

5. **Downloads binarios** - Use `stream=True` para downloads grandes para
   evitar problemas de memoria.

---

*Documentacao gerada em Dezembro 2025*
*ETL Team*
