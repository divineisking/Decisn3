/**
 * Decisn3 Interactive Engine
 * Dual-Engine Visualization: 3D WebGL (Three.js) & 2D SVG with Unified State
 * Supports Entire Graph, Focus Neighbourhood, Trace History, Orbit Navigation & Search-to-Node
 */

(function () {
  'use strict';

  // Global Application State
  let decisions = [];
  let sources = [];
  let sessions = [];
  let selectedDecision = null;
  let activeTab = 'graph';
  let dimension = '3d'; // '3d' or '2d'
  let viewMode = 'all'; // 'all', 'neighbourhood', 'trace'
  let showLabels = true;
  let graphLayout2D = 'chronological'; // 'chronological' or 'force'
  let explorerViewMode = 'decisions'; // 'decisions' or 'sessions'
  let timelineGroupMode = true; // group decisions by session in timeline

  // 2D SVG State
  let zoom2D = { x: 0, y: 0, scale: 1 };
  let isDragging2D = false;
  let dragStart2D = { x: 0, y: 0 };

  // 3D Three.js State
  let scene3D, camera3D, renderer3D, controls3D;
  let nodeMeshMap = new Map(); // id -> { mesh, ring, data, pos3D }
  let edgeMeshList = []; // array of { line, cone, sourceId, targetId, type }
  let gizmoScene, gizmoCamera, gizmoRenderer;
  let raycaster, mousePointer;
  let pointerDownPos = { x: 0, y: 0 };
  let hoveredNode = null;
  let animFrameId = null;
  let cameraAnimation = null; // { startEye, endEye, startLook, endLook, startTime, duration }

  // Filter & Search State
  let activeFilters = {
    search: '',
    category: 'all',
    status: 'all',
    significance: 'all',
    evidence: 'all',
    sort: 'date-desc',
    session: 'all'
  };

  // Node Category Colors
  const CATEGORY_COLORS = {
    architecture: '#f2b705',
    product: '#58a6ff',
    infrastructure: '#39c5bb',
    security: '#f85149',
    ai: '#bc8cff',
    ux: '#ec4899',
    operations: '#f97316',
    automation: '#10b981'
  };

  // DOM Elements Cache
  const elements = {};

  function initElements() {
    elements.themeToggle = document.getElementById('theme-toggle');
    elements.tabBtns = document.querySelectorAll('.tab-btn');
    elements.viewPanes = document.querySelectorAll('.view-pane');
    
    // Canvas & SVG
    elements.graphCanvasWrapper = document.getElementById('graph-canvas-wrapper');
    elements.canvas3d = document.getElementById('graph-canvas-3d');
    elements.graphSvg = document.getElementById('graph-svg');
    elements.billboardLayer = document.getElementById('billboard-labels-layer');
    elements.tooltip3d = document.getElementById('graph-3d-tooltip');
    elements.gizmoCanvas = document.getElementById('gizmo-canvas');
    elements.modeBadge = document.getElementById('graph-mode-badge');

    // Controls
    elements.dimensionToggle = document.getElementById('dimension-toggle');
    elements.modeBtns = document.querySelectorAll('.mode-btn');
    elements.zoomInBtn = document.getElementById('zoom-in-btn');
    elements.zoomOutBtn = document.getElementById('zoom-out-btn');
    elements.zoomResetBtn = document.getElementById('zoom-reset-btn');
    elements.focusNodeBtn = document.getElementById('focus-node-btn');
    elements.orbitResetBtn = document.getElementById('orbit-reset-btn');
    elements.labelsToggleBtn = document.getElementById('labels-toggle-btn');
    elements.layoutToggle = document.getElementById('layout-toggle');

    // Filters
    elements.graphCategoryFilter = document.getElementById('graph-category-filter');
    elements.graphStatusFilter = document.getElementById('graph-status-filter');
    elements.graphSessionFilter = document.getElementById('graph-session-filter');
    elements.searchInput = document.getElementById('search-input');
    elements.categoryFilter = document.getElementById('category-filter');
    elements.statusFilter = document.getElementById('status-filter');
    elements.significanceFilter = document.getElementById('significance-filter');
    elements.evidenceFilter = document.getElementById('evidence-filter');
    elements.sortFilter = document.getElementById('sort-filter');
    elements.explorerSessionFilter = document.getElementById('explorer-session-filter');
    elements.timelineGroupToggle = document.getElementById('timeline-group-toggle');
    elements.explorerToggleDecisions = document.getElementById('explorer-toggle-decisions');
    elements.explorerToggleSessions = document.getElementById('explorer-toggle-sessions');
    elements.statSessions = document.getElementById('stat-sessions');

    // Views
    elements.detailDrawer = document.getElementById('detail-drawer');
    elements.drawerContent = document.getElementById('drawer-content');
    elements.explorerCards = document.getElementById('explorer-cards');
    elements.timelineTrack = document.getElementById('timeline-track');
    elements.sourcesTableBody = document.getElementById('sources-tbody');
  }

  // Populate dynamic session options in select elements
  function populateSessionFilters() {
    if (elements.graphSessionFilter && sessions.length > 0) {
      elements.graphSessionFilter.innerHTML = '<option value="all">All Sessions (' + sessions.length + ')</option>' +
        sessions.map(s => `<option value="${s.id}">${s.id}: ${escapeHtml(s.title)}</option>`).join('');
    } else if (elements.graphSessionFilter) {
      elements.graphSessionFilter.innerHTML = '<option value="all">All Sessions (0)</option>';
    }
    if (elements.explorerSessionFilter && sessions.length > 0) {
      elements.explorerSessionFilter.innerHTML = '<option value="all">Session: All (' + sessions.length + ')</option>' +
        sessions.map(s => `<option value="${s.id}">${s.id}: ${escapeHtml(s.title)}</option>`).join('');
    } else if (elements.explorerSessionFilter) {
      elements.explorerSessionFilter.innerHTML = '<option value="all">Session: All (0)</option>';
    }
  }

  // Load Dataset
  async function loadData() {
    if (window.DECISN3_DATA && window.DECISN3_DATA.decisions) {
      decisions = window.DECISN3_DATA.decisions;
      sources = window.DECISN3_DATA.sources || [];
      sessions = window.DECISN3_DATA.sessions || [];
      console.log('Loaded decision data from embedded data.js payload.');
    } else {
      try {
        const decRes = await fetch('data/decisions.json');
        const decJson = await decRes.json();
        decisions = decJson.decisions || [];

        const srcRes = await fetch('data/sources.json');
        const srcJson = await srcRes.json();
        sources = srcJson.sources || [];

        try {
          const sesRes = await fetch('data/sessions.json');
          const sesJson = await sesRes.json();
          sessions = sesJson.sessions || [];
        } catch (e) {
          sessions = [];
        }
        console.log('Loaded decision data via fetch API.');
      } catch (err) {
        console.error('Failed to load decisions via fetch:', err);
        showErrorBanner('Unable to load decision data. If opening via file://, ensure data/data.js is present.');
        return;
      }
    }

    populateSessionFilters();
    renderOverviewStats();
    init3D();
    renderTimeline();
    renderExplorer();
    renderSources();
  }

  function showErrorBanner(msg) {
    const banner = document.createElement('div');
    banner.style.cssText = 'background: #cf222e; color: #fff; padding: 12px; text-align: center; font-weight: bold; position: fixed; top: 0; left: 0; right: 0; z-index: 9999;';
    banner.textContent = msg;
    document.body.prepend(banner);
  }

  // Overview Statistics
  function renderOverviewStats() {
    const totalEl = document.getElementById('stat-total-decisions');
    if (totalEl) totalEl.textContent = decisions.length;
    
    const validatedCount = decisions.filter(d => d.status === 'validated').length;
    const implementedCount = decisions.filter(d => d.status === 'implemented').length;
    const valEl = document.getElementById('stat-validated');
    if (valEl) valEl.innerHTML = `${validatedCount} <span class="stat-pill badge-status-validated">${implementedCount} impl</span>`;

    const reversedCount = decisions.filter(d => d.status === 'reversed').length;
    const supersededCount = decisions.filter(d => d.status === 'superseded').length;
    const revEl = document.getElementById('stat-reversed');
    if (revEl) revEl.innerHTML = `${reversedCount} <span class="stat-pill badge-status-reversed">${supersededCount} superseded</span>`;

    const documentedCount = decisions.filter(d => d.evidence_status === 'documented' || d.evidence_status === 'corroborated').length;
    const inferredCount = decisions.filter(d => d.evidence_status === 'inferred').length;
    const evEl = document.getElementById('stat-evidence');
    if (evEl) evEl.innerHTML = `${documentedCount} <span class="stat-pill badge-ev-documented">${inferredCount} inferred</span>`;

    const sesEl = document.getElementById('stat-sessions');
    if (sesEl) sesEl.textContent = sessions.length;

    const srcEl = document.getElementById('stat-sources');
    if (srcEl) srcEl.textContent = sources.length;
  }

  // Theme Management
  function initTheme() {
    const saved = localStorage.getItem('decisn3_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeBtn(saved);

    elements.themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('decisn3_theme', next);
      updateThemeBtn(next);
      updateSceneTheme();
      if (dimension === '2d') {
        render2DGraph();
      }
    });
  }

  function updateThemeBtn(theme) {
    elements.themeToggle.innerHTML = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  }

  function updateSceneTheme() {
    if (!scene3D || !renderer3D) return;
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const bgCol = isDark ? 0x0e1117 : 0xf6f8fa;
    scene3D.background = new THREE.Color(bgCol);
    if (scene3D.fog) scene3D.fog.color.setHex(bgCol);
  }

  // Tab Navigation
  function initTabs() {
    elements.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        switchTab(tab);
      });
    });
  }

  function switchTab(tabName) {
    activeTab = tabName;
    elements.tabBtns.forEach(b => b.classList.toggle('active', b.getAttribute('data-tab') === tabName));
    elements.viewPanes.forEach(p => p.classList.toggle('active', p.id === `view-${tabName}`));

    if (tabName === 'graph') {
      setTimeout(() => {
        handleResize();
        if (dimension === '3d') {
          update3DVisibility();
        } else {
          render2DGraph();
        }
      }, 50);
    }
  }

  /* ==========================================================================
     3D DETERMINISTIC SPATIAL LAYOUT ALGORITHM
     ========================================================================== */

  function compute3DPositions() {
    // 1. Epoch-Aware Horizontal Progression (X axis: -380 to +380)
    // Distributes 10 epochs evenly so early July and later October are both clearly spaced
    const categoryYMap = {
      product: 160,
      architecture: 100,
      automation: 60,
      infrastructure: 20,
      ai: -20,
      security: -80,
      operations: -140,
      ux: -190
    };

    const incomingCounts = new Map();
    decisions.forEach(d => incomingCounts.set(d.id, 0));
    decisions.forEach(d => {
      (d.relationships || []).forEach(rel => {
        incomingCounts.set(rel.target, (incomingCounts.get(rel.target) || 0) + 1);
      });
    });

    const nodePositions = new Map();

    decisions.forEach((d, idx) => {
      // Determine epoch number (1 to 12) or derive from chronological index
      const epochNum = (typeof d.epoch === 'number' && d.epoch >= 1)
        ? Math.min(d.epoch, 12)
        : Math.min(12, Math.max(1, Math.ceil(((idx + 1) / Math.max(1, decisions.length)) * 12)));
      const baseX = (epochNum - 6.5) * 68;
      const intraEpochOffset = ((idx % 3) - 1) * 36;
      const x = baseX + intraEpochOffset;

      const y = categoryYMap[d.category] !== undefined ? categoryYMap[d.category] : 0;

      const inCount = incomingCounts.get(d.id) || 0;
      const relCount = (d.relationships || []).length;
      const pseudoHash = ((idx * 31) % 7) - 3;
      const z = (relCount - inCount) * 26 + pseudoHash * 28;

      nodePositions.set(d.id, { x, y, z });
    });

    // 2. Collision Repulsion Iterations (Deterministic 3D Relaxation)
    const ids = Array.from(nodePositions.keys());
    const minDist = 72; // Generous distance between 3D sphere centers
    for (let iter = 0; iter < 24; iter++) {
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const p1 = nodePositions.get(ids[i]);
          const p2 = nodePositions.get(ids[j]);
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dz = p2.z - p1.z;
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.001;

          if (dist < minDist) {
            const overlap = (minDist - dist) * 0.5;
            const nx = dx / dist;
            const ny = dy / dist;
            const nz = dz / dist;
            p1.x -= nx * overlap * 0.45;
            p1.y -= ny * overlap * 0.45;
            p1.z -= nz * overlap * 0.75;
            p2.x += nx * overlap * 0.45;
            p2.y += ny * overlap * 0.45;
            p2.z += nz * overlap * 0.75;
          }
        }
      }
    }

    return nodePositions;
  }

  /* ==========================================================================
     3D WEBGL ENGINE INITIALIZATION & RENDERING
     ========================================================================== */

  function init3D() {
    if (!window.THREE || !window.THREE.OrbitControls) {
      console.warn('Three.js or OrbitControls not available. Falling back to 2D.');
      setDimension('2d');
      return;
    }

    try {
      const container = elements.graphCanvasWrapper;
      const width = container.clientWidth || 1100;
      const height = container.clientHeight || 750;

      // 1. Scene & Camera
      scene3D = new THREE.Scene();
      const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
      const bgCol = isDark ? 0x0e1117 : 0xf6f8fa;
      scene3D.background = new THREE.Color(bgCol);
      scene3D.fog = new THREE.FogExp2(bgCol, 0.00065);

      camera3D = new THREE.PerspectiveCamera(50, width / height, 5, 4000);
      camera3D.position.set(160, 180, 580);

      // 2. WebGL Renderer
      renderer3D = new THREE.WebGLRenderer({
        canvas: elements.canvas3d,
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
      });
      renderer3D.setSize(width, height);
      renderer3D.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

      // 3. Orbit Controls
      controls3D = new THREE.OrbitControls(camera3D, renderer3D.domElement);
      controls3D.enableDamping = true;
      controls3D.dampingFactor = 0.07;
      controls3D.minDistance = 80;
      controls3D.maxDistance = 1600;
      controls3D.maxPolarAngle = Math.PI * 0.94;
      controls3D.target.set(0, 0, 0);

      // 4. Lights
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
      scene3D.add(ambientLight);

      const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
      dirLight1.position.set(400, 600, 500);
      scene3D.add(dirLight1);

      const dirLight2 = new THREE.DirectionalLight(0x88bbff, 0.35);
      dirLight2.position.set(-400, -300, -400);
      scene3D.add(dirLight2);

      // 5. Raycaster
      raycaster = new THREE.Raycaster();
      mousePointer = new THREE.Vector2();

      // 6. Build Graph Objects
      build3DGraphObjects();

      // 7. Mini Orientation Gizmo
      initOrientationGizmo();

      // 8. Event Listeners
      init3DEventListeners();

      // 9. Animation Loop
      animate3D();

      console.log('3D WebGL Decision Graph initialized successfully.');
    } catch (err) {
      console.error('WebGL initialization failed:', err);
      showErrorBanner('WebGL initialization failed. Switched to 2D SVG mode.');
      setDimension('2d');
    }
  }

  function build3DGraphObjects() {
    // Clear existing objects
    nodeMeshMap.forEach(item => {
      scene3D.remove(item.mesh);
      if (item.ring) scene3D.remove(item.ring);
      if (item.halo) scene3D.remove(item.halo);
    });
    nodeMeshMap.clear();

    edgeMeshList.forEach(e => {
      scene3D.remove(e.line);
      if (e.cone) scene3D.remove(e.cone);
    });
    edgeMeshList = [];

    const positions = compute3DPositions();

    // Reusable Geometries
    const sphereGeoHigh = new THREE.SphereGeometry(18, 32, 24);
    const sphereGeoMed = new THREE.SphereGeometry(15, 28, 20);
    const sphereGeoLow = new THREE.SphereGeometry(12, 24, 16);
    const torusGeo = new THREE.TorusGeometry(23, 1.4, 16, 32);
    const coneGeo = new THREE.ConeGeometry(4, 10, 16);

    // 1. Build Nodes
    decisions.forEach(d => {
      const pos = positions.get(d.id) || { x: 0, y: 0, z: 0 };
      const geo = d.significance === 'high' ? sphereGeoHigh : d.significance === 'medium' ? sphereGeoMed : sphereGeoLow;
      const baseColor = new THREE.Color(CATEGORY_COLORS[d.category] || '#58a6ff');

      const mat = new THREE.MeshStandardMaterial({
        color: baseColor,
        roughness: 0.28,
        metalness: 0.22,
        transparent: true,
        opacity: 1.0
      });

      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(pos.x, pos.y, pos.z);
      mesh.userData = { id: d.id, decision: d };
      scene3D.add(mesh);

      // Reversal Indicator Torus Ring
      let ring = null;
      if (d.status === 'reversed') {
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0xf85149,
          wireframe: false,
          transparent: true,
          opacity: 0.95
        });
        ring = new THREE.Mesh(torusGeo, ringMat);
        ring.position.set(pos.x, pos.y, pos.z);
        ring.rotation.x = Math.PI / 3;
        scene3D.add(ring);
      }

      // Selection Halo
      const haloMat = new THREE.MeshBasicMaterial({
        color: 0xf2b705,
        wireframe: true,
        transparent: true,
        opacity: 0,
        visible: false
      });
      const halo = new THREE.Mesh(new THREE.TorusGeometry(25, 1.5, 12, 28), haloMat);
      halo.position.set(pos.x, pos.y, pos.z);
      scene3D.add(halo);

      nodeMeshMap.set(d.id, {
        mesh,
        ring,
        halo,
        data: d,
        pos3D: new THREE.Vector3(pos.x, pos.y, pos.z),
        baseColor
      });
    });

    // 2. Build 3D Directed Edges
    decisions.forEach(sourceDec => {
      const srcNode = nodeMeshMap.get(sourceDec.id);
      if (!srcNode) return;

      (sourceDec.relationships || []).forEach(rel => {
        const tgtNode = nodeMeshMap.get(rel.target);
        if (!tgtNode) return;

        // Quadratic Bezier Curve in 3D
        const p1 = srcNode.pos3D;
        const p2 = tgtNode.pos3D;
        const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);

        // Arch outward away from center (0,0,0) for elegant curved depth
        const outward = mid.clone().normalize().multiplyScalar(28);
        const controlPoint = mid.clone().add(outward);

        const curve = new THREE.QuadraticBezierCurve3(p1, controlPoint, p2);
        const points = curve.getPoints(24);
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);

        const lineMat = new THREE.LineBasicMaterial({
          color: 0x4a5568,
          transparent: true,
          opacity: 0.45,
          linewidth: 1
        });
        const line = new THREE.Line(lineGeo, lineMat);
        scene3D.add(line);

        // Arrowhead Cone at target boundary
        const coneMat = new THREE.MeshBasicMaterial({
          color: 0x4a5568,
          transparent: true,
          opacity: 0.65
        });
        const cone = new THREE.Mesh(coneGeo, coneMat);

        // Position cone just outside target sphere
        const lastPoint = points[points.length - 2];
        const dir = new THREE.Vector3().subVectors(p2, lastPoint).normalize();
        const tgtRadius = tgtNode.data.significance === 'high' ? 20 : 16;
        const conePos = p2.clone().sub(dir.clone().multiplyScalar(tgtRadius + 4));
        cone.position.copy(conePos);
        cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
        scene3D.add(cone);

        edgeMeshList.push({
          line,
          cone,
          sourceId: sourceDec.id,
          targetId: rel.target,
          type: rel.type,
          explanation: rel.explanation
        });
      });
    });

    update3DVisibility();
  }

  // Mini 3D Orientation Gizmo
  function initOrientationGizmo() {
    const canvas = elements.gizmoCanvas;
    if (!canvas) return;

    gizmoScene = new THREE.Scene();
    gizmoCamera = new THREE.PerspectiveCamera(50, 1, 1, 100);
    gizmoCamera.position.set(0, 0, 18);

    gizmoRenderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true
    });
    gizmoRenderer.setSize(70, 70);

    const axes = new THREE.AxesHelper(9);
    // Custom colors: X = Red (Time), Y = Green (Layer), Z = Blue (Depth)
    gizmoScene.add(axes);
  }

  function updateOrientationGizmo() {
    if (!gizmoRenderer || !gizmoCamera || !camera3D) return;
    gizmoCamera.position.copy(camera3D.position).sub(controls3D.target).normalize().multiplyScalar(18);
    gizmoCamera.lookAt(0, 0, 0);
    gizmoRenderer.render(gizmoScene, gizmoCamera);
  }

  /* ==========================================================================
     VIEW MODES & HIGHLIGHTING (ENTIRE GRAPH, NEIGHBOURHOOD, TRACE HISTORY)
     ========================================================================== */

  function getNeighbourhoodIds(targetId) {
    const neighbours = new Set([targetId]);
    const upstreamIds = new Set();
    const downstreamIds = new Set();

    decisions.forEach(d => {
      (d.relationships || []).forEach(rel => {
        if (rel.target === targetId) {
          neighbours.add(d.id);
          upstreamIds.add(d.id);
        }
        if (d.id === targetId) {
          neighbours.add(rel.target);
          downstreamIds.add(rel.target);
        }
      });
    });

    return { neighbours, upstreamIds, downstreamIds };
  }

  function getTraceHistoryIds(targetId) {
    const ancestors = new Set();
    const descendants = new Set();

    // Traverse Upstream (Ancestors)
    function traverseUp(id) {
      decisions.forEach(d => {
        (d.relationships || []).forEach(rel => {
          if (rel.target === id && !ancestors.has(d.id)) {
            ancestors.add(d.id);
            traverseUp(d.id);
          }
        });
      });
    }

    // Traverse Downstream (Descendants)
    function traverseDown(id) {
      const current = decisions.find(d => d.id === id);
      if (!current) return;
      (current.relationships || []).forEach(rel => {
        if (!descendants.has(rel.target)) {
          descendants.add(rel.target);
          traverseDown(rel.target);
        }
      });
    }

    traverseUp(targetId);
    traverseDown(targetId);

    const allTrace = new Set([targetId, ...ancestors, ...descendants]);
    return { allTrace, ancestors, descendants };
  }

  function update3DVisibility() {
    if (dimension !== '3d' || !scene3D) return;

    const catFilter = elements.graphCategoryFilter ? elements.graphCategoryFilter.value : 'all';
    const statFilter = elements.graphStatusFilter ? elements.graphStatusFilter.value : 'all';
    const sesFilter = elements.graphSessionFilter ? elements.graphSessionFilter.value : 'all';

    // Base filter set
    const matchesFilters = (d) => {
      const catMatch = catFilter === 'all' || d.category === catFilter;
      const statMatch = statFilter === 'all' || d.status === statFilter;
      return catMatch && statMatch;
    };

    const matchesSession = (d) => {
      return sesFilter === 'all' || d.session_id === sesFilter || (d.provenance && d.provenance.conversation_id === sesFilter);
    };

    let activeSet = null;
    let upstreamSet = new Set();
    let downstreamSet = new Set();

    if (selectedDecision) {
      if (viewMode === 'neighbourhood') {
        const nb = getNeighbourhoodIds(selectedDecision.id);
        activeSet = nb.neighbours;
        upstreamSet = nb.upstreamIds;
        downstreamSet = nb.downstreamIds;
      } else if (viewMode === 'trace') {
        const tr = getTraceHistoryIds(selectedDecision.id);
        activeSet = tr.allTrace;
        upstreamSet = tr.ancestors;
        downstreamSet = tr.descendants;
      } else {
        // 'all' mode with selection
        const nb = getNeighbourhoodIds(selectedDecision.id);
        upstreamSet = nb.upstreamIds;
        downstreamSet = nb.downstreamIds;
      }
    }

    // Update Nodes
    nodeMeshMap.forEach((item, id) => {
      const match = matchesFilters(item.data);
      const inSession = matchesSession(item.data);
      const isSelected = selectedDecision && selectedDecision.id === id;
      const isUpstream = upstreamSet.has(id);
      const isDownstream = downstreamSet.has(id);
      const inActiveSet = !activeSet || activeSet.has(id);

      if (!match) {
        item.mesh.visible = false;
        if (item.ring) item.ring.visible = false;
        if (item.halo) item.halo.visible = false;
        return;
      }

      // If not in selected session, ghost to 6% opacity per R1 requirement
      if (!inSession) {
        item.mesh.visible = true;
        item.mesh.material.opacity = 0.06;
        item.mesh.material.color.copy(item.baseColor);
        if (item.ring) item.ring.visible = false;
        if (item.halo) item.halo.visible = false;
        return;
      }

      item.mesh.visible = true;
      if (item.ring) item.ring.visible = true;

      if (!selectedDecision) {
        // Clean default state
        item.mesh.material.opacity = 1.0;
        item.mesh.material.color.copy(item.baseColor);
        if (item.halo) item.halo.visible = false;
      } else if (isSelected) {
        item.mesh.material.opacity = 1.0;
        item.mesh.material.color.setHex(0xf2b705); // Highlight selected gold
        if (item.halo) {
          item.halo.visible = true;
          item.halo.material.opacity = 0.9;
        }
      } else if (isUpstream) {
        item.mesh.material.opacity = 1.0;
        item.mesh.material.color.setHex(0x3fb950); // Vibrant green upstream
        if (item.halo) item.halo.visible = false;
      } else if (isDownstream) {
        item.mesh.material.opacity = 1.0;
        item.mesh.material.color.setHex(0x58a6ff); // Bright blue downstream
        if (item.halo) item.halo.visible = false;
      } else if (inActiveSet && viewMode === 'trace') {
        item.mesh.material.opacity = 0.95;
        item.mesh.material.color.copy(item.baseColor);
        if (item.halo) item.halo.visible = false;
      } else {
        // Ghost distant/unrelated nodes
        const ghostOpacity = viewMode === 'all' ? 0.22 : 0.06;
        item.mesh.material.opacity = ghostOpacity;
        item.mesh.material.color.copy(item.baseColor);
        if (item.halo) item.halo.visible = false;
      }
    });

    // Update Edges
    edgeMeshList.forEach(edge => {
      const srcNode = nodeMeshMap.get(edge.sourceId);
      const tgtNode = nodeMeshMap.get(edge.targetId);

      if (!srcNode || !tgtNode || !srcNode.mesh.visible || !tgtNode.mesh.visible) {
        edge.line.visible = false;
        edge.cone.visible = false;
        return;
      }

      const srcInSession = matchesSession(srcNode.data);
      const tgtInSession = matchesSession(tgtNode.data);

      if (sesFilter !== 'all' && (!srcInSession || !tgtInSession)) {
        edge.line.visible = false;
        edge.cone.visible = false;
        return;
      }

      edge.line.visible = true;
      edge.cone.visible = true;

      if (!selectedDecision) {
        edge.line.material.color.setHex(0x4a5568);
        edge.line.material.opacity = 0.45;
        edge.cone.material.color.setHex(0x4a5568);
        edge.cone.material.opacity = 0.65;
      } else {
        const isTargetOfSelected = edge.sourceId === selectedDecision.id;
        const isSourceOfSelected = edge.targetId === selectedDecision.id;
        const isTracePath = activeSet && activeSet.has(edge.sourceId) && activeSet.has(edge.targetId);

        if (isSourceOfSelected) {
          // Upstream link (Green)
          edge.line.material.color.setHex(0x3fb950);
          edge.line.material.opacity = 0.95;
          edge.cone.material.color.setHex(0x3fb950);
          edge.cone.material.opacity = 1.0;
        } else if (isTargetOfSelected) {
          // Downstream link (Gold)
          edge.line.material.color.setHex(0xf2b705);
          edge.line.material.opacity = 0.95;
          edge.cone.material.color.setHex(0xf2b705);
          edge.cone.material.opacity = 1.0;
        } else if (viewMode === 'trace' && isTracePath) {
          // Causal trace pathway (Teal)
          edge.line.material.color.setHex(0x39c5bb);
          edge.line.material.opacity = 0.8;
          edge.cone.material.color.setHex(0x39c5bb);
          edge.cone.material.opacity = 0.9;
        } else {
          // Dim / hide
          edge.line.material.opacity = viewMode === 'all' ? 0.08 : 0.02;
          edge.cone.material.opacity = viewMode === 'all' ? 0.1 : 0.02;
        }
      }
    });

    renderBillboardLabels();
    updateModeBadge();
  }

  function updateModeBadge() {
    if (!elements.modeBadge) return;
    if (dimension === '2d') {
      elements.modeBadge.textContent = '2D Plane';
      elements.modeBadge.style.borderColor = 'var(--border-color)';
    } else {
      if (viewMode === 'neighbourhood') {
        elements.modeBadge.textContent = '3D Neighbourhood';
        elements.modeBadge.style.borderColor = 'var(--accent-green)';
      } else if (viewMode === 'trace') {
        elements.modeBadge.textContent = '3D Causal Trace';
        elements.modeBadge.style.borderColor = 'var(--accent-teal)';
      } else {
        elements.modeBadge.textContent = '3D Landscape';
        elements.modeBadge.style.borderColor = 'var(--accent-gold)';
      }
    }
  }

  // 3D Billboard Labels Layer
  function renderBillboardLabels() {
    const layer = elements.billboardLayer;
    if (!layer || dimension !== '3d' || !camera3D) return;
    layer.innerHTML = '';

    if (!showLabels) return;

    const width = layer.clientWidth || 1000;
    const height = layer.clientHeight || 700;

    let targetIdsToLabel = new Set();

    if (!selectedDecision) {
      // In entire graph mode: label key landmark nodes + hovered node
      decisions.forEach((d, idx) => {
        if (decisions.length <= 15 || d.significance === 'high' || d.significance === 'foundational' || idx % 3 === 0) {
          targetIdsToLabel.add(d.id);
        }
      });
      if (hoveredNode) targetIdsToLabel.add(hoveredNode.id);
    } else {
      // In focused mode: label selected node, active neighbourhood, and hovered node
      targetIdsToLabel.add(selectedDecision.id);
      const nb = getNeighbourhoodIds(selectedDecision.id);
      nb.neighbours.forEach(id => targetIdsToLabel.add(id));
      if (hoveredNode) targetIdsToLabel.add(hoveredNode.id);
    }

    targetIdsToLabel.forEach(id => {
      const item = nodeMeshMap.get(id);
      if (!item || !item.mesh.visible) return;

      // Project 3D vector to screen space
      const screenPos = item.pos3D.clone().project(camera3D);

      // Node must be in front of camera
      if (screenPos.z >= 1.0) return;

      const px = (screenPos.x * 0.5 + 0.5) * width;
      const py = (-screenPos.y * 0.5 + 0.5) * height;

      // Create Label DOM Element
      const lbl = document.createElement('div');
      lbl.className = 'billboard-label';
      if (selectedDecision && selectedDecision.id === id) {
        lbl.classList.add('active');
      }
      lbl.style.left = `${px}px`;
      lbl.style.top = `${py}px`;

      const cleanTitle = item.data.title.length > 22 ? item.data.title.slice(0, 20) + '…' : item.data.title;
      lbl.textContent = `${item.data.id}: ${cleanTitle}`;

      lbl.addEventListener('click', (e) => {
        e.stopPropagation();
        selectDecision(item.data);
      });

      layer.appendChild(lbl);
    });
  }

  /* ==========================================================================
     CAMERA NAVIGATION, ANIMATION & FOCUS CONTROLS
     ========================================================================== */

  function flyCameraTo(targetEye, targetLookAt, duration = 750) {
    if (!camera3D || !controls3D) return;

    cameraAnimation = {
      startEye: camera3D.position.clone(),
      endEye: targetEye.clone(),
      startLook: controls3D.target.clone(),
      endLook: targetLookAt.clone(),
      startTime: performance.now(),
      duration: duration
    };
  }

  function focusNode(node) {
    if (!node || dimension !== '3d') return;
    const item = nodeMeshMap.get(node.id);
    if (!item) return;

    const targetLookAt = item.pos3D.clone();

    // Calculate camera vantage offset from node position
    const viewDir = camera3D.position.clone().sub(controls3D.target).normalize();
    const distance = 180;
    const targetEye = targetLookAt.clone().add(viewDir.multiplyScalar(distance));

    // Ensure camera is slightly elevated
    targetEye.y = Math.max(targetEye.y, targetLookAt.y + 45);

    flyCameraTo(targetEye, targetLookAt, 700);
  }

  function frameEntire3DGraph() {
    if (!camera3D || !controls3D) return;

    // Center on origin with comfortable wide perspective
    const targetLookAt = new THREE.Vector3(0, 0, 0);
    const targetEye = new THREE.Vector3(140, 160, 560);
    flyCameraTo(targetEye, targetLookAt, 650);
  }

  function resetCameraOrbit() {
    if (!camera3D || !controls3D) return;
    controls3D.reset();
    frameEntire3DGraph();
  }

  function animate3D() {
    animFrameId = requestAnimationFrame(animate3D);

    // Update Smooth Camera Lerp Animation
    if (cameraAnimation) {
      const now = performance.now();
      const elapsed = now - cameraAnimation.startTime;
      const progress = Math.min(1.0, elapsed / cameraAnimation.duration);
      // Ease in-out cubic
      const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      camera3D.position.lerpVectors(cameraAnimation.startEye, cameraAnimation.endEye, ease);
      controls3D.target.lerpVectors(cameraAnimation.startLook, cameraAnimation.endLook, ease);

      if (progress >= 1.0) {
        cameraAnimation = null;
      }
    }

    if (controls3D) {
      controls3D.update();
    }

    if (renderer3D && scene3D && camera3D && dimension === '3d') {
      renderer3D.render(scene3D, camera3D);
      renderBillboardLabels();
      updateOrientationGizmo();
    }
  }

  /* ==========================================================================
     3D EVENT LISTENERS (RAYCASTING, HOVER, DISAMBIGUATED CLICK)
     ========================================================================== */

  function init3DEventListeners() {
    const canvas = elements.canvas3d;
    if (!canvas) return;

    canvas.addEventListener('pointerdown', (e) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('pointermove', (e) => {
      if (dimension !== '3d') return;
      const rect = canvas.getBoundingClientRect();
      mousePointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mousePointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mousePointer, camera3D);
      const meshes = Array.from(nodeMeshMap.values()).map(v => v.mesh).filter(m => m.visible);
      const intersects = raycaster.intersectObjects(meshes, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const dec = hit.userData.decision;
        hoveredNode = dec;
        canvas.style.cursor = 'pointer';
        show3DTooltip(e.clientX, e.clientY, dec);
      } else {
        if (hoveredNode) {
          hoveredNode = null;
          canvas.style.cursor = 'default';
          hide3DTooltip();
        }
      }
    });

    canvas.addEventListener('pointerup', (e) => {
      if (dimension !== '3d') return;
      // Disambiguate click from camera orbit/pan drag (threshold > 5px)
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (dist > 5) return; // User was rotating/panning

      const rect = canvas.getBoundingClientRect();
      mousePointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mousePointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mousePointer, camera3D);
      const meshes = Array.from(nodeMeshMap.values()).map(v => v.mesh).filter(m => m.visible);
      const intersects = raycaster.intersectObjects(meshes, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const dec = hit.userData.decision;
        selectDecision(dec);
      } else {
        // Click on background in entire graph clears selection
        if (e.target === canvas && viewMode === 'all') {
          clearSelection();
        }
      }
    });

    // View Mode Buttons (All, Neighbourhood, Trace)
    elements.modeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-mode');
        setViewMode(mode);
      });
    });

    // Dimension Toggle (2D / 3D)
    if (elements.dimensionToggle) {
      elements.dimensionToggle.addEventListener('click', () => {
        toggleDimension();
      });
    }

    // Camera Action Buttons
    if (elements.focusNodeBtn) {
      elements.focusNodeBtn.addEventListener('click', () => {
        if (selectedDecision) {
          focusNode(selectedDecision);
        } else {
          // Focus first major decision
          const high = decisions.find(d => d.significance === 'high');
          if (high) {
            selectDecision(high);
            focusNode(high);
          }
        }
      });
    }

    if (elements.orbitResetBtn) {
      elements.orbitResetBtn.addEventListener('click', resetCameraOrbit);
    }

    if (elements.labelsToggleBtn) {
      elements.labelsToggleBtn.addEventListener('click', () => {
        showLabels = !showLabels;
        elements.labelsToggleBtn.style.opacity = showLabels ? '1.0' : '0.5';
        renderBillboardLabels();
      });
    }

    if (elements.zoomInBtn) {
      elements.zoomInBtn.addEventListener('click', () => {
        if (dimension === '3d' && camera3D) {
          const dir = controls3D.target.clone().sub(camera3D.position).multiplyScalar(0.22);
          camera3D.position.add(dir);
        } else {
          zoom2D.scale = Math.min(3.5, zoom2D.scale * 1.25);
          update2DTransform();
        }
      });
    }

    if (elements.zoomOutBtn) {
      elements.zoomOutBtn.addEventListener('click', () => {
        if (dimension === '3d' && camera3D) {
          const dir = camera3D.position.clone().sub(controls3D.target).multiplyScalar(0.25);
          camera3D.position.add(dir);
        } else {
          zoom2D.scale = Math.max(0.3, zoom2D.scale * 0.8);
          update2DTransform();
        }
      });
    }

    if (elements.zoomResetBtn) {
      elements.zoomResetBtn.addEventListener('click', () => {
        if (dimension === '3d') {
          frameEntire3DGraph();
        } else {
          fit2DGraphToViewport();
        }
      });
    }

    if (elements.graphCategoryFilter) {
      elements.graphCategoryFilter.addEventListener('change', () => {
        if (dimension === '3d') update3DVisibility();
        else render2DGraph();
      });
    }

    if (elements.graphStatusFilter) {
      elements.graphStatusFilter.addEventListener('change', () => {
        if (dimension === '3d') update3DVisibility();
        else render2DGraph();
      });
    }

    if (elements.graphSessionFilter) {
      elements.graphSessionFilter.addEventListener('change', () => {
        if (dimension === '3d') update3DVisibility();
        else render2DGraph();
      });
    }
  }

  function setViewMode(mode) {
    viewMode = mode;
    elements.modeBtns.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
    });

    if (!selectedDecision && (mode === 'neighbourhood' || mode === 'trace')) {
      // Pick high impact decision as default active anchor
      const anchor = decisions.find(d => d.significance === 'high' || d.significance === 'foundational') || decisions[0];
      if (anchor) selectDecision(anchor);
    }

    if (dimension === '3d') {
      update3DVisibility();
      if (selectedDecision && mode !== 'all') {
        focusNode(selectedDecision);
      }
    } else {
      render2DGraph();
    }
  }

  function toggleDimension() {
    setDimension(dimension === '3d' ? '2d' : '3d');
  }

  function setDimension(newDim) {
    dimension = newDim;
    if (elements.dimensionToggle) {
      elements.dimensionToggle.textContent = dimension === '3d' ? '🌐 3D' : '📄 2D';
      elements.dimensionToggle.title = `Currently viewing in ${dimension.toUpperCase()}. Click to switch.`;
    }

    if (elements.layoutToggle) {
      elements.layoutToggle.style.display = dimension === '2d' ? 'inline-flex' : 'none';
    }

    if (dimension === '3d') {
      elements.canvas3d.style.display = 'block';
      elements.graphSvg.style.display = 'none';
      if (elements.billboardLayer) elements.billboardLayer.style.display = 'block';
      handleResize();
      update3DVisibility();
      if (selectedDecision) {
        focusNode(selectedDecision);
      }
    } else {
      elements.canvas3d.style.display = 'none';
      elements.graphSvg.style.display = 'block';
      if (elements.billboardLayer) elements.billboardLayer.style.display = 'none';
      render2DGraph();
      setTimeout(fit2DGraphToViewport, 50);
    }
    updateModeBadge();
  }

  // 3D Hover Tooltip
  function show3DTooltip(clientX, clientY, dec) {
    const tip = elements.tooltip3d;
    if (!tip) return;
    const rect = elements.graphCanvasWrapper.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
    tip.style.display = 'block';

    tip.innerHTML = `
      <div class="tooltip-header">
        <span class="tooltip-id">${dec.id}</span>
        <span class="badge badge-cat-${dec.category}">${dec.category}</span>
      </div>
      <div class="tooltip-title">${escapeHtml(dec.title)}</div>
      <div class="tooltip-meta">
        <span class="badge badge-status-${dec.status}">${dec.status}</span>
        <span>•</span>
        <span>${(dec.dates && (dec.dates.proposed || dec.dates.implemented)) || (dec.provenance && dec.provenance.timestamp) || ''}</span>
        <span>•</span>
        <span>🔗 ${(dec.relationships || []).length} rels</span>
      </div>
    `;
  }

  function hide3DTooltip() {
    if (elements.tooltip3d) {
      elements.tooltip3d.style.display = 'none';
    }
  }

  /* ==========================================================================
     FALLBACK & ALTERNATIVE: 2D SVG GRAPH IMPLEMENTATION
     ========================================================================== */

  function compute2DPositions() {
    const width = elements.graphCanvasWrapper.clientWidth || 1100;
    const height = elements.graphCanvasWrapper.clientHeight || 750;

    const timestamps = decisions.map(d => {
      const ds = (d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp);
      const t = ds ? new Date(ds).getTime() : NaN;
      return Number.isFinite(t) ? t : null;
    }).filter(t => t !== null);
    const minDate = timestamps.length > 0 ? Math.min(...timestamps) : 0;
    const maxDate = timestamps.length > 1 && Math.max(...timestamps) > minDate ? Math.max(...timestamps) : minDate + 86400000;

    const nodes = decisions.map((d, index) => {
      let x = 0;
      let y = 0;

      if (graphLayout2D === 'chronological') {
        const dateStr = (d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp) || '';
        const dateVal = dateStr ? new Date(dateStr).getTime() : NaN;
        const normX = Number.isFinite(dateVal)
          ? Math.max(0, Math.min(1, (dateVal - minDate) / (maxDate - minDate)))
          : (decisions.length > 1 ? index / (decisions.length - 1) : 0.5);
        
        x = 180 + normX * (width * 1.5 - 320);
        
        const categories = ['product', 'architecture', 'automation', 'infrastructure', 'ai', 'security', 'operations', 'ux'];
        const catIndex = categories.indexOf(d.category);
        const catOffset = catIndex >= 0 ? catIndex : 2;
        
        const stagger = (index % 3) * 45 - 45;
        y = 120 + (catOffset / (categories.length - 1)) * (height - 240) + stagger;
      } else {
        const angle = (index / decisions.length) * 2 * Math.PI;
        const radius = Math.min(width, height) * 0.38 + (index % 3) * 50;
        x = width / 2 + radius * Math.cos(angle);
        y = height / 2 + radius * Math.sin(angle);
      }

      return {
        ...d,
        x,
        y,
        radius: d.significance === 'high' ? 24 : d.significance === 'medium' ? 19 : 15,
        color: CATEGORY_COLORS[d.category] || '#58a6ff'
      };
    });

    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const edges = [];

    nodes.forEach(sourceNode => {
      (sourceNode.relationships || []).forEach(rel => {
        const targetNode = nodeMap.get(rel.target);
        if (targetNode) {
          edges.push({
            source: sourceNode,
            target: targetNode,
            type: rel.type,
            explanation: rel.explanation
          });
        }
      });
    });

    return { nodes, edges, nodeMap };
  }

  function render2DGraph() {
    const svg = elements.graphSvg;
    if (!svg) return;
    svg.innerHTML = '';

    const { nodes, edges } = compute2DPositions();

    const selectedCat = elements.graphCategoryFilter ? elements.graphCategoryFilter.value : 'all';
    const selectedStat = elements.graphStatusFilter ? elements.graphStatusFilter.value : 'all';
    const selectedSes = elements.graphSessionFilter ? elements.graphSessionFilter.value : 'all';

    const visibleNodeIds = new Set(
      nodes.filter(n => {
        const catMatch = selectedCat === 'all' || n.category === selectedCat;
        const statMatch = selectedStat === 'all' || n.status === selectedStat;
        return catMatch && statMatch;
      }).map(n => n.id)
    );

    const sessionNodeIds = new Set(
      nodes.filter(n => {
        return selectedSes === 'all' || n.session_id === selectedSes || (n.provenance && n.provenance.conversation_id === selectedSes);
      }).map(n => n.id)
    );

    // Defs
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
      <marker id="arrow-default" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--border-color)" />
      </marker>
      <marker id="arrow-upstream" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent-green)" />
      </marker>
      <marker id="arrow-downstream" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent-gold)" />
      </marker>
    `;
    svg.appendChild(defs);

    const mainGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    mainGroup.setAttribute('id', 'graph-main-group');
    mainGroup.setAttribute('transform', `translate(${zoom2D.x}, ${zoom2D.y}) scale(${zoom2D.scale})`);
    svg.appendChild(mainGroup);

    const edgesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    edgesGroup.setAttribute('class', 'edges-layer');
    mainGroup.appendChild(edgesGroup);

    const upstreamNodeIds = new Set();
    const downstreamNodeIds = new Set();

    if (selectedDecision) {
      edges.forEach(e => {
        if (e.target.id === selectedDecision.id) upstreamNodeIds.add(e.source.id);
        if (e.source.id === selectedDecision.id) downstreamNodeIds.add(e.target.id);
      });
    }

    edges.forEach(edge => {
      const isVisible = visibleNodeIds.has(edge.source.id) && visibleNodeIds.has(edge.target.id);
      if (!isVisible) return;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const cx1 = edge.source.x + dx * 0.45;
      const cy1 = edge.source.y;
      const cx2 = edge.target.x - dx * 0.45;
      const cy2 = edge.target.y;
      const d = `M ${edge.source.x} ${edge.source.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${edge.target.x} ${edge.target.y}`;

      path.setAttribute('d', d);
      path.setAttribute('class', 'graph-edge');

      if (selectedDecision) {
        if (edge.target.id === selectedDecision.id) {
          path.classList.add('highlighted-upstream');
          path.setAttribute('marker-end', 'url(#arrow-upstream)');
        } else if (edge.source.id === selectedDecision.id) {
          path.classList.add('highlighted-downstream');
          path.setAttribute('marker-end', 'url(#arrow-downstream)');
        } else {
          path.classList.add('dimmed');
          path.setAttribute('marker-end', 'url(#arrow-default)');
        }
      } else {
        path.setAttribute('marker-end', 'url(#arrow-default)');
      }

      edgesGroup.appendChild(path);
    });

    const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nodesGroup.setAttribute('class', 'nodes-layer');
    mainGroup.appendChild(nodesGroup);

    nodes.forEach(node => {
      const isVisible = visibleNodeIds.has(node.id);
      if (!isVisible) return;

      const isInSession = sessionNodeIds.has(node.id);

      const nodeG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      nodeG.setAttribute('class', 'graph-node');
      nodeG.setAttribute('transform', `translate(${node.x}, ${node.y})`);

      if (!isInSession) {
        nodeG.classList.add('dimmed');
        nodeG.style.opacity = '0.08';
      } else if (selectedDecision) {
        if (node.id === selectedDecision.id) {
          nodeG.classList.add('selected');
        } else if (upstreamNodeIds.has(node.id) || downstreamNodeIds.has(node.id)) {
          // Connected
        } else {
          nodeG.classList.add('dimmed');
        }
      }

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('r', node.radius);
      circle.setAttribute('fill', node.color);
      circle.setAttribute('stroke', node.status === 'reversed' ? 'var(--accent-red)' : 'var(--bg-secondary)');
      circle.setAttribute('stroke-width', node.status === 'reversed' ? '3' : '2');
      nodeG.appendChild(circle);

      if (node.status === 'reversed') {
        const revBadge = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        revBadge.setAttribute('y', 4);
        revBadge.setAttribute('text-anchor', 'middle');
        revBadge.setAttribute('fill', '#ffffff');
        revBadge.setAttribute('font-size', '11px');
        revBadge.setAttribute('font-weight', 'bold');
        revBadge.textContent = '↺';
        nodeG.appendChild(revBadge);
      }

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('y', node.radius + 15);
      label.setAttribute('class', 'node-label');
      const cleanTitle = node.title.length > 24 ? node.title.slice(0, 22) + '…' : node.title;
      label.textContent = cleanTitle;
      nodeG.appendChild(label);

      const sublabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sublabel.setAttribute('y', node.radius + 28);
      sublabel.setAttribute('class', 'node-sublabel');
      sublabel.textContent = `${node.id} • ${(node.dates && (node.dates.proposed || node.dates.implemented)) || (node.provenance && node.provenance.timestamp) || ''}`;
      nodeG.appendChild(sublabel);

      nodeG.addEventListener('click', (e) => {
        e.stopPropagation();
        selectDecision(node);
      });

      nodesGroup.appendChild(nodeG);
    });

    svg.onclick = (e) => {
      if (e.target.tagName === 'svg' || e.target.id === 'graph-main-group') {
        clearSelection();
      }
    };
  }

  function fit2DGraphToViewport() {
    const canvas = elements.graphCanvasWrapper;
    if (!canvas) return;
    const width = canvas.clientWidth || 1100;
    const height = canvas.clientHeight || 700;
    const { nodes } = compute2DPositions();
    if (nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });

    const graphWidth = maxX - minX + 160;
    const graphHeight = maxY - minY + 140;

    const scaleX = (width - 160) / graphWidth;
    const scaleY = (height - 140) / graphHeight;
    const newScale = Math.min(Math.max(0.4, Math.min(scaleX, scaleY)), 1.15);

    zoom2D.scale = newScale;
    zoom2D.x = Math.max(90 - minX * newScale, (width - (minX + maxX) * newScale) / 2);
    zoom2D.y = (height - (minY + maxY) * newScale) / 2;
    update2DTransform();
  }

  function update2DTransform() {
    const mainGroup = document.getElementById('graph-main-group');
    if (mainGroup) {
      mainGroup.setAttribute('transform', `translate(${zoom2D.x}, ${zoom2D.y}) scale(${zoom2D.scale})`);
    }
  }

  function init2DGraphInteraction() {
    const canvas = elements.graphCanvasWrapper;
    if (!canvas) return;

    canvas.addEventListener('mousedown', (e) => {
      if (dimension !== '2d') return;
      if (e.button !== 0) return;
      isDragging2D = true;
      dragStart2D = { x: e.clientX - zoom2D.x, y: e.clientY - zoom2D.y };
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging2D || dimension !== '2d') return;
      zoom2D.x = e.clientX - dragStart2D.x;
      zoom2D.y = e.clientY - dragStart2D.y;
      update2DTransform();
    });

    window.addEventListener('mouseup', () => {
      isDragging2D = false;
    });

    canvas.addEventListener('wheel', (e) => {
      if (dimension !== '2d') return;
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
      const newScale = Math.max(0.3, Math.min(3.5, zoom2D.scale * zoomFactor));

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      zoom2D.x = mouseX - (mouseX - zoom2D.x) * (newScale / zoom2D.scale);
      zoom2D.y = mouseY - (mouseY - zoom2D.y) * (newScale / zoom2D.scale);
      zoom2D.scale = newScale;

      update2DTransform();
    }, { passive: false });

    if (elements.layoutToggle) {
      elements.layoutToggle.addEventListener('click', () => {
        graphLayout2D = graphLayout2D === 'chronological' ? 'force' : 'chronological';
        elements.layoutToggle.innerHTML = graphLayout2D === 'chronological' ? '⏱️ Chrono' : '🕸️ Radial';
        render2DGraph();
      });
    }
  }

  /* ==========================================================================
     UNIFIED SELECTION, DRAWER & SEARCH-TO-NODE NAVIGATION
     ========================================================================== */

  function selectDecision(decision) {
    if (!decision) return;
    selectedDecision = decision;
    renderDetailDrawer(decision);
    openDrawer();

    if (dimension === '3d') {
      update3DVisibility();
      focusNode(decision);
    } else {
      render2DGraph();
    }
  }

  function clearSelection() {
    selectedDecision = null;
    closeDrawer();
    if (dimension === '3d') {
      update3DVisibility();
    } else {
      render2DGraph();
    }
  }

  function openDrawer() {
    if (elements.detailDrawer) {
      elements.detailDrawer.classList.add('open');
    }
  }

  function closeDrawer() {
    if (elements.detailDrawer) {
      elements.detailDrawer.classList.remove('open');
    }
  }

  function renderDetailDrawer(d) {
    if (!elements.drawerContent) return;

    const upstreamDecs = [];
    const downstreamDecs = [];

    decisions.forEach(other => {
      (other.relationships || []).forEach(rel => {
        if (rel.target === d.id) {
          upstreamDecs.push({ decision: other, rel });
        }
      });
      if (other.id === d.id) {
        (d.relationships || []).forEach(rel => {
          const targetDec = decisions.find(x => x.id === rel.target);
          if (targetDec) {
            downstreamDecs.push({ decision: targetDec, rel });
          }
        });
      }
    });

    const alternativesHtml = (d.alternatives || []).map(alt => `
      <li class="alternative-item">
        <div class="alternative-opt">❌ ${escapeHtml(alt.option)}</div>
        <div class="alternative-tradeoff"><strong>Trade-off:</strong> ${escapeHtml(alt.trade_off)}</div>
      </li>
    `).join('') || '<div class="detail-text" style="color:var(--text-muted)">None recorded.</div>';

    const upstreamChipsHtml = upstreamDecs.map(item => `
      <div class="rel-chip" onclick="window.selectDecisionById('${item.decision.id}')">
        <div>
          <span style="font-weight:600; color:var(--accent-green); font-size:0.75rem;">← ${item.rel.type}</span>
          <div style="font-weight:600; color:var(--text-primary);">${item.decision.id}: ${escapeHtml(item.decision.title)}</div>
        </div>
        <span class="badge badge-cat-${item.decision.category}">${item.decision.category}</span>
      </div>
    `).join('') || '<div class="detail-text" style="color:var(--text-muted)">No upstream parents recorded.</div>';

    const downstreamChipsHtml = downstreamDecs.map(item => `
      <div class="rel-chip" onclick="window.selectDecisionById('${item.decision.id}')">
        <div>
          <span style="font-weight:600; color:var(--accent-gold); font-size:0.75rem;">→ ${item.rel.type}</span>
          <div style="font-weight:600; color:var(--text-primary);">${item.decision.id}: ${escapeHtml(item.decision.title)}</div>
        </div>
        <span class="badge badge-cat-${item.decision.category}">${item.decision.category}</span>
      </div>
    `).join('') || '<div class="detail-text" style="color:var(--text-muted)">No downstream consequences recorded.</div>';

    elements.drawerContent.innerHTML = `
      <div class="drawer-header">
        <div class="drawer-title-group">
          <div class="drawer-badges">
            <span class="badge badge-cat-${d.category}">${d.category}</span>
            <span class="badge badge-status-${d.status}">${d.status}</span>
            <span class="badge badge-sig-${d.significance}">${d.significance} sig</span>
            <span class="badge badge-ev-${d.evidence_status}">${d.evidence_status}</span>
          </div>
          <div class="card-id">${d.id} • ${(d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp) || ''}</div>
          <div class="drawer-title">${escapeHtml(d.title)}</div>
        </div>
        <button class="drawer-close-btn" id="drawer-close-btn">&times;</button>
      </div>

      <div class="drawer-body">
        <div class="detail-section">
          <div class="detail-section-title">Summary & Core Choice</div>
          <div class="detail-text" style="font-weight:600; margin-bottom:0.35rem;">${escapeHtml(d.summary)}</div>
          <div class="detail-text">${escapeHtml(d.choice)}</div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Context & Motivation</div>
          <div class="detail-text">${escapeHtml(d.context)}</div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Evidenced Alternatives & Rejected Options</div>
          <ul class="alternatives-list">
            ${alternativesHtml}
          </ul>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Evidence & Provenance</div>
          <div class="evidence-box">${escapeHtml((d.provenance && d.provenance.evidence_excerpt) || 'Direct implementation record.')}</div>
          <div class="provenance-meta" style="margin-top:0.5rem;">
            <span>Source Type:</span> <strong>${escapeHtml((d.provenance && (d.provenance.source_type || d.provenance.source)) || 'N/A')}</strong>
            <span>File Path:</span> <code>${escapeHtml((d.provenance && d.provenance.file_path) || 'N/A')}</code>
            <span>Session / Conv ID:</span> <code>${escapeHtml(((d.provenance && d.provenance.conversation_id) || d.session_id || 'N/A').slice(0, 18))}</code>
            <span>Authorship:</span> <strong>${escapeHtml(d.provenance ? ((d.provenance.authors || []).join(', ') || d.provenance.author || 'N/A') : 'N/A')}</strong>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Session & Conversation Context</div>
          ${(() => {
            const matchedSession = sessions.find(s => s.id === d.session_id || s.conversation_id === d.session_id || (d.provenance && s.conversation_id === d.provenance.conversation_id));
            if (!matchedSession) {
              return `<div class="detail-text" style="color:var(--text-muted)">Session ID: ${escapeHtml(d.session_id || 'N/A')}</div>`;
            }
            const logs = matchedSession.conversation_logs || [];
            const logsHtml = logs.map(l => `
              <div class="conversation-log-turn role-${escapeHtml(l.role)}">
                <div class="conversation-log-header">
                  <span>${l.role === 'user' ? '👤 Developer Prompt' : '🤖 Agent Rationale'}</span>
                  <span>${escapeHtml(l.timestamp || '')}</span>
                </div>
                <div class="conversation-log-content">${escapeHtml(l.content)}</div>
              </div>
            `).join('') || '<div class="detail-text" style="color:var(--text-muted); padding:0.5rem;">No archived dialogue turns recorded.</div>';

            return `
              <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:0.75rem; margin-bottom:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                  <span class="badge" style="background:var(--accent-blue-bg); color:var(--accent-blue); font-weight:700;">💬 ${matchedSession.id}</span>
                  <span style="font-size:0.75rem; color:var(--text-muted);">${matchedSession.date} • Epoch ${matchedSession.epoch}</span>
                </div>
                <div style="font-weight:700; color:var(--text-primary); font-size:0.95rem; margin-bottom:0.3rem;">${escapeHtml(matchedSession.title)}</div>
                <div style="font-size:0.83rem; color:var(--text-secondary); line-height:1.45; margin-bottom:0.5rem;">${escapeHtml(matchedSession.summary)}</div>
                <div class="provenance-meta" style="font-size:0.75rem; border-top:1px solid var(--border-color); padding-top:0.4rem;">
                  <span>Agent Role:</span> <strong>${escapeHtml(matchedSession.agent_name || 'main_assistant')}</strong>
                  <span>Steps / Msgs:</span> <strong>${matchedSession.step_count} steps • ${matchedSession.message_count} msgs</strong>
                  <span>Participants:</span> <strong>${escapeHtml((matchedSession.participants || []).join(', '))}</strong>
                </div>
              </div>

              <details class="conversation-logs-accordion" open>
                <summary>💬 Dialogue & Transcript Logs (${logs.length} excerpts)</summary>
                <div class="conversation-logs-list">
                  ${logsHtml}
                </div>
              </details>
            `;
          })()}
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Implementation Footprint</div>
          <div class="detail-text" style="font-family:var(--font-mono); font-size:0.8rem; background:var(--bg-card); padding:0.6rem; border-radius:var(--radius-md);">
            ${((d.implementation && d.implementation.files) || []).map(f => `<div>📄 ${escapeHtml(f)}</div>`).join('')}
            ${((d.implementation && d.implementation.services) || []).map(s => `<div style="color:var(--accent-teal);">⚙️ ${escapeHtml(s)}</div>`).join('')}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Observed Outcomes & Side Effects</div>
          <div class="detail-text" style="margin-bottom:0.35rem;"><strong>Observed:</strong> ${escapeHtml(d.observed_effects)}</div>
          <div class="detail-text" style="color:var(--text-secondary);"><strong>Side Effects / Risks:</strong> ${escapeHtml(d.side_effects || d.risks || 'None reported.')}</div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Lessons Learned</div>
          <div style="display:flex; flex-direction:column; gap:0.4rem;">
            <div style="background:var(--bg-card); border-left:3px solid var(--accent-green); padding:0.5rem 0.75rem; border-radius:0 4px 4px 0; font-size:0.83rem;">
              <span class="badge badge-ev-documented" style="margin-bottom:0.2rem;">Documented Lesson</span>
              <div>${escapeHtml((d.lessons && d.lessons.documented) || 'None documented explicitly.')}</div>
            </div>
            <div style="background:var(--bg-card); border-left:3px solid var(--accent-gold); padding:0.5rem 0.75rem; border-radius:0 4px 4px 0; font-size:0.83rem;">
              <span class="badge badge-ev-inferred" style="margin-bottom:0.2rem;">Inferred Lesson</span>
              <div>${escapeHtml((d.lessons && d.lessons.inferred) || 'None inferred.')}</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Upstream Motivations & Dependencies</div>
          <div class="rel-chips-group">
            ${upstreamChipsHtml}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Downstream Consequences & Influences</div>
          <div class="rel-chips-group">
            ${downstreamChipsHtml}
          </div>
        </div>

        <div class="detail-section" style="margin-bottom:1.5rem;">
          <div class="detail-section-title">Open Questions & Knowledge Gaps</div>
          <div class="detail-text" style="color:var(--accent-gold); font-style:italic;">
            ❓ ${escapeHtml(d.open_questions || 'All key claims verified.')}
          </div>
        </div>
      </div>
    `;

    document.getElementById('drawer-close-btn').addEventListener('click', closeDrawer);
  }

  // Global helper for search-to-node & chip navigation
  window.selectDecisionById = function (id) {
    const target = decisions.find(d => d.id === id);
    if (!target) return;

    // Switch to graph tab if currently elsewhere
    if (activeTab !== 'graph') {
      switchTab('graph');
    }

    selectDecision(target);
  };

  /* ==========================================================================
     TIMELINE, EXPLORER & SOURCES VIEWS
     ========================================================================== */

  function renderTimeline() {
    const track = elements.timelineTrack;
    if (!track) return;
    track.innerHTML = '';

    if (decisions.length === 0 && sessions.length === 0) {
      track.innerHTML = `
        <div style="padding: 3rem; text-align: center; color: var(--text-secondary);">
          <h3>No decisions or sessions recorded yet</h3>
          <p style="margin-top:0.5rem; font-size:0.9rem;">Run <code>python init_decision_graph.py</code> or add records to <code>data/decisions.json</code> and run <code>python sync_decisions.py</code>.</p>
        </div>
      `;
      return;
    }

    const epochMap = new Map();
    sessions.forEach(s => {
      const epNum = typeof s.epoch === 'number' ? s.epoch : 1;
      if (!epochMap.has(epNum)) {
        epochMap.set(epNum, {
          num: epNum,
          id: `ep-${epNum}`,
          title: s.epoch_title || `Epoch ${epNum}`,
          start: s.date || s.start_time || ''
        });
      }
    });
    decisions.forEach(d => {
      const epNum = typeof d.epoch === 'number' ? d.epoch : 1;
      if (!epochMap.has(epNum)) {
        const dDate = (d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp) || '';
        epochMap.set(epNum, {
          num: epNum,
          id: `ep-${epNum}`,
          title: d.epoch_title || `Epoch ${epNum}`,
          start: dDate
        });
      }
    });
    if (epochMap.size === 0) {
      epochMap.set(1, { num: 1, id: 'ep-1', title: 'Epoch 1', start: '' });
    }
    const epochs = Array.from(epochMap.values()).sort((a, b) => a.num - b.num);

    if (timelineGroupMode && sessions.length > 0) {
      // Group by Session Mode (with Epoch preserved)
      epochs.forEach((ep) => {
        const epNum = ep.num;
        const epochSessions = sessions.filter(s => (typeof s.epoch === 'number' ? s.epoch : 1) === epNum);
        if (epochSessions.length === 0) return;

        // Render Epoch Marker
        const epochMarker = document.createElement('div');
        epochMarker.setAttribute('class', 'timeline-epoch-marker');
        epochMarker.innerHTML = `
          <div class="epoch-dot"></div>
          <div class="epoch-title">${escapeHtml(ep.title)}</div>
        `;
        track.appendChild(epochMarker);

        // Render Session Groups within this Epoch
        epochSessions.forEach(ses => {
          const sesGroup = document.createElement('div');
          sesGroup.setAttribute('class', 'timeline-session-group');

          const sessionDecisions = decisions.filter(d => 
            d.session_id === ses.id || 
            (ses.decisions && ses.decisions.includes(d.id))
          );

          sesGroup.innerHTML = `
            <div class="timeline-session-header">
              <div class="timeline-session-title">
                <span class="badge" style="background:var(--accent-blue-bg); color:var(--accent-blue); font-weight:700;">💬 ${ses.id}</span>
                <span>${escapeHtml(ses.title)}</span>
              </div>
              <div class="timeline-session-meta">
                <span>📅 ${ses.date || ses.start_time || ''}</span>
                <span>•</span>
                <span>⚡ ${ses.step_count} steps</span>
                <span>•</span>
                <span>🎯 ${sessionDecisions.length} decisions</span>
              </div>
            </div>
            <div class="timeline-card-summary" style="margin-bottom:1rem; font-size:0.84rem; color:var(--text-secondary);">${escapeHtml(ses.summary)}</div>
            <div class="timeline-session-cards" id="session-cards-${ses.id}"></div>
          `;

          const cardsContainer = sesGroup.querySelector(`#session-cards-${ses.id}`);
          sessionDecisions.forEach(d => {
            const dateStr = (d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp) || '';
            const card = document.createElement('div');
            card.setAttribute('class', 'timeline-node-card');
            card.innerHTML = `
              <div class="timeline-card-dot" style="background:${CATEGORY_COLORS[d.category] || '#58a6ff'}"></div>
              <div class="timeline-card-header">
                <div style="display:flex; gap:0.4rem; align-items:center;">
                  <span class="badge badge-cat-${d.category}">${d.category}</span>
                  <span class="badge badge-status-${d.status}">${d.status}</span>
                  ${d.status === 'reversed' ? '<span class="badge badge-status-reversed">↺ REVERSAL</span>' : ''}
                </div>
                <div class="timeline-date">${dateStr}</div>
              </div>
              <div class="timeline-card-title">${d.id}: ${escapeHtml(d.title)}</div>
              <div class="timeline-card-summary">${escapeHtml(d.summary)}</div>
            `;
            card.addEventListener('click', () => {
              window.selectDecisionById(d.id);
            });
            cardsContainer.appendChild(card);
          });

          track.appendChild(sesGroup);
        });
      });
    } else {
      // Flat Chronological Mode
      const sorted = [...decisions].sort((a, b) => {
        const da = (a.dates && (a.dates.proposed || a.dates.implemented)) || (a.provenance && a.provenance.timestamp) || '';
        const db = (b.dates && (b.dates.proposed || b.dates.implemented)) || (b.provenance && b.provenance.timestamp) || '';
        return new Date(da || 0) - new Date(db || 0);
      });

      let renderedEpochNums = new Set();

      sorted.forEach(d => {
        const dateStr = (d.dates && (d.dates.proposed || d.dates.implemented)) || (d.provenance && d.provenance.timestamp) || '';
        const epNum = typeof d.epoch === 'number' ? d.epoch : 1;
        if (!renderedEpochNums.has(epNum)) {
          renderedEpochNums.add(epNum);
          const epObj = epochMap.get(epNum) || { title: `Epoch ${epNum}` };
          const epochMarker = document.createElement('div');
          epochMarker.setAttribute('class', 'timeline-epoch-marker');
          epochMarker.innerHTML = `
            <div class="epoch-dot"></div>
            <div class="epoch-title">${escapeHtml(epObj.title)}</div>
          `;
          track.appendChild(epochMarker);
        }

        const card = document.createElement('div');
        card.setAttribute('class', 'timeline-node-card');
        card.innerHTML = `
          <div class="timeline-card-dot" style="background:${CATEGORY_COLORS[d.category] || '#58a6ff'}"></div>
          <div class="timeline-card-header">
            <div>
              <span class="badge badge-cat-${d.category}">${d.category}</span>
              <span class="badge badge-status-${d.status}">${d.status}</span>
              ${d.status === 'reversed' ? '<span class="badge badge-status-reversed">↺ REVERSAL</span>' : ''}
              <span class="badge" style="background:var(--accent-blue-bg); color:var(--accent-blue); font-size:0.7rem; font-family:var(--font-mono);">${d.session_id || ''}</span>
            </div>
            <div class="timeline-date">${dateStr}</div>
          </div>
          <div class="timeline-card-title">${d.id}: ${escapeHtml(d.title)}</div>
          <div class="timeline-card-summary">${escapeHtml(d.summary)}</div>
        `;

        card.addEventListener('click', () => {
          window.selectDecisionById(d.id);
        });

        track.appendChild(card);
      });
    }
  }

  function renderExplorer() {
    const container = elements.explorerCards;
    if (!container) return;
    container.innerHTML = '';

    const q = activeFilters.search.toLowerCase().trim();
    const sesFilter = activeFilters.session;

    if (explorerViewMode === 'sessions') {
      // Sessions View Mode
      let filteredSessions = sessions.filter(s => {
        const matchSearch = !q || (
          s.id.toLowerCase().includes(q) ||
          s.title.toLowerCase().includes(q) ||
          s.summary.toLowerCase().includes(q) ||
          (s.agent_name || '').toLowerCase().includes(q) ||
          (s.decisions || []).some(id => id.toLowerCase().includes(q))
        );
        const matchSes = !sesFilter || sesFilter === 'all' || s.id === sesFilter;
        return matchSearch && matchSes;
      });

      if (filteredSessions.length === 0) {
        container.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; color: var(--text-secondary);">
            <h3>No sessions match the selected filters</h3>
            <p style="margin-top:0.5rem; font-size:0.9rem;">Try clearing search keywords or resetting filter dropdowns.</p>
          </div>
        `;
        return;
      }

      filteredSessions.forEach(s => {
        const card = document.createElement('div');
        card.setAttribute('class', 'session-card');
        card.innerHTML = `
          <div>
            <div class="session-card-header">
              <div>
                <div class="session-card-id-row">
                  <span class="badge" style="background:var(--accent-blue-bg); color:var(--accent-blue); font-weight:700;">💬 ${s.id}</span>
                  <span class="badge badge-status-validated">Epoch ${s.epoch}</span>
                  <span style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">${s.date}</span>
                </div>
                <div class="session-card-title">${escapeHtml(s.title)}</div>
              </div>
            </div>
            <div class="session-card-summary" style="margin-top:0.5rem;">${escapeHtml(s.summary)}</div>
            <div style="margin-top:0.75rem;">
              <div style="font-size:0.75rem; font-weight:600; color:var(--text-secondary); margin-bottom:0.3rem;">Mapped Decisions (${(s.decisions || []).length}):</div>
              <div class="session-decisions-pills">
                ${(s.decisions || []).map(decId => `<span class="session-decision-pill" onclick="event.stopPropagation(); window.selectDecisionById('${decId}')">${decId}</span>`).join('') || '<span style="font-size:0.75rem; color:var(--text-muted);">None</span>'}
              </div>
            </div>
          </div>
          <div class="session-card-footer">
            <span>🤖 ${escapeHtml(s.agent_name || 'main_assistant')}</span>
            <span>⚡ ${s.step_count} steps • 💬 ${s.message_count} msgs</span>
          </div>
        `;

        card.addEventListener('click', () => {
          activeFilters.session = s.id;
          if (elements.explorerSessionFilter) {
            elements.explorerSessionFilter.value = s.id;
          }
          explorerViewMode = 'decisions';
          if (elements.explorerToggleDecisions) elements.explorerToggleDecisions.classList.add('active');
          if (elements.explorerToggleSessions) elements.explorerToggleSessions.classList.remove('active');
          renderExplorer();
        });

        container.appendChild(card);
      });
      return;
    }

    // Decisions View Mode
    const cat = activeFilters.category;
    const stat = activeFilters.status;
    const sig = activeFilters.significance;
    const ev = activeFilters.evidence;

    let filtered = decisions.filter(d => {
      const matchSearch = !q || (
        d.id.toLowerCase().includes(q) ||
        d.title.toLowerCase().includes(q) ||
        d.summary.toLowerCase().includes(q) ||
        d.choice.toLowerCase().includes(q) ||
        ((d.lessons && d.lessons.documented) || '').toLowerCase().includes(q) ||
        ((d.provenance && d.provenance.evidence_excerpt) || '').toLowerCase().includes(q) ||
        (d.session_id || '').toLowerCase().includes(q) ||
        (d.session_title || '').toLowerCase().includes(q)
      );

      const matchCat = cat === 'all' || d.category === cat;
      const matchStat = stat === 'all' || d.status === stat;
      const matchSig = sig === 'all' || d.significance === sig;
      const matchEv = ev === 'all' || d.evidence_status === ev;
      const matchSes = !sesFilter || sesFilter === 'all' || d.session_id === sesFilter;

      return matchSearch && matchCat && matchStat && matchSig && matchEv && matchSes;
    });

    filtered.sort((a, b) => {
      const da = (a.dates && (a.dates.proposed || a.dates.implemented)) || (a.provenance && a.provenance.timestamp) || '';
      const db = (b.dates && (b.dates.proposed || b.dates.implemented)) || (b.provenance && b.provenance.timestamp) || '';
      if (activeFilters.sort === 'date-desc') {
        return new Date(db || 0) - new Date(da || 0);
      } else if (activeFilters.sort === 'date-asc') {
        return new Date(da || 0) - new Date(db || 0);
      } else if (activeFilters.sort === 'sig') {
        const weight = { foundational: 4, high: 3, medium: 2, low: 1 };
        return (weight[b.significance] || 0) - (weight[a.significance] || 0);
      } else if (activeFilters.sort === 'title') {
        return a.title.localeCompare(b.title);
      }
      return 0;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; color: var(--text-secondary);">
          <h3>No decisions match the selected filters</h3>
          <p style="margin-top:0.5rem; font-size:0.9rem;">Try clearing search keywords or resetting filter dropdowns.</p>
        </div>
      `;
      return;
    }

    filtered.forEach(d => {
      const card = document.createElement('div');
      card.setAttribute('class', 'decision-card');
      card.innerHTML = `
        <div class="card-top">
          <div class="card-meta-row">
            <span class="card-id">${d.id}</span>
            <div style="display:flex; gap:0.3rem; align-items:center;">
              <span class="badge badge-cat-${d.category}">${d.category}</span>
              <span class="badge badge-status-${d.status}">${d.status}</span>
              <span class="badge" style="background:var(--accent-blue-bg); color:var(--accent-blue); font-size:0.7rem; font-family:var(--font-mono);">${d.session_id || ''}</span>
            </div>
          </div>
          <div class="card-title">${escapeHtml(d.title)}</div>
          <div class="card-summary">${escapeHtml(d.summary)}</div>
        </div>
        <div class="card-bottom">
          <span class="card-rels-count">🔗 ${(d.relationships || []).length} relationships</span>
          <span class="badge badge-ev-${d.evidence_status}">${d.evidence_status}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        window.selectDecisionById(d.id);
      });

      container.appendChild(card);
    });
  }

  function renderSources() {
    const tbody = elements.sourcesTableBody;
    if (!tbody) return;
    tbody.innerHTML = '';

    if (sources.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="5" style="padding: 2rem; text-align: center; color: var(--text-secondary);">No sources recorded yet.</td>`;
      tbody.appendChild(tr);
      return;
    }

    sources.forEach(src => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-family:var(--font-mono); font-weight:700;">${src.id}</td>
        <td>
          <div style="font-weight:600; color:var(--text-primary);">${escapeHtml(src.name)}</div>
          <div style="color:var(--text-secondary); font-size:0.78rem;">${escapeHtml(src.description)}</div>
        </td>
        <td><code style="font-size:0.75rem;">${escapeHtml(src.path)}</code></td>
        <td><span class="badge badge-cat-${src.type.includes('rule') ? 'security' : src.type.includes('skill') ? 'ai' : 'product'}">${src.type}</span></td>
        <td>
          ${src.accessible 
            ? '<span class="badge badge-status-validated">✓ Accessible</span>' 
            : '<span class="badge badge-status-reversed">✗ Inaccessible</span>'}
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function initExplorerListeners() {
    if (elements.searchInput) {
      elements.searchInput.addEventListener('input', (e) => {
        activeFilters.search = e.target.value;
        renderExplorer();
      });
    }

    if (elements.categoryFilter) {
      elements.categoryFilter.addEventListener('change', (e) => {
        activeFilters.category = e.target.value;
        renderExplorer();
      });
    }

    if (elements.statusFilter) {
      elements.statusFilter.addEventListener('change', (e) => {
        activeFilters.status = e.target.value;
        renderExplorer();
      });
    }

    if (elements.significanceFilter) {
      elements.significanceFilter.addEventListener('change', (e) => {
        activeFilters.significance = e.target.value;
        renderExplorer();
      });
    }

    if (elements.evidenceFilter) {
      elements.evidenceFilter.addEventListener('change', (e) => {
        activeFilters.evidence = e.target.value;
        renderExplorer();
      });
    }

    if (elements.sortFilter) {
      elements.sortFilter.addEventListener('change', (e) => {
        activeFilters.sort = e.target.value;
        renderExplorer();
      });
    }

    if (elements.explorerSessionFilter) {
      elements.explorerSessionFilter.addEventListener('change', (e) => {
        activeFilters.session = e.target.value;
        renderExplorer();
      });
    }

    if (elements.explorerToggleDecisions) {
      elements.explorerToggleDecisions.addEventListener('click', () => {
        explorerViewMode = 'decisions';
        elements.explorerToggleDecisions.classList.add('active');
        if (elements.explorerToggleSessions) elements.explorerToggleSessions.classList.remove('active');
        renderExplorer();
      });
    }

    if (elements.explorerToggleSessions) {
      elements.explorerToggleSessions.addEventListener('click', () => {
        explorerViewMode = 'sessions';
        elements.explorerToggleSessions.classList.add('active');
        if (elements.explorerToggleDecisions) elements.explorerToggleDecisions.classList.remove('active');
        renderExplorer();
      });
    }

    if (elements.timelineGroupToggle) {
      elements.timelineGroupToggle.addEventListener('click', () => {
        timelineGroupMode = !timelineGroupMode;
        elements.timelineGroupToggle.classList.toggle('active', timelineGroupMode);
        elements.timelineGroupToggle.textContent = timelineGroupMode ? '👥 Grouped by Session' : '📋 Flat Chronological';
        renderTimeline();
      });
    }
  }

  function handleResize() {
    const container = elements.graphCanvasWrapper;
    if (!container) return;
    const width = container.clientWidth;
    const height = container.clientHeight;

    if (renderer3D && camera3D) {
      camera3D.aspect = width / height;
      camera3D.updateProjectionMatrix();
      renderer3D.setSize(width, height);
    }

    if (dimension === '2d') {
      render2DGraph();
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.addEventListener('resize', handleResize);

  // App Initialization
  document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initTheme();
    initTabs();
    init2DGraphInteraction();
    initExplorerListeners();
    loadData();
  });

})();
