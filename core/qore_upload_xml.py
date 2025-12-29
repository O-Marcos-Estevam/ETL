"""
================================================================================
QORE XML DIRECT UPLOAD TO ACCESS DATABASE
================================================================================

Este script realiza o upload direto de dados de arquivos XML (formato Anbima 5.0 / 
ISO 20022 SEMT.003) para um banco de dados Microsoft Access, sem necessidade de 
conversão intermediária para Excel.

FLUXO DE EXECUÇÃO:
    1. Lê todos os arquivos .xml da pasta XML_QORE
    2. Parseia cada XML extraindo: Data, Fundo, Patrimônio, Caixa
    3. Conecta ao banco Access (Base Fundos_v2.accdb)
    4. Para cada arquivo:
       - Deleta registros anteriores da mesma data/fundo (evita duplicatas)
       - Insere novos registros nas tabelas:
         * Cotas_Patrimonio_Qore (PL do fundo)
         * Caixa_Qore (saldos em conta)

ESTRUTURA DO XML ESPERADO:
    <Document>
        <SctiesBalAcctgRpt>
            <StmtGnlDtls>
                <StmtDtTm><Dt>2025-12-08</Dt></StmtDtTm>  <- Data referência
            </StmtGnlDtls>
            <BalForAcct>
                <AcctBaseCcyAmts><HldgVal><Amt>...</Amt></HldgVal></AcctBaseCcyAmts>  <- Patrimônio
            </BalForAcct>
            <SubAcctDtls>
                <BalForSubAcct>  <- Ativos individuais (caixa, RF, RV, etc.)
                    ...
                </BalForSubAcct>
            </SubAcctDtls>
        </SctiesBalAcctgRpt>
    </Document>

CONVENÇÃO DE NOMES DOS ARQUIVOS:
    DD.MM - Carteira XML - FIP <NOME_DO_FUNDO>.xml
    Exemplo: "08.12 - Carteira XML - FIP AMG.xml"
    - DD.MM = dia e mês (usado para compor a data completa)
    - FIP <NOME> = identificador do fundo

TABELAS DE DESTINO NO ACCESS:
    1. Cotas_Patrimonio_Qore
       - DATA_INPUT: datetime (data de referência)
       - FUNDO: string (nome do fundo)
       - PL Posição: float (patrimônio líquido)
       - QtdeCota: float (quantidade de cotas - não extraído do XML)
       - Valor da Cota Bruta: float (valor da cota - não extraído do XML)

    2. Caixa_Qore
       - DATA_INPUT: datetime
       - FUNDO: string
       - Descrição: string (descrição do saldo)
       - Moeda_Origem: string (moeda, default "BRL")
       - Valor: float (valor do saldo)

DEPENDÊNCIAS:
    - pyodbc: Conexão com Access via ODBC
    - xml.etree.ElementTree: Parser XML nativo do Python

AUTOR: ETL Team
DATA: Dezembro 2025
VERSÃO: 1.1 (com logging estruturado)
================================================================================
"""

import os
import sys
import logging
import xml.etree.ElementTree as ET
import pyodbc
from datetime import datetime
from typing import Optional, Dict, List, Any

# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================
# Formato: timestamp [NÍVEL] mensagem
# Níveis usados:
#   - INFO: operações normais (processamento, inserções OK)
#   - WARNING: situações não ideais mas não críticas (data não parseada)
#   - ERROR: erros que impedem processamento (XML inválido, conexão falhou)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÕES DE CAMINHOS
# =============================================================================

# Caminho do banco de dados Access
DB_PATH = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\09. Base_de_Dados\Base Fundos_v2.accdb'

# Pasta contendo os arquivos XML a serem processados
XML_FOLDER = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\XML_QORE'

# =============================================================================
# CONFIGURAÇÃO DE ENCODING (WINDOWS)
# =============================================================================
# Configura encoding UTF-8 para evitar erros com caracteres especiais no console

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 não possui método reconfigure
        pass


# =============================================================================
# CLASSE: Xml5Parser
# =============================================================================

