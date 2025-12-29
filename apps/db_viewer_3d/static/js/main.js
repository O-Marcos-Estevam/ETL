/**
 * Main Module - Three.js scene setup and orchestration
 */

// Global state
const App = {
    scene: null,
    camera: null,
    renderer: null,
    labelRenderer: null,
    controls: null,
    clock: null,
    raycaster: null,
    mouse: null,

    // Modules
    particles: null,
    grid: null,
    schemaViz: null,
    financialCharts: null,
    fundsComparison: null,
    quotaEvolution: null,
    portfolioChart: null,

    // State
    currentView: 'overview',
    hoveredObject: null,
    stats: null,
    funds: [],
    allTables: [],

    // Auto-refresh
    autoRefreshInterval: null,
    autoRefreshEnabled: false
};

// Initialize
async function init() {
    updateLoadingStatus('Setting up 3D environment...');

    // Create scene - Financial market theme
    App.scene = new THREE.Scene();
    App.scene.background = new THREE.Color(0x0d1117);
    App.scene.fog = new THREE.FogExp2(0x0d1117, 0.006);

    // Create camera
    App.camera = new THREE.PerspectiveCamera(
        60,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    App.camera.position.set(0, 30, 80);

    // Create renderer
    App.renderer = new THREE.WebGLRenderer({ antialias: true });
    App.renderer.setSize(window.innerWidth, window.innerHeight);
    App.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    document.getElementById('canvas-container').appendChild(App.renderer.domElement);

    // Create CSS2D renderer for labels
    App.labelRenderer = new THREE.CSS2DRenderer();
    App.labelRenderer.setSize(window.innerWidth, window.innerHeight);
    App.labelRenderer.domElement.style.position = 'absolute';
    App.labelRenderer.domElement.style.top = '0';
    App.labelRenderer.domElement.style.pointerEvents = 'none';
    document.getElementById('canvas-container').appendChild(App.labelRenderer.domElement);

    // Controls
    App.controls = new THREE.OrbitControls(App.camera, App.renderer.domElement);
    App.controls.enableDamping = true;
    App.controls.dampingFactor = 0.05;
    App.controls.maxDistance = 200;
    App.controls.minDistance = 20;

    // Raycaster for mouse interaction
    App.raycaster = new THREE.Raycaster();
    App.mouse = new THREE.Vector2();

    // Clock
    App.clock = new THREE.Clock();

    // Lighting
    setupLighting();

    // Initialize panels
    InfoPanel.init();
    FundSelector.init();
    TableSearch.init();

    updateLoadingStatus('Loading database...');

    // Load data and create visualizations
    try {
        // Test connection
        await API.test();

        // Load stats
        App.stats = await API.getStats();
        updateHeaderStats();

        // Initialize effects
        App.particles = new ParticleSystem(App.scene);
        App.grid = new NeonGrid(App.scene);

        updateLoadingStatus('Building 3D schema...');

        // Initialize schema visualization
        App.schemaViz = new SchemaVisualization(App.scene, App.camera);
        await App.schemaViz.load();

        // Load all tables for search
        App.allTables = await API.getAllTables();
        TableSearch.setTables(App.allTables);
        document.getElementById('stat-tables').textContent = App.allTables.length;

        // Initialize financial charts
        App.financialCharts = new FinancialCharts(App.scene);

        // Initialize new charts
        App.fundsComparison = new FundsComparisonChart(App.scene);
        App.quotaEvolution = new QuotaEvolutionChart(App.scene);
        App.portfolioChart = new PortfolioCompositionChart(App.scene);

        // Load funds for selector
        App.funds = await API.getFunds();
        FundSelector.loadFunds();
        FundSelector.setOnChange(async (fundId, period) => {
            const fund = App.funds.find(f => f.id === fundId);
            if (fund) {
                LoadingOverlay.show();
                try {
                    await App.financialCharts.loadFundData(fundId, period);
                    const navData = await API.getNav(fundId, period);
                    InfoPanel.showFund(fund, navData);
                } finally {
                    LoadingOverlay.hide();
                }
            }
        });

        // Setup table search callback
        TableSearch.setOnSelect(async (schema, table) => {
            LoadingOverlay.show();
            try {
                const columns = await API.getColumns(schema, table);
                InfoPanel.showTable(schema, table, columns);
                TableSearch.clear();
            } finally {
                LoadingOverlay.hide();
            }
        });

        // Setup event listeners
        setupEventListeners();

        // Hide loading screen
        hideLoadingScreen();

        // Start animation loop
        animate();

        // Show initial view
        switchView('overview');

    } catch (error) {
        console.error('Initialization failed:', error);
        updateLoadingStatus('Connection failed. Check console.');
    }
}

function setupLighting() {
    // Ambient light - financial theme (cooler, professional)
    const ambient = new THREE.AmbientLight(0x161b22, 0.6);
    App.scene.add(ambient);

    // Point lights - subtle, professional colors
    const pointLight1 = new THREE.PointLight(0x58a6ff, 0.7, 120);
    pointLight1.position.set(30, 30, 30);
    App.scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(0x3fb950, 0.5, 100);
    pointLight2.position.set(-30, 20, -30);
    App.scene.add(pointLight2);

    const pointLight3 = new THREE.PointLight(0xf0f6fc, 0.4, 100);
    pointLight3.position.set(0, -20, 40);
    App.scene.add(pointLight3);

    // Directional light for clean illumination
    const directional = new THREE.DirectionalLight(0xffffff, 0.5);
    directional.position.set(0, 50, 0);
    App.scene.add(directional);
}

function setupEventListeners() {
    // Window resize
    window.addEventListener('resize', onWindowResize);

    // Mouse move
    window.addEventListener('mousemove', onMouseMove);

    // Mouse click
    window.addEventListener('click', onMouseClick);

    // Navigation buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });

    // Control buttons
    document.getElementById('btn-reset-camera').addEventListener('click', resetCamera);

    document.getElementById('btn-toggle-particles').addEventListener('click', () => {
        const enabled = App.particles.toggle();
        document.getElementById('btn-toggle-particles').classList.toggle('active', enabled);
    });

    document.getElementById('btn-toggle-labels').addEventListener('click', () => {
        if (App.schemaViz) {
            const enabled = App.schemaViz.toggleLabels();
            document.getElementById('btn-toggle-labels').classList.toggle('active', enabled);
        }
    });

    // Refresh button
    const refreshBtn = document.getElementById('btn-refresh');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }
}

