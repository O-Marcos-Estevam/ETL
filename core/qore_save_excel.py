import sys
import os
import pandas as pd
import traceback
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime

# --- CONFIGURAÇÃO DE AMBIENTE ---
# Remove o diretório atual do path temporariamente para evitar conflito com os.py local
if '' in sys.path: sys.path.remove('')
if '.' in sys.path: sys.path.remove('.')

# Adiciona o diretório atual de volta se necessário
current_dir = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\0. Python'
if current_dir not in sys.path:
    sys.path.append(current_dir)


# --- UTILITÁRIOS ---
def setup_environment():
    """Configurações iniciais de ambiente (encoding, paths, etc)"""
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

def clean_filename(filename):
    """Limpa caracteres inválidos para nome de arquivo"""
    return filename.replace(' ', '_').replace('/', '-').replace('\\', '-').replace(':', '-').replace('.', '')


# --- INTERFACE STRATEGY ---
class ReportParser(ABC):
    """Classe base para todos os parsers de relatório"""
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Retorna True se este parser consegue ler o arquivo"""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> bool:
        """
        Lê o arquivo, processa e salva os outputs.
        Retorna True se sucesso, False caso contrário.
        """
        pass

    def get_destination_folder(self):
        return r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\13. AUXILIAR_QORE'


# --- PARSER LEGADO (QORE V1) ---
class LegacyExcelParser(ReportParser):
    """Mantém a lógica original do qore_save_excel_folders.py"""

    def can_parse(self, file_path: str) -> bool:
        # Lógica original: verifica se tem 'CARTEIRA' ou 'POSIÇÃO' no nome
        # E se NÃO é o novo formato (ex: assumindo que o novo não tem 'CARTEIRA' ou tem estrutura diferente)
        # Por segurança, vamos deixar este parser "guloso" para .xlsx antigos, 
        # mas idealmente deveríamos ter uma distinção mais clara.
        # Vou assumir que se o nome contém "CARTEIRA_DIARIA" (com underscore) é NOVO,
        # e "Carteira Excel" (com espaço e hífen) é VELHO, baseado nos nomes vistos.
        
        name = os.path.basename(file_path).upper()
        if not file_path.endswith(('.xlsx', '.xls')):
            return False
            
        # Padrão antigo geralmente tem "Carteira Excel" ou "Posição"
        is_legacy_naming = "CARTEIRA EXCEL" in name or "POSICAO" in name or "POSIÇÃO" in name
        
        # O novo arquivo se chama "CARTEIRA_DIARIA_..." (underscores)
        if "CARTEIRA_DIARIA_" in name:
            return False 
            
        return is_legacy_naming

    def parse(self, file_path: str) -> bool:
        print(f"[LEGACY PARSER] Processando: {os.path.basename(file_path)}")
        try:
            df = pd.read_excel(file_path)
            return self._process_legacy_logic(df, os.path.basename(file_path))
        except Exception as e:
            print(f"Erro no LegacyParser: {e}")
            traceback.print_exc()
            return False

    def _process_legacy_logic(self, df, nome_arquivo_original):
        # ... [CÓDIGO ORIGINAL REFATORADO PARA DENTRO DA PROPRIEDADE] ...
        # Copiando a lógica de "identificar índices" para cá
        
        caminho_pasta_destino = self.get_destination_folder()
        indices = {
            'rv': None, 'ltda': None, 'fundo': None, 'dc': None, 
            'rf': None, 'caixa': None, 'areceber': None, 'apagar': None,
            'rentab': None, 'cp': None, 'cotista': None
        }
        # Estrutura para guardar (start, end)
        ranges = {k: [None, None] for k in indices}

        # Varredura (lógica original)
        for num_linha, primeira_coluna_valor in enumerate(df.iloc[:, 1]):
            if not isinstance(primeira_coluna_valor, str): continue
            
            val_lower = primeira_coluna_valor.lower()
            
            # Mapeamento de regras (simplificado para brevidade, mas mantendo a lógica)
            # Renda Variável
            if ranges['rv'][0] is None and "ações" in val_lower: ranges['rv'][0] = num_linha
            if ranges['rv'][0] is not None and ranges['rv'][1] is None and "total ações: " in val_lower: ranges['rv'][1] = num_linha
            
            # Sociedade Limitada
            if ranges['ltda'][0] is None and "participação em sociedade limitada" in val_lower: ranges['ltda'][0] = num_linha
            if ranges['ltda'][0] is not None and ranges['ltda'][1] is None and "total participação em sociedade limitada" in val_lower: ranges['ltda'][1] = num_linha

            # Fundos
            if ranges['fundo'][0] is None and "cotas de investimento" in val_lower: ranges['fundo'][0] = num_linha
            if ranges['fundo'][0] is not None and ranges['fundo'][1] is None and "total cotas de investimento: " in val_lower: ranges['fundo'][1] = num_linha

            # Direito Creditório
            if ranges['dc'][0] is None and "direito creditório" in val_lower: ranges['dc'][0] = num_linha
            if ranges['dc'][0] is not None and ranges['dc'][1] is None and "total direito creditório" in val_lower: ranges['dc'][1] = num_linha

            # Renda Fixa
            if ranges['rf'][0] is None and "renda fixa" in val_lower: ranges['rf'][0] = num_linha
            if ranges['rf'][0] is not None and ranges['rf'][1] is None and "total renda fixa:" in val_lower: ranges['rf'][1] = num_linha

            # Caixa
            if ranges['caixa'][0] is None and "saldos em conta corrente" in val_lower: ranges['caixa'][0] = num_linha
            # Nota: lógica original subtrai 1 no end linha do caixa
            if ranges['caixa'][0] is not None and ranges['caixa'][1] is None and "patrimônio fechamento" in val_lower: ranges['caixa'][1] = num_linha - 1

            # Valores a Receber (Liquidar)
            if ranges['areceber'][0] is None and "valores a liquidar" in val_lower: ranges['areceber'][0] = num_linha
            if ranges['areceber'][0] is not None and ranges['areceber'][1] is None and "total liquidação:" in val_lower: ranges['areceber'][1] = num_linha

            # Cotas e Patrimônio (CP)
            if ranges['cp'][0] is None and "patrimônio fechamento" in val_lower: ranges['cp'][0] = num_linha
            if ranges['cp'][0] is not None and ranges['cp'][1] is None and "rentabilidades" in val_lower: ranges['cp'][1] = num_linha

            # Rentabilidade
            if ranges['rentab'][0] is None and "rentabilidades" in val_lower: ranges['rentab'][0] = num_linha
            if ranges['rentab'][0] is not None and ranges['rentab'][1] is None and "(%) cdi" in val_lower: ranges['rentab'][1] = num_linha
            
            # Investidor (Passivo)
            if ranges['cotista'][0] is None and "investidor" in val_lower: ranges['cotista'][0] = num_linha
            if ranges['cotista'][0] is not None and ranges['cotista'][1] is None and "total" in val_lower and "subtotal" not in val_lower: ranges['cotista'][1] = num_linha

        # Processamento das seções encontradas
        mapa_secoes = {
            'rv': "renda variável | ações",
            'ltda': "Sociedade_Limitada",
            'rf': "Renda Fixa",
            'fundo': "Cotas_Fundos",
            'dc': "Direito_Creditorio",
            'caixa': "caixa",
            'areceber': "Valores_a_Liquidar",
            'cp': "Cotas_e_Patrimonio",
            'rentab': "Rentabilidade_(%)",
            'cotista': "passivo"
        }

        success = True
        for key, nome_secao in mapa_secoes.items():
            start, end = ranges[key]
            if start is not None and end is not None:
                print(f"  -> Extraindo {nome_secao}...")
                if not self._save_subset(df, nome_arquivo_original, caminho_pasta_destino, start, end, nome_secao):
                    success = False
        
        return success

    def _save_subset(self, df, nome_arquivo_original, pasta_destino, start, end, parte):
        try:
            os.makedirs(pasta_destino, exist_ok=True)
            df_subset = df.iloc[start : end + 1].copy()
            nome_carteira_limpo = self._extract_info_legacy(nome_arquivo_original, parte)
            
            full_path = os.path.join(pasta_destino, nome_carteira_limpo)
            df_subset.to_excel(full_path, index=False)
            print(f"     [OK] Salvo: {nome_carteira_limpo}")
            return True
        except Exception as e:
            print(f"     [ERRO] Falha ao salvar subset: {e}")
            return False

    def _extract_info_legacy(self, nome_arquivo_original, parte):
        # Lógica original de extração de nome e data
        nome_base_original, _ = os.path.splitext(nome_arquivo_original)
        parte_ajustado = (parte[:parte.find('|')].strip() if parte and '|' in parte else parte.strip()).replace(' ', '_')
        
        # Tento extrair data e nome (simplificado da lógica original)
        if " - " in nome_base_original:
            partes = nome_base_original.split(" - ")
            data_bruta = partes[0].strip()
            nome_carteira_bruto = partes[-1].strip()
        else:
             # Fallback
            data_bruta = nome_base_original[:5] if len(nome_base_original) >= 5 else "DATA_DESC"
            nome_carteira_bruto = nome_base_original[5:].strip() if len(nome_base_original) >= 5 else nome_base_original

        # Formatação Data
        data_carteira = "DATA_DESCONHECIDA"
        try:
            # Tenta formatos comuns
            for fmt in ['%d.%m', '%d/%m', '%d-%m']:
                try:
                    dt = datetime.strptime(data_bruta, fmt)
                    dt = dt.replace(year=2025) # Hardcoded conforme original
                    data_carteira = dt.strftime('%d-%m-%Y')
                    break
                except: continue
        except: pass

        nome_carteira = clean_filename(nome_carteira_bruto)
        return f"{nome_carteira}_{data_carteira}_{parte_ajustado}.xlsx"


# --- PARSER NOVO (EXCEL 'NOVO') ---
class NewExcelParser(ReportParser):
    """Parser para o novo formato CARTEIRA_DIARIA_..."""

    def can_parse(self, file_path: str) -> bool:
        name = os.path.basename(file_path).upper()
        # Identifica pelo padrão de nome com underscores e 'CARTEIRA_DIARIA'
        return "CARTEIRA_DIARIA_" in name and file_path.endswith(('.xlsx', '.xls'))

    def parse(self, file_path: str) -> bool:
        print(f"[NEW PARSER] Processando: {os.path.basename(file_path)}")
        try:
            df = pd.read_excel(file_path, header=None) # Header=None pois layout é posicional
            
            # Extrair metadados do nome do arquivo
            # Ex: CARTEIRA_DIARIA_55523261_08-12-2025-5d69...xlsx
            nome_arquivo = os.path.basename(file_path)
            try:
                # Tenta extrair data via regex
                import re
                match = re.search(r'(\d{2}-\d{2}-\d{4})', nome_arquivo)
                if match:
                    data_ref = match.group(1)
                else:
                    data_ref = datetime.now().strftime('%d-%m-%Y')
            except:
                data_ref = "DATA_DESCONHECIDA"

            # Nome do fundo (está na célula A1 do novo layout?)
            nome_fundo = str(df.iloc[0, 0]).strip() if not pd.isna(df.iloc[0,0]) else "FUNDO_DESCONHECIDO"
            nome_fundo = clean_filename(nome_fundo)

            # Mapeamento de Seções (Baseado na inspeção)
            # Layout observado: 
            # "Totais" -> Patrimônio
            # "Outros (Não Categorizados)"
            # "Caixa"
            # "Provisões"
            
            secoes_encontradas = {}
            current_section = None
            start_idx = None
            
            # Varredura simples
            for idx, row in df.iterrows():
                val = str(row[0]).strip() if not pd.isna(row[0]) else ""
                
                # Detecta início de seções
                if val in ["Totais", "Outros (Não Categorizados)", "Caixa", "Provisões"]:
                    # Fecha seção anterior se houver
                    if current_section and start_idx is not None:
                        # end_idx é a linha atual (não inclusa)
                        secoes_encontradas[current_section] = (start_idx, idx)
                    
                    current_section = val
                    start_idx = idx # Inclui o cabeçalho da seção? O script original geralmente corta cabeçalhos...
                                    # O Parser Legacy corta headers.
                                    # Se "Totais" é apenas um título, os dados começam em idx + something.
                                    # No Excel inspecionado:
                                    # Row 3: 'Totais', Row 4: 'Patrimônio', Row 5: 20153849.18
                                    # Vamos pegar o bloco inteiro por enquanto.
            
            # Fecha última seção
            if current_section and start_idx is not None:
                secoes_encontradas[current_section] = (start_idx, len(df))

            # Processar e Salvar cada seção detectada
            # Mapeamento de nomes e lógica específica de colunas
            
            caminho_destino = self.get_destination_folder()
            os.makedirs(caminho_destino, exist_ok=True)

            for sec_original, (s, e) in secoes_encontradas.items():
                # Slice raw do DataFrame
                df_subset = df.iloc[s:e].copy()
                
                # Identifica header real (geralmente primeira linha do slice)
                # Na inspeção: Row 9 (index relative 0 do slice Outros) é o header: Descrição, Nome...
                # Row 3 (index relative 0 do slice Totais) é título 'Totais'. Row 4 é header 'Patrimônio'...
                
                # Reset index para facilitar manipulação
                df_subset.reset_index(drop=True, inplace=True)
                
                # LÓGICA ESPECÍFICA POR SEÇÃO
                nome_final_sulfixo = clean_filename(sec_original)
                df_to_save = df_subset # Default
                
                if sec_original == "Outros (Não Categorizados)":
                    # É a RENDA VARIÁVEL / ATIVOS
                    nome_final_sulfixo = "renda_variável" # Match DE PARA
                    # Remover linhas de cabeçalho.
                    # Inspeção: Row 0='Outros...', Row 1='Descrição'(Header), Row 2='CARPO'(Data)
                    # Vamos procurar a linha que contem 'Quantidade' e 'Preço' para usar de header
                    header_row_idx = None
                    for r_idx, r_val in df_subset.iterrows():
                        row_vals = [str(x).lower() for x in r_val.values]
                        if 'descrição' in row_vals and 'quantidade' in row_vals:
                            header_row_idx = r_idx
                            break
                    
                    if header_row_idx is not None:
                        # Define header e dados
                        df_subset.columns = df_subset.iloc[header_row_idx]
                        df_data = df_subset.iloc[header_row_idx+1:].copy()
                        
                        # Seleciona colunas desejadas (pelo nome ou índice relativo)
                        # Inspeção mostrou: A(0)=Descrição, E(4)=Quantidade, F(5)=Preço, G(6)=Vl. Mercado
                        # Mas melhor usar nomes se possível
                        
                        cols_map = {}
                        for c in df_data.columns:
                            c_str = str(c).strip()
                            if c_str == 'Descrição': cols_map['Papel'] = c
                            elif c_str == 'Quantidade': cols_map['Quantidade'] = c
                            elif c_str == 'Preço': cols_map['Preço Médio'] = c
                            elif c_str.startswith('Vl. Mercado'): cols_map['Financeiro'] = c

                        if len(cols_map) >= 2:
                            new_df = pd.DataFrame()
                            for dest_col, src_col in cols_map.items():
                                new_df[dest_col] = df_data[src_col]
                            df_to_save = new_df

                elif sec_original == "Totais":
                    nome_final_sulfixo = "Patrimonio_Simples"
                    # Pode conter Cotas se tratarmos direito, mas vamos manter simples por enquanto
                    # Row 0='Totais', Row 1='Patrimônio' (Header)...
                    
                elif sec_original == "Caixa":
                    nome_final_sulfixo = "caixa"
                    # Row 0='Caixa', Row 1='Moeda' (Header)...
                    header_row_idx = None
                    for r_idx, r_val in df_subset.iterrows():
                        if 'Moeda' in [str(x) for x in r_val.values]:
                            header_row_idx = r_idx
                            break
                    
                    if header_row_idx is not None:
                        df_subset.columns = df_subset.iloc[header_row_idx]
                        df_data = df_subset.iloc[header_row_idx+1:].copy()
                        # Extrai Moeda e Saldo
                        cols_map = {}
                        for c in df_data.columns:
                            c_str = str(c).strip()
                            if c_str == 'Moeda': cols_map['Moeda'] = c
                            elif c_str == 'Saldo': cols_map['Valor'] = c
                        
                        if cols_map:
                            # Inicializa com o index correto
                            new_df = pd.DataFrame(index=df_data.index)
                            
                            if 'Moeda' in cols_map: new_df['Moeda'] = df_data[cols_map['Moeda']]
                            else: new_df['Moeda'] = 'BRL'
                            
                            new_df['Valor'] = df_data[cols_map['Valor']]
                            new_df['Descrição'] = "Saldo em Conta" # Broadcast seguro agora
                            
                            # Forçar ordem para alinhar com DB: [Data, Fundo, Descrição, Moeda_Origem, Valor]
                            df_to_save = new_df[['Descrição', 'Moeda', 'Valor']]

                            
                elif sec_original == "Provisões":
                    nome_final_sulfixo = "Valores_a_Liquidar" # Alias para CPR_Qore
                    # Columns: Descrição, Lançamento, Vencimento, Valor
                    
                    # Scan for header
                    header_row_idx = None
                    for r_idx, r_val in df_subset.iterrows():
                        row_strings = [str(x).strip() for x in r_val.values]
                        if 'Descrição' in row_strings and 'Valor' in row_strings:
                            header_row_idx = r_idx
                            break
                    
                    if header_row_idx is not None:
                        df_subset.columns = df_subset.iloc[header_row_idx]
                        df_data = df_subset.iloc[header_row_idx+1:].copy()
                        
                        # Mapear
                        cols_map = {}
                        for c in df_data.columns:
                            c_str = str(c).strip()
                            if 'Descrição' in c_str: cols_map['Descrição'] = c
                            elif 'Valor' in c_str: cols_map['Valor'] = c
                        
                        if cols_map:
                            new_df = pd.DataFrame(index=df_data.index)
                            new_df['Descrição'] = df_data[cols_map['Descrição']]
                            new_df['Lançamento'] = data_ref # Data do Arquivo
                            new_df['Vencimento'] = data_ref # Data do Arquivo (Fallback)
                            new_df['Valor'] = df_data[cols_map['Valor']]
                            
                            df_to_save = new_df[['Descrição', 'Lançamento', 'Vencimento', 'Valor']]

                # GERAÇÃO DO ARQUIVO FINAL
                nome_final = f"{nome_fundo}_{data_ref}_{nome_final_sulfixo}.xlsx"
                full_path = os.path.join(caminho_destino, nome_final)
                
                # Regra dos 4 Headers: O Upload Script espera ler header na linha 4.
                # Se meu df_to_save já tem header limpo (ex: Papel, Quantidade),
                # eu preciso escrever com header=True mas deslocado?
                # O XMLParser usou header=True (implícito no to_excel default) e startrow=3.
                # Isso escreve Header na linha 4 (0-based row 3). PERFEITO.
                
                with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
                    df_to_save.to_excel(writer, index=False, startrow=3)
                
                print(f"     [OK] Salvo: {nome_final} (Compatível c/ Upload)")

            return True

        except Exception as e:
            print(f"Erro no NewExcelParser: {e}")
            traceback.print_exc()
            return False


# --- PARSER XML (SEM-T.003 ISO 20022) ---
class Xml5Parser(ReportParser):
    """Parser para arquivos XML (ISO 20022 / SEMT.003)"""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith('.xml')

    def _strip_ns(self, tag):
        return tag.split('}', 1)[1] if '}' in tag else tag

    def _find_child(self, node, name):
        """Busca filho ignorando namespace"""
        for child in node:
            if self._strip_ns(child.tag) == name:
                return child
        return None
    
    def _findall_child(self, node, name):
        """Busca todos filhos ignorando namespace"""
        found = []
        for child in node:
            if self._strip_ns(child.tag) == name:
                found.append(child)
        return found

    def parse(self, file_path: str) -> bool:
        print(f"[XML PARSER] Processando: {os.path.basename(file_path)}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Navegar até o Report
            doc = self._find_child(root, 'Document')
            rpt = self._find_child(doc, 'SctiesBalAcctgRpt')
            if not rpt:
                print("     [ERRO] Nó 'SctiesBalAcctgRpt' não encontrado.")
                return False

            # --- 1. Extrair Patrimônio e Passivo (BalForAcct Principal) ---
            bal_main = self._find_child(rpt, 'BalForAcct')
            
            patrimonio = 0.0
            passivos_lista = []
            
            if bal_main:
                # Patrimônio Líquido (HldgVal - Payables, mas aqui pegamos o HldgVal que parece ser o Bruto ou Líquido, validaremos)
                # Na inspeção: HldgVal = 20M (Ativo Total?) e Payables = 32k.
                # Net Worth real = 20153849.18 (que estava em AcctBaseCcyTtlAmts no primeiro inspect)
                
                # Vamos pegar o TOTAL DO EXTRATO que é o mais confiavel para PL
                ttl_amts = self._find_child(rpt, 'AcctBaseCcyTtlAmts')
                if ttl_amts:
                    hldg_val_node = self._find_child(ttl_amts, 'TtlHldgsValOfStmt')
                    if hldg_val_node:
                        amt_node = self._find_child(hldg_val_node, 'Amt')
                        if amt_node is not None:
                            patrimonio = float(amt_node.text)

                # Extrair Passivos (Provisões/Payables) do BalBrkdwn
                for bal_brkdwn in self._findall_child(bal_main, 'BalBrkdwn'):
                    sub_bal_tp = self._find_child(bal_brkdwn, 'SubBalTp')
                    if sub_bal_tp:
                        prtry = self._find_child(sub_bal_tp, 'Prtry')
                        if prtry:
                            schem_id = self._find_child(prtry, 'Id')
                            if schem_id is not None and schem_id.text == 'PAYA':
                                # É um Payables (Passivo)
                                # Detalhes (Taxas, Auditoria, etc) estão em AddtlBalBrkdwnDtls
                                for add_dtl in self._findall_child(bal_brkdwn, 'AddtlBalBrkdwnDtls'):
                                    # Descrição
                                    desc = "Despesa"
                                    sbt = self._find_child(add_dtl, 'SubBalTp')
                                    if sbt:
                                        p = self._find_child(sbt, 'Prtry')
                                        if p:
                                            nm_node = self._find_child(p, 'SchmeNm')
                                            if nm_node is not None: desc = nm_node.text
                                    
                                    # Valor
                                    val = 0.0
                                    qty_wrap = self._find_child(add_dtl, 'Qty')
                                    if qty_wrap:
                                        qty_inner = self._find_child(qty_wrap, 'Qty')
                                        if qty_inner:
                                            face_amt = self._find_child(qty_inner, 'FaceAmt')
                                            if face_amt is not None: val = float(face_amt.text)
                                    
                                    passivos_lista.append({'Descrição': desc, 'Valor': val})

            # --- 2. Extrair Ativos (SubAcctDtls -> BalForSubAcct) ---
            sub_acct = self._find_child(rpt, 'SubAcctDtls')
            ativos_lista = []
            caixa_lista = []
            
            if sub_acct:
                for sub_bal in self._findall_child(sub_acct, 'BalForSubAcct'):
                    # Identificar o Ativo
                    fin_id = self._find_child(sub_bal, 'FinInstrmId')
                    ticker = "DESCONHECIDO"
                    asset_type = "OUTRO"
                    
                    if fin_id:
                        # Tenta achar ticker ou ID
                        for othr in self._findall_child(fin_id, 'OthrId'):
                            tid = self._find_child(othr, 'Id').text
                            ttp_node = self._find_child(othr, 'Tp')
                            if ttp_node:
                                prtry = self._find_child(ttp_node, 'Prtry')
                                if prtry and prtry.text:
                                    t_type = prtry.text
                                    if t_type == 'TICKER': ticker = tid
                                    if tid == 'CASH': asset_type = 'CAIXA'
                                    if tid == 'EQUI': asset_type = 'RV' # Equity

                    # Valor (Financeiro)
                    valor_fin = 0.0
                    acct_amts = self._find_child(sub_bal, 'AcctBaseCcyAmts')
                    if acct_amts:
                        hldg = self._find_child(acct_amts, 'HldgVal')
                        if hldg:
                            amt = self._find_child(hldg, 'Amt')
                            if amt is not None: valor_fin = float(amt.text)

                    # Quantidade
                    qtd = 0.0
                    aggt = self._find_child(sub_bal, 'AggtBal')
                    if aggt:
                        qty_wrap0 = self._find_child(aggt, 'Qty')
                        if qty_wrap0:
                            qty_wrap1 = self._find_child(qty_wrap0, 'Qty')
                            if qty_wrap1:
                                # Tenta Unit ou FaceAmt
                                unit = self._find_child(qty_wrap1, 'Unit')
                                face = self._find_child(qty_wrap1, 'FaceAmt')
                                if unit is not None: qtd = float(unit.text)
                                elif face is not None: qtd = float(face.text)
                    
                    # Preço
                    preco = 0.0
                    p_dtls = self._find_child(sub_bal, 'PricDtls')
                    if p_dtls:
                        val_node = self._find_child(p_dtls, 'Val')
                        if val_node:
                            p_amt = self._find_child(val_node, 'Amt')
                            if p_amt is not None: preco = float(p_amt.text)

                    if asset_type == 'CAIXA':
                        caixa_lista.append({'Descrição': 'Saldo em Conta', 'Valor': valor_fin})
                    else:
                        ativos_lista.append({'Ticker': ticker, 'Quantidade': qtd, 'Preço': preco, 'Valor': valor_fin, 'Tipo': asset_type})

            # --- 3. Salvar os Excel (Compatibilidade com Layout QORE) ---
            # O script de upload (qore_upload_access.py) ignora as primeiras 3 linhas 
            # e espera o cabeçalho na linha 4. Vamos simular isso.

            caminho_destino = self.get_destination_folder()
            # Nome base para arquivos (Ex: XML_555232_DATA...)
            cre_dt = self._find_child(self._find_child(root, 'AppHdr'), 'CreDt').text[:10] # YYYY-MM-DD
            data_fmt = datetime.strptime(cre_dt, '%Y-%m-%d').strftime('%d-%m-%Y')
            nome_fundo = "FUNDO_XML" 

            def salvar_compativel(df, nome_final):
                full_path = os.path.join(caminho_destino, nome_final)
                # Cria writer engine openpyxl ou xlsxwriter para pular linhas
                # Ou simplesmente escrevemos um dataframe com index que simule linhas vazias
                # Mais simples: salvar com startrow=3
                with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, startrow=3)
                print(f"     [OK] Salvo: {nome_final} (Compatível c/ Upload)")

            # Salvar Patrimônio
            # OBS: Cotas_Patrimonio_Qore espera colunas específicas (Cota, Qtd) que não temos.
            # Salvaremos como 'Patrimonio' genericamente para registro, mas sabendo que o Upload pode falhar
            # se for para a tabela Cotas_Patrimonio_Qore sem as colunas certas.
            if patrimonio > 0:
                df_pl = pd.DataFrame([{'Descrição': 'Patrimônio Líquido', 'Valor': patrimonio}])
                salvar_compativel(df_pl, f"{nome_fundo}_{data_fmt}_Patrimonio_Simples.xlsx")

            # Salvar Passivos (Provisões) -> CPR_Qore (Valores_a_Liquidar)
            if passivos_lista:
                df_pass = pd.DataFrame(passivos_lista)
                # Adicionar campos faltantes para tabela CPR
                if 'Descrição' not in df_pass.columns: df_pass['Descrição'] = 'Provisão'
                df_pass['Lançamento'] = data_fmt
                df_pass['Vencimento'] = data_fmt
                
                # Selecionar Colunas
                df_pass = df_pass[['Descrição', 'Lançamento', 'Vencimento', 'Valor']]
                
                salvar_compativel(df_pass, f"{nome_fundo}_{data_fmt}_Valores_a_Liquidar.xlsx")

            # Salvar Caixa
            # Mapeia para 'caixa' (DE PARA: Caixa_Qore)
            if caixa_lista:
                df_cx = pd.DataFrame(caixa_lista)
                # Garante que temos a coluna Moeda (que faltava)
                if 'Moeda' not in df_cx.columns: df_cx['Moeda'] = 'BRL'
                
                # Forçar ordem para alinhar com DB: [Data, Fundo, Descrição, Moeda_Origem, Valor]
                if 'Descrição' not in df_cx.columns: df_cx['Descrição'] = 'Saldo em Conta'
                
                df_cx = df_cx[['Descrição', 'Moeda', 'Valor']]
                salvar_compativel(df_cx, f"{nome_fundo}_{data_fmt}_caixa.xlsx")

            # Salvar Renda Variável (RV)
            # Mapeia para 'renda_variável' (DE PARA: Renda_Variável_Qore)
            rv_itens = [a for a in ativos_lista if a['Tipo'] == 'RV' or a['Tipo'] == 'OUTRO'] 
            if rv_itens:
                df_rv = pd.DataFrame(rv_itens)
                # Renomear para cabeçalhos que o upload possa reconhecer (chute educado baseado em padrão de mercado)
                # E garantir ordem COLUNAS: Papel | Quantidade | Preço | Financeiro
                df_rv.rename(columns={'Ticker': 'Papel', 'Valor': 'Financeiro', 'Tipo': 'Classificação', 'Preço': 'Preço Médio'}, inplace=True)
                
                # Selecionar e ordenar colunas para evitar corrupção por posição
                cols_order = ['Papel', 'Quantidade', 'Preço Médio', 'Financeiro']
                # Se alguma não existir (ex: qtd veio zerada), garante que a coluna exista
                for c in cols_order:
                    if c not in df_rv.columns: df_rv[c] = 0
                
                df_rv = df_rv[cols_order]

                # Nome exato do sufixo conforme DE PARA
                salvar_compativel(df_rv, f"{nome_fundo}_{data_fmt}_renda_variável.xlsx")

            return True

        except Exception as e:
            print(f"Erro no Xml5Parser: {e}")
            traceback.print_exc()
            return False

        except Exception as e:
            print(f"Erro no Xml5Parser: {e}")
            traceback.print_exc()
            return False


# --- MAIN ---
if __name__ == "__main__":
    #caminho_da_pasta = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\12. QORE_EXCEL'
    caminho_da_pasta = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\XML_QORE'
    # Adicionando o caminho "Novo" para teste se necessário, ou assumindo que usuário moveu inputs
    # Para compatibilidade, mantemos o caminho original como default, mas aceitamos argumento
    
    if len(sys.argv) > 1:
        caminho_da_pasta = sys.argv[1]

    print(f"V2: Iniciando processamento na pasta: {caminho_da_pasta}")
    
    if not os.path.exists(caminho_da_pasta):
        print(f"Pasta não encontrada: {caminho_da_pasta}")
        # Tenta a pasta de testes 'Dev' se a de produção não existir
        caminho_da_pasta = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo'
        print(f"Tentando caminho alternativo: {caminho_da_pasta}")

    if os.path.exists(caminho_da_pasta):
        # Definição da Estratégia
        parsers = [NewExcelParser(), LegacyExcelParser(), Xml5Parser()]
        
        files = os.listdir(caminho_da_pasta)
        for f in files:
            full_path = os.path.join(caminho_da_pasta, f)
            if os.path.isfile(full_path):
                
                parsed = False
                for parser in parsers:
                    if parser.can_parse(full_path):
                        print(f"--- Arquivo: {f} ---")
                        if parser.parse(full_path):
                            parsed = True
                        break # Encontrou um parser, processou, para de tentar outros
                
                if not parsed and f.endswith(('.xls', '.xlsx', '.xml')):
                    print(f"[AVISO] Nenhum parser compatível para: {f}")

    else:
        print("Caminho não encontrado. Verifique os diretórios.")
