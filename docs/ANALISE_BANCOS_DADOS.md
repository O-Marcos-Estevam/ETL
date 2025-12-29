# Analise dos Bancos de Dados

## Resumo Executivo

O sistema utiliza dois bancos de dados:
1. **Microsoft Access** (local) - Banco de origem, recebe dados do QORE e BriTech
2. **PostgreSQL** (AWS RDS) - Banco de destino, dados migrados e normalizados

---

## 1. BANCO ACCESS (Base Fundos_v2.accdb)

### Volume Total: ~950.000 registros

### Tabelas Principais

| Tabela | Registros | Descricao |
|--------|-----------|-----------|
| **BriTech_Carteiras** | 80 | Cadastro de fundos (depara) |
| **BriTech_Historico_Cota** | 46.201 | Historico de cotas e PL |
| **BriTech_Posicao_Cotista** | 143.245 | Posicao por cotista |
| **BriTech_Passivo_Fundos** | 36.430 | Passivo dos fundos |
| **BriTech_Saldo_Caixa** | 21.393 | Saldos em conta |
| **CPR_Lancamentos** | 135.642 | Lancamentos de CPR |
| **CPR_QORE** | 29.746 | CPR do QORE |
| **JCOT** | 109.058 | Movimentacoes |

### Tabelas do QORE (Input Automatico)

| Tabela | Registros | Fonte |
|--------|-----------|-------|
| Cotas_Patrimonio_Qore | 2.170 | XML QORE |
| Caixa_Qore | 2.618 | XML QORE |
| Renda_Fixa_Qore | 1.658 | Excel QORE |
| CPR_QORE | 29.746 | Excel QORE |
| Sociedade_Limitada_QORE | 1.827 | Excel QORE |
| Direito_Creditorio_Qore | 69 | Excel QORE |
| Fundos_Qore | 575 | Excel QORE |
| Rentabilidade_Qore | 4.238 | Excel QORE |

### Estrutura das Tabelas QORE

**Cotas_Patrimonio_Qore** (PL e Cotas)
```
DATA_INPUT          - Data de referencia
FUNDO               - Nome do fundo
PL Posicao          - Patrimonio Liquido
QtdeCota            - Quantidade de cotas
Valor da Cota Bruta - Valor da cota
```

**Caixa_Qore** (Saldos em Conta)
```
DATA_INPUT    - Data
FUNDO         - Nome do fundo
Descricao     - Descricao da conta
Moeda_Origem  - Moeda (BRL)
Valor         - Saldo
```

**Renda_Fixa_Qore** (Posicao RF)
```
DATA_INPUT   - Data
FUNDO        - Fundo
Titulo       - Tipo do titulo
Emissor      - Emissor
Vencimento   - Data vencimento
Qtd          - Quantidade
Valor_Bruto  - Valor de mercado
Taxa         - Taxa do titulo
```

---

## 2. BANCO POSTGRESQL (nscapital - AWS RDS)

### Schemas

| Schema | Descricao | Tabelas |
|--------|-----------|---------|
| **cad** | Cadastros | info_fundos, info_rf, info_rv, info_cpr, etc. |
| **pos** | Posicoes | pos_cota, pos_caixa, pos_rf, pos_rv, pos_cpr, pos_dir_cred |
| **aux** | Auxiliar | depara_fundos, depara_ativos, parametros |
| **stage** | Staging | stg_* (area de carga) |
| **hist** | Historico | Dados historicos |
| **mov** | Movimentacoes | Entradas/saidas |

### Volume por Schema

| Schema | Registros Principais |
|--------|---------------------|
| cad.info_fundos | 81 fundos |
| cad.info_cotistas | 90 cotistas |
| cad.info_cpr | 28.181 CPRs cadastradas |
| cad.info_rf | 57 titulos RF |
| cad.info_rv | 20 acoes |
| pos.pos_cota | 23.047 registros |
| pos.pos_caixa | 21.408 registros |
| pos.pos_cpr_2025 | 28.137 registros |
| pos.pos_passivo | 32.071 registros |

### Estrutura Principal - Fundos

**cad.info_fundos** (Cadastro de Fundos)
```sql
id_fundo         - PK sequencial
codigo_britech   - ID no BriTech
codigo_qore      - ID no QORE
codigo_maps      - ID no Maps
nome_fundo       - Nome completo
tipo_fundo       - FIM, FIDC, FIP, FIA
cnpj             - CNPJ do fundo
is_active        - Ativo/Inativo
```

