/* ============================================================
   CONSOLEX — three-scene.js
   Immersive 3D hero scene built with Three.js
   - Procedural PS5 console model
   - Floating game discs
   - Particle field
   - Dynamic cyan / purple / orange lighting
   - UnrealBloom post-processing
   - Mouse-reactive camera parallax
   ============================================================ */

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

/* ── Constants ───────────────────────────────────────────── */
const CYAN    = 0x00f0ff;
const PURPLE  = 0xbf00ff;
const ORANGE  = 0xff6b00;
const DARK    = 0x080810;

let scene, camera, renderer, composer;
let ps5Group, discs = [], particleSystem;
let mouse = { x: 0, y: 0, tx: 0, ty: 0 };
let clock;
let animationId;
let isMobile = window.innerWidth < 768;

/* ── Bootstrap ───────────────────────────────────────────── */
export function initScene(canvas) {
    clock = new THREE.Clock();

    /* Scene */
    scene = new THREE.Scene();
    scene.background = new THREE.Color(DARK);
    scene.fog = new THREE.FogExp2(DARK, 0.018);

    /* Camera */
    camera = new THREE.PerspectiveCamera(
        50,
        canvas.clientWidth / canvas.clientHeight,
        0.1,
        200
    );
    camera.position.set(0, 1.5, isMobile ? 10 : 7);

    /* Renderer */
    renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: !isMobile,
        alpha: true,
        powerPreference: 'high-performance',
    });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    /* Post-processing — bloom */
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    const bloom = new UnrealBloomPass(
        new THREE.Vector2(canvas.clientWidth, canvas.clientHeight),
        0.8,   /* strength */
        0.4,   /* radius */
        0.6    /* threshold */
    );
    composer.addPass(bloom);

    /* Build the scene */
    createLights();
    createPS5();
    createGameDiscs();
    createParticleField();
    createGridFloor();

    /* Events */
    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('resize', () => onResize(canvas), { passive: true });
    canvas.addEventListener('pointermove', onPointerMove, { passive: true });

    /* Start */
    animate();
}

/* ── Lights ──────────────────────────────────────────────── */
function createLights() {
    /* Ambient */
    scene.add(new THREE.AmbientLight(0x222233, 0.4));

    /* Key light — cyan, from top-left */
    const key = new THREE.PointLight(CYAN, 2.5, 30);
    key.position.set(-4, 5, 4);
    scene.add(key);

    /* Fill — purple, from right */
    const fill = new THREE.PointLight(PURPLE, 1.8, 25);
    fill.position.set(5, 2, -2);
    scene.add(fill);

    /* Rim — orange, from behind */
    const rim = new THREE.PointLight(ORANGE, 1.2, 20);
    rim.position.set(0, -1, -5);
    scene.add(rim);

    /* Spot on PS5 */
    const spot = new THREE.SpotLight(CYAN, 1.5, 20, Math.PI / 6, 0.6);
    spot.position.set(0, 8, 5);
    spot.target.position.set(0, 0, 0);
    scene.add(spot);
    scene.add(spot.target);
}

