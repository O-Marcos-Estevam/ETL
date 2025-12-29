"""
================================================================================
CONFIGURADOR DE FUNDOS QORE - Interface Web
================================================================================

Interface web interativa para gerenciar quais fundos serão baixados do QORE.

EXECUÇÃO:
    python config_fundos_web.py

Acesse: http://localhost:5000
================================================================================
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

# Configuração
CONFIG_FILE = Path(r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\Config QORE\config_fundos_qore.json")
BD_PATH = r"C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\07. DEPARA\BD.xlsx"

app = Flask(__name__)

# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QORE - Configuração de Fundos</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }

        h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #888;
            font-size: 1.1em;
        }

        .stats-bar {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px 30px;
            text-align: center;
            min-width: 150px;
        }

        .stat-card .number {
            font-size: 2em;
            font-weight: bold;
            color: #00d4ff;
        }

        .stat-card.active .number { color: #4ade80; }
        .stat-card.inactive .number { color: #f87171; }

        .stat-card .label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            flex: 1;
            min-width: 250px;
            padding: 12px 20px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1em;
        }

        .search-box:focus {
            outline: none;
            border-color: #00d4ff;
        }

        .filter-btn {
            padding: 12px 24px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: transparent;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
        }

        .filter-btn:hover, .filter-btn.active {
            background: rgba(0,212,255,0.2);
            border-color: #00d4ff;
        }

        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            color: #fff;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,212,255,0.4);
        }

        .btn-success {
            background: linear-gradient(90deg, #4ade80, #22c55e);
            color: #fff;
        }

        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(74,222,128,0.4);
        }

        .btn-danger {
            background: linear-gradient(90deg, #f87171, #ef4444);
            color: #fff;
        }

        .funds-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .fund-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }

        .fund-card:hover {
            background: rgba(255,255,255,0.06);
            transform: translateY(-2px);
        }

        .fund-card.active {
            border-color: rgba(74,222,128,0.5);
        }

        .fund-card.inactive {
            border-color: rgba(248,113,113,0.3);
            opacity: 0.7;
        }

        .fund-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .fund-name {
            font-size: 1.2em;
            font-weight: 600;
            color: #fff;
        }

        .fund-type {
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }

        .fund-type.fidc { background: rgba(123,44,191,0.3); color: #c084fc; }
        .fund-type.fim { background: rgba(251,146,60,0.3); color: #fb923c; }

        .fund-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }

        .fund-info-item {
            font-size: 0.85em;
        }

        .fund-info-item .label {
            color: #666;
            display: block;
        }

        .fund-info-item .value {
            color: #aaa;
        }

        .toggle-switch {
            position: relative;
            width: 60px;
            height: 30px;
        }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(248,113,113,0.5);
            border-radius: 30px;
            transition: 0.3s;
        }

        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 24px;
            width: 24px;
            left: 3px;
            bottom: 3px;
            background: #fff;
            border-radius: 50%;
            transition: 0.3s;
        }

        input:checked + .toggle-slider {
            background: linear-gradient(90deg, #4ade80, #22c55e);
        }

        input:checked + .toggle-slider:before {
            transform: translateX(30px);
        }

        .fund-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }

        .status-badge.active {
            background: rgba(74,222,128,0.2);
            color: #4ade80;
        }

        .status-badge.inactive {
            background: rgba(248,113,113,0.2);
            color: #f87171;
        }

        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #1e293b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px 25px;
            display: flex;
            align-items: center;
            gap: 12px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        .toast.success { border-color: #4ade80; }
        .toast.error { border-color: #f87171; }

        .toast-icon {
            font-size: 1.5em;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .loading {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 2000;
        }

        .loading.show {
            display: flex;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255,255,255,0.1);
            border-top-color: #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .obs-input {
            width: 100%;
            padding: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 0.85em;
            margin-top: 10px;
        }

        .obs-input:focus {
            outline: none;
            border-color: #00d4ff;
        }

        @media (max-width: 768px) {
            .funds-grid {
                grid-template-columns: 1fr;
            }

            h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>QORE Config</h1>
            <p class="subtitle">Gerencie quais fundos serão baixados automaticamente</p>
        </header>

        <div class="stats-bar">
            <div class="stat-card">
                <div class="number" id="total-count">0</div>
                <div class="label">Total de Fundos</div>
            </div>
            <div class="stat-card active">
                <div class="number" id="active-count">0</div>
                <div class="label">Ativos</div>
            </div>
            <div class="stat-card inactive">
                <div class="number" id="inactive-count">0</div>
                <div class="label">Inativos</div>
            </div>
        </div>

        <div class="controls">
            <input type="text" class="search-box" id="search" placeholder="Buscar fundo..." oninput="filterFunds()">
            <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">Todos</button>
            <button class="filter-btn" data-filter="active" onclick="setFilter('active')">Ativos</button>
            <button class="filter-btn" data-filter="inactive" onclick="setFilter('inactive')">Inativos</button>
            <button class="filter-btn" data-filter="fip" onclick="setFilter('fip')">FIP</button>
            <button class="filter-btn" data-filter="fidc" onclick="setFilter('fidc')">FIDC</button>
            <button class="filter-btn" data-filter="fim" onclick="setFilter('fim')">FIM</button>
        </div>

        <div class="funds-grid" id="funds-grid">
            <!-- Fundos serão carregados aqui -->
        </div>

        <div class="action-buttons">
            <button class="btn btn-primary" onclick="saveConfig()">
                💾 Salvar Configuração
            </button>
            <button class="btn btn-success" onclick="activateAll()">
                ✅ Ativar Todos
            </button>
            <button class="btn btn-danger" onclick="deactivateAll()">
                ❌ Desativar Todos
            </button>
            <button class="btn btn-primary" onclick="runPipeline()">
                🚀 Executar Pipeline
            </button>
        </div>
    </div>

    <div class="toast" id="toast">
        <span class="toast-icon" id="toast-icon">✅</span>
        <span id="toast-message">Configuração salva!</span>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
    </div>

    <script>
        let fundos = [];
        let currentFilter = 'all';

        // Carrega fundos ao iniciar
        document.addEventListener('DOMContentLoaded', loadFunds);

        async function loadFunds() {
            showLoading(true);
            try {
                const response = await fetch('/api/fundos');
                fundos = await response.json();
                renderFunds();
                updateStats();
            } catch (error) {
                showToast('Erro ao carregar fundos', 'error');
            }
            showLoading(false);
        }

        function renderFunds() {
            const grid = document.getElementById('funds-grid');
            const searchTerm = document.getElementById('search').value.toLowerCase();

            const filtered = fundos.filter(f => {
                const matchesSearch = f.nome.toLowerCase().includes(searchTerm) ||
                                     f.cnpj.includes(searchTerm) ||
                                     f.sigla.toLowerCase().includes(searchTerm);

                if (currentFilter === 'all') return matchesSearch;
                if (currentFilter === 'active') return matchesSearch && f.ativo;
                if (currentFilter === 'inactive') return matchesSearch && !f.ativo;
                if (currentFilter === 'fip') return matchesSearch && f.tipo === 'FIP';
                if (currentFilter === 'fidc') return matchesSearch && f.tipo === 'FIDC';
                if (currentFilter === 'fim') return matchesSearch && f.tipo === 'FIM';
                return matchesSearch;
            });

            grid.innerHTML = filtered.map((f, idx) => `
                <div class="fund-card ${f.ativo ? 'active' : 'inactive'}" data-index="${fundos.indexOf(f)}">
                    <div class="fund-header">
                        <span class="fund-name">${f.nome}</span>
                        <span class="fund-type ${f.tipo.toLowerCase()}">${f.tipo}</span>
                    </div>
                    <div class="fund-info">
                        <div class="fund-info-item">
                            <span class="label">CNPJ</span>
                            <span class="value">${f.cnpj}</span>
                        </div>
                        <div class="fund-info-item">
                            <span class="label">Sigla Busca</span>
                            <span class="value">${f.sigla}</span>
                        </div>
                    </div>
                    <input type="text" class="obs-input" placeholder="Observação..."
                           value="${f.obs || ''}" onchange="updateObs(${fundos.indexOf(f)}, this.value)">
                    <div class="fund-footer">
                        <span class="status-badge ${f.ativo ? 'active' : 'inactive'}">
                            ${f.ativo ? 'ATIVO' : 'INATIVO'}
                        </span>
                        <label class="toggle-switch">
                            <input type="checkbox" ${f.ativo ? 'checked' : ''}
                                   onchange="toggleFund(${fundos.indexOf(f)})">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            `).join('');
        }

        function toggleFund(index) {
            fundos[index].ativo = !fundos[index].ativo;
            renderFunds();
            updateStats();
        }

        function updateObs(index, value) {
            fundos[index].obs = value;
        }

        function updateStats() {
            const total = fundos.length;
            const active = fundos.filter(f => f.ativo).length;
            const inactive = total - active;

            document.getElementById('total-count').textContent = total;
            document.getElementById('active-count').textContent = active;
            document.getElementById('inactive-count').textContent = inactive;
        }

        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === filter);
            });
            renderFunds();
        }

        function filterFunds() {
            renderFunds();
        }

        function activateAll() {
            fundos.forEach(f => f.ativo = true);
            renderFunds();
            updateStats();
            showToast('Todos os fundos ativados!', 'success');
        }

        function deactivateAll() {
            fundos.forEach(f => f.ativo = false);
            renderFunds();
            updateStats();
            showToast('Todos os fundos desativados!', 'success');
        }

        async function saveConfig() {
            showLoading(true);
            try {
                const response = await fetch('/api/fundos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(fundos)
                });
                const result = await response.json();
                if (result.success) {
                    showToast('Configuração salva com sucesso!', 'success');
                } else {
                    showToast('Erro ao salvar: ' + result.error, 'error');
                }
            } catch (error) {
                showToast('Erro ao salvar configuração', 'error');
            }
            showLoading(false);
        }

        async function runPipeline() {
            if (!confirm('Deseja executar o pipeline agora?\\n\\nIsso irá baixar os XMLs dos fundos ativos.')) {
                return;
            }

            showLoading(true);
            showToast('Iniciando pipeline... Aguarde.', 'success');

            try {
                const response = await fetch('/api/run-pipeline', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    showToast('Pipeline executado! Verifique o console.', 'success');
                } else {
                    showToast('Erro: ' + result.error, 'error');
                }
            } catch (error) {
                showToast('Erro ao executar pipeline', 'error');
            }
            showLoading(false);
        }

        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const icon = document.getElementById('toast-icon');
            const msg = document.getElementById('toast-message');

            toast.className = 'toast ' + type;
            icon.textContent = type === 'success' ? '✅' : '❌';
            msg.textContent = message;

            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        function showLoading(show) {
            document.getElementById('loading').classList.toggle('show', show);
        }
    </script>
</body>
</html>
"""

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/fundos', methods=['GET'])
def get_fundos():
    """Retorna lista de fundos."""
    fundos = load_config()
    return jsonify(fundos)


