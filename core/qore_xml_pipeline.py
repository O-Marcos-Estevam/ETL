"""
================================================================================
QORE XML PIPELINE V2 - Download D-1 + Upload + Email
================================================================================

Pipeline automatizado que:
1. Calcula D-1 (dia útil anterior) usando calendário ANBIMA
2. Baixa XMLs do QORE via Selenium
3. Faz upload para banco Access
4. Envia email de relatório via Outlook

EXECUÇÃO:
    Manual:     python qore_xml_pipeline_v2.py
    Agendado:   Task Scheduler às 08:00

DEPENDÊNCIAS:
    pip install bizdays selenium pyodbc pywin32 pandas openpyxl

AUTOR: ETL Team
DATA: Dezembro 2025
VERSÃO: 2.0
================================================================================
"""

import os
import sys
import time
import logging
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, List, Any

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importa classes do script de upload existente
from qore_upload_xml_acess import Xml5Parser, get_db_connection, upload_xml_data

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# Configuração de encoding (Windows)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# =============================================================================
# CONFIGURAÇÃO DE EMAIL (EDITAR AQUI)
# =============================================================================
EMAIL_CONFIG = {
    "recipients": ["marcos.morais@nscapital.com.br", "camila.renda@nscapital.com.br"],  # Destinatários principais
    "cc": [],                                   # Cópia (opcional)
    "send_on_success": True,                    # Enviar email em caso de sucesso
    "send_on_error": True,                      # Enviar email em caso de erro
}

# =============================================================================
# CAMINHOS (lidos da planilha, mas com defaults)
# =============================================================================
DEFAULT_CONFIG = {
    "planilha_downloads": r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\DOWNLOADS_AUX.xlsx",
    "config_fundos": r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\CONFIG_FUNDOS_QORE.xlsx",
    "xml_output_path": r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\XML_QORE",
    "temp_download_path": r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\06. SELENIUM",
    "db_path": r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\09. Base_de_Dados\Base Fundos_v2.accdb",
}


# =============================================================================
# CLASSE: CalendarioANBIMA
# =============================================================================

class CalendarioANBIMA:
    """
    Gerencia cálculos de dias úteis usando o calendário ANBIMA.

    Utiliza a biblioteca bizdays que já inclui o calendário ANBIMA
    com todos os feriados bancários brasileiros.
    """

    def __init__(self):
        """Inicializa o calendário ANBIMA."""
        try:
            from bizdays import Calendar
            self.cal = Calendar.load('ANBIMA')
            log.info("Calendário ANBIMA carregado com sucesso")
        except ImportError:
            log.error("Biblioteca 'bizdays' não instalada. Execute: pip install bizdays")
            raise
        except Exception as e:
            log.error(f"Erro ao carregar calendário ANBIMA: {e}")
            raise

    def get_d1(self, reference_date: Optional[date] = None) -> date:
        """
        Retorna o dia útil anterior (D-1) considerando feriados ANBIMA.

        Args:
            reference_date: Data de referência. Se None, usa hoje.

        Returns:
            Data do dia útil anterior.
        """
        if reference_date is None:
            reference_date = date.today()

        # offset(-1) retorna o dia útil anterior
        d1 = self.cal.offset(reference_date, -1)
        log.info(f"D-1 calculado: {d1.strftime('%d/%m/%Y')} (referência: {reference_date.strftime('%d/%m/%Y')})")
        return d1

    def is_business_day(self, check_date: date) -> bool:
        """Verifica se uma data é dia útil."""
        return self.cal.isbizday(check_date)


# =============================================================================
# CLASSE: QoreDownloader
# =============================================================================