class Xml5Parser:
    """
    Parser para arquivos XML no formato Anbima 5.0 / ISO 20022 (SEMT.003).
    
    Esta classe é responsável por extrair dados financeiros de arquivos XML
    de carteira, incluindo:
    - Metadados (data de referência, nome do fundo)
    - Patrimônio líquido total
    - Saldos de caixa
    - Classificação de ativos (caixa, renda fixa, renda variável, passivo)
    
    Attributes:
        Não possui atributos de instância. Todos os métodos são utilitários.
    
    Example:
        >>> parser = Xml5Parser()
        >>> data = parser.extract_data('/path/to/file.xml')
        >>> print(data['patrimonio'])  # Patrimônio líquido
        >>> print(data['caixa'])       # Lista de saldos de caixa
    """

    def _strip_ns(self, tag: str) -> str:
        """
        Remove o namespace de uma tag XML.
        
        Tags XML com namespace têm formato: {http://namespace.url}TagName
        Este método extrai apenas 'TagName'.
        
        Args:
            tag: Tag XML completa (pode incluir namespace)
            
        Returns:
            Tag sem o namespace
            
        Example:
            >>> self._strip_ns('{urn:iso:std:iso:20022}Document')
            'Document'
        """
        return tag.split('}', 1)[1] if '}' in tag else tag

    def _find_child(self, node: Optional[ET.Element], name: str) -> Optional[ET.Element]:
        """
        Busca um elemento filho pelo nome, ignorando namespaces.
        
        Percorre os filhos diretos do nó e retorna o primeiro que
        corresponder ao nome especificado (após remover namespace).
        
        Args:
            node: Elemento pai onde buscar. Se None, retorna None.
            name: Nome da tag a buscar (sem namespace)
            
        Returns:
            Elemento encontrado ou None se não existir
            
        Example:
            >>> doc = self._find_child(root, 'Document')
            >>> rpt = self._find_child(doc, 'SctiesBalAcctgRpt')
        """
        if node is None:
            return None
        for child in node:
            if self._strip_ns(child.tag) == name:
                return child
        return None
    
    def _findall_child(self, node: Optional[ET.Element], name: str) -> List[ET.Element]:
        """
        Busca todos os elementos filhos com determinado nome.
        
        Similar a _find_child, mas retorna uma lista com todos os
        filhos que correspondem ao nome (útil para elementos repetidos).
        
        Args:
            node: Elemento pai onde buscar
            name: Nome da tag a buscar
            
        Returns:
            Lista de elementos encontrados (lista vazia se nenhum)
            
        Example:
            >>> sub_bals = self._findall_child(sub_acct, 'BalForSubAcct')
            >>> for bal in sub_bals:
            ...     # processa cada ativo
        """
        if node is None:
            return []
        found = []
        for child in node:
            if self._strip_ns(child.tag) == name:
                found.append(child)
        return found
    
    def _get_text_safe(self, node: Optional[ET.Element], path_list: List[str]) -> Optional[str]:
        """
        Navega por um caminho de tags e retorna o texto do último nó.
        
        Permite acessar elementos aninhados de forma segura, retornando
        None se qualquer elemento intermediário não existir.
        
        Args:
            node: Elemento inicial
            path_list: Lista de nomes de tags a navegar em ordem
            
        Returns:
            Texto do elemento final, ou None se não encontrado
            
        Example:
            >>> # Navega: StmtGnlDtls -> TtlNetVal -> Amt
            >>> valor = self._get_text_safe(stmt_dtls, ['TtlNetVal', 'Amt'])
        """
        curr = node
        for tag in path_list:
            curr = self._find_child(curr, tag)
            if curr is None:
                return None
        return curr.text

    def extract_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extrai todos os dados relevantes de um arquivo XML.
        
        Processa o arquivo XML e retorna um dicionário estruturado com:
        - Metadados (data, fundo, nome do arquivo)
        - Patrimônio líquido total
        - Lista de saldos de caixa
        - Lista de ativos de renda variável
        - Lista de passivos
        - Lista de ativos de renda fixa
        
        Args:
            file_path: Caminho completo do arquivo XML
            
        Returns:
            Dicionário com os dados extraídos, ou None se falhar.
            Estrutura do retorno:
            {
                'meta': {
                    'data_ref': '2025-12-08',  # Data no formato YYYY-MM-DD
                    'fundo': 'AMG',            # Nome do fundo
                    'filename': 'arquivo.xml'  # Nome do arquivo original
                },
                'patrimonio': 20186303.73,     # PL total (float ou None)
                'caixa': [...],                # Lista de dicts de caixa
                'rv': [...],                   # Renda variável (não usado)
                'passivo': [...],              # Passivos (não usado)
                'rf': [...]                    # Renda fixa (não usado)
            }
            
        Raises:
            Não levanta exceções - erros são logados e retorna None
        """
        # Estrutura de dados de retorno
        data = {
            'meta': {},
            'patrimonio': None,
            'qtd_cotas': None,
            'qtd_cotas_antes': None,
            'valor_cota_bruta': None,
            'valor_cota_liquida': None,
            'valor_cota_rendimento': None,
            'caixa': [],
            'rv': [],
            'passivo': [],
            'rf': []
        }

        try:
            # -------------------------------------------------------------
            # PASSO 1: Parse do XML e navegação até o nó principal
            # -------------------------------------------------------------
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Localiza o nó Document (raiz do conteúdo)
            doc = self._find_child(root, 'Document')
            if doc is None:
                log.error("%s: Nó 'Document' não encontrado.", os.path.basename(file_path))
                return None

            # Localiza o relatório de balanço de títulos
            rpt = self._find_child(doc, 'SctiesBalAcctgRpt')
            if not rpt:
                log.error("%s: Nó 'SctiesBalAcctgRpt' não encontrado.", os.path.basename(file_path))
                return None

            # -------------------------------------------------------------
            # PASSO 2: Extração da data de referência
            # -------------------------------------------------------------
            # A data pode vir de duas fontes:
            # 1. Nome do arquivo (DD.MM) - preferencial
            # 2. XML (StmtGnlDtls/StmtDtTm/Dt) - fallback
            
            stmt_dtls = self._find_child(rpt, 'StmtGnlDtls')
            stmt_dt = self._find_child(stmt_dtls, 'StmtDtTm')
            dt_node = self._find_child(stmt_dt, 'Dt')
            
            # Validação: data é obrigatória
            if dt_node is None or dt_node.text is None:
                log.error("%s: Data não encontrada no XML.", os.path.basename(file_path))
                return None
            
            dt_ref_str = dt_node.text  # Formato: YYYY-MM-DD

            # Extrai data do nome do arquivo (formato: "DD.MM - Carteira XML - ...")
            basename = os.path.basename(file_path)
            if " - Carteira XML - " in basename:
                date_part = basename.split(" - Carteira XML - ")[0].strip()
                if '.' in date_part:
                    try:
                        day, month = map(int, date_part.split('.'))
                        year = datetime.strptime(dt_ref_str, "%Y-%m-%d").year
                        data_ref = datetime(year, month, day).strftime("%Y-%m-%d")
                    except (ValueError, AttributeError) as e:
                        log.warning("Falha ao parsear data do filename, usando XML: %s", e)
                        data_ref = dt_ref_str
                else:
                    data_ref = dt_ref_str
            else:
                data_ref = dt_ref_str

            data['meta']['data_ref'] = data_ref
            data['meta']['filename'] = basename

            # -------------------------------------------------------------
            # PASSO 3: Extração do nome do fundo
            # -------------------------------------------------------------
            # O nome vem do padrão do arquivo: "... - FIP <NOME>.xml"
            # Mantém o prefixo FIP/FIDC/FIM no nome do fundo

            if " - FIP " in basename:
                parts = basename.split(" - FIP ")
                fund_name = "FIP " + parts[-1].replace(".xml", "").strip()
                data['meta']['fundo'] = fund_name
            elif " - FIDC " in basename:
                parts = basename.split(" - FIDC ")
                fund_name = "FIDC " + parts[-1].replace(".xml", "").strip()
                data['meta']['fundo'] = fund_name
            elif " - FIM " in basename:
                parts = basename.split(" - FIM ")
                fund_name = "FIM " + parts[-1].replace(".xml", "").strip()
                data['meta']['fundo'] = fund_name
            else:
                data['meta']['fundo'] = "DESCONHECIDO"

            # -------------------------------------------------------------
            # PASSO 4: Extração do Patrimônio Líquido
            # -------------------------------------------------------------
            # Prioridade de extração (do mais preciso ao fallback):
            # 1. AcctBaseCcyTtlAmts/TtlHldgsValOfStmt/Amt - PL LÍQUIDO (já deduz passivos)
            # 2. TtlNetVal no header - valor consolidado
            # 3. AcctBaseCcyAmts/HldgVal/Amt no BalForAcct - capital integralizado (bruto)

            bal_main = self._find_child(rpt, 'BalForAcct')

            # Tentativa 1: TtlHldgsValOfStmt - PL Líquido (preferencial)
            ttl_amts = self._find_child(rpt, 'AcctBaseCcyTtlAmts')
            ttl_hldgs = self._find_child(ttl_amts, 'TtlHldgsValOfStmt')
            ttl_hldgs_amt = self._find_child(ttl_hldgs, 'Amt')

            if ttl_hldgs_amt is not None and ttl_hldgs_amt.text:
                data['patrimonio'] = float(ttl_hldgs_amt.text)
            else:
                # Tentativa 2: TtlNetVal no header
                ttl_net_val = self._get_text_safe(stmt_dtls, ['TtlNetVal', 'Amt'])
                if ttl_net_val:
                    data['patrimonio'] = float(ttl_net_val)
                else:
                    # Tentativa 3: HldgVal (capital integralizado - fallback)
                    acct_amts = self._find_child(bal_main, 'AcctBaseCcyAmts')
                    hldg = self._find_child(acct_amts, 'HldgVal')
                    amt = self._find_child(hldg, 'Amt')
                    if amt is not None:
                        data['patrimonio'] = float(amt.text)

            # -------------------------------------------------------------
            # PASSO 4.1: Extração da Quantidade de Cotas
            # -------------------------------------------------------------
            # Localização: BalForAcct/AggtBal/Qty/Qty/Qty/Unit
            # Estrutura aninhada com múltiplos níveis de Qty

            aggt_bal = self._find_child(bal_main, 'AggtBal')
            if aggt_bal:
                # Navega pela estrutura aninhada de Qty
                qty_level1 = self._find_child(aggt_bal, 'Qty')
                qty_level2 = self._find_child(qty_level1, 'Qty')
                qty_level3 = self._find_child(qty_level2, 'Qty')
                unit_node = self._find_child(qty_level3, 'Unit')

                if unit_node is not None and unit_node.text:
                    data['qtd_cotas'] = float(unit_node.text)
                    # QtdeCota_antes não está disponível no XML, usa o mesmo valor
                    data['qtd_cotas_antes'] = data['qtd_cotas']

            # -------------------------------------------------------------
            # PASSO 4.2: Extração dos Valores de Cota
            # -------------------------------------------------------------
            # PricDtls pode ter múltiplas ocorrências:
            # - NAVL (Net Asset Value per unit) = Cota Bruta
            # - INTE (Interest/Integral) = Cota Líquida

            if bal_main:
                for price_dtls in self._findall_child(bal_main, 'PricDtls'):
                    tp_node = self._find_child(price_dtls, 'Tp')
                    cd_node = self._find_child(tp_node, 'Cd')

                    if cd_node is not None and cd_node.text:
                        price_type = cd_node.text.upper()

                        # Extrai o valor do preço
                        val_node = self._find_child(price_dtls, 'Val')
                        amt_node = self._find_child(val_node, 'Amt')

                        if amt_node is not None and amt_node.text:
                            price_value = float(amt_node.text)

                            if price_type == 'NAVL':
                                # NAVL = Net Asset Value per unit (Cota Bruta)
                                data['valor_cota_bruta'] = price_value
                            elif price_type == 'INTE':
                                # INTE = Cota Líquida
                                data['valor_cota_liquida'] = price_value

                # Se não encontrou valores separados, usa o mesmo para ambos
                if data['valor_cota_bruta'] and not data['valor_cota_liquida']:
                    data['valor_cota_liquida'] = data['valor_cota_bruta']
                elif data['valor_cota_liquida'] and not data['valor_cota_bruta']:
                    data['valor_cota_bruta'] = data['valor_cota_liquida']

                # Valor da Cota Rendimento = mesmo que Cota Bruta (padrão QORE)
                if data['valor_cota_bruta']:
                    data['valor_cota_rendimento'] = data['valor_cota_bruta']

            # -------------------------------------------------------------
            # PASSO 5: Extração dos ativos individuais (SubAccounts)
            # -------------------------------------------------------------
            # Cada SubAccount representa um ativo na carteira.
            # Classificados por tipo: caixa, RV, RF, fundos, etc.

            sub_acct = self._find_child(rpt, 'SubAcctDtls')
            if sub_acct:
                for sub_bal in self._findall_child(sub_acct, 'BalForSubAcct'):
                    item = {}

                    # Identificação do instrumento (pode ter múltiplos OthrId)
                    fin_id = self._find_child(sub_bal, 'FinInstrmId')
                    fin_attr = self._find_child(sub_bal, 'FinInstrmAttrbts')

                    # ISIN (se disponível)
                    item['isin'] = self._get_text_safe(fin_id, ['ISIN'])

                    # Extrai todos os OthrId com seus tipos
                    item['tipo_nivel1'] = None  # CASH, EQUI, RFBC, etc.
                    item['ticker'] = None
                    item['tipo_b3'] = None  # ACOES, etc.
                    item['instituicao'] = None

                    if fin_id:
                        for othr_id in self._findall_child(fin_id, 'OthrId'):
                            id_val = self._get_text_safe(othr_id, ['Id'])
                            tp_node = self._find_child(othr_id, 'Tp')
                            tp_prtry = self._get_text_safe(tp_node, ['Prtry'])

                            if tp_prtry:
                                tp_upper = tp_prtry.upper()
                                if 'NIVEL 1' in tp_upper or 'TABELA' in tp_upper:
                                    item['tipo_nivel1'] = id_val
                                elif 'TICKER' in tp_upper:
                                    item['ticker'] = id_val
                                elif 'ATIVOSB3' in tp_upper:
                                    item['tipo_b3'] = id_val
                                elif 'INSTITUICAO' in tp_upper or 'FINANCEIRA' in tp_upper:
                                    item['instituicao'] = id_val

                    # Descrição e CFI
                    item['desc'] = self._get_text_safe(fin_attr, ['Desc'])
                    item['cfi'] = self._get_text_safe(fin_attr, ['ClssfctnFinInstrm'])

                    # Moeda
                    item['moeda'] = self._get_text_safe(fin_attr, ['DnmtnCcy']) or 'BRL'

                    # Valor financeiro (AcctBaseCcyAmts/HldgVal/Amt)
                    acct_amts = self._find_child(sub_bal, 'AcctBaseCcyAmts')
                    hldg = self._find_child(acct_amts, 'HldgVal')
                    amt = self._find_child(hldg, 'Amt')
                    if amt is not None and amt.text:
                        item['financeiro'] = float(amt.text)

                    # Preço unitário (PricDtls/Val/Amt)
                    price_dtls = self._find_child(sub_bal, 'PricDtls')
                    if price_dtls:
                        price_amt = self._find_child(self._find_child(price_dtls, 'Val'), 'Amt')
                        if price_amt is not None and price_amt.text:
                            item['preco_unitario'] = float(price_amt.text)

                    # Quantidade (navega pela estrutura aninhada Qty/Qty/Qty/Unit)
                    aggt_bal = self._find_child(sub_bal, 'AggtBal')
                    if aggt_bal:
                        qty_l1 = self._find_child(aggt_bal, 'Qty')
                        qty_l2 = self._find_child(qty_l1, 'Qty')
                        qty_l3 = self._find_child(qty_l2, 'Qty')
                        unit = self._find_child(qty_l3, 'Unit')
                        if unit is not None and unit.text:
                            item['qtd'] = float(unit.text)

                    # ---------------------------------------------------------
                    # Classificação do ativo por tipo_nivel1
                    # ---------------------------------------------------------
                    tipo = str(item.get('tipo_nivel1', '')).upper()
                    ticker_up = str(item.get('ticker', '')).upper()
                    tipo_b3 = str(item.get('tipo_b3', '')).upper()

                    if tipo == 'CASH' or ticker_up == 'CASH':
                        # Saldo em conta corrente
                        data['caixa'].append(item)
                    elif tipo == 'EQUI' or tipo_b3 == 'ACOES' or 'ACAO' in tipo:
                        # Ações / Renda Variável
                        data['rv'].append(item)
                    elif tipo in ('RFBC', 'RFPR', 'DEBT') or 'DEBENTURE' in tipo or 'CRI' in tipo or 'CRA' in tipo:
                        # Renda Fixa
                        data['rf'].append(item)
                    elif tipo == 'FUND' or 'FUNDO' in tipo:
                        # Investimento em outros fundos
                        if 'fundos' not in data:
                            data['fundos'] = []
                        data['fundos'].append(item)
                    else:
                        # Default: RF
                        data['rf'].append(item)

            # -------------------------------------------------------------
            # PASSO 6: Extração de Passivos e Recebíveis (BalBrkdwn)
            # -------------------------------------------------------------
            # PAYABLES = Passivos (valores negativos no banco)
            # RECEIVABLES = Recebíveis (valores positivos no banco)

            if bal_main:
                for bal_brkdwn in self._findall_child(bal_main, 'BalBrkdwn'):
                    sub_bal_tp = self._find_child(bal_brkdwn, 'SubBalTp')
                    prtry = self._find_child(sub_bal_tp, 'Prtry')
                    scheme_nm = self._get_text_safe(prtry, ['SchmeNm'])

                    # PAYABLES (passivos - serão negativos)
                    if scheme_nm and 'PAYABLES' in scheme_nm.upper():
                        for addtl in self._findall_child(bal_brkdwn, 'AddtlBalBrkdwnDtls'):
                            passivo_item = {}

                            sub_tp = self._find_child(addtl, 'SubBalTp')
                            sub_prtry = self._find_child(sub_tp, 'Prtry')

                            passivo_item['desc'] = self._get_text_safe(sub_prtry, ['SchmeNm'])
                            passivo_item['codigo'] = self._get_text_safe(sub_prtry, ['Id'])
                            passivo_item['tipo'] = 'PAYABLE'  # Marca como passivo

                            p_qty = self._find_child(addtl, 'Qty')
                            p_qty_inner = self._find_child(p_qty, 'Qty')
                            p_face = self._get_text_safe(p_qty_inner, ['FaceAmt'])
                            if p_face:
                                passivo_item['valor'] = float(p_face)

                            if passivo_item.get('desc') or passivo_item.get('valor'):
                                data['passivo'].append(passivo_item)

                    # RECEIVABLES (recebíveis - serão positivos)
                    elif scheme_nm and 'RECEIVABLES' in scheme_nm.upper():
                        for addtl in self._findall_child(bal_brkdwn, 'AddtlBalBrkdwnDtls'):
                            recebivel_item = {}

                            sub_tp = self._find_child(addtl, 'SubBalTp')
                            sub_prtry = self._find_child(sub_tp, 'Prtry')

                            recebivel_item['desc'] = self._get_text_safe(sub_prtry, ['SchmeNm'])
                            recebivel_item['codigo'] = self._get_text_safe(sub_prtry, ['Id'])
                            recebivel_item['tipo'] = 'RECEIVABLE'  # Marca como recebível

                            p_qty = self._find_child(addtl, 'Qty')
                            p_qty_inner = self._find_child(p_qty, 'Qty')
                            p_face = self._get_text_safe(p_qty_inner, ['FaceAmt'])
                            if p_face:
                                recebivel_item['valor'] = float(p_face)

                            if recebivel_item.get('desc') or recebivel_item.get('valor'):
                                data['passivo'].append(recebivel_item)

            return data

        except Exception as e:
            log.exception("Erro ao processar XML: %s", e)
            return None


# =============================================================================
# FUNÇÕES DE BANCO DE DADOS
# =============================================================================

def get_db_connection() -> Optional[pyodbc.Connection]:
    """
    Estabelece conexão com o banco de dados Access.
    
    Utiliza o driver ODBC do Microsoft Access para conectar
    ao arquivo .accdb especificado em DB_PATH.
    
    Returns:
        Objeto de conexão pyodbc, ou None se falhar
        
    Note:
        Requer o driver "Microsoft Access Driver (*.mdb, *.accdb)"
        instalado no sistema (geralmente disponível no Office)
    """
    try:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            r'DBQ=' + DB_PATH + ';'
        )
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        log.error("Erro de conexão com BD: %s", e)
        return None


def upload_xml_data(conn: pyodbc.Connection, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Faz upload dos dados parseados para o banco Access.

    Para cada tipo de dado (patrimônio, caixa), esta função:
    1. Remove registros existentes da mesma data/fundo (upsert)
    2. Insere os novos dados

    Args:
        conn: Conexão ativa com o banco Access
        parsed_data: Dicionário retornado por Xml5Parser.extract_data()

    Returns:
        Dicionário com estatísticas do upload:
        {
            'success': bool,
            'patrimonio': float ou None,
            'caixa_count': int,
            'cpr_count': int,
            'rv_count': int,
            'rf_count': int,
            'errors': list[str]
        }

    Side Effects:
        - Deleta e insere registros nas tabelas:
          * Cotas_Patrimonio_Qore
          * Caixa_Qore
        - Executa commit na conexão
    """
    cursor = conn.cursor()

    fundo = parsed_data['meta']['fundo']
    data_ref = parsed_data['meta']['data_ref']

    # Estatísticas do upload
    stats = {
        'success': True,
        'fundo': fundo,
        'data_ref': data_ref,
        'patrimonio': None,
        'caixa_count': 0,
        'cpr_count': 0,
        'cpr_total': 0,
        'rv_count': 0,
        'rv_total': 0,
        'rf_count': 0,
        'rf_total': 0,
        'errors': []
    }

    # =========================================================================
    # 1. PATRIMÔNIO (Tabela: Cotas_Patrimonio_Qore)
    # =========================================================================
    # Colunas: DATA_INPUT, FUNDO, PL Posição, QtdeCota_antes, QtdeCota,
    #          Valor da Cota Bruta, Valor da Cota Líquida, Valor da Cota Rendimento

    try:
        table_cp = "Cotas_Patrimonio_Qore"

        # Deletar registros anteriores (evita duplicatas)
        del_query = f"DELETE FROM {table_cp} WHERE [DATA_INPUT] = ? AND [FUNDO] = ?"
        cursor.execute(del_query, (data_ref, fundo))

        # Inserir novo registro se patrimônio disponível
        if parsed_data['patrimonio'] is not None:
            pl_val = float(parsed_data['patrimonio'])

            # Extrair valores de cotas (usa 0 se não disponível)
            qtd_cotas_antes = parsed_data.get('qtd_cotas_antes') or 0
            qtd_cotas = parsed_data.get('qtd_cotas') or 0
            valor_cota_bruta = parsed_data.get('valor_cota_bruta') or 0
            valor_cota_liquida = parsed_data.get('valor_cota_liquida') or 0
            valor_cota_rendimento = parsed_data.get('valor_cota_rendimento') or 0

            insert_query = f"""
            INSERT INTO {table_cp} (
                [DATA_INPUT], [FUNDO], [PL Posição],
                [QtdeCota_antes], [QtdeCota],
                [Valor da Cota Bruta], [Valor da Cota Líquida], [Valor da Cota Rendimento]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (
                data_ref, fundo, pl_val,
                qtd_cotas_antes, qtd_cotas,
                valor_cota_bruta, valor_cota_liquida, valor_cota_rendimento
            ))

            stats['patrimonio'] = pl_val

    except Exception as e:
        stats['errors'].append(f"Patrimônio: {e}")
        stats['success'] = False
        log.error("   Falha ao inserir Patrimônio: %s", e)

    # =========================================================================
    # 2. CAIXA (Tabela: Caixa_Qore)
    # =========================================================================
    # Colunas: DATA_INPUT, FUNDO, Descrição, Moeda_Origem, Valor

    try:
        table_cx = "Caixa_Qore"

        # Deletar registros anteriores
        del_query = f"DELETE FROM {table_cx} WHERE [DATA_INPUT] = ? AND [FUNDO] = ?"
        cursor.execute(del_query, (data_ref, fundo))

        # Inserir cada item de caixa
        for item in parsed_data['caixa']:
            # Monta descrição: "Disponível c/c - {instituicao}"
            instituicao = item.get('instituicao') or ''
            desc = item.get('desc') or f"Disponível c/c - {instituicao}"
            val = item.get('financeiro', 0.0)
            moeda = item.get('moeda', 'BRL')

            insert_query = f"""
            INSERT INTO {table_cx} ([DATA_INPUT], [FUNDO], [Descrição], [Moeda_Origem], [Valor])
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (data_ref, fundo, desc, moeda, val))

        stats['caixa_count'] = len(parsed_data['caixa'])

    except Exception as e:
        stats['errors'].append(f"Caixa: {e}")
        stats['success'] = False
        log.error("   Falha ao inserir Caixa: %s", e)

    # =========================================================================
    # 3. CPR_QORE (Contas a Pagar/Receber)
    # =========================================================================
    # Colunas: DATA_INPUT, FUNDO, Descrição, Lançamento, Vencimento, Valor, %Valores, %PL
    # PAYABLES = valores negativos (contas a pagar)
    # RECEIVABLES = valores positivos (contas a receber, ex: Diferimento Taxa CVM)

    try:
        table_cpr = "CPR_QORE"

        # Deletar registros anteriores
        del_query = f"DELETE FROM {table_cpr} WHERE [DATA_INPUT] = ? AND [FUNDO] = ?"
        cursor.execute(del_query, (data_ref, fundo))

        # Calcular total de passivos para %Valores
        total_passivo = sum(item.get('valor', 0) for item in parsed_data['passivo'])
        pl_total = parsed_data.get('patrimonio') or 1  # Evita divisão por zero

        # Inserir cada passivo/recebível
        for item in parsed_data['passivo']:
            desc = item.get('desc', 'Passivo')
            valor_abs = item.get('valor', 0.0)
            tipo = item.get('tipo', 'PAYABLE')

            # PAYABLES = negativos, RECEIVABLES = positivos
            if tipo == 'RECEIVABLE':
                valor = abs(valor_abs) if valor_abs else 0.0
            else:
                valor = -abs(valor_abs) if valor_abs else 0.0

            # Calcula percentuais (usando valor absoluto para cálculo)
            pct_valores = (valor_abs / total_passivo * 100) if total_passivo > 0 else 0
            pct_pl = (valor_abs / pl_total * 100) if pl_total > 0 else 0

            insert_query = f"""
            INSERT INTO {table_cpr} (
                [DATA_INPUT], [FUNDO], [Descrição], [Lançamento], [Vencimento],
                [Valor], [%Valores], [%PL]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            # Lançamento e Vencimento não estão no XML, usamos data_ref para ambos
            cursor.execute(insert_query, (
                data_ref, fundo, desc, data_ref, data_ref,
                valor, pct_valores, pct_pl
            ))

        stats['cpr_count'] = len(parsed_data['passivo'])
        stats['cpr_total'] = total_passivo

    except Exception as e:
        stats['errors'].append(f"CPR: {e}")
        stats['success'] = False
        log.error("   Falha ao inserir CPR: %s", e)

    # =========================================================================
    # 4. SOCIEDADE_LIMITADA_QORE (Renda Variável / Ações)
    # =========================================================================
    # Colunas: DATA_INPUT, FUNDO, Id_Operacao, Descricao, Emissor, Tipo_Companhia,
    #          Codigo, Data_Aquisicao, Qtde, Qtde_Bloqueada, PU_Custo, Valor_Custo,
    #          Pu_Mercado, Valor_Mercado, %Outros_Ativos, %PL

    try:
        table_rv = "Sociedade_Limitada_QORE"

        # Deletar registros anteriores
        del_query = f"DELETE FROM {table_rv} WHERE [DATA_INPUT] = ? AND [FUNDO] = ?"
        cursor.execute(del_query, (data_ref, fundo))

        # Calcular total de RV para percentuais
        total_rv = sum(item.get('financeiro', 0) for item in parsed_data['rv'])
        pl_total = parsed_data.get('patrimonio') or 1

        # Inserir cada ativo de RV
        for item in parsed_data['rv']:
            ticker = item.get('ticker') or item.get('tipo_nivel1') or 'N/A'
            tipo_b3 = item.get('tipo_b3') or 'ACOES'
            qtd = item.get('qtd', 0)
            preco_unit = item.get('preco_unitario', 0)
            valor_mercado = item.get('financeiro', 0)

            # Percentuais
            pct_outros = (valor_mercado / total_rv * 100) if total_rv > 0 else 0
            pct_pl = (valor_mercado / pl_total * 100) if pl_total > 0 else 0

            insert_query = f"""
            INSERT INTO {table_rv} (
                [DATA_INPUT], [FUNDO], [Id_Operacao], [Descricao], [Emissor],
                [Tipo_Companhia], [Codigo], [Data_Aquisicao], [Qtde], [Qtde_Bloqueada],
                [PU_Custo], [Valor_Custo], [Pu_Mercado], [Valor_Mercado],
                [%Outros_Ativos], [%PL]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (
                data_ref, fundo,
                ticker,  # Id_Operacao
                item.get('desc') or f"Participação {ticker}",  # Descricao
                ticker,  # Emissor
                tipo_b3,  # Tipo_Companhia
                ticker,  # Codigo
                None,  # Data_Aquisicao (não disponível no XML)
                qtd,  # Qtde
                0,  # Qtde_Bloqueada
                preco_unit,  # PU_Custo (usamos preço de mercado)
                valor_mercado,  # Valor_Custo
                preco_unit,  # Pu_Mercado
                valor_mercado,  # Valor_Mercado
                pct_outros,
                pct_pl
            ))

        stats['rv_count'] = len(parsed_data['rv'])
        stats['rv_total'] = total_rv

    except Exception as e:
        stats['errors'].append(f"RV: {e}")
        stats['success'] = False
        log.error("   Falha ao inserir RV: %s", e)

    # =========================================================================
    # 5. RENDA_FIXA_QORE (se houver ativos de RF)
    # =========================================================================
    # Colunas: DATA_INPUT, FUNDO, ID, Operação, Emissão, Vencimento, Titulo,
    #          Emissor, Qtd, QtdBloq, Taxa, Valor_Aplic, PU_Mercado, Valor_Bruto,
    #          Tributos, Valor_Liquido, %RF, %PL

    try:
        if parsed_data['rf']:
            table_rf = "Renda_Fixa_Qore"

            # Deletar registros anteriores
            del_query = f"DELETE FROM {table_rf} WHERE [DATA_INPUT] = ? AND [FUNDO] = ?"
            cursor.execute(del_query, (data_ref, fundo))

            # Calcular total de RF para percentuais
            total_rf = sum(item.get('financeiro', 0) for item in parsed_data['rf'])
            pl_total = parsed_data.get('patrimonio') or 1

            for item in parsed_data['rf']:
                ticker = item.get('ticker') or item.get('tipo_nivel1') or 'N/A'
                qtd = item.get('qtd', 0)
                preco_unit = item.get('preco_unitario', 0)
                valor = item.get('financeiro', 0)

                pct_rf = (valor / total_rf * 100) if total_rf > 0 else 0
                pct_pl = (valor / pl_total * 100) if pl_total > 0 else 0

                insert_query = f"""
                INSERT INTO {table_rf} (
                    [DATA_INPUT], [FUNDO], [ID], [Operação], [Emissão], [Vencimento],
                    [Titulo], [Emissor], [Qtd], [QtdBloq], [Taxa],
                    [Valor_Aplic], [PU_Mercado], [Valor_Bruto], [Tributos], [Valor_Liquido],
                    [%RF], [%PL]
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, (
                    data_ref, fundo,
                    ticker,  # ID
                    None, None, None,  # Operação, Emissão, Vencimento
                    item.get('desc') or ticker,  # Titulo
                    ticker,  # Emissor
                    qtd, 0, 0,  # Qtd, QtdBloq, Taxa
                    valor, preco_unit, valor, 0, valor,  # Valores
                    pct_rf, pct_pl
                ))

            stats['rf_count'] = len(parsed_data['rf'])
            stats['rf_total'] = total_rf

    except Exception as e:
        stats['errors'].append(f"RF: {e}")
        stats['success'] = False
        log.error("   Falha ao inserir Renda Fixa: %s", e)

    # Commit das alterações
    conn.commit()

    return stats


# =============================================================================
# FUNÇÃO PRINCIPAL (MAIN)
# =============================================================================

def format_currency(value: float) -> str:
    """Formata valor monetário de forma compacta."""
    if value >= 1_000_000:
        return f"R$ {value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"R$ {value/1_000:.1f}K"
    else:
        return f"R$ {value:.2f}"


def print_header():
    """Imprime cabeçalho formatado."""
    print()
    print("=" * 80)
    print("  QORE XML UPLOAD - Data Upload para Access Database")
    print("=" * 80)
    print()


def print_progress_line(idx: int, total: int, fundo: str, data_ref: str, stats: dict):
    """Imprime linha de progresso compacta para cada arquivo."""
    status = "[OK]" if stats['success'] else "[ERRO]"

    # Monta resumo das inserções
    insercoes = []
    if stats.get('patrimonio'):
        insercoes.append(f"PL={format_currency(stats['patrimonio'])}")
    if stats.get('caixa_count'):
        insercoes.append(f"Caixa={stats['caixa_count']}")
    if stats.get('cpr_count'):
        insercoes.append(f"CPR={stats['cpr_count']}")
    if stats.get('rv_count'):
        insercoes.append(f"RV={stats['rv_count']}")
    if stats.get('rf_count'):
        insercoes.append(f"RF={stats['rf_count']}")

    resumo = " | ".join(insercoes) if insercoes else "Sem dados"

    # Formata a linha
    progress = f"[{idx:02d}/{total:02d}]"
    print(f"  {progress} {status} {fundo:<20} {data_ref}  ->  {resumo}")


def print_summary(total_files: int, sucesso: int, erros: int, pulados: int,
                  patrimonio: float, registros: dict, arquivos_erro: list):
    """Imprime relatório final formatado."""
    print()
    print("-" * 80)
    print("  RESUMO DO PROCESSAMENTO")
    print("-" * 80)
    print()
    print(f"    Arquivos encontrados:     {total_files}")
    print(f"    Processados com sucesso:  {sucesso}")
    print(f"    Processados com erro:     {erros}")
    print(f"    Pulados (parse falhou):   {pulados}")
    print()
    print("  TOTAIS INSERIDOS:")
    print(f"    Patrimonio total:  R$ {patrimonio:>18,.2f}")
    print(f"    Linhas de Caixa:   {registros['caixa']:>18}")
    print(f"    Linhas de CPR:     {registros['cpr']:>18}")
    print(f"    Linhas de RV:      {registros['rv']:>18}")
    print(f"    Linhas de RF:      {registros['rf']:>18}")

    if arquivos_erro:
        print()
        print("  ARQUIVOS COM ERRO:")
        for erro in arquivos_erro:
            print(f"    [X] {erro}")

    print()
    print("=" * 80)
    print("  PROCESSO CONCLUIDO")
    print("=" * 80)
    print()


if __name__ == "__main__":
    """
    Ponto de entrada do script.

    Fluxo:
    1. Verifica se a pasta XML existe
    2. Lista todos os arquivos .xml
    3. Conecta ao banco Access
    4. Para cada arquivo:
       - Parseia o XML
       - Faz upload dos dados
    5. Fecha a conexão (garantido pelo finally)
    """

    print_header()

    # Validação: pasta XML deve existir
    if not os.path.exists(XML_FOLDER):
        log.error("Pasta XML nao encontrada: %s", XML_FOLDER)
        sys.exit(1)

    # Lista arquivos XML
    xml_files = sorted([f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')])
    print(f"  Arquivos XML encontrados: {len(xml_files)}")
    print()

    if not xml_files:
        print("  Nenhum arquivo para processar.")
        sys.exit(0)

    # Conexão com banco
    conn = get_db_connection()
    if not conn:
        log.error("Abortando devido a erro de conexao.")
        sys.exit(1)

    print("  Conexao com banco: OK")
    print()
    print("-" * 80)
    print("  PROCESSAMENTO")
    print("-" * 80)
    print()

    # Processa arquivos
    parser = Xml5Parser()

    # Contadores para relatório final
    total_processados = 0
    total_sucesso = 0
    total_erros = 0
    total_pulados = 0
    total_patrimonio = 0.0
    total_registros = {'caixa': 0, 'cpr': 0, 'rv': 0, 'rf': 0}
    arquivos_com_erro = []

    try:
        for idx, f in enumerate(xml_files, 1):
            full_path = os.path.join(XML_FOLDER, f)

            data = parser.extract_data(full_path)

            if data:
                stats = upload_xml_data(conn, data)
                total_processados += 1

                # Imprime linha de progresso
                print_progress_line(
                    idx, len(xml_files),
                    stats['fundo'], stats['data_ref'], stats
                )

                if stats['success']:
                    total_sucesso += 1
                    if stats['patrimonio']:
                        total_patrimonio += stats['patrimonio']
                    total_registros['caixa'] += stats['caixa_count']
                    total_registros['cpr'] += stats['cpr_count']
                    total_registros['rv'] += stats['rv_count']
                    total_registros['rf'] += stats['rf_count']
                else:
                    total_erros += 1
                    arquivos_com_erro.append(f"{f}: {', '.join(stats['errors'])}")
            else:
                total_pulados += 1
                print(f"  [{idx:02d}/{len(xml_files):02d}] [SKIP] {f} - Falha na extracao")

    finally:
        # Garante fechamento da conexão mesmo em caso de erro
        conn.close()

        # Relatório final
        print_summary(
            len(xml_files), total_sucesso, total_erros, total_pulados,
            total_patrimonio, total_registros, arquivos_com_erro
        )