async function refreshData() {
    const refreshBtn = document.getElementById('btn-refresh');
    if (refreshBtn) {
        refreshBtn.classList.add('refreshing');
    }

    LoadingOverlay.show();

    try {
        // Reload stats
        App.stats = await API.getStats();
        updateHeaderStats();

        // Reload current view data
        if (App.currentView === 'financial' && FundSelector.currentFundId) {
            const fund = App.funds.find(f => f.id === FundSelector.currentFundId);
            if (fund) {
                await App.financialCharts.loadFundData(FundSelector.currentFundId, FundSelector.currentPeriod);
                const navData = await API.getNav(FundSelector.currentFundId, FundSelector.currentPeriod);
                InfoPanel.showFund(fund, navData);
            }
        } else if (App.currentView === 'overview') {
            InfoPanel.showStats(App.stats);
        }

        console.log('Data refreshed successfully');
    } catch (error) {
        console.error('Refresh failed:', error);
    } finally {
        LoadingOverlay.hide();
        if (refreshBtn) {
            refreshBtn.classList.remove('refreshing');
        }
    }
}

function switchView(view) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    App.currentView = view;

    // Hide all visualizations and clear charts to remove DOM labels
    if (App.schemaViz) App.schemaViz.hide();
    if (App.financialCharts) {
        App.financialCharts.clear();
        App.financialCharts.hide();
    }
    if (App.fundsComparison) {
        App.fundsComparison.clear();
        App.fundsComparison.hide();
    }
    if (App.quotaEvolution) {
        App.quotaEvolution.clear();
        App.quotaEvolution.hide();
    }
    if (App.portfolioChart) {
        App.portfolioChart.clear();
        App.portfolioChart.hide();
    }
    FundSelector.hide();
    TableSearch.hide();
    InfoPanel.hide();
    Tooltip.hide();

    // Show relevant visualization
    switch (view) {
        case 'overview':
            if (App.schemaViz) App.schemaViz.show();
            if (App.stats) InfoPanel.showStats(App.stats);
            resetCamera();
            break;

        case 'schemas':
            if (App.schemaViz) App.schemaViz.show();
            TableSearch.show();
            App.camera.position.set(0, 50, 60);
            break;

        case 'financial':
            if (App.financialCharts) App.financialCharts.show();
            FundSelector.show();
            App.camera.position.set(0, 30, 70);
            break;

        case 'comparison':
            // Load and show funds comparison chart
            LoadingOverlay.show();
            App.fundsComparison.loadData().then(() => {
                App.fundsComparison.show();
                LoadingOverlay.hide();
            });
            App.camera.position.set(0, 40, 90);
            break;

        case 'portfolio':
            // Show portfolio composition chart with fund selector
            if (App.portfolioChart) App.portfolioChart.show();
            FundSelector.show();
            // Set callback for portfolio view
            FundSelector.setOnChange(async (fundId, period) => {
                const fund = App.funds.find(f => f.id === fundId);
                if (fund) {
                    LoadingOverlay.show();
                    try {
                        const portfolioResponse = await App.portfolioChart.loadData(fundId);
                        // Show portfolio info panel
                        showPortfolioInfo(fund, null, portfolioResponse);
                    } finally {
                        LoadingOverlay.hide();
                    }
                }
            });
            App.camera.position.set(0, 35, 80);
            break;
    }

    // Reset fund selector callback for financial view
    if (view === 'financial') {
        FundSelector.setOnChange(async (fundId, period) => {
            const fund = App.funds.find(f => f.id === fundId);
            if (fund) {
                LoadingOverlay.show();
                try {
                    await App.financialCharts.loadFundData(fundId, period);
                    const navData = await API.getNav(fundId, period);
                    InfoPanel.showFund(fund, navData);
                } finally {
                    LoadingOverlay.hide();
                }
            }
        });
    }
}

