"""
================================================================================
QORE AUTOMATION + XML UPLOAD INTEGRADO
================================================================================

Este script integra a automação de download do QORE (automacao_qore_v8.py) com
o upload direto de XMLs para o Access (qore_upload_xml_acess.py).

FLUXO DE EXECUÇÃO:
    1. Executa automação QORE v8 (download de PDFs, Excel, XMLs)
    2. Aguarda conclusão dos downloads
    3. Executa upload direto dos XMLs para o banco Access
    4. Gera relatório consolidado

MODO DE USO:
    python qore_automation_integrated.py

DEPENDÊNCIAS:
    - automacao_qore_v8.py (na pasta Legacy)
    - qore_upload_xml_acess.py (mesma pasta)

AUTOR: ETL Team
DATA: Dezembro 2025
================================================================================
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# =============================================================================
# CAMINHOS E CONFIGURAÇÕES
# =============================================================================

# Diretório base do ETL
ETL_DIR = Path(__file__).parent.resolve()
LEGACY_DIR = ETL_DIR / "Legacy"

# Caminhos dos scripts
AUTOMACAO_V8_PATH = LEGACY_DIR / "automacao_qore_v8.py"
UPLOAD_XML_PATH = ETL_DIR / "qore_upload_xml_acess.py"

# Pasta onde os XMLs são baixados
XML_QORE_FOLDER = Path(r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\XML_QORE')


# =============================================================================
# FUNÇÃO: Executar Automação QORE v8
# =============================================================================

def run_qore_automation() -> bool:
    """
    Executa o script de automação QORE v8.
    
    Este script faz login no portal QORE e baixa os relatórios
    (PDF, Excel, XML) para as pastas configuradas.
    
    Returns:
        True se executou com sucesso, False se falhou
    """
    log.info("=" * 60)
    log.info("ETAPA 1: AUTOMAÇÃO QORE v8")
    log.info("=" * 60)
    
    if not AUTOMACAO_V8_PATH.exists():
        log.error("Script não encontrado: %s", AUTOMACAO_V8_PATH)
        return False
    
    try:
        # Importa e executa o run_qore do automacao_qore_v8
        sys.path.insert(0, str(LEGACY_DIR))
        
        # Importação dinâmica para evitar dependências circulares
        import importlib.util
        spec = importlib.util.spec_from_file_location("automacao_qore_v8", AUTOMACAO_V8_PATH)
        automacao = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(automacao)
        
        # Lê parâmetros da planilha
        log.info("Carregando parâmetros da planilha...")
        
        # Configurações padrão (serão lidas da planilha pelo script)
        CAMINHO_PLANILHA_AUX_BD = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\06. BD\BD.xlsx"
        CAMINHO_PLANILHA_AUX_DOWNLOAD = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\DOWNLOADS_AUX.xlsx"
        
        QORE_PDF_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\01. QORE\PDF_QORE"
        QORE_EXCEL_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\01. QORE\EXCEL_QORE"
        QORE_XML_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\XML_QORE"
        QORE_PDF_MONITORAMENTO_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\01. QORE\PDF_MONITORAMENTO"
        SELENIUM_DOWNLOAD_TEMP_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\00. Temp\SELENIUM_DOWNLOADS"
        
        # Lê parâmetros
        import pandas as pd
        df = pd.read_excel(CAMINHO_PLANILHA_AUX_DOWNLOAD, sheet_name='Downloads')
        
        params = automacao.ler_parametros_planilha(
            df, None, None, None, None, None, None, None, None, None,
            CAMINHO_PLANILHA_AUX_BD, CAMINHO_PLANILHA_AUX_DOWNLOAD
        )
        
        (QORE_enabled, PDF_enabled, modo_lote_pdf, Excel_enabled, modo_lote_excel,
         XML_enabled, modo_lote_xml, data_inicial_dt, data_final_dt) = params
        
        # Lê credenciais
        creds = automacao.ler_credenciais_e_link(
            df, None, None, None, CAMINHO_PLANILHA_AUX_DOWNLOAD
        )
        email, senha, link_dashboard = creds
        
        if not QORE_enabled:
            log.warning("QORE está desabilitado na planilha de parâmetros.")
            return True  # Não é erro, apenas está desabilitado
        
        log.info("Iniciando automação QORE...")
        log.info("  Período: %s a %s", data_inicial_dt.strftime('%d/%m/%Y'), data_final_dt.strftime('%d/%m/%Y'))
        log.info("  PDF: %s | Excel: %s | XML: %s", PDF_enabled, Excel_enabled, XML_enabled)
        
        # Executa o run_qore
        automacao.run_qore(
            CAMINHO_PLANILHA_AUX_BD=CAMINHO_PLANILHA_AUX_BD,
            QORE_PDF_PATH_DEFAULT=QORE_PDF_PATH,
            QORE_EXCEL_PATH_DEFAULT=QORE_EXCEL_PATH,
            QORE_XML_PATH_DEFAULT=QORE_XML_PATH,
            QORE_PDF_MONITORAMENTO_PATH=QORE_PDF_MONITORAMENTO_PATH,
            CAMINHO_PLANILHA_AUX_DOWNLOAD=CAMINHO_PLANILHA_AUX_DOWNLOAD,
            link_dashboard=link_dashboard,
            senha=senha,
            email=email,
            df=df,
            QORE_enabled=QORE_enabled,
            PDF_enabled=PDF_enabled,
            modo_lote_pdf=modo_lote_pdf,
            Excel_enabled=Excel_enabled,
            modo_lote_excel=modo_lote_excel,
            XML_enabled=XML_enabled,
            modo_lote_xml=modo_lote_xml,
            data_inicial_dt=data_inicial_dt,
            data_final_dt=data_final_dt,
            SELENIUM_DOWNLOAD_TEMP_PATH=SELENIUM_DOWNLOAD_TEMP_PATH
        )
        
        log.info("Automação QORE concluída com sucesso!")
        return True
        
    except Exception as e:
        log.exception("Erro na automação QORE: %s", e)
        return False


# =============================================================================
# FUNÇÃO: Upload XMLs para Access
# =============================================================================

def run_xml_upload() -> bool:
    """
    Executa o upload direto dos XMLs para o banco Access.
    
    Importa e executa as funções do qore_upload_xml_acess.py
    para processar todos os XMLs na pasta XML_QORE.
    
    Returns:
        True se executou com sucesso, False se falhou
    """
    log.info("")
    log.info("=" * 60)
    log.info("ETAPA 2: UPLOAD XML -> ACCESS")
    log.info("=" * 60)
    
    if not UPLOAD_XML_PATH.exists():
        log.error("Script não encontrado: %s", UPLOAD_XML_PATH)
        return False
    
    try:
        # Importa o módulo de upload
        import importlib.util
        spec = importlib.util.spec_from_file_location("qore_upload_xml_acess", UPLOAD_XML_PATH)
        upload_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_module)
        
        # Lista XMLs disponíveis
        if not XML_QORE_FOLDER.exists():
            log.error("Pasta XML não encontrada: %s", XML_QORE_FOLDER)
            return False
        
        xml_files = [f for f in os.listdir(XML_QORE_FOLDER) if f.lower().endswith('.xml')]
        log.info("Arquivos XML encontrados: %d", len(xml_files))
        
        if not xml_files:
            log.warning("Nenhum XML para processar.")
            return True
        
        # Conecta ao banco
        conn = upload_module.get_db_connection()
        if not conn:
            log.error("Falha na conexão com banco Access.")
            return False
        
        # Processa XMLs
        parser = upload_module.Xml5Parser()
        success_count = 0
        error_count = 0
        
        try:
            for f in xml_files:
                full_path = os.path.join(XML_QORE_FOLDER, f)
                log.info("Processando: %s", f)
                
                data = parser.extract_data(full_path)
                
                if data:
                    upload_module.upload_xml_data(conn, data)
                    success_count += 1
                else:
                    log.warning("   Falha na extração - pulando.")
                    error_count += 1
        finally:
            conn.close()
        
        log.info("")
        log.info("Upload concluído: %d sucesso, %d erros", success_count, error_count)
        return error_count == 0
        
    except Exception as e:
        log.exception("Erro no upload XML: %s", e)
        return False


# =============================================================================
# FUNÇÃO: Gerar Relatório
# =============================================================================

def generate_report(automation_ok: bool, upload_ok: bool) -> None:
    """
    Gera um relatório consolidado da execução.
    
    Args:
        automation_ok: True se automação foi bem-sucedida
        upload_ok: True se upload foi bem-sucedido
    """
    log.info("")
    log.info("=" * 60)
    log.info("RELATÓRIO DE EXECUÇÃO")
    log.info("=" * 60)
    log.info("")
    log.info("  Automação QORE:  %s", "✅ OK" if automation_ok else "❌ ERRO")
    log.info("  Upload XML:      %s", "✅ OK" if upload_ok else "❌ ERRO")
    log.info("")
    
    if automation_ok and upload_ok:
        log.info("  STATUS GERAL: ✅ SUCESSO COMPLETO")
    elif automation_ok or upload_ok:
        log.info("  STATUS GERAL: ⚠️ SUCESSO PARCIAL")
    else:
        log.info("  STATUS GERAL: ❌ FALHA")
    
    log.info("")
    log.info("=" * 60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """
    Função principal que orquestra todo o processo.
    """
    start_time = datetime.now()
    
    log.info("")
    log.info("╔" + "═" * 58 + "╗")
    log.info("║" + " QORE AUTOMATION + XML UPLOAD INTEGRADO ".center(58) + "║")
    log.info("║" + f" Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ".center(58) + "║")
    log.info("╚" + "═" * 58 + "╝")
    log.info("")
    
    # ETAPA 1: Automação QORE
    automation_ok = run_qore_automation()
    
    # ETAPA 2: Upload XML (sempre executa, mesmo se automação falhou)
    # Os XMLs podem já existir de execuções anteriores
    upload_ok = run_xml_upload()
    
    # Relatório final
    end_time = datetime.now()
    duration = end_time - start_time
    
    generate_report(automation_ok, upload_ok)
    
    log.info("Tempo total de execução: %s", str(duration).split('.')[0])
    log.info("")
    
    # Exit code baseado no resultado
    if automation_ok and upload_ok:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