/* ── PS5 Console (procedural geometry) ───────────────────── */
function createPS5() {
    ps5Group = new THREE.Group();

    const bodyMat = new THREE.MeshStandardMaterial({
        color: 0x111118,
        roughness: 0.25,
        metalness: 0.8,
    });
    const whiteMat = new THREE.MeshStandardMaterial({
        color: 0xd8d8e0,
        roughness: 0.3,
        metalness: 0.5,
    });
    const blackMat = new THREE.MeshStandardMaterial({
        color: 0x050508,
        roughness: 0.1,
        metalness: 0.9,
    });
    const glowMat = new THREE.MeshStandardMaterial({
        color: CYAN,
        emissive: CYAN,
        emissiveIntensity: 2.5,
        roughness: 0,
        metalness: 1,
    });

    /* Main body — tall curved slab */
    const bodyGeo = new THREE.BoxGeometry(1.4, 3.2, 0.5, 1, 1, 1);
    /* Slightly taper the top vertices for the PS5 curve */
    const pos = bodyGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
        const y = pos.getY(i);
        const norm = (y + 1.6) / 3.2; /* 0 at bottom, 1 at top */
        const taper = 1 - norm * 0.06;
        pos.setX(i, pos.getX(i) * taper);
        /* Add the subtle PS5 curve */
        const zOff = Math.sin(norm * Math.PI) * 0.08;
        pos.setZ(i, pos.getZ(i) + zOff);
    }
    bodyGeo.computeVertexNormals();
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    ps5Group.add(body);

    /* White side panels (the iconic PS5 wings) */
    const wingGeo = new THREE.BoxGeometry(0.06, 3.1, 0.48);
    const wingL = new THREE.Mesh(wingGeo, whiteMat);
    wingL.position.set(-0.73, 0, 0);
    ps5Group.add(wingL);

    const wingR = new THREE.Mesh(wingGeo, whiteMat);
    wingR.position.set(0.73, 0, 0);
    ps5Group.add(wingR);

    /* Black center strip */
    const stripGeo = new THREE.BoxGeometry(0.6, 3.15, 0.52);
    const strip = new THREE.Mesh(stripGeo, blackMat);
    strip.position.set(0, 0, 0);
    ps5Group.add(strip);

    /* Blue LED line */
    const ledGeo = new THREE.BoxGeometry(0.02, 2.8, 0.02);
    const led = new THREE.Mesh(ledGeo, glowMat);
    led.position.set(0, 0.1, 0.26);
    ps5Group.add(led);

    /* Top vent grille lines */
    for (let i = 0; i < 5; i++) {
        const ventGeo = new THREE.BoxGeometry(1.2, 0.008, 0.02);
        const vent = new THREE.Mesh(ventGeo, blackMat);
        vent.position.set(0, 1.45 + i * 0.04, 0.22);
        ps5Group.add(vent);
    }

    /* USB port on front */
    const usbGeo = new THREE.BoxGeometry(0.12, 0.05, 0.02);
    const usb = new THREE.Mesh(usbGeo, blackMat);
    usb.position.set(0, -0.8, 0.26);
    ps5Group.add(usb);

    /* Position the whole group */
    ps5Group.position.set(isMobile ? 0 : 2.5, -0.3, 0);
    ps5Group.rotation.y = -0.3;
    ps5Group.rotation.x = 0.05;
    scene.add(ps5Group);
}

/* ── Floating game discs ─────────────────────────────────── */
function createGameDiscs() {
    const discCount = isMobile ? 4 : 7;
    const discColors = [CYAN, PURPLE, ORANGE, 0xff4444, 0x44ff44, 0xffff44, 0x4488ff];

    for (let i = 0; i < discCount; i++) {
        const group = new THREE.Group();

        /* Disc body — torus */
        const torusGeo = new THREE.TorusGeometry(0.45, 0.06, 16, 48);
        const mat = new THREE.MeshStandardMaterial({
            color: discColors[i % discColors.length],
            emissive: discColors[i % discColors.length],
            emissiveIntensity: 0.6,
            roughness: 0.2,
            metalness: 0.8,
            transparent: true,
            opacity: 0.7,
        });
        const disc = new THREE.Mesh(torusGeo, mat);
        group.add(disc);

        /* Inner label */
        const labelGeo = new THREE.CircleGeometry(0.35, 32);
        const labelMat = new THREE.MeshStandardMaterial({
            color: discColors[i % discColors.length],
            emissive: discColors[i % discColors.length],
            emissiveIntensity: 0.3,
            transparent: true,
            opacity: 0.25,
            side: THREE.DoubleSide,
        });
        const label = new THREE.Mesh(labelGeo, labelMat);
        group.add(label);

        /* Position in an arc around the PS5 */
        const angle = (i / discCount) * Math.PI * 1.6 - 0.4;
        const radius = 2.5 + Math.random() * 1.5;
        group.position.set(
            Math.cos(angle) * radius + (isMobile ? 0 : 0.5),
            (Math.random() - 0.5) * 3,
            Math.sin(angle) * radius - 1
        );
        group.rotation.set(
            Math.random() * Math.PI,
            Math.random() * Math.PI,
            Math.random() * Math.PI
        );

        group.userData = {
            baseY: group.position.y,
            speed: 0.3 + Math.random() * 0.5,
            rotSpeed: 0.5 + Math.random() * 1.2,
            floatAmp: 0.15 + Math.random() * 0.3,
            phase: Math.random() * Math.PI * 2,
        };

        discs.push(group);
        scene.add(group);
    }
}

