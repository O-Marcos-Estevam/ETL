/**
 * API Module - Backend communication
 */

const API = {
    baseUrl: '',

    async fetch(endpoint) {
        try {
            const response = await fetch(this.baseUrl + endpoint);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Test connection
    async test() {
        return this.fetch('/api/test');
    },

    // Get database stats
    async getStats() {
        return this.fetch('/api/stats');
    },

    // Get schemas
    async getSchemas() {
        return this.fetch('/api/schemas');
    },

    // Get tables for schema
    async getTables(schema) {
        return this.fetch(`/api/tables/${schema}`);
    },

    // Get all tables
    async getAllTables() {
        return this.fetch('/api/all-tables');
    },

    // Get columns for table
    async getColumns(schema, table) {
        return this.fetch(`/api/columns/${schema}/${table}`);
    },

    // Get foreign keys
    async getForeignKeys() {
        return this.fetch('/api/foreign-keys');
    },

    // Get funds list
    async getFunds() {
        return this.fetch('/api/funds');
    },

    // Get NAV history for fund with optional period filter
    async getNav(fundId, period = '365') {
        return this.fetch(`/api/nav/${fundId}?period=${period}`);
    },

    // Get table preview (10 rows sample)
    async getPreview(schema, table) {
        return this.fetch(`/api/preview/${schema}/${table}`);
    },

    // Export table as CSV (returns URL)
    getExportUrl(schema, table) {
        return `${this.baseUrl}/api/export/${schema}/${table}`;
    },

    // Get funds comparison (PL of all active funds)
    async getFundsComparison() {
        return this.fetch('/api/funds-comparison');
    },

    // Get portfolio composition for a fund
    async getPortfolio(fundId) {
        return this.fetch(`/api/portfolio/${fundId}`);
    },

    // Get quota evolution with metrics
    async getQuotaEvolution(fundId, period = '365') {
        return this.fetch(`/api/quota-evolution/${fundId}?period=${period}`);
    }
};

// Format helpers
const Format = {
    number(n) {
        if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
        if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
        return n.toString();
    },

    currency(n) {
        return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
    },

    date(str) {
        if (!str) return '--';
        const d = new Date(str);
        return d.toLocaleDateString('pt-BR');
    }
};