class QoreDownloader:
    """
    Gerencia o download de XMLs do sistema QORE via Selenium.

    Simplificação do automacao_qore_v8.py focando apenas em XML.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o downloader.

        Args:
            config: Dicionário com email, senha, link, temp_path, output_path
        """
        self.email = config['email']
        self.senha = config['senha']
        self.link = config['link']
        self.temp_path = config['temp_path']
        self.output_path = config['output_path']
        self.fundos = config['fundos']  # dict {apelido: sigla_busca}
        self.driver = None

        # Garante que pastas existem
        os.makedirs(self.temp_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)

    def _init_driver(self):
        """Inicializa o Chrome WebDriver."""
        chrome_options = Options()
        prefs = {
            "download.default_directory": self.temp_path,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        log.info("Chrome WebDriver inicializado")

    def _clear_temp_folder(self):
        """Limpa a pasta temporária de downloads."""
        try:
            for item in os.listdir(self.temp_path):
                item_path = os.path.join(self.temp_path, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            log.info(f"Pasta temporária limpa: {self.temp_path}")
        except Exception as e:
            log.warning(f"Erro ao limpar pasta temporária: {e}")

    def login(self) -> bool:
        """
        Realiza login no sistema QORE.

        Returns:
            True se login bem sucedido, False caso contrário.
        """
        try:
            self._init_driver()
            self._clear_temp_folder()

            log.info(f"Acessando dashboard: {self.link}")
            self.driver.get(self.link)

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.NAME, 'email'))
            ).send_keys(self.email)

            self.driver.find_element(By.NAME, 'password').send_keys(self.senha + Keys.RETURN)

            WebDriverWait(self.driver, 15).until(EC.url_contains("dashboard"))
            log.info("Login realizado com sucesso!")
            return True

        except TimeoutException:
            log.error("Timeout durante o login - verifique credenciais ou conectividade")
            return False
        except Exception as e:
            log.error(f"Falha no login: {e}")
            return False

    def download_xml_for_fund(self, fund_name: str, sigla: str, target_date: date) -> Optional[str]:
        """
        Baixa o XML de um fundo para uma data específica.

        Args:
            fund_name: Nome do fundo (ex: "FIP AMG")
            sigla: Sigla para busca no site (ex: "AMG")
            target_date: Data do XML desejado

        Returns:
            Caminho do arquivo baixado ou None se falhou.
        """
        data_formatada = target_date.strftime("%d/%m/%Y")

        try:
            # Navega para o dashboard
            self.driver.get(self.link)
            time.sleep(2)

            # Clica no link do fundo
            fund_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, sigla))
            )
            fund_link.click()
            time.sleep(3)

            # Clica no botão XML
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(., "XML Anbima 5.0")]'))
            ).click()
            time.sleep(2)

            # Busca a data na tabela
            linhas = self.driver.find_elements(By.XPATH, '//table/tbody/tr')
            for linha in linhas:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) >= 3 and colunas[1].text.strip() == data_formatada:
                    botao = colunas[3].find_element(By.TAG_NAME, 'button')
                    botao.click()
                    log.info(f"Baixando XML: {fund_name} - {data_formatada}")
                    time.sleep(3)

                    # Move o arquivo para pasta final
                    return self._move_downloaded_file(fund_name, target_date)

            log.warning(f"Data {data_formatada} não encontrada para {fund_name}")
            return None

        except TimeoutException:
            log.error(f"Timeout ao processar {fund_name}")
            return None
        except Exception as e:
            log.error(f"Erro ao baixar XML de {fund_name}: {e}")
            return None

    def _move_downloaded_file(self, fund_name: str, target_date: date) -> Optional[str]:
        """
        Move e renomeia o arquivo baixado para a pasta final.

        Returns:
            Caminho do arquivo final ou None se não encontrou.
        """
        timeout = time.time() + 30

        while time.time() < timeout:
            xml_files = list(Path(self.temp_path).glob("*.xml"))
            if xml_files:
                # Pega o mais recente
                source_file = max(xml_files, key=os.path.getmtime)

                # Novo nome: DD.MM - Carteira XML - FUNDO.xml
                new_name = f"{target_date.strftime('%d.%m')} - Carteira XML - {fund_name}.xml"
                dest_path = os.path.join(self.output_path, new_name)

                # Versionamento se já existe
                version = 0
                base_dest = dest_path
                while os.path.exists(dest_path):
                    version += 1
                    dest_path = base_dest.replace(".xml", f" ({version}).xml")

                shutil.move(str(source_file), dest_path)
                log.info(f"XML salvo: {dest_path}")
                return dest_path

            time.sleep(1)

        log.error(f"Timeout aguardando download de {fund_name}")
        return None

    def download_all_funds(self, target_date: date) -> Dict[str, Optional[str]]:
        """
        Baixa XMLs de todos os fundos configurados.

        Args:
            target_date: Data alvo para download

        Returns:
            Dict {fund_name: file_path ou None}
        """
        results = {}

        for fund_name, sigla in self.fundos.items():
            log.info(f"Processando: {fund_name} (busca: {sigla})")
            file_path = self.download_xml_for_fund(fund_name, sigla, target_date)
            results[fund_name] = file_path
            time.sleep(1)  # Pequena pausa entre fundos

        return results

    def close(self):
        """Fecha o navegador."""
        if self.driver:
            try:
                self.driver.quit()
                log.info("Chrome WebDriver encerrado")
            except Exception as e:
                log.warning(f"Erro ao fechar driver: {e}")