/* ── Particle field ──────────────────────────────────────── */
function createParticleField() {
    const count = isMobile ? 400 : 1200;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);

    const palette = [
        new THREE.Color(CYAN),
        new THREE.Color(PURPLE),
        new THREE.Color(ORANGE),
        new THREE.Color(0xffffff),
    ];

    for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        positions[i3]     = (Math.random() - 0.5) * 30;
        positions[i3 + 1] = (Math.random() - 0.5) * 20;
        positions[i3 + 2] = (Math.random() - 0.5) * 20 - 5;

        const c = palette[Math.floor(Math.random() * palette.length)];
        colors[i3]     = c.r;
        colors[i3 + 1] = c.g;
        colors[i3 + 2] = c.b;

        sizes[i] = Math.random() * 3 + 1;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const mat = new THREE.PointsMaterial({
        size: 0.04,
        vertexColors: true,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        sizeAttenuation: true,
    });

    particleSystem = new THREE.Points(geo, mat);
    scene.add(particleSystem);
}

/* ── Grid floor ──────────────────────────────────────────── */
function createGridFloor() {
    const gridGeo = new THREE.PlaneGeometry(40, 40, 40, 40);
    const gridMat = new THREE.MeshBasicMaterial({
        color: CYAN,
        wireframe: true,
        transparent: true,
        opacity: 0.04,
    });
    const grid = new THREE.Mesh(gridGeo, gridMat);
    grid.rotation.x = -Math.PI / 2;
    grid.position.y = -2;
    scene.add(grid);
}

/* ── Mouse / pointer tracking ────────────────────────────── */
function onMouseMove(e) {
    mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
    mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
}
function onPointerMove(e) {
    mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
    mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
}

/* ── Resize ──────────────────────────────────────────────── */
function onResize(canvas) {
    isMobile = window.innerWidth < 768;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
}

/* ── Animation loop ──────────────────────────────────────── */
function animate() {
    animationId = requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    const dt = clock.getDelta();

    /* Smooth mouse follow */
    mouse.x += (mouse.tx - mouse.x) * 0.04;
    mouse.y += (mouse.ty - mouse.y) * 0.04;

    /* Camera parallax */
    camera.position.x = mouse.x * 1.2;
    camera.position.y = 1.5 + mouse.y * -0.6;
    camera.lookAt(0, 0.5, 0);

    /* PS5 rotation */
    if (ps5Group) {
        ps5Group.rotation.y = -0.3 + Math.sin(t * 0.3) * 0.15 + mouse.x * 0.2;
        ps5Group.rotation.x = 0.05 + Math.sin(t * 0.2) * 0.03;
        ps5Group.position.y = -0.3 + Math.sin(t * 0.5) * 0.12;
    }

    /* Floating discs */
    discs.forEach(d => {
        const ud = d.userData;
        d.position.y = ud.baseY + Math.sin(t * ud.speed + ud.phase) * ud.floatAmp;
        d.rotation.x += ud.rotSpeed * 0.005;
        d.rotation.y += ud.rotSpeed * 0.008;
    });

    /* Particle drift */
    if (particleSystem) {
        const pos = particleSystem.geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            const i3 = i * 3;
            pos.array[i3 + 1] += 0.003;
            if (pos.array[i3 + 1] > 10) pos.array[i3 + 1] = -10;
            pos.array[i3] += Math.sin(t + i) * 0.0008;
        }
        pos.needsUpdate = true;
        particleSystem.rotation.y = t * 0.02;
    }

    /* Render with bloom */
    composer.render();
}

/* ── Cleanup (for SPA transitions) ───────────────────────── */
export function disposeScene() {
    if (animationId) cancelAnimationFrame(animationId);
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onResize);
    renderer?.dispose();
    composer?.dispose();
}
