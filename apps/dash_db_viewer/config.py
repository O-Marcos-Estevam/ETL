"""
Configuracoes do Dashboard PostgreSQL
Carrega variaveis de ambiente do arquivo .env
"""

import os
from pathlib import Path

# Tenta carregar dotenv se disponivel
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Configuracao do banco PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'prod-db2.c5kgei88itd4.sa-east-1.rds.amazonaws.com'),
    'database': os.getenv('POSTGRES_DB', 'nscapital'),
    'user': os.getenv('POSTGRES_USER', 'nscapitaladmin'),
    'password': os.getenv('POSTGRES_PASSWORD', '7lV5Juj0wsgoUmub'),
    'port': int(os.getenv('POSTGRES_PORT', 5432))
}

# Schemas a serem exibidos
VISIBLE_SCHEMAS = ['cad', 'pos', 'aux', 'stage']

# Configuracao do app
APP_CONFIG = {
    'debug': os.getenv('DEBUG', 'True').lower() == 'true',
    'host': os.getenv('APP_HOST', '127.0.0.1'),
    'port': int(os.getenv('APP_PORT', 8050)),
    'title': 'PostgreSQL Database Viewer'
}