# =============================================================================
# CLASSE: OutlookReporter
# =============================================================================

class OutlookReporter:
    """
    Envia relatórios por email via Microsoft Outlook.

    Utiliza win32com para integração com Outlook desktop.
    """

    def __init__(self, recipients: List[str], cc: List[str] = None):
        """
        Inicializa o reporter.

        Args:
            recipients: Lista de emails destinatários
            cc: Lista de emails em cópia (opcional)
        """
        self.recipients = recipients
        self.cc = cc or []

    def send_report(self, stats: Dict[str, Any], success: bool = True) -> bool:
        """
        Envia o relatório de execução.

        Args:
            stats: Estatísticas do processamento
            success: Se a execução foi bem sucedida

        Returns:
            True se email enviado com sucesso
        """
        try:
            import win32com.client as win32

            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)

            # Destinatários
            mail.To = ';'.join(self.recipients)
            if self.cc:
                mail.CC = ';'.join(self.cc)

            # Assunto
            status_icon = "✅" if success else "❌"
            status_text = "Sucesso" if success else "Erros"
            d1_str = stats.get('d1', datetime.now()).strftime('%d/%m/%Y')
            mail.Subject = f"[QORE] Relatório D-1 ({d1_str}) - {status_icon} {status_text}"

            # Corpo HTML
            mail.HTMLBody = self._build_html_body(stats, success)

            # Envia
            mail.Send()
            log.info(f"Email enviado para: {', '.join(self.recipients)}")
            return True

        except ImportError:
            log.error("pywin32 não instalado. Execute: pip install pywin32")
            return False
        except Exception as e:
            log.error(f"Erro ao enviar email: {e}")
            return False

    def _build_html_body(self, stats: Dict[str, Any], success: bool) -> str:
        """Constrói o corpo HTML do email."""

        d1 = stats.get('d1', date.today())
        exec_time = stats.get('execution_time', datetime.now())

        # Estatísticas de download
        download_stats = stats.get('download', {})
        total_fundos = download_stats.get('total', 0)
        baixados = download_stats.get('success', 0)
        falhas_download = download_stats.get('failed', 0)

        # Estatísticas de upload
        upload_stats = stats.get('upload', {})
        patrimonio_total = upload_stats.get('patrimonio_total', 0)
        registros = upload_stats.get('registros', {})

        # Detalhes por fundo
        fund_details = stats.get('fund_details', [])

        status_color = "#28a745" if success else "#dc3545"
        status_text = "Sucesso" if success else "Com Erros"
        status_icon = "✅" if success else "❌"

        # Tabela de detalhes por fundo
        fund_rows = ""
        for fund in fund_details:
            dl_icon = "✅" if fund.get('download_ok') else "❌"
            up_icon = "✅" if fund.get('upload_ok') else "❌"
            pl = fund.get('patrimonio', 0)
            pl_str = f"R$ {pl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pl else "-"
            fund_rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{fund.get('name', 'N/A')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{dl_icon}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{up_icon}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{pl_str}</td>
                </tr>
            """

        patrimonio_str = f"R$ {patrimonio_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; color: #333; }}
                h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h3 {{ color: #34495e; margin-top: 25px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th {{ background-color: #3498db; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .status {{ font-size: 18px; font-weight: bold; color: {status_color}; }}
                .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; color: #888; font-size: 11px; }}
            </style>
        </head>
        <body>
            <h2>Relatório de Execução - QORE XML Pipeline</h2>

            <table>
                <tr><th style="width: 200px;">Data de Referência (D-1)</th><td><strong>{d1.strftime('%d/%m/%Y')}</strong></td></tr>
                <tr><th>Executado em</th><td>{exec_time.strftime('%d/%m/%Y %H:%M:%S')}</td></tr>
                <tr><th>Status Geral</th><td class="status">{status_icon} {status_text}</td></tr>
            </table>

            <h3>Resumo do Download</h3>
            <table>
                <tr><th style="width: 200px;">Fundos processados</th><td>{total_fundos}</td></tr>
                <tr><th>XMLs baixados</th><td>{baixados}</td></tr>
                <tr><th>Falhas no download</th><td>{falhas_download}</td></tr>
            </table>

            <h3>Resumo do Upload</h3>
            <table>
                <tr><th style="width: 200px;">Patrimônio Total</th><td><strong>{patrimonio_str}</strong></td></tr>
                <tr><th>Registros de Caixa</th><td>{registros.get('caixa', 0)}</td></tr>
                <tr><th>Registros de CPR</th><td>{registros.get('cpr', 0)}</td></tr>
                <tr><th>Registros de RV</th><td>{registros.get('rv', 0)}</td></tr>
                <tr><th>Registros de RF</th><td>{registros.get('rf', 0)}</td></tr>
            </table>

            <h3>Detalhes por Fundo</h3>
            <table>
                <tr>
                    <th>Fundo</th>
                    <th style="width: 80px; text-align: center;">Download</th>
                    <th style="width: 80px; text-align: center;">Upload</th>
                    <th style="width: 150px; text-align: right;">Patrimônio</th>
                </tr>
                {fund_rows}
            </table>

            <div class="footer">
                Gerado automaticamente por QORE XML Pipeline v2<br>
                {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </body>
        </html>
        """

        return html


# =============================================================================
# CLASSE: PipelineOrchestrator
# =============================================================================

class PipelineOrchestrator:
    """
    Orquestra todo o pipeline: Download → Upload → Email.
    """

    def __init__(self, config_path: str = None):
        """
        Inicializa o orquestrador.

        Args:
            config_path: Caminho da planilha DOWNLOADS_AUX.xlsx
        """
        self.config_path = config_path or DEFAULT_CONFIG['planilha_downloads']
        self.config = {}
        self.stats = {
            'd1': None,
            'execution_time': datetime.now(),
            'download': {'total': 0, 'success': 0, 'failed': 0},
            'upload': {'patrimonio_total': 0, 'registros': {'caixa': 0, 'cpr': 0, 'rv': 0, 'rf': 0}},
            'fund_details': []
        }

    def _load_config(self):
        """Carrega configurações da planilha Excel."""
        try:
            df = pd.read_excel(self.config_path, sheet_name="Downloads", engine='openpyxl', header=None)

            # Lê credenciais QORE
            self.config['email'] = str(df.iloc[9, 13]).strip()
            self.config['senha'] = str(df.iloc[9, 14]).strip()
            self.config['link'] = str(df.iloc[9, 12]).strip()

            # Lê caminhos
            self.config['planilha_bd'] = str(df.iloc[18, 8]).strip()
            self.config['temp_path'] = str(df.iloc[19, 8]).strip() or DEFAULT_CONFIG['temp_download_path']

            try:
                self.config['output_path'] = str(df.iloc[20, 8]).strip()
            except:
                self.config['output_path'] = DEFAULT_CONFIG['xml_output_path']

            log.info("Configurações carregadas da planilha")
            return True

        except Exception as e:
            log.error(f"Erro ao carregar configurações: {e}")
            return False

    def _load_funds(self) -> Dict[str, str]:
        """
        Carrega lista de fundos QORE do config_fundos.json ou CONFIG_FUNDOS_QORE.xlsx.

        Prioridade:
        1. config_fundos.json (interface web)
        2. CONFIG_FUNDOS_QORE.xlsx (planilha Excel)

        Returns:
            Dict {nome_fundo: sigla_busca}
        """
        import json

        # Tenta carregar do JSON primeiro (interface web)
        json_path = Path(r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\Config QORE\config_fundos_qore.json")
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    fundos_list = json.load(f)

                fundos = {}
                for f in fundos_list:
                    if f.get('ativo', False):
                        fundos[f['nome']] = f['sigla']

                log.info(f"Fundos QORE carregados de config_fundos.json: {len(fundos)}")
                for nome, sigla in fundos.items():
                    log.info(f"  - {nome} -> busca: '{sigla}'")

                return fundos
            except Exception as e:
                log.warning(f"Erro ao ler JSON, tentando Excel: {e}")

        # Fallback para Excel
        try:
            config_path = DEFAULT_CONFIG['config_fundos']
            df = pd.read_excel(config_path, sheet_name="Fundos", engine='openpyxl')

            # Filtra apenas fundos ativos (ATIVO = "SIM")
            df_ativos = df[df['ATIVO'].astype(str).str.strip().str.upper() == 'SIM']

            fundos = {}
            for _, row in df_ativos.iterrows():
                nome = str(row['NOME DO FUNDO']).strip()
                sigla = str(row['SIGLA BUSCA']).strip()

                if nome and sigla and nome != 'nan':
                    fundos[nome] = sigla

            log.info(f"Fundos QORE carregados de CONFIG_FUNDOS_QORE.xlsx: {len(fundos)}")
            for nome, sigla in fundos.items():
                log.info(f"  - {nome} -> busca: '{sigla}'")

            return fundos

        except FileNotFoundError:
            log.error(f"Nenhum arquivo de configuração encontrado!")
            log.error("Execute: python config_fundos_web.py para criar a interface")
            return {}
        except Exception as e:
            log.error(f"Erro ao carregar fundos: {e}")
            return {}

    def run(self, force_date: date = None, force_fund: str = None) -> bool:
        """
        Executa o pipeline completo.

        Args:
            force_date: Data específica para buscar (ignora cálculo D-1)
            force_fund: Fundo específico para testar (ignora lista do BD.xlsx)

        Returns:
            True se executou com sucesso (mesmo com alguns erros parciais)
        """
        log.info("=" * 60)
        log.info("INICIANDO QORE XML PIPELINE V2")
        log.info("=" * 60)

        overall_success = True
        downloader = None

        try:
            # 1. Carrega configurações
            if not self._load_config():
                raise Exception("Falha ao carregar configurações")

            # Carrega fundos ou usa fundo forçado
            if force_fund:
                # Extrai sigla do nome do fundo (ex: "FIP AMG" -> "AMG")
                partes = force_fund.split()
                sigla = partes[-1] if len(partes) > 1 else force_fund
                fundos = {force_fund: sigla}
                log.info(f"Usando fundo forçado: {force_fund} (sigla: {sigla})")
            else:
                fundos = self._load_funds()
                if not fundos:
                    raise Exception("Nenhum fundo QORE encontrado")

            self.config['fundos'] = fundos

            # 2. Calcula D-1 ou usa data forçada
            if force_date:
                d1 = force_date
                log.info(f"Usando data forçada: {d1.strftime('%d/%m/%Y')}")
            else:
                calendario = CalendarioANBIMA()
                d1 = calendario.get_d1()
            self.stats['d1'] = d1

            # 3. Download dos XMLs
            log.info("-" * 60)
            log.info("FASE 1: DOWNLOAD DE XMLs")
            log.info("-" * 60)

            downloader = QoreDownloader(self.config)
            if not downloader.login():
                raise Exception("Falha no login do QORE")

            download_results = downloader.download_all_funds(d1)
            downloader.close()
            downloader = None

            # Atualiza estatísticas de download
            self.stats['download']['total'] = len(download_results)
            self.stats['download']['success'] = sum(1 for v in download_results.values() if v)
            self.stats['download']['failed'] = sum(1 for v in download_results.values() if not v)

            # 4. Upload para Access
            log.info("-" * 60)
            log.info("FASE 2: UPLOAD PARA ACCESS")
            log.info("-" * 60)

            parser = Xml5Parser()
            conn = get_db_connection()

            if not conn:
                raise Exception("Falha ao conectar ao banco Access")

            try:
                for fund_name, file_path in download_results.items():
                    fund_detail = {
                        'name': fund_name,
                        'download_ok': file_path is not None,
                        'upload_ok': False,
                        'patrimonio': 0
                    }

                    if file_path and os.path.exists(file_path):
                        data = parser.extract_data(file_path)

                        if data:
                            upload_stats = upload_xml_data(conn, data)

                            if upload_stats['success']:
                                fund_detail['upload_ok'] = True
                                fund_detail['patrimonio'] = upload_stats.get('patrimonio', 0) or 0

                                # Acumula estatísticas
                                self.stats['upload']['patrimonio_total'] += fund_detail['patrimonio']
                                self.stats['upload']['registros']['caixa'] += upload_stats.get('caixa_count', 0)
                                self.stats['upload']['registros']['cpr'] += upload_stats.get('cpr_count', 0)
                                self.stats['upload']['registros']['rv'] += upload_stats.get('rv_count', 0)
                                self.stats['upload']['registros']['rf'] += upload_stats.get('rf_count', 0)

                    self.stats['fund_details'].append(fund_detail)

            finally:
                conn.close()

            # Verifica se houve erros críticos
            if self.stats['download']['failed'] > 0:
                overall_success = False

        except Exception as e:
            log.exception(f"Erro crítico no pipeline: {e}")
            overall_success = False

        finally:
            # Garante que o driver seja fechado
            if downloader:
                downloader.close()

        # 5. Envia relatório por email
        log.info("-" * 60)
        log.info("FASE 3: ENVIO DE RELATÓRIO")
        log.info("-" * 60)

        self.stats['execution_time'] = datetime.now()

        should_send = (
            (overall_success and EMAIL_CONFIG['send_on_success']) or
            (not overall_success and EMAIL_CONFIG['send_on_error'])
        )

        if should_send and EMAIL_CONFIG['recipients']:
            reporter = OutlookReporter(
                recipients=EMAIL_CONFIG['recipients'],
                cc=EMAIL_CONFIG.get('cc', [])
            )
            reporter.send_report(self.stats, success=overall_success)
        else:
            log.info("Envio de email desabilitado ou sem destinatários")

        # Relatório final no console
        log.info("=" * 60)
        log.info("RELATÓRIO FINAL")
        log.info("=" * 60)
        log.info(f"Data D-1: {self.stats['d1']}")
        log.info(f"Fundos processados: {self.stats['download']['total']}")
        log.info(f"Downloads OK: {self.stats['download']['success']}")
        log.info(f"Downloads FALHA: {self.stats['download']['failed']}")
        log.info(f"Patrimônio Total: R$ {self.stats['upload']['patrimonio_total']:,.2f}")
        log.info(f"Status: {'SUCESSO' if overall_success else 'COM ERROS'}")
        log.info("=" * 60)

        return overall_success


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    log.info("QORE XML Pipeline v2 iniciado")

    # Argumentos de linha de comando
    # Uso: python qore_xml_pipeline_v2.py [--date DD/MM/YYYY] [--fund "NOME FUNDO"] [config_path]
    config_path = None
    force_date = None
    force_fund = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--date' and i + 1 < len(args):
            # Parse da data forçada
            try:
                force_date = datetime.strptime(args[i + 1], "%d/%m/%Y").date()
                log.info(f"Data forçada via argumento: {force_date.strftime('%d/%m/%Y')}")
            except ValueError:
                log.error(f"Formato de data inválido: {args[i + 1]}. Use DD/MM/YYYY")
                sys.exit(1)
            i += 2
        elif args[i] == '--fund' and i + 1 < len(args):
            # Fundo específico para teste
            force_fund = args[i + 1]
            log.info(f"Fundo forçado via argumento: {force_fund}")
            i += 2
        elif not args[i].startswith('--'):
            config_path = args[i]
            i += 1
        else:
            i += 1

    # Executa o pipeline
    orchestrator = PipelineOrchestrator(config_path)
    success = orchestrator.run(force_date=force_date, force_fund=force_fund)

    # Exit code
    sys.exit(0 if success else 1)