// Helper function to show portfolio info
function showPortfolioInfo(fund, quotaResponse, portfolioResponse) {
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

    if (quotaResponse && quotaResponse.metrics) {
        const metrics = quotaResponse.metrics;
        const returnColor = metrics.total_return >= 0 ? 'green' : 'negative';
        html += `
            <div class="data-row">
                <span class="data-label">RETORNO</span>
                <span class="data-value ${returnColor}">${metrics.total_return.toFixed(2)}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">COTA ATUAL</span>
                <span class="data-value cyan">${metrics.last_quota.toFixed(6)}</span>
            </div>
        `;
    }

    if (portfolioResponse) {
        html += `
            <div class="data-row">
                <span class="data-label">TOTAL CARTEIRA</span>
                <span class="data-value green">${Format.currency(portfolioResponse.total)}</span>
            </div>
        `;
    }

    InfoPanel.show('PORTFOLIO', html);
}

function animate() {
    requestAnimationFrame(animate);

    const time = App.clock.getElapsedTime();

    // Update controls
    App.controls.update();

    // Update TWEEN
    if (TWEEN) TWEEN.update();

    // Update particles
    if (App.particles) App.particles.update(time);

    // Update schema visualization
    if (App.schemaViz && App.schemaViz.group.visible) {
        App.schemaViz.update(time);
    }

    // Update financial charts
    if (App.financialCharts && App.financialCharts.group.visible) {
        App.financialCharts.update(time);
    }

    // Update funds comparison chart
    if (App.fundsComparison && App.fundsComparison.group.visible) {
        App.fundsComparison.update(time);
    }

    // Update quota evolution chart
    if (App.quotaEvolution && App.quotaEvolution.group.visible) {
        App.quotaEvolution.update(time);
    }

    // Update portfolio composition chart
    if (App.portfolioChart && App.portfolioChart.group.visible) {
        App.portfolioChart.update(time);
    }

    // Render
    App.renderer.render(App.scene, App.camera);
    App.labelRenderer.render(App.scene, App.camera);
}