**pos.pos_cota** (Posicao de Cotas/PL)
```sql
id_fundo         - FK para info_fundos
data_pos         - Data da posicao
cota_abertura    - Cota abertura
cota_fechamento  - Cota fechamento
pl_abertura      - PL abertura
pl_fechamento    - PL fechamento
qt_cotas_fech    - Qtd cotas
rentab_dia/mes/ano - Rentabilidades
```

### Particionamento por Ano

As tabelas de posicao sao particionadas por ano para melhor performance:
- pos_caixa_2023, pos_caixa_2024, pos_caixa_2025...
- pos_rf_2025
- pos_rv_2025
- pos_cpr_2025
- pos_dir_cred_2024, pos_dir_cred_2025

---

## 3. MAPEAMENTO ACCESS -> POSTGRESQL

```
ACCESS                          POSTGRESQL
------------------------------------------------------------------
BriTech_Carteiras          ->   cad.info_fundos + aux.depara_fundos
BriTech_Cotistas           ->   cad.info_cotistas
BriTech_Historico_Cota     ->   pos.pos_cota
BriTech_Posicao_Cotista    ->   pos.pos_passivo
BriTech_Saldo_Caixa        ->   pos.pos_caixa
Caixa_Qore                 ->   pos.pos_caixa
Cotas_Patrimonio_Qore      ->   pos.pos_cota
CPR_QORE                   ->   pos.pos_cpr
Renda_Fixa_Qore            ->   pos.pos_rf
Sociedade_Limitada_QORE    ->   pos.pos_rv
Direito_Creditorio_Qore    ->   pos.pos_dir_cred
```

---

## 4. DADOS ATUAIS (Dezembro 2025)

### AUM Total (17/12/2025): R$ 4.83 bilhoes

### Top 10 Fundos por PL

| Fundo | PL |
|-------|---:|
| FIM SOMME | 2.172.532.803,60 |
| MONTBLANC FIP | 520.624.535,02 |
| BLOKO FIM | 520.569.211,22 |
| GTB FIP | 482.497.179,39 |
| FIDC FANGIO NP | 268.246.914,64 |
| MINAS FIP | 178.920.177,49 |
| BLOKO URBANISMO FIP | 131.911.290,75 |
| ESTOCOLMO FIP | 120.918.527,32 |
| TERRAVISTA FIP | 118.110.015,61 |
| BRAVO FIM | 102.609.108,03 |

### Range de Dados

| Dado | Inicio | Fim | Registros |
|------|--------|-----|-----------|
| pos_cota | 2023-04-03 | 2025-12-19 | 23.047 |
| pos_caixa | 2025-01-02 | 2025-12-19 | 12.578 |
| pos_rf | 2025-09-30 | 2025-12-17 | 1.156 |
| pos_cpr | 2025-08-01 | 2025-12-17 | 28.137 |

---

## 5. FLUXO DE DADOS

```
┌─────────────────┐
│   QORE Portal   │
│  (XML / Excel)  │
└────────┬────────┘
         │ Download Selenium
         v
┌─────────────────┐
│    ETL Script   │
│  (Parse + Load) │
└────────┬────────┘
         │
         v
┌─────────────────┐     Migracao      ┌─────────────────┐
│  MS ACCESS      │ ───────────────>  │   PostgreSQL    │
│  (Local)        │                   │   (AWS RDS)     │
└─────────────────┘                   └─────────────────┘
         │                                     │
         v                                     v
┌─────────────────┐                   ┌─────────────────┐
│  Reports Excel  │                   │  db_viewer_3d   │
│  (Manual)       │                   │  (Dashboard)    │
└─────────────────┘                   └─────────────────┘
```

---

## 6. OBSERVACOES IMPORTANTES

### Dados Inconsistentes
- Algumas datas tem mais fundos que outras (ex: 2025-12-01 = 58 fundos, 2025-12-19 = 1 fundo)
- Isso indica que a carga de dados nao esta sendo feita para todos os fundos diariamente

### Encoding
- Access usa encoding Windows (CP1252)
- PostgreSQL usa UTF-8
- Caracteres especiais (acentos) podem aparecer como "?" ou caracteres estranhos

### Performance
- Access tem limite de ~2GB
- PostgreSQL usa particionamento por ano para melhor performance
- Queries em pos.pos_cota sao mais lentas que nas tabelas particionadas

### Seguranca
- Credenciais hardcoded (precisa migrar para variaveis de ambiente)
- Banco AWS sem restricao de IP (precisa configurar security group)

---

*Analise realizada em: 26/12/2025*