@app.route('/api/fundos', methods=['POST'])
def save_fundos():
    """Salva configuração de fundos."""
    try:
        fundos = request.json
        save_config(fundos)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/run-pipeline', methods=['POST'])
def run_pipeline():
    """Executa o pipeline."""
    try:
        script_path = Path(__file__).parent / "qore_xml_pipeline_v2.py"
        subprocess.Popen([sys.executable, str(script_path)],
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        return jsonify({"success": True, "message": "Pipeline iniciado"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =============================================================================
# CONFIG FUNCTIONS
# =============================================================================

def load_config():
    """Carrega configuração do JSON ou cria do BD.xlsx."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Cria config inicial do BD.xlsx
    return create_initial_config()


def save_config(fundos):
    """Salva configuração no JSON."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(fundos, f, ensure_ascii=False, indent=2)


def create_initial_config():
    """Cria configuração inicial a partir do BD.xlsx."""
    import pandas as pd

    try:
        df = pd.read_excel(BD_PATH, sheet_name='BD', engine='openpyxl')
        mask = df['SISTEMA'].astype(str).str.strip().str.upper() == 'QORE'
        fundos_qore = df[mask]

        fundos = []
        for _, row in fundos_qore.iterrows():
            apelido = str(row['Apelido']).strip()
            tipo = str(row['Tipo']).strip()
            cnpj = str(row['CNPJ']).strip()

            # Extrai sigla
            partes = apelido.split()
            if "BLOKO" in apelido.upper():
                sigla = "BLOKO URBANISMO" if "MULT" in apelido.upper() else "BLOKO FIM"
            elif len(partes) > 1:
                sigla = partes[1]
            else:
                sigla = apelido

            fundos.append({
                "nome": apelido,
                "sigla": sigla,
                "tipo": tipo,
                "cnpj": cnpj,
                "ativo": True,
                "obs": ""
            })

        save_config(fundos)
        return fundos

    except Exception as e:
        print(f"Erro ao criar config: {e}")
        return []


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("QORE - Configurador de Fundos")
    print("=" * 60)
    print()
    print("Acesse: http://localhost:5000")
    print()
    print("Pressione Ctrl+C para encerrar")
    print("=" * 60)

    import webbrowser
    webbrowser.open('http://localhost:5000')

    app.run(debug=False, port=5000)
