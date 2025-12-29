/**
 * Effects Module - Particles and visual effects
 */

class ParticleSystem {
    constructor(scene, count = 2000) {
        this.scene = scene;
        this.count = count;
        this.particles = null;
        this.enabled = true;

        this.init();
    }

    init() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.count * 3);
        const colors = new Float32Array(this.count * 3);
        const sizes = new Float32Array(this.count);

        // Financial theme - subtle, professional colors
        const colorPalette = [
            new THREE.Color(0x58a6ff), // Blue
            new THREE.Color(0x3fb950), // Green
            new THREE.Color(0x8b949e), // Gray
        ];

        for (let i = 0; i < this.count; i++) {
            // Position - spread in a large sphere
            const radius = 50 + Math.random() * 150;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);

            positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = radius * Math.cos(phi);

            // Color
            const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;

            // Size
            sizes[i] = Math.random() * 2 + 0.5;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 1,
            vertexColors: true,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }

    update(time) {
        if (!this.enabled || !this.particles) return;

        // Slow rotation
        this.particles.rotation.y = time * 0.02;
        this.particles.rotation.x = Math.sin(time * 0.01) * 0.1;

        // Pulse size
        const positions = this.particles.geometry.attributes.position.array;
        for (let i = 0; i < this.count; i++) {
            const idx = i * 3 + 1; // Y position
            positions[idx] += Math.sin(time * 2 + i) * 0.01;
        }
        this.particles.geometry.attributes.position.needsUpdate = true;
    }

    toggle() {
        this.enabled = !this.enabled;
        if (this.particles) {
            this.particles.visible = this.enabled;
        }
        return this.enabled;
    }

    dispose() {
        if (this.particles) {
            this.particles.geometry.dispose();
            this.particles.material.dispose();
            this.scene.remove(this.particles);
        }
    }
}

// Grid helper - Financial theme
class NeonGrid {
    constructor(scene) {
        this.scene = scene;
        this.grid = null;
        this.init();
    }

    init() {
        // Create custom grid - subtle, professional
        const size = 200;
        const divisions = 40;
        const color1 = 0x30363d;
        const color2 = 0x21262d;

        this.grid = new THREE.GridHelper(size, divisions, color1, color2);
        this.grid.material.transparent = true;
        this.grid.material.opacity = 0.2;
        this.grid.position.y = -30;

        this.scene.add(this.grid);
    }

    dispose() {
        if (this.grid) {
            this.grid.geometry.dispose();
            this.grid.material.dispose();
            this.scene.remove(this.grid);
        }
    }
}

// Glow effect for objects - subtle
function addGlow(mesh, color = 0x58a6ff, intensity = 0.3) {
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: intensity,
        side: THREE.BackSide
    });

    const glowMesh = new THREE.Mesh(mesh.geometry.clone(), glowMaterial);
    glowMesh.scale.multiplyScalar(1.08);
    mesh.add(glowMesh);

    return glowMesh;
}

// Animated connection line between two points
class EnergyLine {
    constructor(scene, start, end, color = 0x8b949e) {
        this.scene = scene;
        this.start = start;
        this.end = end;
        this.color = color;
        this.line = null;
        this.particles = null;

        this.init();
    }

    init() {
        // Main line
        const points = [this.start, this.end];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
            color: this.color,
            transparent: true,
            opacity: 0.4
        });

        this.line = new THREE.Line(geometry, material);
        this.scene.add(this.line);

        // Flowing particles on line
        this.createFlowingParticles();
    }

    createFlowingParticles() {
        const particleCount = 5;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            color: this.color,
            size: 2,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });

        this.particles = new THREE.Points(geometry, material);
        this.particles.userData.offsets = [];

        for (let i = 0; i < particleCount; i++) {
            this.particles.userData.offsets.push(Math.random());
        }

        this.scene.add(this.particles);
    }

    update(time) {
        if (!this.particles) return;

        const positions = this.particles.geometry.attributes.position.array;
        const offsets = this.particles.userData.offsets;

        for (let i = 0; i < offsets.length; i++) {
            let t = (offsets[i] + time * 0.5) % 1;

            positions[i * 3] = this.start.x + (this.end.x - this.start.x) * t;
            positions[i * 3 + 1] = this.start.y + (this.end.y - this.start.y) * t;
            positions[i * 3 + 2] = this.start.z + (this.end.z - this.start.z) * t;
        }

        this.particles.geometry.attributes.position.needsUpdate = true;
    }

    dispose() {
        if (this.line) {
            this.line.geometry.dispose();
            this.line.material.dispose();
            this.scene.remove(this.line);
        }
        if (this.particles) {
            this.particles.geometry.dispose();
            this.particles.material.dispose();
            this.scene.remove(this.particles);
        }
    }
}
