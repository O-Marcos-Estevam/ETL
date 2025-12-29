/**
 * Panels Module - Info panel management with preview, export, search, and tooltips
 */

// Loading overlay helper
const LoadingOverlay = {
    el: null,

    init() {
        this.el = document.getElementById('loading-overlay');
    },

    show() {
        if (this.el) this.el.classList.remove('hidden');
    },

    hide() {
        if (this.el) this.el.classList.add('hidden');
    }
};

// Tooltip helper
const Tooltip = {
    el: null,

    init() {
        this.el = document.getElementById('tooltip');
    },

    show(x, y, content) {
        if (!this.el) return;
        this.el.innerHTML = content;
        this.el.style.left = `${x + 15}px`;
        this.el.style.top = `${y + 15}px`;
        this.el.classList.remove('hidden');
    },

    hide() {
        if (this.el) this.el.classList.add('hidden');
    },

    // Generate tooltip content for table
    tableContent(data) {
        return `
            <div class="tooltip-title">${data.schema}.${data.name}</div>
            <div class="tooltip-row">
                <span class="tooltip-label">Columns</span>
                <span class="tooltip-value">${data.columns || '--'}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Rows</span>
                <span class="tooltip-value">${Format.number(data.rows || 0)}</span>
            </div>
        `;
    },

    // Generate tooltip content for chart bar
    chartContent(data) {
        return `
            <div class="tooltip-title">${Format.date(data.date)}</div>
            <div class="tooltip-row">
                <span class="tooltip-label">PL</span>
                <span class="tooltip-value">${Format.currency(data.pl)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Quota</span>
                <span class="tooltip-value">${data.quota.toFixed(6)}</span>
            </div>
        `;
    },

    // Generate tooltip content for fund comparison bar
    fundComparisonContent(data) {
        return `
            <div class="tooltip-title">${data.name}</div>
            <div class="tooltip-row">
                <span class="tooltip-label">Type</span>
                <span class="tooltip-value">${data.type}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">PL</span>
                <span class="tooltip-value">${Format.currency(data.pl)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Data</span>
                <span class="tooltip-value">${Format.date(data.date)}</span>
            </div>
        `;
    },

    // Generate tooltip content for quota point
    quotaContent(data) {
        return `
            <div class="tooltip-title">${Format.date(data.date)}</div>
            <div class="tooltip-row">
                <span class="tooltip-label">Cota</span>
                <span class="tooltip-value">${data.quota.toFixed(6)}</span>
            </div>
        `;
    },

    // Generate tooltip content for portfolio bar
    portfolioContent(data) {
        let html = `
            <div class="tooltip-title">${data.category}</div>
            <div class="tooltip-row">
                <span class="tooltip-label">Valor Total</span>
                <span class="tooltip-value">${Format.currency(data.value)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">% do PL</span>
                <span class="tooltip-value">${data.percentage}%</span>
            </div>
        `;

        // Show asset count
        if (data.asset_count > 0) {
            html += `
                <div class="tooltip-row">
                    <span class="tooltip-label">Ativos</span>
                    <span class="tooltip-value">${data.asset_count}</span>
                </div>
            `;
        }

        // Show top assets (up to 5)
        if (data.assets && data.assets.length > 0) {
            html += `<div class="tooltip-divider"></div><div class="tooltip-subtitle">Top Ativos:</div>`;
            data.assets.slice(0, 5).forEach(asset => {
                const name = asset.name.length > 25 ? asset.name.substring(0, 22) + '...' : asset.name;
                html += `
                    <div class="tooltip-asset">
                        <span class="asset-name">${name}</span>
                        <span class="asset-value">${Format.currency(asset.value)}</span>
                    </div>
                `;
            });
            if (data.assets.length > 5) {
                html += `<div class="tooltip-more">+${data.assets.length - 5} mais...</div>`;
            }
        }

        return html;
    }
};

