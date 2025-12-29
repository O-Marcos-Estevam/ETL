/**
 * Charts Module - 3D financial charts
 */

class FinancialCharts {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.bars = [];
        this.ribbon = null;
        this.labels = [];
        this.labelElements = []; // Store DOM elements for cleanup

        this.scene.add(this.group);
        this.group.visible = false;
    }

    clear() {
        // Remove CSS2D label DOM elements
        this.labelElements.forEach(el => {
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
        this.labelElements = [];

        // Remove all children
        while (this.group.children.length > 0) {
            const child = this.group.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else {
                    child.material.dispose();
                }
            }
            this.group.remove(child);
        }
        this.bars = [];
        this.ribbon = null;
        this.labels = [];
    }

    async loadFundData(fundId, period = '365') {
        try {
            const data = await API.getNav(fundId, period);
            this.clear();

            if (data.length === 0) {
                console.warn('No NAV data for fund');
                return;
            }

            // Create 3D bar chart
            this.createBarChart(data);

            // Create 3D ribbon for PL trend
            this.createRibbon(data);

            // Create floor grid
            this.createFloor();

            // Create axis labels
            this.createAxisLabels(data);

        } catch (error) {
            console.error('Failed to load fund data:', error);
        }
    }

    createBarChart(data) {
        // Sample data (show every Nth bar to avoid clutter)
        const sampleRate = Math.max(1, Math.floor(data.length / 30));
        const sampledData = data.filter((_, i) => i % sampleRate === 0);

        // Find max PL for scaling
        const maxPL = Math.max(...sampledData.map(d => d.pl));
        const scaleFactor = 30 / maxPL;

        // Chart dimensions
        const chartWidth = 60;
        const barWidth = chartWidth / sampledData.length * 0.8;
        const startX = -chartWidth / 2;

        sampledData.forEach((d, i) => {
            const height = Math.max(0.1, d.pl * scaleFactor);
            const x = startX + (i / sampledData.length) * chartWidth;

            // Create bar
            const geometry = new THREE.BoxGeometry(barWidth, height, barWidth);
            geometry.translate(0, height / 2, 0);

            // Color gradient based on height - Financial theme (blue to green)
            const ratio = d.pl / maxPL;
            const color = new THREE.Color().lerpColors(
                new THREE.Color(0x58a6ff), // Blue
                new THREE.Color(0x3fb950), // Green
                ratio
            );

            const material = new THREE.MeshPhongMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.2,
                transparent: true,
                opacity: 0.8
            });

            const bar = new THREE.Mesh(geometry, material);
            bar.position.set(x, -20, 0);

            // Store data
            bar.userData = {
                date: d.date,
                pl: d.pl,
                quota: d.quota
            };

            this.group.add(bar);
            this.bars.push(bar);

            // Add wireframe
            const wireframe = new THREE.LineSegments(
                new THREE.EdgesGeometry(geometry),
                new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 })
            );
            bar.add(wireframe);
        });
    }

    createRibbon(data) {
        // Sample for ribbon
        const sampleRate = Math.max(1, Math.floor(data.length / 60));
        const sampledData = data.filter((_, i) => i % sampleRate === 0);

        if (sampledData.length < 2) return;

        // Find max for scaling
        const maxPL = Math.max(...sampledData.map(d => d.pl));
        const scaleFactor = 25 / maxPL;

        // Create ribbon shape
        const shape = new THREE.Shape();

        const chartWidth = 60;
        const startX = -chartWidth / 2;

        // Bottom line
        shape.moveTo(0, 0);

        // Top curve (PL values)
        sampledData.forEach((d, i) => {
            const x = (i / (sampledData.length - 1)) * chartWidth;
            const y = d.pl * scaleFactor;
            shape.lineTo(x, y);
        });

        // Close shape
        shape.lineTo(chartWidth, 0);
        shape.lineTo(0, 0);

        // Extrude
        const geometry = new THREE.ExtrudeGeometry(shape, {
            depth: 2,
            bevelEnabled: false
        });

        const material = new THREE.MeshPhongMaterial({
            color: 0x58a6ff,
            emissive: 0x58a6ff,
            emissiveIntensity: 0.15,
            transparent: true,
            opacity: 0.4,
            side: THREE.DoubleSide
        });

        this.ribbon = new THREE.Mesh(geometry, material);
        this.ribbon.position.set(startX, -20, 15);
        this.ribbon.rotation.x = -Math.PI / 2;

        this.group.add(this.ribbon);
    }

    createFloor() {
        // Grid floor - Financial theme
        const gridHelper = new THREE.GridHelper(80, 20, 0x30363d, 0x21262d);
        gridHelper.position.y = -20;
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.3;
        this.group.add(gridHelper);

        // Reflective floor
        const floorGeometry = new THREE.PlaneGeometry(80, 80);
        const floorMaterial = new THREE.MeshPhongMaterial({
            color: 0x0d1117,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -20.1;
        this.group.add(floor);
    }

    createAxisLabels(data) {
        if (data.length === 0) return;

        // Y-axis label (PL)
        const plLabel = document.createElement('div');
        plLabel.className = 'label-3d';
        plLabel.textContent = 'PL (R$)';
        plLabel.style.color = '#3fb950';

        const plLabelObj = new THREE.CSS2DObject(plLabel);
        plLabelObj.position.set(-35, 0, 0);
        this.group.add(plLabelObj);
        this.labels.push(plLabelObj);
        this.labelElements.push(plLabel); // Track DOM element

        // Start date
        const startLabel = document.createElement('div');
        startLabel.className = 'label-3d';
        startLabel.textContent = Format.date(data[0].date);

        const startLabelObj = new THREE.CSS2DObject(startLabel);
        startLabelObj.position.set(-30, -22, 0);
        this.group.add(startLabelObj);
        this.labels.push(startLabelObj);
        this.labelElements.push(startLabel); // Track DOM element

        // End date
        const endLabel = document.createElement('div');
        endLabel.className = 'label-3d';
        endLabel.textContent = Format.date(data[data.length - 1].date);

        const endLabelObj = new THREE.CSS2DObject(endLabel);
        endLabelObj.position.set(30, -22, 0);
        this.group.add(endLabelObj);
        this.labels.push(endLabelObj);
        this.labelElements.push(endLabel); // Track DOM element

        // Latest PL value
        const latestPL = data[data.length - 1].pl;
        const valueLabel = document.createElement('div');
        valueLabel.className = 'label-3d';
        valueLabel.textContent = Format.currency(latestPL);
        valueLabel.style.color = '#58a6ff';
        valueLabel.style.fontSize = '14px';

        const valueLabelObj = new THREE.CSS2DObject(valueLabel);
        valueLabelObj.position.set(0, 15, 0);
        this.group.add(valueLabelObj);
        this.labels.push(valueLabelObj);
        this.labelElements.push(valueLabel); // Track DOM element
    }

    update(time) {
        // Animate bars
        this.bars.forEach((bar, i) => {
            bar.rotation.y = Math.sin(time + i * 0.1) * 0.05;
        });

        // Animate ribbon
        if (this.ribbon) {
            this.ribbon.material.emissiveIntensity = 0.2 + Math.sin(time * 2) * 0.1;
        }
    }

    getBarAtPosition(raycaster) {
        const intersects = raycaster.intersectObjects(this.bars);
        return intersects.length > 0 ? intersects[0].object : null;
    }

    highlightBar(bar, highlight = true) {
        if (!bar) return;

        if (highlight) {
            bar.material.emissiveIntensity = 0.6;
            bar.scale.x = 1.2;
            bar.scale.z = 1.2;
        } else {
            bar.material.emissiveIntensity = 0.2;
            bar.scale.x = 1;
            bar.scale.z = 1;
        }
    }

    show() {
        this.group.visible = true;
    }

    hide() {
        this.group.visible = false;
    }

    dispose() {
        this.clear();
        this.scene.remove(this.group);
    }
}

/**
 * Funds Comparison Chart - 3D bar chart comparing PL of all funds
 */
class FundsComparisonChart {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.bars = [];
        this.labels = [];
        this.labelElements = []; // Store DOM elements for cleanup

        this.scene.add(this.group);
        this.group.visible = false;
    }

    clear() {
        // Remove CSS2D label DOM elements
        this.labelElements.forEach(el => {
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
        this.labelElements = [];

        while (this.group.children.length > 0) {
            const child = this.group.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else {
                    child.material.dispose();
                }
            }
            this.group.remove(child);
        }
        this.bars = [];
        this.labels = [];
    }

    async loadData() {
        try {
            const data = await API.getFundsComparison();
            this.clear();

            if (data.length === 0) {
                console.warn('No funds comparison data');
                return;
            }

            // Sort by PL descending
            data.sort((a, b) => b.pl - a.pl);

            // Create 3D bar chart
            this.createBarChart(data);
            this.createFloor();
            this.createTitle();

        } catch (error) {
            console.error('Failed to load funds comparison:', error);
        }
    }

    createBarChart(data) {
        const maxPL = Math.max(...data.map(d => d.pl));
        const scaleFactor = 40 / maxPL;

        const chartWidth = 70;
        const barWidth = Math.min(6, chartWidth / data.length * 0.7);
        const startX = -chartWidth / 2;
        const spacing = chartWidth / data.length;

        // Fund type colors
        const typeColors = {
            'FIC FIDC': 0x58a6ff,
            'FIDC': 0x3fb950,
            'FIM': 0xf0883e,
            'FIA': 0xbc8cff,
            'DEFAULT': 0x8b949e
        };

        data.forEach((fund, i) => {
            const height = Math.max(0.5, fund.pl * scaleFactor);
            const x = startX + i * spacing + spacing / 2;

            // Create bar
            const geometry = new THREE.BoxGeometry(barWidth, height, barWidth);
            geometry.translate(0, height / 2, 0);

            const color = new THREE.Color(typeColors[fund.type] || typeColors.DEFAULT);

            const material = new THREE.MeshPhongMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.2,
                transparent: true,
                opacity: 0.85
            });

            const bar = new THREE.Mesh(geometry, material);
            bar.position.set(x, -20, 0);

            // Store data for hover
            bar.userData = {
                id: fund.id,
                name: fund.name,
                type: fund.type,
                pl: fund.pl,
                date: fund.date
            };

            this.group.add(bar);
            this.bars.push(bar);

            // Add wireframe
            const wireframe = new THREE.LineSegments(
                new THREE.EdgesGeometry(geometry),
                new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 })
            );
            bar.add(wireframe);

            // Only show value labels for top funds to avoid clutter
            if (i < 10) {
                const valueLabel = document.createElement('div');
                valueLabel.className = 'label-3d';
                valueLabel.textContent = Format.number(fund.pl);
                valueLabel.style.color = '#' + color.getHexString();
                valueLabel.style.fontSize = '10px';

                const valueLabelObj = new THREE.CSS2DObject(valueLabel);
                valueLabelObj.position.set(x, -20 + height + 2, 0);
                this.group.add(valueLabelObj);
                this.labels.push(valueLabelObj);
                this.labelElements.push(valueLabel);
            }
        });
    }

    createFloor() {
        const gridHelper = new THREE.GridHelper(90, 20, 0x30363d, 0x21262d);
        gridHelper.position.y = -20;
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.3;
        this.group.add(gridHelper);

        const floorGeometry = new THREE.PlaneGeometry(90, 90);
        const floorMaterial = new THREE.MeshPhongMaterial({
            color: 0x0d1117,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -20.1;
        this.group.add(floor);
    }

    createTitle() {
        const titleLabel = document.createElement('div');
        titleLabel.className = 'label-3d';
        titleLabel.textContent = 'COMPARATIVO DE PL - FUNDOS';
        titleLabel.style.color = '#58a6ff';
        titleLabel.style.fontSize = '16px';
        titleLabel.style.fontWeight = 'bold';

        const titleLabelObj = new THREE.CSS2DObject(titleLabel);
        titleLabelObj.position.set(0, 30, 0);
        this.group.add(titleLabelObj);
        this.labels.push(titleLabelObj);
        this.labelElements.push(titleLabel); // Track DOM element
    }

    update(time) {
        this.bars.forEach((bar, i) => {
            bar.rotation.y = Math.sin(time * 0.5 + i * 0.2) * 0.03;
        });
    }

    getBarAtPosition(raycaster) {
        const intersects = raycaster.intersectObjects(this.bars);
        return intersects.length > 0 ? intersects[0].object : null;
    }

    highlightBar(bar, highlight = true) {
        if (!bar) return;
        if (highlight) {
            bar.material.emissiveIntensity = 0.6;
            bar.scale.x = 1.2;
            bar.scale.z = 1.2;
        } else {
            bar.material.emissiveIntensity = 0.2;
            bar.scale.x = 1;
            bar.scale.z = 1;
        }
    }

    show() { this.group.visible = true; }
    hide() { this.group.visible = false; }
    dispose() { this.clear(); this.scene.remove(this.group); }
}


/**
 * Quota Evolution Chart - 3D line chart showing quota evolution
 */
class QuotaEvolutionChart {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.line = null;
        this.points = [];
        this.labels = [];
        this.labelElements = []; // Store DOM elements for cleanup

        this.scene.add(this.group);
        this.group.visible = false;
    }

    clear() {
        // Remove CSS2D label DOM elements
        this.labelElements.forEach(el => {
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
        this.labelElements = [];

        while (this.group.children.length > 0) {
            const child = this.group.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else {
                    child.material.dispose();
                }
            }
            this.group.remove(child);
        }
        this.line = null;
        this.points = [];
        this.labels = [];
    }

    async loadData(fundId, period = '365') {
        try {
            const response = await API.getQuotaEvolution(fundId, period);
            this.clear();

            if (!response.data || response.data.length === 0) {
                console.warn('No quota data');
                return response;
            }

            this.createLineChart(response.data);
            this.createFloor();
            this.createMetrics(response.metrics);

            return response;
        } catch (error) {
            console.error('Failed to load quota evolution:', error);
            return null;
        }
    }

    createLineChart(data) {
        // Sample data for performance
        const sampleRate = Math.max(1, Math.floor(data.length / 100));
        const sampledData = data.filter((_, i) => i % sampleRate === 0);

        const minQuota = Math.min(...sampledData.map(d => d.quota));
        const maxQuota = Math.max(...sampledData.map(d => d.quota));
        const range = maxQuota - minQuota || 1;
        const scaleFactor = 30 / range;

        const chartWidth = 60;
        const startX = -chartWidth / 2;

        // Create points for the line
        const linePoints = [];

        sampledData.forEach((d, i) => {
            const x = startX + (i / (sampledData.length - 1)) * chartWidth;
            const y = (d.quota - minQuota) * scaleFactor - 15;
            const z = 0;

            linePoints.push(new THREE.Vector3(x, y, z));

            // Create point sphere for hover
            const sphereGeom = new THREE.SphereGeometry(0.5, 16, 16);
            const sphereMat = new THREE.MeshPhongMaterial({
                color: 0x58a6ff,
                emissive: 0x58a6ff,
                emissiveIntensity: 0.3
            });
            const sphere = new THREE.Mesh(sphereGeom, sphereMat);
            sphere.position.set(x, y, z);
            sphere.userData = {
                date: d.date,
                quota: d.quota
            };
            this.group.add(sphere);
            this.points.push(sphere);
        });

        // Create tube geometry for 3D line effect
        const curve = new THREE.CatmullRomCurve3(linePoints);
        const tubeGeometry = new THREE.TubeGeometry(curve, 100, 0.3, 8, false);
        const tubeMaterial = new THREE.MeshPhongMaterial({
            color: 0x3fb950,
            emissive: 0x3fb950,
            emissiveIntensity: 0.3,
            transparent: true,
            opacity: 0.9
        });
        this.line = new THREE.Mesh(tubeGeometry, tubeMaterial);
        this.group.add(this.line);

        // Add glow effect
        const glowGeometry = new THREE.TubeGeometry(curve, 100, 0.6, 8, false);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0x3fb950,
            transparent: true,
            opacity: 0.2
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        this.group.add(glow);

        // Date labels
        const startLabel = document.createElement('div');
        startLabel.className = 'label-3d';
        startLabel.textContent = Format.date(sampledData[0].date);
        const startObj = new THREE.CSS2DObject(startLabel);
        startObj.position.set(startX, -22, 0);
        this.group.add(startObj);
        this.labels.push(startObj);
        this.labelElements.push(startLabel); // Track DOM element

        const endLabel = document.createElement('div');
        endLabel.className = 'label-3d';
        endLabel.textContent = Format.date(sampledData[sampledData.length - 1].date);
        const endObj = new THREE.CSS2DObject(endLabel);
        endObj.position.set(-startX, -22, 0);
        this.group.add(endObj);
        this.labels.push(endObj);
        this.labelElements.push(endLabel); // Track DOM element
    }

    createFloor() {
        const gridHelper = new THREE.GridHelper(80, 20, 0x30363d, 0x21262d);
        gridHelper.position.y = -20;
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.3;
        this.group.add(gridHelper);

        const floorGeometry = new THREE.PlaneGeometry(80, 80);
        const floorMaterial = new THREE.MeshPhongMaterial({
            color: 0x0d1117,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -20.1;
        this.group.add(floor);
    }

    createMetrics(metrics) {
        if (!metrics) return;

        const titleLabel = document.createElement('div');
        titleLabel.className = 'label-3d';
        titleLabel.textContent = 'EVOLUÇÃO DA COTA';
        titleLabel.style.color = '#3fb950';
        titleLabel.style.fontSize = '16px';
        titleLabel.style.fontWeight = 'bold';

        const titleObj = new THREE.CSS2DObject(titleLabel);
        titleObj.position.set(0, 25, 0);
        this.group.add(titleObj);
        this.labels.push(titleObj);
        this.labelElements.push(titleLabel); // Track DOM element

        // Return metrics label
        const returnColor = metrics.total_return >= 0 ? '#3fb950' : '#f85149';
        const returnLabel = document.createElement('div');
        returnLabel.className = 'label-3d';
        returnLabel.innerHTML = `Retorno: <span style="color: ${returnColor}">${metrics.total_return.toFixed(2)}%</span>`;
        returnLabel.style.fontSize = '12px';

        const returnObj = new THREE.CSS2DObject(returnLabel);
        returnObj.position.set(-35, 15, 0);
        this.group.add(returnObj);
        this.labels.push(returnObj);
        this.labelElements.push(returnLabel); // Track DOM element
    }

    update(time) {
        if (this.line) {
            this.line.material.emissiveIntensity = 0.3 + Math.sin(time * 2) * 0.1;
        }
        this.points.forEach((p, i) => {
            p.material.emissiveIntensity = 0.3 + Math.sin(time * 3 + i * 0.1) * 0.2;
        });
    }

    getPointAtPosition(raycaster) {
        const intersects = raycaster.intersectObjects(this.points);
        return intersects.length > 0 ? intersects[0].object : null;
    }

    highlightPoint(point, highlight = true) {
        if (!point) return;
        if (highlight) {
            point.scale.setScalar(2);
            point.material.emissiveIntensity = 0.8;
        } else {
            point.scale.setScalar(1);
            point.material.emissiveIntensity = 0.3;
        }
    }

    show() { this.group.visible = true; }
    hide() { this.group.visible = false; }
    dispose() { this.clear(); this.scene.remove(this.group); }
}


/**
 * Portfolio Composition Chart - 3D bars showing portfolio breakdown
 */
class PortfolioCompositionChart {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.bars = [];
        this.labels = [];
        this.labelElements = []; // Store DOM elements for cleanup

        this.scene.add(this.group);
        this.group.visible = false;
    }

    clear() {
        // Remove CSS2D label DOM elements
        this.labelElements.forEach(el => {
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
        this.labelElements = [];

        while (this.group.children.length > 0) {
            const child = this.group.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else {
                    child.material.dispose();
                }
            }
            this.group.remove(child);
        }
        this.bars = [];
        this.labels = [];
    }

    async loadData(fundId) {
        try {
            const response = await API.getPortfolio(fundId);
            this.clear();

            if (!response.composition || response.composition.length === 0) {
                console.warn('No portfolio data');
                return response;
            }

            this.createBarChart(response.composition, response.total);
            this.createFloor();
            this.createTitle(response.fund_name);

            return response;
        } catch (error) {
            console.error('Failed to load portfolio:', error);
            return null;
        }
    }

    createBarChart(composition, total) {
        // Category colors
        const categoryColors = {
            'Caixa': 0x58a6ff,
            'Renda Fixa': 0x3fb950,
            'Renda Variável': 0xf0883e,
            'Dir. Creditórios': 0xbc8cff,
            'CPR': 0xf778ba
        };

        // Filter non-zero items and sort
        const items = composition.filter(c => c.value > 0).sort((a, b) => b.value - a.value);

        if (items.length === 0) return;

        const maxValue = Math.max(...items.map(c => c.value));
        const scaleFactor = 35 / maxValue;

        const chartWidth = 50;
        const barWidth = 8;
        const startX = -chartWidth / 2;
        const spacing = chartWidth / items.length;

        items.forEach((item, i) => {
            const height = Math.max(1, item.value * scaleFactor);
            const x = startX + i * spacing + spacing / 2;

            const geometry = new THREE.BoxGeometry(barWidth, height, barWidth);
            geometry.translate(0, height / 2, 0);

            const color = new THREE.Color(categoryColors[item.category] || 0x8b949e);

            const material = new THREE.MeshPhongMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.25,
                transparent: true,
                opacity: 0.85
            });

            const bar = new THREE.Mesh(geometry, material);
            bar.position.set(x, -20, 0);

            bar.userData = {
                category: item.category,
                value: item.value,
                percentage: (item.value / total * 100).toFixed(1),
                assets: item.assets || [],
                asset_count: item.asset_count || 0
            };

            this.group.add(bar);
            this.bars.push(bar);

            // Wireframe
            const wireframe = new THREE.LineSegments(
                new THREE.EdgesGeometry(geometry),
                new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.4 })
            );
            bar.add(wireframe);

            // Category label
            const catLabel = document.createElement('div');
            catLabel.className = 'label-3d';
            catLabel.textContent = item.category;
            catLabel.style.fontSize = '10px';
            catLabel.style.color = '#' + color.getHexString();

            const catObj = new THREE.CSS2DObject(catLabel);
            catObj.position.set(x, -23, 0);
            this.group.add(catObj);
            this.labels.push(catObj);
            this.labelElements.push(catLabel); // Track DOM element

            // Value label
            const valLabel = document.createElement('div');
            valLabel.className = 'label-3d';
            valLabel.textContent = Format.currency(item.value);
            valLabel.style.fontSize = '9px';

            const valObj = new THREE.CSS2DObject(valLabel);
            valObj.position.set(x, -20 + height + 2, 0);
            this.group.add(valObj);
            this.labels.push(valObj);
            this.labelElements.push(valLabel); // Track DOM element

            // Percentage label
            const pctLabel = document.createElement('div');
            pctLabel.className = 'label-3d';
            pctLabel.textContent = `${(item.value / total * 100).toFixed(1)}%`;
            pctLabel.style.fontSize = '11px';
            pctLabel.style.color = '#' + color.getHexString();
            pctLabel.style.fontWeight = 'bold';

            const pctObj = new THREE.CSS2DObject(pctLabel);
            pctObj.position.set(x, -20 + height / 2, 0);
            this.group.add(pctObj);
            this.labels.push(pctObj);
            this.labelElements.push(pctLabel); // Track DOM element
        });

        // Total label
        const totalLabel = document.createElement('div');
        totalLabel.className = 'label-3d';
        totalLabel.innerHTML = `Total: <span style="color: #3fb950">${Format.currency(total)}</span>`;
        totalLabel.style.fontSize = '14px';

        const totalObj = new THREE.CSS2DObject(totalLabel);
        totalObj.position.set(0, -26, 0);
        this.group.add(totalObj);
        this.labels.push(totalObj);
        this.labelElements.push(totalLabel); // Track DOM element
    }

    createFloor() {
        const gridHelper = new THREE.GridHelper(70, 20, 0x30363d, 0x21262d);
        gridHelper.position.y = -20;
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.3;
        this.group.add(gridHelper);

        const floorGeometry = new THREE.PlaneGeometry(70, 70);
        const floorMaterial = new THREE.MeshPhongMaterial({
            color: 0x0d1117,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -20.1;
        this.group.add(floor);
    }

    createTitle(fundName) {
        const titleLabel = document.createElement('div');
        titleLabel.className = 'label-3d';
        titleLabel.textContent = 'COMPOSIÇÃO DA CARTEIRA';
        titleLabel.style.color = '#bc8cff';
        titleLabel.style.fontSize = '16px';
        titleLabel.style.fontWeight = 'bold';

        const titleObj = new THREE.CSS2DObject(titleLabel);
        titleObj.position.set(0, 28, 0);
        this.group.add(titleObj);
        this.labels.push(titleObj);
        this.labelElements.push(titleLabel); // Track DOM element

        if (fundName) {
            const fundLabel = document.createElement('div');
            fundLabel.className = 'label-3d';
            fundLabel.textContent = fundName;
            fundLabel.style.fontSize = '12px';

            const fundObj = new THREE.CSS2DObject(fundLabel);
            fundObj.position.set(0, 24, 0);
            this.group.add(fundObj);
            this.labels.push(fundObj);
            this.labelElements.push(fundLabel); // Track DOM element
        }
    }

    update(time) {
        this.bars.forEach((bar, i) => {
            bar.rotation.y = Math.sin(time * 0.5 + i * 0.3) * 0.05;
            bar.material.emissiveIntensity = 0.25 + Math.sin(time * 2 + i) * 0.1;
        });
    }

    getBarAtPosition(raycaster) {
        const intersects = raycaster.intersectObjects(this.bars);
        return intersects.length > 0 ? intersects[0].object : null;
    }

    highlightBar(bar, highlight = true) {
        if (!bar) return;
        if (highlight) {
            bar.material.emissiveIntensity = 0.6;
            bar.scale.x = 1.15;
            bar.scale.z = 1.15;
        } else {
            bar.material.emissiveIntensity = 0.25;
            bar.scale.x = 1;
            bar.scale.z = 1;
        }
    }

    show() { this.group.visible = true; }
    hide() { this.group.visible = false; }
    dispose() { this.clear(); this.scene.remove(this.group); }
}
