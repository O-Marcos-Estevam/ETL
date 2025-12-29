# Guia Rapido - ETL QORE

## Comandos Mais Usados

### Executar Pipeline Completo (D-1)
```bash
python core/qore_xml_pipeline.py
```
Baixa XMLs do dia anterior, faz upload e envia email.

### Iniciar Visualizador 3D
```bash
cd apps/db_viewer_3d
python server.py
# Acesse: http://127.0.0.1:8080
```

### Configurar Fundos (Interface Web)
```bash
python utils/config_fundos_web.py
# Acesse: http://localhost:5000
```

### Migrar Dados Access -> PostgreSQL
```bash
python utils/migration_access_to_postgres.py
```

## Estrutura de Pastas

| Pasta | Conteudo |
|-------|----------|
| core/ | Scripts principais de producao |
| apps/ | Aplicacoes web (visualizadores) |
| utils/ | Ferramentas auxiliares |
| tests/ | Testes automatizados |
| debug/ | Scripts de debug/inspecao |
| docs/ | Documentacao |
| legacy/ | Versoes antigas |

## Arquivos de Configuracao

| Arquivo | Local | Funcao |
|---------|-------|--------|
| DOWNLOADS_AUX.xlsx | 07. DEPARA/ | Caminhos e credenciais |
| config_fundos_qore.json | Config QORE/ | Fundos ativos |
| BD.xlsx | 07. DEPARA/ | Mapeamento fundos |
| .env | apps/*/ | Credenciais PostgreSQL |

## Verificacao Rapida

### Testar conexao com banco
```bash
python utils/explore_postgres_db.py
```

### Ver dados enviados
```bash
python utils/show_uploaded_data.py
```

### Verificar upload
```bash
python tests/verify_upload.py
```

## Troubleshooting Rapido

| Problema | Solucao |
|----------|---------|
| ChromeDriver desatualizado | Baixar nova versao compativel |
| Erro de conexao QORE | Verificar credenciais na planilha |
| Erro Access | Verificar driver ODBC instalado |
| Erro PostgreSQL | Verificar .env e conexao internet |
| Selenium timeout | Aumentar timeouts no codigo |

## Contatos

- ETL Team
- Dezembro 2025
