/**
 * Schema Module - 3D database schema visualization
 */

class SchemaVisualization {
    constructor(scene, camera) {
        this.scene = scene;
        this.camera = camera;
        this.group = new THREE.Group();
        this.nodes = [];
        this.connections = [];
        this.labels = [];
        this.labelsVisible = true;

        // Schema colors - Financial Market Theme
        this.schemaColors = {
            'cad': 0x58a6ff,    // Blue
            'pos': 0x3fb950,    // Green
            'aux': 0xa371f7,    // Purple
            'stage': 0xd29922   // Yellow/Gold
        };

        // Schema positions (radial layout)
        this.schemaPositions = {
            'cad': { angle: 0, radius: 35 },
            'pos': { angle: Math.PI / 2, radius: 35 },
            'aux': { angle: Math.PI, radius: 35 },
            'stage': { angle: 3 * Math.PI / 2, radius: 35 }
        };

        this.scene.add(this.group);
    }

    async load() {
        try {
            // Fetch data
            const [tables, foreignKeys] = await Promise.all([
                API.getAllTables(),
                API.getForeignKeys()
            ]);

            this.createNodes(tables);
            this.createConnections(foreignKeys);

            return true;
        } catch (error) {
            console.error('Failed to load schema:', error);
            return false;
        }
    }

    createNodes(tables) {
        // Group tables by schema
        const bySchema = {};
        tables.forEach(t => {
            if (!bySchema[t.schema]) bySchema[t.schema] = [];
            bySchema[t.schema].push(t);
        });

        // Create nodes for each schema
        Object.keys(bySchema).forEach(schema => {
            const schemaTables = bySchema[schema];
            const schemaPos = this.schemaPositions[schema] || { angle: 0, radius: 35 };
            const color = this.schemaColors[schema] || 0xffffff;

            // Schema center position
            const centerX = Math.cos(schemaPos.angle) * schemaPos.radius;
            const centerZ = Math.sin(schemaPos.angle) * schemaPos.radius;

            // Create schema label (larger, in center)
            this.createSchemaLabel(schema, centerX, 15, centerZ, color);

            // Create table nodes around schema center
            schemaTables.forEach((table, idx) => {
                const angle = (idx / schemaTables.length) * Math.PI * 2;
                const tableRadius = 12 + Math.min(schemaTables.length, 10);

                const x = centerX + Math.cos(angle) * tableRadius;
                const z = centerZ + Math.sin(angle) * tableRadius;
                const y = Math.sin(idx * 0.5) * 3; // Slight vertical variation

                this.createTableNode(table, x, y, z, color);
            });
        });
    }

    createTableNode(table, x, y, z, color) {
        // Size based on row count (log scale)
        const size = 1 + Math.log10(Math.max(table.rows, 1)) * 0.5;

        // Cube geometry
        const geometry = new THREE.BoxGeometry(size, size, size);

        // Material with emissive glow
        const material = new THREE.MeshPhongMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.3,
            transparent: true,
            opacity: 0.8
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, z);

        // Store table data
        mesh.userData = {
            type: 'table',
            schema: table.schema,
            name: table.name,
            fullName: table.full_name,
            columns: table.columns,
            rows: table.rows
        };

        // Wireframe overlay
        const wireframe = new THREE.LineSegments(
            new THREE.EdgesGeometry(geometry),
            new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.5 })
        );
        mesh.add(wireframe);

        this.group.add(mesh);
        this.nodes.push(mesh);

        // Create label
        this.createTableLabel(table.name, x, y + size + 0.5, z);

        return mesh;
    }

    createSchemaLabel(text, x, y, z, color) {
        const div = document.createElement('div');
        div.className = 'label-3d schema';
        div.textContent = text.toUpperCase();
        div.style.borderColor = '#' + color.toString(16).padStart(6, '0');
        div.style.color = '#' + color.toString(16).padStart(6, '0');

        const label = new THREE.CSS2DObject(div);
        label.position.set(x, y, z);

        this.group.add(label);
        this.labels.push(label);
    }

    createTableLabel(text, x, y, z) {
        const div = document.createElement('div');
        div.className = 'label-3d table';
        div.textContent = text;

        const label = new THREE.CSS2DObject(div);
        label.position.set(x, y, z);

        this.group.add(label);
        this.labels.push(label);
    }

    createConnections(foreignKeys) {
        foreignKeys.forEach(fk => {
            const sourceNode = this.findNode(fk.source_schema, fk.source_table);
            const targetNode = this.findNode(fk.target_schema, fk.target_table);

            if (sourceNode && targetNode) {
                const line = new EnergyLine(
                    this.group,
                    sourceNode.position,
                    targetNode.position,
                    0x8b949e // Subtle gray for FK lines
                );
                this.connections.push(line);
            }
        });
    }

    findNode(schema, table) {
        return this.nodes.find(n =>
            n.userData.schema === schema && n.userData.name === table
        );
    }

    update(time) {
        // Animate nodes
        this.nodes.forEach((node, i) => {
            // Gentle floating
            node.position.y += Math.sin(time * 2 + i * 0.5) * 0.002;

            // Slow rotation
            node.rotation.y = time * 0.2;
            node.rotation.x = Math.sin(time + i) * 0.1;
        });

        // Update connection particles
        this.connections.forEach(conn => conn.update(time));
    }

    toggleLabels() {
        this.labelsVisible = !this.labelsVisible;
        this.labels.forEach(label => {
            label.visible = this.labelsVisible;
        });
        return this.labelsVisible;
    }

    // Get node at mouse position
    getNodeAtPosition(raycaster) {
        const intersects = raycaster.intersectObjects(this.nodes);
        return intersects.length > 0 ? intersects[0].object : null;
    }

    // Highlight node
    highlightNode(node, highlight = true) {
        if (!node) return;

        if (highlight) {
            node.material.emissiveIntensity = 0.8;
            node.scale.setScalar(1.3);
        } else {
            node.material.emissiveIntensity = 0.3;
            node.scale.setScalar(1);
        }
    }

    show() {
        this.group.visible = true;
    }

    hide() {
        this.group.visible = false;
    }

    dispose() {
        this.nodes.forEach(node => {
            node.geometry.dispose();
            node.material.dispose();
        });

        this.connections.forEach(conn => conn.dispose());

        this.scene.remove(this.group);
    }
}