const InfoPanel = {
    panel: null,
    title: null,
    content: null,
    currentTable: null, // Store current table for actions

    init() {
        this.panel = document.getElementById('info-panel');
        this.title = document.getElementById('panel-title');
        this.content = document.getElementById('panel-content');

        document.getElementById('panel-close').addEventListener('click', () => {
            this.hide();
        });

        // Initialize loading and tooltip
        LoadingOverlay.init();
        Tooltip.init();
    },

    show(title, html) {
        this.title.textContent = title;
        this.content.innerHTML = html;
        this.panel.classList.remove('hidden');
    },

    hide() {
        this.panel.classList.add('hidden');
    },

    // Show table details with preview and export buttons
    showTable(schema, table, columns = []) {
        this.currentTable = { schema, table };
        const badge = `<span class="schema-badge ${schema}">${schema.toUpperCase()}</span>`;

        let html = `
            <div class="data-row">
                <span class="data-label">SCHEMA</span>
                <span class="data-value cyan">${badge}</span>
            </div>
            <div class="data-row">
                <span class="data-label">TABLE</span>
                <span class="data-value">${table}</span>
            </div>
            <div class="data-row">
                <span class="data-label">COLUMNS</span>
                <span class="data-value cyan">${columns.length}</span>
            </div>
        `;

        if (columns.length > 0) {
            html += `
                <div style="margin-top: 15px;">
                    <div class="data-label" style="margin-bottom: 10px;">STRUCTURE</div>
                    <div class="columns-list">
            `;

            columns.forEach(col => {
                html += `
                    <div class="column-item">
                        <span class="column-name">${col.name}</span>
                        <span class="column-type">${col.type}</span>
                    </div>
                `;
            });

            html += '</div></div>';
        }

        // Add action buttons
        html += `
            <div class="action-buttons">
                <button class="action-btn" onclick="InfoPanel.loadPreview('${schema}', '${table}')">
                    <span>👁</span> Preview
                </button>
                <a class="action-btn primary" href="${API.getExportUrl(schema, table)}" download>
                    <span>⬇</span> Export CSV
                </a>
            </div>
            <div id="preview-container"></div>
        `;

        this.show(table.toUpperCase(), html);
    },

    // Load and show preview data
    async loadPreview(schema, table) {
        const container = document.getElementById('preview-container');
        if (!container) return;

        container.innerHTML = '<div class="mini-loader" style="margin: 20px auto;"></div>';

        try {
            const data = await API.getPreview(schema, table);

            if (data.rows.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No data found</p>';
                return;
            }

            // Build preview table (show first 5 columns max for space)
            const displayCols = data.columns.slice(0, 5);
            let tableHtml = `
                <div class="preview-container">
                    <table class="preview-table">
                        <thead>
                            <tr>
                                ${displayCols.map(c => `<th>${c}</th>`).join('')}
                                ${data.columns.length > 5 ? '<th>...</th>' : ''}
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.rows.forEach(row => {
                tableHtml += '<tr>';
                displayCols.forEach(col => {
                    const val = row[col];
                    const display = val === null ? '<em>null</em>' : String(val).substring(0, 30);
                    tableHtml += `<td title="${val}">${display}</td>`;
                });
                if (data.columns.length > 5) {
                    tableHtml += '<td>...</td>';
                }
                tableHtml += '</tr>';
            });

            tableHtml += `
                        </tbody>
                    </table>
                </div>
                <p style="color: var(--text-muted); font-size: 11px; margin-top: 8px; text-align: center;">
                    Showing ${data.rows.length} of ${data.total} rows | ${data.columns.length} columns
                </p>
            `;

            container.innerHTML = tableHtml;

        } catch (error) {
            console.error('Failed to load preview:', error);
            container.innerHTML = '<p style="color: var(--negative); text-align: center; padding: 20px;">Failed to load preview</p>';
        }
    },

    // Show schema details
    showSchema(schema, tables = []) {
        let html = `
            <div class="data-row">
                <span class="data-label">SCHEMA</span>
                <span class="data-value cyan">${schema.toUpperCase()}</span>
            </div>
            <div class="data-row">
                <span class="data-label">TABLES</span>
                <span class="data-value green">${tables.length}</span>
            </div>
        `;

        if (tables.length > 0) {
            html += `
                <div style="margin-top: 15px;">
                    <div class="data-label" style="margin-bottom: 10px;">TABLES</div>
                    <div class="columns-list">
            `;

            tables.forEach(t => {
                html += `
                    <div class="column-item">
                        <span class="column-name">${t.name}</span>
                        <span class="column-type">${Format.number(t.row_count)} rows</span>
                    </div>
                `;
            });

            html += '</div></div>';
        }

        this.show(schema.toUpperCase() + ' SCHEMA', html);
    },

    // Show fund details
    showFund(fund, navData = []) {
        const latest = navData.length > 0 ? navData[navData.length - 1] : null;

        let html = `
            <div class="data-row">
                <span class="data-label">FUND</span>
                <span class="data-value">${fund.short_name}</span>
            </div>
            <div class="data-row">
                <span class="data-label">TYPE</span>
                <span class="data-value cyan">${fund.type}</span>
            </div>
        `;

        if (latest) {
            html += `
                <div class="data-row">
                    <span class="data-label">LATEST PL</span>
                    <span class="data-value green">${Format.currency(latest.pl)}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">QUOTA</span>
                    <span class="data-value magenta">${latest.quota.toFixed(6)}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">DATE</span>
                    <span class="data-value">${Format.date(latest.date)}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">DATA POINTS</span>
                    <span class="data-value">${navData.length}</span>
                </div>
            `;
        }

        this.show(fund.short_name, html);
    },

    // Show stats
    showStats(stats) {
        let html = `
            <div class="data-row">
                <span class="data-label">TOTAL FUNDS</span>
                <span class="data-value cyan">${stats.total_funds}</span>
            </div>
            <div class="data-row">
                <span class="data-label">TOTAL INVESTORS</span>
                <span class="data-value green">${Format.number(stats.total_investors)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">TOTAL PL</span>
                <span class="data-value magenta">${Format.currency(stats.total_pl)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">DATA RANGE</span>
                <span class="data-value">${Format.date(stats.date_start)} - ${Format.date(stats.date_end)}</span>
            </div>
        `;

        this.show('DATABASE STATS', html);
    }
};

// Fund selector panel with period filter
const FundSelector = {
    panel: null,
    dropdown: null,
    onChange: null,
    currentPeriod: '365',
    currentFundId: null,

    init() {
        this.panel = document.getElementById('fund-selector');
        this.dropdown = document.getElementById('fund-dropdown');

        this.dropdown.addEventListener('change', (e) => {
            if (this.onChange && e.target.value) {
                this.currentFundId = parseInt(e.target.value);
                this.onChange(this.currentFundId, this.currentPeriod);
            }
        });

        // Period buttons
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentPeriod = e.target.dataset.period;

                // Reload data if fund is selected
                if (this.currentFundId && this.onChange) {
                    this.onChange(this.currentFundId, this.currentPeriod);
                }
            });
        });
    },

    async loadFunds() {
        try {
            const funds = await API.getFunds();

            this.dropdown.innerHTML = '<option value="">Select a fund...</option>';

            funds.forEach(fund => {
                const option = document.createElement('option');
                option.value = fund.id;
                option.textContent = `${fund.short_name} (${fund.type})`;
                this.dropdown.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load funds:', error);
        }
    },

    show() {
        this.panel.classList.remove('hidden');
    },

    hide() {
        this.panel.classList.add('hidden');
    },

    setOnChange(callback) {
        this.onChange = callback;
    }
};

// Table Search Panel
const TableSearch = {
    panel: null,
    input: null,
    results: null,
    allTables: [],
    onSelect: null,

    init() {
        this.panel = document.getElementById('table-search');
        this.input = document.getElementById('search-input');
        this.results = document.getElementById('search-results');

        if (this.input) {
            this.input.addEventListener('input', (e) => {
                this.search(e.target.value);
            });
        }
    },

    setTables(tables) {
        this.allTables = tables;
    },

    search(query) {
        if (!this.results) return;

        if (!query || query.length < 2) {
            this.results.innerHTML = '';
            return;
        }

        const filtered = this.allTables.filter(t =>
            t.name.toLowerCase().includes(query.toLowerCase()) ||
            t.schema.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 10);

        if (filtered.length === 0) {
            this.results.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 16px;">No tables found</p>';
            return;
        }

        this.results.innerHTML = filtered.map(t => `
            <div class="search-result-item" data-schema="${t.schema}" data-table="${t.name}">
                <span class="search-result-name">${t.name}</span>
                <span class="search-result-schema schema-badge ${t.schema}">${t.schema}</span>
            </div>
        `).join('');

        // Add click handlers
        this.results.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const schema = item.dataset.schema;
                const table = item.dataset.table;
                if (this.onSelect) {
                    this.onSelect(schema, table);
                }
            });
        });
    },

    setOnSelect(callback) {
        this.onSelect = callback;
    },

    show() {
        if (this.panel) this.panel.classList.remove('hidden');
    },

    hide() {
        if (this.panel) this.panel.classList.add('hidden');
    },

    clear() {
        if (this.input) this.input.value = '';
        if (this.results) this.results.innerHTML = '';
    }
};