function onWindowResize() {
    App.camera.aspect = window.innerWidth / window.innerHeight;
    App.camera.updateProjectionMatrix();
    App.renderer.setSize(window.innerWidth, window.innerHeight);
    App.labelRenderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseMove(event) {
    App.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    App.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    // Raycast
    App.raycaster.setFromCamera(App.mouse, App.camera);

    // Check for hover
    let newHovered = null;

    if (App.currentView === 'schemas' && App.schemaViz) {
        newHovered = App.schemaViz.getNodeAtPosition(App.raycaster);
    } else if (App.currentView === 'financial' && App.financialCharts) {
        newHovered = App.financialCharts.getBarAtPosition(App.raycaster);
    } else if (App.currentView === 'comparison' && App.fundsComparison) {
        newHovered = App.fundsComparison.getBarAtPosition(App.raycaster);
    } else if (App.currentView === 'portfolio' && App.portfolioChart) {
        newHovered = App.portfolioChart.getBarAtPosition(App.raycaster);
    }

    // Handle hover state change
    if (newHovered !== App.hoveredObject) {
        // Unhighlight previous
        if (App.hoveredObject) {
            if (App.currentView === 'schemas') {
                App.schemaViz.highlightNode(App.hoveredObject, false);
            } else if (App.currentView === 'financial') {
                App.financialCharts.highlightBar(App.hoveredObject, false);
            } else if (App.currentView === 'comparison') {
                App.fundsComparison.highlightBar(App.hoveredObject, false);
            } else if (App.currentView === 'portfolio') {
                App.portfolioChart.highlightBar(App.hoveredObject, false);
            }
            Tooltip.hide();
        }

        // Highlight new
        if (newHovered) {
            if (App.currentView === 'schemas') {
                App.schemaViz.highlightNode(newHovered, true);
                if (newHovered.userData.type === 'table') {
                    Tooltip.show(event.clientX, event.clientY, Tooltip.tableContent(newHovered.userData));
                }
            } else if (App.currentView === 'financial') {
                App.financialCharts.highlightBar(newHovered, true);
                if (newHovered.userData.date) {
                    Tooltip.show(event.clientX, event.clientY, Tooltip.chartContent(newHovered.userData));
                }
            } else if (App.currentView === 'comparison') {
                App.fundsComparison.highlightBar(newHovered, true);
                Tooltip.show(event.clientX, event.clientY, Tooltip.fundComparisonContent(newHovered.userData));
            } else if (App.currentView === 'portfolio' && newHovered.userData.category) {
                App.portfolioChart.highlightBar(newHovered, true);
                Tooltip.show(event.clientX, event.clientY, Tooltip.portfolioContent(newHovered.userData));
            }
            document.body.style.cursor = 'pointer';
        } else {
            document.body.style.cursor = 'default';
        }

        App.hoveredObject = newHovered;
    } else if (newHovered) {
        // Update tooltip position while hovering same object
        if (App.currentView === 'schemas' && newHovered.userData.type === 'table') {
            Tooltip.show(event.clientX, event.clientY, Tooltip.tableContent(newHovered.userData));
        } else if (App.currentView === 'financial' && newHovered.userData.date) {
            Tooltip.show(event.clientX, event.clientY, Tooltip.chartContent(newHovered.userData));
        } else if (App.currentView === 'comparison') {
            Tooltip.show(event.clientX, event.clientY, Tooltip.fundComparisonContent(newHovered.userData));
        } else if (App.currentView === 'portfolio' && newHovered.userData.category) {
            Tooltip.show(event.clientX, event.clientY, Tooltip.portfolioContent(newHovered.userData));
        }
    }
}

async function onMouseClick(event) {
    if (!App.hoveredObject) return;

    const data = App.hoveredObject.userData;

    if (App.currentView === 'schemas' && data.type === 'table') {
        // Fetch columns and show info panel
        LoadingOverlay.show();
        try {
            const columns = await API.getColumns(data.schema, data.name);
            InfoPanel.showTable(data.schema, data.name, columns);
        } catch (error) {
            console.error('Failed to load columns:', error);
        } finally {
            LoadingOverlay.hide();
        }
    } else if (App.currentView === 'financial' && data.date) {
        // Show bar info
        InfoPanel.show('DATA POINT', `
            <div class="data-row">
                <span class="data-label">DATE</span>
                <span class="data-value">${Format.date(data.date)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">PL</span>
                <span class="data-value green">${Format.currency(data.pl)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">QUOTA</span>
                <span class="data-value cyan">${data.quota.toFixed(6)}</span>
            </div>
        `);
    } else if (App.currentView === 'portfolio' && data.category) {
        // Show detailed portfolio asset info
        let html = `
            <div class="data-row">
                <span class="data-label">CATEGORIA</span>
                <span class="data-value cyan">${data.category}</span>
            </div>
            <div class="data-row">
                <span class="data-label">VALOR TOTAL</span>
                <span class="data-value green">${Format.currency(data.value)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">% DO PL</span>
                <span class="data-value">${data.percentage}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">QTD ATIVOS</span>
                <span class="data-value">${data.asset_count}</span>
            </div>
        `;

        if (data.assets && data.assets.length > 0) {
            html += `<div class="section-divider"></div>`;
            html += `<div class="section-title">ATIVOS (Top ${Math.min(data.assets.length, 10)})</div>`;
            html += `<div class="asset-list">`;
            data.assets.forEach((asset, i) => {
                const pct = (asset.value / data.value * 100).toFixed(1);
                html += `
                    <div class="asset-item">
                        <div class="asset-header">
                            <span class="asset-num">${i + 1}.</span>
                            <span class="asset-name">${asset.name}</span>
                        </div>
                        <div class="asset-details">
                            ${asset.type ? `<span class="asset-type">${asset.type}</span>` : ''}
                            <span class="asset-value">${Format.currency(asset.value)}</span>
                            <span class="asset-pct">(${pct}%)</span>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        InfoPanel.show(data.category, html);
    }
}

function resetCamera() {
    new TWEEN.Tween(App.camera.position)
        .to({ x: 0, y: 30, z: 80 }, 1000)
        .easing(TWEEN.Easing.Quadratic.Out)
        .start();

    new TWEEN.Tween(App.controls.target)
        .to({ x: 0, y: 0, z: 0 }, 1000)
        .easing(TWEEN.Easing.Quadratic.Out)
        .start();
}

function updateHeaderStats() {
    if (!App.stats) return;

    document.getElementById('stat-funds').textContent = App.stats.total_funds;
    document.getElementById('stat-pl').textContent = Format.number(App.stats.total_pl);
}

function updateLoadingStatus(message) {
    document.getElementById('loading-status').textContent = message;
}

function hideLoadingScreen() {
    document.getElementById('loading-screen').classList.add('hidden');
}

// Start
document.addEventListener('DOMContentLoaded', init);
