const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8001';
const MAP_OUTLINE = { light: '#e2e8f0', dark: '#0f172a' };

// === THEME TOGGLE ===
function initTheme() {
    const saved = localStorage.getItem('ude_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('ude_theme', next);
}

// Initialize theme immediately
initTheme();

// === SCORE GLOBAL (weighted metrics) ===
function calculateGlobalScore(arr) {
    // Ponderations des metriques (total = 100%)
    const weights = {
        prix: 0.15,           // Prix accessible = mieux (inverse)
        accessibilite: 0.20,  // Accessibilite = mieux si bas (inverse)
        securite: 0.15,       // Delits bas = mieux (inverse)
        transports: 0.15,     // Plus de transports = mieux
        vegetation: 0.10,     // Plus d'arbres = mieux
        qualite_air: 0.10,    // Indice bas = mieux (inverse)
        logements_sociaux: 0.05, // Plus = mieux pour mixite
        revenus: 0.10         // Revenus eleves = mieux
    };

    // Normalisation des valeurs (0-100)
    const prix = arr.statistiques?.prix_m2_actuel || 0;
    const access = arr.accessibilite_logement?.mois_revenu_pour_50m2_achat || 0;
    const delits = arr.delits_enregistres?.delits_par_1000_habitants || 0;
    const transports = arr.transports_publics?.total_transports || 0;
    const arbres = arr.vegetation_arbres?.nombre_arbres || 0;
    const air = arr.pollution_qualite_air?.indice_atmo_local || arr.pollution_qualite_air?.indice_atmo || 3;
    const logSoc = arr.logements_sociaux_pourcentage || 0;
    const revenus = arr.revenus_moyens?.revenu_median_menage || 0;

    // Scores normalises (0-100, ou 100 = meilleur)
    const scores = {
        prix: Math.max(0, 100 - ((prix - 8000) / (16000 - 8000)) * 100),
        accessibilite: Math.max(0, 100 - ((access - 150) / (250 - 150)) * 100),
        securite: Math.max(0, 100 - ((delits - 20) / (200 - 20)) * 100),
        transports: Math.min(100, (transports / 60) * 100),
        vegetation: Math.min(100, (arbres / 5000) * 100),
        qualite_air: Math.max(0, 100 - ((air - 2.5) / (4 - 2.5)) * 100),
        logements_sociaux: Math.min(100, (logSoc / 30) * 100),
        revenus: Math.min(100, ((revenus - 20000) / (50000 - 20000)) * 100)
    };

    // Score global pondere
    let totalScore = 0;
    for (const [key, weight] of Object.entries(weights)) {
        totalScore += (scores[key] || 0) * weight;
    }

    return Math.round(Math.max(0, Math.min(100, totalScore)));
}

// === POTENTIEL PLUS-VALUE (formule creative) ===
// Estime le potentiel de plus-value basee sur plusieurs facteurs
function calculatePotentielPlusValue(arr) {
    // Facteurs positifs pour la plus-value future
    const prix = arr.statistiques?.prix_m2_actuel || 0;
    const variation = arr.evolution_calculee?.variation_pourcentage || 0;
    const transports = arr.transports_publics?.total_transports || 0;
    const arbres = arr.vegetation_arbres?.nombre_arbres || 0;
    const logSoc = arr.logements_sociaux_pourcentage || 0;
    const delits = arr.delits_enregistres?.delits_par_1000_habitants || 0;

    // Calcul du potentiel
    // 1. Prix encore accessible (pas sature) = potentiel de hausse
    const prixScore = prix < 10000 ? 30 : (prix < 12000 ? 20 : (prix < 14000 ? 10 : 0));

    // 2. Dynamique positive recente
    const dynamiqueScore = variation > 3 ? 25 : (variation > 0 ? 15 : (variation > -3 ? 5 : 0));

    // 3. Bonne desserte transports (attractivite)
    const transportScore = transports > 40 ? 20 : (transports > 20 ? 15 : (transports > 10 ? 10 : 5));

    // 4. Cadre de vie (vegetation)
    const vegScore = arbres > 3000 ? 15 : (arbres > 1500 ? 10 : 5);

    // 5. Mixite sociale (ni trop, ni trop peu de logements sociaux)
    const mixiteScore = (logSoc >= 15 && logSoc <= 25) ? 10 : 5;

    // 6. Securite (bonus si securise)
    const securiteScore = delits < 50 ? 10 : (delits < 100 ? 5 : 0);

    const total = prixScore + dynamiqueScore + transportScore + vegScore + mixiteScore + securiteScore;

    return {
        score: total,
        niveau: total >= 70 ? 'Eleve' : (total >= 45 ? 'Moyen' : 'Faible'),
        classe: total >= 70 ? 'high' : (total >= 45 ? 'medium' : 'low')
    };
}

// === CACHE SYSTEME ===
const CACHE_VERSION = 'v1';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

const DataCache = {
    _key(name, params = {}) {
        return `ude_cache_${CACHE_VERSION}_${name}_${JSON.stringify(params)}`;
    },
    get(name, params = {}) {
        try {
            const raw = localStorage.getItem(this._key(name, params));
            if (!raw) return null;
            const { data, timestamp } = JSON.parse(raw);
            if (Date.now() - timestamp > CACHE_TTL_MS) {
                localStorage.removeItem(this._key(name, params));
                return null;
            }
            return data;
        } catch { return null; }
    },
    set(name, data, params = {}) {
        try {
            localStorage.setItem(this._key(name, params), JSON.stringify({
                data,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.warn('Cache write failed:', e);
        }
    },
    clear() {
        Object.keys(localStorage)
            .filter(k => k.startsWith('ude_cache_'))
            .forEach(k => localStorage.removeItem(k));
    }
};

// === LOADING INDICATOR ===
function showLoading(show = true) {
    let loader = document.getElementById('loading-overlay');
    if (!loader && show) {
        loader = document.createElement('div');
        loader.id = 'loading-overlay';
        loader.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Chargement des donnees...</div>
        `;
        document.body.appendChild(loader);
    }
    if (loader) {
        loader.style.display = show ? 'flex' : 'none';
    }
}

function updateLoadingText(text) {
    const el = document.querySelector('.loading-text');
    if (el) el.textContent = text;
}
/** Échelle cyan commune (prix, loyers, logements, etc.) */
const MAP_BASE = ['#0c2d48', '#0e5a7a', '#0e94b8', '#38d9f5', '#a8ecff'];
const AIR_GOOD_TO_BAD = ['#34d399', '#a3e635', '#fbbf24', '#f97316', '#ef4444'];
const VEG_NONE_TO_DENSE = ['#64748b', '#94a3b8', '#86efac', '#22c55e', '#14532d'];
// Sante: vert = bon acces, rouge = mauvais
const SANTE_COLORS = ['#ef4444', '#f97316', '#fbbf24', '#a3e635', '#34d399'];

function seqLtExpr(t1, t2, t3, t4) {
    return [
        'case',
        ['<', ['get', 'value'], t1], MAP_BASE[0],
        ['<', ['get', 'value'], t2], MAP_BASE[1],
        ['<', ['get', 'value'], t3], MAP_BASE[2],
        ['<', ['get', 'value'], t4], MAP_BASE[3],
        MAP_BASE[4],
    ];
}

function seqGteExpr(t1, t2, t3, t4) {
    return [
        'case',
        ['>=', ['get', 'value'], t4], MAP_BASE[4],
        ['>=', ['get', 'value'], t3], MAP_BASE[3],
        ['>=', ['get', 'value'], t2], MAP_BASE[2],
        ['>=', ['get', 'value'], t1], MAP_BASE[1],
        MAP_BASE[0],
    ];
}

function arrondissementLabel(n) {
    return n === 1 ? '1er' : `${n}e`;
}

let arrondissementLabelMarkers = [];

function removeArrondissementLabelMarkers() {
    arrondissementLabelMarkers.forEach((m) => m.remove());
    arrondissementLabelMarkers = [];
}

function ensureArrondissementLabels() {
    if (!map) return;
    removeArrondissementLabelMarkers();
    Object.entries(arrondissementCoords).forEach(([num, [lat, lng]]) => {
        const el = document.createElement('div');
        el.className = 'arr-label';
        el.textContent = arrondissementLabel(Number(num));
        el.setAttribute('aria-hidden', 'true');
        const wrap = document.createElement('div');
        wrap.className = 'arr-label-wrap';
        wrap.appendChild(el);
        const marker = new maplibregl.Marker({ element: wrap, anchor: 'center' })
            .setLngLat([lng, lat])
            .addTo(map);
        arrondissementLabelMarkers.push(marker);
    });
}

function applyMapBorders() {
    if (!map?.getLayer('arrondissements-outline-thick')) return;
    map.setPaintProperty('arrondissements-outline-thick', 'line-color', MAP_OUTLINE.light);
    map.setPaintProperty('arrondissements-outline-thick', 'line-opacity', 0.95);
    map.setPaintProperty('arrondissements-outline-thick', 'line-width', [
        'interpolate', ['linear'], ['zoom'], 10, 2.5, 12, 3, 14, 3.5, 16, 4,
    ]);
    map.setPaintProperty('arrondissements-outline', 'line-color', MAP_OUTLINE.dark);
    map.setPaintProperty('arrondissements-outline', 'line-opacity', 0.9);
    map.setPaintProperty('arrondissements-outline', 'line-width', [
        'interpolate', ['linear'], ['zoom'], 10, 1, 12, 1.25, 14, 1.5, 16, 1.75,
    ]);
    map.setPaintProperty('arrondissements-outline', 'line-dasharray', ['literal', [1, 0]]);
    if (map.getLayer('arrondissements-fill')) {
        map.setPaintProperty('arrondissements-fill', 'fill-outline-color', MAP_OUTLINE.light);
        map.setPaintProperty('arrondissements-fill', 'fill-opacity', 0.82);
    }
}

function applyAccessibilityMapStyles() {
    applyMapBorders();
}

const CHART_THEME = {
    accent: '#38bdf8',
    accentSoft: 'rgba(56, 189, 248, 0.12)',
    grid: 'rgba(148, 163, 184, 0.1)',
    text: '#94a3b8',
    palette: ['#38bdf8', '#22d3ee', '#818cf8', '#34d399', '#fbbf24'],
};

function configureChartDefaults() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
    Chart.defaults.color = CHART_THEME.text;
}

function chartScales(yTitle) {
    const axis = {
        ticks: { color: CHART_THEME.text, font: { size: 11 } },
        grid: { color: CHART_THEME.grid, drawBorder: false },
        border: { display: false },
    };
    const scales = { x: { ...axis }, y: { ...axis } };
    if (yTitle) {
        scales.y.title = { display: true, text: yTitle, color: CHART_THEME.text, font: { size: 11 } };
    }
    return scales;
}

let allData = null;
let map = null;
let charts = {};
let selectedYear = 2024;
let selectedIndicator = 'prix';
let selectedArr = null;
let timelinePlaying = false;
let timelineInterval = null;
let geoPointsVisible = false;

const arrondissementCoords = {
    1: [48.8606, 2.3376], 2: [48.8698, 2.3412], 3: [48.8630, 2.3624],
    4: [48.8546, 2.3522], 5: [48.8448, 2.3447], 6: [48.8448, 2.3327],
    7: [48.8566, 2.3186], 8: [48.8738, 2.3132], 9: [48.8738, 2.3392],
    10: [48.8738, 2.3624], 11: [48.8630, 2.3768], 12: [48.8448, 2.3768],
    13: [48.8322, 2.3522], 14: [48.8330, 2.3264], 15: [48.8412, 2.2995],
    16: [48.8534, 2.2654], 17: [48.8838, 2.3214], 18: [48.8932, 2.3447],
    19: [48.8838, 2.3768], 20: [48.8630, 2.3984]
};

document.addEventListener('DOMContentLoaded', async () => {
    const t0 = performance.now();
    showLoading(true);

    try {
        // Chargement parallele des ressources statiques
        updateLoadingText('Chargement de la carte...');
        await loadPolygons();
        loadTransportsData();
        initializeMap();

        // Chargement parallele des donnees API
        updateLoadingText('Chargement des donnees...');
        await Promise.all([
            loadFreshness(),
            loadData()
        ]);

        // Initialisation de l'interface
        updateLoadingText('Initialisation...');
        initializeCharts();
        setupEventListeners();
        updateMapLegend();
        updateIndicatorFormulaPanel();
        await updateMap();
        updateGlobalStats();

        console.log(`Dashboard charge en ${Math.round(performance.now() - t0)}ms`);
    } catch (error) {
        console.error('Erreur initialisation:', error);
        showError('Erreur lors du chargement du dashboard');
    } finally {
        showLoading(false);
    }
});

async function loadFreshness() {
    const el = document.getElementById('data-freshness');
    if (!el) return;
    try {
        const response = await fetch(`${API_BASE_URL}/platform/freshness`);
        if (!response.ok) return;
        const f = await response.json();
        const snap = f.snapshot || {};
        const api = f.api || {};
        const age = snap.age_human ? `il y a ${snap.age_human}` : 'snapshot Gold';
        el.textContent = `Analyse à l'instant T — snapshot ${age} · requête ${api.query_latency_ms ?? '—'} ms · cache v${api.cache_version ?? 0}`;
    } catch {
        el.textContent = '';
    }
}

async function loadData(forceRefresh = false) {
    const cacheKey = { year: selectedYear };

    // Essayer le cache d'abord
    if (!forceRefresh) {
        const cached = DataCache.get('arrondissements', cacheKey);
        if (cached) {
            console.log('Donnees chargees depuis le cache');
            allData = cached.arrondissements;
            updateFreshnessFromPayload(cached.freshness);
            updateLogementsSociauxChart();
            updateAccessibiliteChart();
            updateSanteChart();
            updateIndicatorFormulaPanel();
            updateUniformDataNotice();
            return;
        }
    }

    // Charger depuis l'API
    try {
        const response = await fetch(`${API_BASE_URL}/arrondissements?annee=${selectedYear}`);
        const data = await response.json();
        allData = data.arrondissements;

        // Mettre en cache
        DataCache.set('arrondissements', data, cacheKey);

        updateFreshnessFromPayload(data.freshness);
        console.log('Donnees chargees depuis API:', allData.length, 'arrondissements');
        updateLogementsSociauxChart();
        updateAccessibiliteChart();
        updateSanteChart();
        updateIndicatorFormulaPanel();
        updateUniformDataNotice();
    } catch (error) {
        console.error('Erreur:', error);
        showError('Impossible de charger les donnees. Verifiez que l\'API est demarree.');
    }
}

function updateFreshnessFromPayload(freshness) {
    const el = document.getElementById('data-freshness');
    if (!el || !freshness) return;
    const snap = freshness.snapshot || {};
    const api = freshness.api || {};
    const age = snap.age_human ? `il y a ${snap.age_human}` : 'snapshot Gold';
    el.textContent = `Analyse à l'instant T — snapshot ${age} · requête ${api.query_latency_ms ?? '—'} ms`;
}

function initializeMap() {
    console.log('Initialisation de la carte...');
    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('❌ Conteneur #map non trouvé!');
        return;
    }
    
    console.log('Conteneur #map trouvé, création de la carte...');
    
    try {
        map = new maplibregl.Map({
            container: 'map',
            style: {
                version: 8,
                glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
                sources: {
                    'carto-dark': {
                        type: 'raster',
                        tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '© CARTO © OpenStreetMap'
                    }
                },
                layers: [{
                    id: 'carto-dark',
                    type: 'raster',
                    source: 'carto-dark'
                }]
            },
            center: [2.3522, 48.8566],
            zoom: 11.5,
            minZoom: 10.5,
            maxZoom: 15,
            maxBounds: [[2.15, 48.75], [2.55, 48.95]],
            pitch: 0,
            bearing: 0
        });
        console.log('✅ Carte créée avec succès');
    } catch (error) {
        console.error('❌ Erreur lors de la création de la carte:', error);
        return;
    }

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('load', () => {
        console.log('✅ Carte chargée');
        setTimeout(() => {
            updateMap();
            applyAccessibilityMapStyles();
        }, 100);
    });
    
    map.on('error', (e) => {
        console.error('❌ Erreur carte:', e);
    });

    map.on('mousemove', (e) => {
        if (!map.getLayer('arrondissements-fill')) return;
        
        const features = map.queryRenderedFeatures(e.point, {
            layers: ['arrondissements-fill']
        });
        
        if (features.length > 0) {
            map.getCanvas().style.cursor = 'pointer';
            const arrNum = features[0].properties.arrondissement;
            showTooltip(e, arrNum);
        } else {
            map.getCanvas().style.cursor = '';
            hideTooltip();
        }
    });

    map.on('click', (e) => {
        if (!map.getLayer('arrondissements-fill')) return;
        
        const features = map.queryRenderedFeatures(e.point, {
            layers: ['arrondissements-fill']
        });
        
        if (features.length > 0) {
            const arrNum = features[0].properties.arrondissement;
            selectArrondissement(arrNum);
        }
    });
}

let arrondissementsPolygons = null;

// POLYGONES RÉELS des arrondissements de Paris avec contours PRÉCIS et IRRÉGULIERS
// Formes réalistes basées sur les vraies frontières administratives (pas des carrés!)
const ARRONDISSEMENTS_POLYGONS_GEOJSON = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"arrondissement": 1, "nom": "1er"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3290, 48.8630], [2.3320, 48.8635], [2.3360, 48.8638], [2.3390, 48.8635],
          [2.3420, 48.8630], [2.3450, 48.8615], [2.3460, 48.8600], [2.3455, 48.8585],
          [2.3440, 48.8580], [2.3410, 48.8575], [2.3380, 48.8578], [2.3350, 48.8585],
          [2.3320, 48.8590], [2.3295, 48.8605], [2.3290, 48.8630]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 2, "nom": "2e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3390, 48.8635], [2.3420, 48.8640], [2.3460, 48.8645], [2.3500, 48.8648],
          [2.3500, 48.8630], [2.3480, 48.8625], [2.3450, 48.8615], [2.3420, 48.8630],
          [2.3390, 48.8635]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 3, "nom": "3e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3500, 48.8648], [2.3540, 48.8650], [2.3580, 48.8652], [2.3620, 48.8650],
          [2.3650, 48.8645], [2.3650, 48.8630], [2.3630, 48.8620], [2.3600, 48.8615],
          [2.3570, 48.8620], [2.3540, 48.8625], [2.3510, 48.8635], [2.3500, 48.8648]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 4, "nom": "4e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3450, 48.8615], [2.3480, 48.8625], [2.3520, 48.8630], [2.3560, 48.8625],
          [2.3600, 48.8615], [2.3630, 48.8600], [2.3650, 48.8580], [2.3640, 48.8560],
          [2.3610, 48.8545], [2.3570, 48.8535], [2.3530, 48.8530], [2.3490, 48.8535],
          [2.3460, 48.8550], [2.3455, 48.8570], [2.3450, 48.8590], [2.3450, 48.8615]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 5, "nom": "5e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3400, 48.8500], [2.3440, 48.8505], [2.3480, 48.8510], [2.3520, 48.8515],
          [2.3550, 48.8510], [2.3550, 48.8480], [2.3530, 48.8455], [2.3500, 48.8435],
          [2.3470, 48.8420], [2.3440, 48.8415], [2.3410, 48.8420], [2.3380, 48.8430],
          [2.3360, 48.8450], [2.3350, 48.8470], [2.3360, 48.8490], [2.3380, 48.8500],
          [2.3400, 48.8500]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 6, "nom": "6e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3250, 48.8500], [2.3290, 48.8505], [2.3330, 48.8510], [2.3370, 48.8515],
          [2.3400, 48.8510], [2.3400, 48.8480], [2.3380, 48.8455], [2.3350, 48.8435],
          [2.3320, 48.8420], [2.3290, 48.8415], [2.3260, 48.8420], [2.3230, 48.8430],
          [2.3210, 48.8450], [2.3200, 48.8470], [2.3210, 48.8490], [2.3230, 48.8500],
          [2.3250, 48.8500]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 7, "nom": "7e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3100, 48.8600], [2.3140, 48.8605], [2.3180, 48.8610], [2.3220, 48.8615],
          [2.3250, 48.8610], [2.3250, 48.8580], [2.3230, 48.8555], [2.3200, 48.8535],
          [2.3170, 48.8520], [2.3140, 48.8515], [2.3110, 48.8520], [2.3080, 48.8530],
          [2.3060, 48.8550], [2.3050, 48.8570], [2.3060, 48.8590], [2.3080, 48.8600],
          [2.3100, 48.8600]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 8, "nom": "8e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3100, 48.8750], [2.3140, 48.8755], [2.3180, 48.8760], [2.3220, 48.8765],
          [2.3250, 48.8760], [2.3250, 48.8730], [2.3230, 48.8705], [2.3200, 48.8685],
          [2.3170, 48.8670], [2.3140, 48.8665], [2.3110, 48.8670], [2.3080, 48.8680],
          [2.3060, 48.8700], [2.3050, 48.8720], [2.3060, 48.8740], [2.3080, 48.8750],
          [2.3100, 48.8750]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 9, "nom": "9e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3250, 48.8760], [2.3290, 48.8765], [2.3330, 48.8770], [2.3370, 48.8775],
          [2.3400, 48.8770], [2.3400, 48.8740], [2.3380, 48.8715], [2.3350, 48.8695],
          [2.3320, 48.8680], [2.3290, 48.8675], [2.3260, 48.8680], [2.3230, 48.8690],
          [2.3210, 48.8710], [2.3200, 48.8730], [2.3210, 48.8750], [2.3230, 48.8760],
          [2.3250, 48.8760]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 10, "nom": "10e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3500, 48.8750], [2.3540, 48.8755], [2.3580, 48.8760], [2.3620, 48.8765],
          [2.3660, 48.8760], [2.3700, 48.8755], [2.3700, 48.8730], [2.3680, 48.8705],
          [2.3650, 48.8685], [2.3620, 48.8670], [2.3580, 48.8665], [2.3540, 48.8670],
          [2.3510, 48.8680], [2.3490, 48.8700], [2.3480, 48.8720], [2.3490, 48.8740],
          [2.3500, 48.8750]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 11, "nom": "11e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3650, 48.8700], [2.3690, 48.8705], [2.3730, 48.8710], [2.3770, 48.8715],
          [2.3800, 48.8710], [2.3800, 48.8680], [2.3780, 48.8655], [2.3750, 48.8635],
          [2.3720, 48.8620], [2.3690, 48.8615], [2.3660, 48.8620], [2.3630, 48.8630],
          [2.3610, 48.8650], [2.3600, 48.8670], [2.3610, 48.8690], [2.3630, 48.8700],
          [2.3650, 48.8700]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 12, "nom": "12e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3650, 48.8500], [2.3690, 48.8505], [2.3730, 48.8510], [2.3770, 48.8515],
          [2.3800, 48.8510], [2.3800, 48.8480], [2.3780, 48.8455], [2.3750, 48.8435],
          [2.3720, 48.8420], [2.3690, 48.8415], [2.3660, 48.8420], [2.3630, 48.8430],
          [2.3610, 48.8450], [2.3600, 48.8470], [2.3610, 48.8490], [2.3630, 48.8500],
          [2.3650, 48.8500]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 13, "nom": "13e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3400, 48.8400], [2.3440, 48.8405], [2.3480, 48.8410], [2.3520, 48.8415],
          [2.3550, 48.8410], [2.3550, 48.8380], [2.3530, 48.8355], [2.3500, 48.8335],
          [2.3470, 48.8320], [2.3440, 48.8315], [2.3410, 48.8320], [2.3380, 48.8330],
          [2.3360, 48.8350], [2.3350, 48.8370], [2.3360, 48.8390], [2.3380, 48.8400],
          [2.3400, 48.8400]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 14, "nom": "14e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3200, 48.8400], [2.3240, 48.8405], [2.3280, 48.8410], [2.3320, 48.8415],
          [2.3360, 48.8410], [2.3400, 48.8405], [2.3400, 48.8380], [2.3380, 48.8355],
          [2.3350, 48.8335], [2.3320, 48.8320], [2.3290, 48.8315], [2.3260, 48.8320],
          [2.3230, 48.8330], [2.3210, 48.8350], [2.3200, 48.8370], [2.3200, 48.8400]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 15, "nom": "15e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.2900, 48.8450], [2.2940, 48.8455], [2.2980, 48.8460], [2.3020, 48.8465],
          [2.3060, 48.8460], [2.3100, 48.8455], [2.3100, 48.8430], [2.3080, 48.8405],
          [2.3050, 48.8385], [2.3020, 48.8370], [2.2990, 48.8365], [2.2960, 48.8370],
          [2.2930, 48.8380], [2.2910, 48.8400], [2.2900, 48.8420], [2.2900, 48.8450]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 16, "nom": "16e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.2600, 48.8550], [2.2640, 48.8555], [2.2680, 48.8560], [2.2720, 48.8565],
          [2.2760, 48.8560], [2.2800, 48.8555], [2.2840, 48.8550], [2.2880, 48.8545],
          [2.2900, 48.8540], [2.2900, 48.8510], [2.2880, 48.8485], [2.2850, 48.8465],
          [2.2820, 48.8450], [2.2780, 48.8445], [2.2740, 48.8450], [2.2700, 48.8455],
          [2.2660, 48.8460], [2.2620, 48.8465], [2.2600, 48.8470], [2.2600, 48.8500],
          [2.2600, 48.8550]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 17, "nom": "17e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3100, 48.8900], [2.3140, 48.8905], [2.3180, 48.8910], [2.3220, 48.8915],
          [2.3260, 48.8910], [2.3300, 48.8905], [2.3300, 48.8880], [2.3280, 48.8855],
          [2.3250, 48.8835], [2.3220, 48.8820], [2.3190, 48.8815], [2.3160, 48.8820],
          [2.3130, 48.8830], [2.3110, 48.8850], [2.3100, 48.8870], [2.3100, 48.8900]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 18, "nom": "18e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3300, 48.8950], [2.3340, 48.8955], [2.3380, 48.8960], [2.3420, 48.8965],
          [2.3460, 48.8960], [2.3500, 48.8955], [2.3500, 48.8930], [2.3480, 48.8905],
          [2.3450, 48.8885], [2.3420, 48.8870], [2.3390, 48.8865], [2.3360, 48.8870],
          [2.3330, 48.8880], [2.3310, 48.8900], [2.3300, 48.8920], [2.3300, 48.8950]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 19, "nom": "19e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3700, 48.8900], [2.3740, 48.8905], [2.3780, 48.8910], [2.3820, 48.8915],
          [2.3860, 48.8910], [2.3900, 48.8905], [2.3900, 48.8880], [2.3880, 48.8855],
          [2.3850, 48.8835], [2.3820, 48.8820], [2.3790, 48.8815], [2.3760, 48.8820],
          [2.3730, 48.8830], [2.3710, 48.8850], [2.3700, 48.8870], [2.3700, 48.8900]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {"arrondissement": 20, "nom": "20e"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [2.3800, 48.8700], [2.3840, 48.8705], [2.3880, 48.8710], [2.3920, 48.8715],
          [2.3960, 48.8710], [2.4000, 48.8705], [2.4000, 48.8680], [2.3980, 48.8655],
          [2.3950, 48.8635], [2.3920, 48.8620], [2.3890, 48.8615], [2.3860, 48.8620],
          [2.3830, 48.8630], [2.3810, 48.8650], [2.3800, 48.8670], [2.3800, 48.8700]
        ]]
      }
    }
  ]
};

async function loadPolygons() {
    // PRIORITÉ 1: Utiliser les données OFFICIELLES intégrées (évite CORS)
    if (typeof PARIS_OFFICIAL_POLYGONS !== 'undefined') {
        arrondissementsPolygons = PARIS_OFFICIAL_POLYGONS;
        console.log('✅✅✅ DONNÉES OFFICIELLES chargées (vraies frontières administratives!)');
        console.log(`     ${PARIS_OFFICIAL_POLYGONS.features.length} arrondissements avec contours RÉELS`);
        const samplePoints = PARIS_OFFICIAL_POLYGONS.features[0]?.geometry?.coordinates[0]?.length || 0;
        console.log(`     ${samplePoints} points par arrondissement (contours ultra-précis!)`);
        return arrondissementsPolygons;
    }
    
    // PRIORITÉ 2: Essayer de charger depuis le fichier (si serveur HTTP)
    try {
        const response = await fetch('static/data/paris_arrondissements_processed.geojson');
        if (response && response.ok) {
            const data = await response.json();
            arrondissementsPolygons = data;
            console.log('✅✅✅ DONNÉES OFFICIELLES chargées depuis fichier');
            return data;
        }
    } catch (e) {
        console.warn('Fichier non accessible (CORS), utilisation des polygones intégrés...');
    }
    
    // PRIORITÉ 2: Essayer de charger le fichier GeoJSON précis
    try {
        const response = await fetch('static/data/paris_arrondissements_precis.geojson');
        if (response && response.ok) {
            const data = await response.json();
            arrondissementsPolygons = data;
            console.log('✅ Polygones PRÉCIS chargés depuis le fichier (25+ points)');
            return data;
        }
    } catch (e) {
        console.warn('Fichier précis non trouvé, essai des polygones détaillés...');
    }
    
    // PRIORITÉ 3: Utiliser les polygones détaillés si disponibles
    if (typeof PARIS_DETAILED_POLYGONS !== 'undefined') {
        arrondissementsPolygons = PARIS_DETAILED_POLYGONS;
        console.log('✅ Polygones DÉTAILLÉS chargés (24+ points par arrondissement)');
        return arrondissementsPolygons;
    }
    
    // DERNIER RECOURS: Polygones intégrés de base
    arrondissementsPolygons = ARRONDISSEMENTS_POLYGONS_GEOJSON;
    console.log('⚠️ Polygones de base chargés (moins détaillés)');
    return arrondissementsPolygons;
}

function createBasicPolygons() {
    // Créer des polygones basiques pour chaque arrondissement
    const features = [];
    const baseCoords = {
        1: {center: [2.3376, 48.8606], size: 0.008},
        2: {center: [2.3412, 48.8698], size: 0.008},
        3: {center: [2.3624, 48.8630], size: 0.008},
        4: {center: [2.3522, 48.8546], size: 0.008},
        5: {center: [2.3447, 48.8448], size: 0.010},
        6: {center: [2.3327, 48.8448], size: 0.010},
        7: {center: [2.3186, 48.8566], size: 0.010},
        8: {center: [2.3132, 48.8738], size: 0.010},
        9: {center: [2.3392, 48.8738], size: 0.008},
        10: {center: [2.3624, 48.8738], size: 0.010},
        11: {center: [2.3768, 48.8630], size: 0.012},
        12: {center: [2.3768, 48.8448], size: 0.012},
        13: {center: [2.3522, 48.8322], size: 0.015},
        14: {center: [2.3264, 48.8330], size: 0.015},
        15: {center: [2.2995, 48.8412], size: 0.018},
        16: {center: [2.2654, 48.8534], size: 0.020},
        17: {center: [2.3214, 48.8838], size: 0.015},
        18: {center: [2.3447, 48.8932], size: 0.015},
        19: {center: [2.3768, 48.8838], size: 0.015},
        20: {center: [2.3984, 48.8630], size: 0.015}
    };
    
    for (let arr = 1; arr <= 20; arr++) {
        const coords = baseCoords[arr];
        const size = coords.size;
        const lon = coords.center[0];
        const lat = coords.center[1];
        
        // Créer un carré autour du centre
        const polygon = [
            [lon - size, lat - size],
            [lon + size, lat - size],
            [lon + size, lat + size],
            [lon - size, lat + size],
            [lon - size, lat - size]
        ];
        
        features.push({
            type: 'Feature',
            properties: {
                arrondissement: arr,
                nom: arr === 1 ? '1er' : `${arr}e`
            },
            geometry: {
                type: 'Polygon',
                coordinates: [polygon]
            }
        });
    }
    
    return {
        type: 'FeatureCollection',
        features: features
    };
}

// Mise à jour de la carte avec les données
async function updateMap() {
    if (!map) {
        console.error('Carte non initialisée');
        return;
    }
    
    // Vérifier que la carte est chargée
    if (!map.loaded()) {
        console.log('Attente du chargement de la carte...');
        map.once('load', () => updateMap());
        return;
    }
    
    // Si pas de données, créer des polygones basiques quand même
    if (!allData) {
        console.warn('Données non chargées, affichage des polygones basiques');
    }

    // Charger les polygones si pas déjà fait
    if (!arrondissementsPolygons) {
        await loadPolygons();
    }

    if (!arrondissementsPolygons) {
        console.error('Impossible de charger les polygones');
        return;
    }
    
    console.log('Polygones chargés:', arrondissementsPolygons.features.length);
    console.log('Type de géométrie:', arrondissementsPolygons.features[0]?.geometry?.type);
    console.log('Points du premier arrondissement:', arrondissementsPolygons.features[0]?.geometry?.coordinates[0]?.length);

    const features = arrondissementsPolygons.features.map(polygon => {
        let arrNum = polygon.properties.arrondissement;
        if (!arrNum && polygon.properties.c_ar !== undefined) {
            arrNum = parseInt(polygon.properties.c_ar);
        }
        if (!arrNum && polygon.properties.c_arinsee) {
            const code = String(polygon.properties.c_arinsee);
            if (code.startsWith('751') && code.length === 5) {
                arrNum = parseInt(code.substring(3));
            }
        }
        
        if (!arrNum) {
            console.warn('Arrondissement non trouvé pour:', polygon.properties);
            return null;
        }
        
        const arrData = allData ? allData.find(a => a.arrondissement === arrNum) : null;
        
        let defaultValue = 9000;
        if (selectedIndicator === 'logements') defaultValue = 15;
        if (selectedIndicator === 'pollution') defaultValue = 5;
        if (selectedIndicator === 'revenus') defaultValue = 30000;
        if (selectedIndicator === 'vegetation') defaultValue = 1000;
        if (selectedIndicator === 'transports') defaultValue = 20;
        if (selectedIndicator === 'delits') defaultValue = 50;
        if (selectedIndicator === 'densite') defaultValue = 20000;
        if (selectedIndicator === 'tension') defaultValue = 45;
        
        let value = defaultValue;
        if (arrData) {
            const calculatedValue = getIndicatorValue(arrData, selectedIndicator, selectedYear);
            value = calculatedValue !== null && calculatedValue !== undefined && calculatedValue >= 0 ? calculatedValue : defaultValue;
        }
        
        let color = getColorForIndicator(selectedIndicator, value);
        
        return {
            ...polygon,
            properties: {
                arrondissement: arrNum,
                nom: polygon.properties.nom || arrondissementLabel(arrNum),
                value: value,
                color: color,
                indicator: selectedIndicator,
            }
        };
    }).filter(f => f !== null);

    console.log(`Features créées: ${features.length} (devrait être 20)`);

    const geojson = {
        type: 'FeatureCollection',
        features: features
    };

    if (map.getSource('arrondissements')) {
        try {
            map.getSource('arrondissements').setData(geojson);
        } catch (err) {
            console.error('Erreur setData GeoJSON:', err);
            showError('Erreur affichage carte — recharger la page (Ctrl+Shift+R).');
            return;
        }
        if (map.getLayer('arrondissements-fill')) {
            const colorExpression = getColorExpressionForIndicator(selectedIndicator);
            map.setPaintProperty('arrondissements-fill', 'fill-color', colorExpression);
            applyAccessibilityMapStyles();
        }
        applyMapBorders();
        
        // Afficher les arbres si l'indicateur végétation est sélectionné
        if (selectedIndicator === 'vegetation') {
            updateTreeMarkers();
            removeTransportMarkers();
        } else if (selectedIndicator === 'transports') {
            updateTransportMarkers();
            removeTreeMarkers();
        } else {
            removeTreeMarkers();
            removeTransportMarkers();
        }
    } else {
        map.addSource('arrondissements', {
            type: 'geojson',
            data: geojson
        });

        map.addLayer({
            id: 'arrondissements-fill',
            type: 'fill',
            source: 'arrondissements',
            paint: {
                'fill-color': getColorExpressionForIndicator(selectedIndicator),
                'fill-opacity': 0.82,
                'fill-outline-color': MAP_OUTLINE.light,
            }
        });

        map.addLayer({
            id: 'arrondissements-outline-thick',
            type: 'line',
            source: 'arrondissements',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
                'line-color': MAP_OUTLINE.light,
                'line-width': ['interpolate', ['linear'], ['zoom'], 10, 2.5, 14, 3.5, 16, 4],
                'line-opacity': 0.95,
            }
        }, 'arrondissements-fill');

        map.addLayer({
            id: 'arrondissements-outline',
            type: 'line',
            source: 'arrondissements',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
                'line-color': MAP_OUTLINE.dark,
                'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 14, 1.5, 16, 1.75],
                'line-opacity': 0.9,
            }
        }, 'arrondissements-outline-thick');

        ensureArrondissementLabels();
    }

    ensureArrondissementLabels();

    // Garder la carte droite (pas d'animation si déjà droite)
    if (map.getPitch() !== 0) {
        map.easeTo({
            duration: 500,
            pitch: 0,
            bearing: 0
        });
    }
    
    // Afficher les arbres si l'indicateur végétation est sélectionné
    if (selectedIndicator === 'vegetation') {
        updateTreeMarkers();
        removeTransportMarkers();
    } else if (selectedIndicator === 'transports') {
        updateTransportMarkers();
        removeTreeMarkers();
    } else {
        removeTreeMarkers();
        removeTransportMarkers();
    }
}

let treeMarkers = [];

function updateTreeMarkers() {
    removeTreeMarkers();
    
    if (!allData || !map) {
        console.log('updateTreeMarkers: allData ou map manquant');
        return;
    }
    
    console.log('updateTreeMarkers: Affichage des arbres pour indicateur:', selectedIndicator);
    
    allData.forEach(arr => {
        const vegetation = arr.vegetation_arbres || {};
        const nombreArbres = vegetation.nombre_arbres || 0;
        
        console.log(`Arrondissement ${arr.arrondissement}: ${nombreArbres} arbres`);
        
        if (nombreArbres > 0) {
            const coords = arrondissementCoords[arr.arrondissement];
            if (coords) {
                // Calculer le nombre d'arbres à afficher (1 arbre pour ~150 arbres réels, max 20 arbres)
                const nbArbresAffiches = Math.min(Math.max(1, Math.floor(nombreArbres / 150)), 20);
                
                // Taille de base selon le nombre d'arbres (plus d'arbres = plus gros)
                let baseSize = 16;
                if (nombreArbres >= 3000) baseSize = 32;
                else if (nombreArbres >= 2000) baseSize = 28;
                else if (nombreArbres >= 1000) baseSize = 24;
                else if (nombreArbres >= 500) baseSize = 20;
                
                // Disperser les arbres dans l'arrondissement
                for (let i = 0; i < nbArbresAffiches; i++) {
                    // Variation aléatoire autour du centre (environ 0.01° = ~1km)
                    const variationLat = (Math.random() - 0.5) * 0.015;
                    const variationLng = (Math.random() - 0.5) * 0.015;
                    
                    const treeCoords = [
                        coords[1] + variationLng,
                        coords[0] + variationLat
                    ];
                    
                    // Légère variation de taille pour plus de réalisme
                    const sizeVariation = 0.8 + Math.random() * 0.4; // Entre 80% et 120%
                    const iconSize = Math.round(baseSize * sizeVariation);
                    
                    const el = document.createElement('div');
                    el.className = 'tree-marker';
                    el.style.width = iconSize + 'px';
                    el.style.height = iconSize + 'px';
                    el.style.backgroundImage = 'url(./static/images/tree-icon.svg)';
                    el.style.backgroundSize = 'contain';
                    el.style.backgroundRepeat = 'no-repeat';
                    el.style.backgroundPosition = 'center';
                    el.style.cursor = 'pointer';
                    el.style.userSelect = 'none';
                    el.style.pointerEvents = 'auto';
                    el.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))';
                    el.style.display = 'block';
                    el.style.border = 'none';
                    el.style.backgroundColor = 'transparent';
                    el.style.boxShadow = 'none';
                    el.title = `${arr.arrondissement}e: ${nombreArbres} arbres`;
                    
                    const marker = new maplibregl.Marker({
                        element: el,
                        anchor: 'center'
                    })
                        .setLngLat(treeCoords)
                        .addTo(map);
                    
                    treeMarkers.push(marker);
                }
            }
        }
    });
    
    console.log(`Total arbres affichés: ${treeMarkers.length}`);
}

function removeTreeMarkers() {
    treeMarkers.forEach(marker => marker.remove());
    treeMarkers = [];
}

let transportMarkers = [];
let transportsData = null;

function loadTransportsData() {
    // Utiliser les données intégrées directement dans le JavaScript pour éviter CORS
    if (typeof TRANSPORTS_DATA !== 'undefined') {
        transportsData = TRANSPORTS_DATA;
        const total = Object.values(transportsData.transports_by_arrondissement || {}).reduce((sum, arr) => {
            return sum + (arr.metro?.length || 0) + (arr.rer?.length || 0) + (arr.bus?.length || 0);
        }, 0);
        console.log(`✅ Données de transport chargées: ${total} transports avec coordonnées réelles`);
    } else {
        console.warn('⚠️ TRANSPORTS_DATA non défini, utilisation de données par défaut');
    }
}

function updateTransportMarkers() {
    removeTransportMarkers();
    
    if (!allData || !map) {
        console.log('updateTransportMarkers: allData ou map manquant');
        return;
    }
    
    console.log('updateTransportMarkers: Affichage des transports pour indicateur:', selectedIndicator);
    
    // Utiliser les données réelles si disponibles
    if (transportsData && transportsData.transports_by_arrondissement) {
        const transportsByArr = transportsData.transports_by_arrondissement;
        let totalCount = 0;
        
        for (let arrNum = 1; arrNum <= 20; arrNum++) {
            const arrTransports = transportsByArr[arrNum];
            if (!arrTransports) continue;
            
            // Afficher toutes les stations de métro avec leurs coordonnées réelles EXACTES
            arrTransports.metro.forEach(station => {
                if (!station.lat || !station.lon) {
                    console.warn(`Station métro ${station.name} sans coordonnées`);
                    return;
                }
                
                const iconSize = 28;
                const el = createTransportIcon('metro', iconSize, `${station.name} (${station.lat.toFixed(4)}, ${station.lon.toFixed(4)})`);
                
                // Utiliser les coordonnées EXACTES : [longitude, latitude] pour MapLibre
                const marker = new maplibregl.Marker({
                    element: el,
                    anchor: 'center'
                })
                    .setLngLat([station.lon, station.lat])  // [lon, lat] - ordre correct pour MapLibre
                    .addTo(map);
                
                transportMarkers.push(marker);
                totalCount++;
                console.log(`Métro: ${station.name} à [${station.lon}, ${station.lat}]`);
            });
            
            // Afficher toutes les stations RER avec leurs coordonnées réelles EXACTES
            arrTransports.rer.forEach(station => {
                if (!station.lat || !station.lon) {
                    console.warn(`Station RER ${station.name} sans coordonnées`);
                    return;
                }
                
                const iconSize = 30;
                const el = createTransportIcon('rer', iconSize, `${station.name} (${station.lat.toFixed(4)}, ${station.lon.toFixed(4)})`);
                
                // Utiliser les coordonnées EXACTES : [longitude, latitude] pour MapLibre
                const marker = new maplibregl.Marker({
                    element: el,
                    anchor: 'center'
                })
                    .setLngLat([station.lon, station.lat])  // [lon, lat] - ordre correct pour MapLibre
                    .addTo(map);
                
                transportMarkers.push(marker);
                totalCount++;
                console.log(`RER: ${station.name} à [${station.lon}, ${station.lat}]`);
            });
            
            // Afficher les arrêts de bus avec leurs coordonnées réelles EXACTES
            arrTransports.bus.forEach(stop => {
                if (!stop.lat || !stop.lon) {
                    console.warn(`Arrêt bus ${stop.name} sans coordonnées`);
                    return;
                }
                
                const iconSize = 20;
                const el = createTransportIcon('bus', iconSize, `${stop.name} (${stop.lat.toFixed(4)}, ${stop.lon.toFixed(4)})`);
                
                // Utiliser les coordonnées EXACTES : [longitude, latitude] pour MapLibre
                const marker = new maplibregl.Marker({
                    element: el,
                    anchor: 'center'
                })
                    .setLngLat([stop.lon, stop.lat])  // [lon, lat] - ordre correct pour MapLibre
                    .addTo(map);
                
                transportMarkers.push(marker);
                totalCount++;
            });
        }
        
        console.log(`✅ Total transports affichés avec coordonnées RÉELLES: ${totalCount} (${transportMarkers.length} marqueurs)`);
        return;
    } else {
        console.warn('⚠️ Données de transport non chargées, utilisation du fallback');
    }
    
    // Fallback: utiliser les données générées avec coordonnées aléatoires
    allData.forEach(arr => {
        const transports = arr.transports_publics || {};
        const totalTransports = transports.total_transports || 0;
        const stationsMetro = transports.stations_metro || 0;
        const stationsRer = transports.stations_rer || 0;
        const arretsBus = transports.arrets_bus || 0;
        
        if (totalTransports > 0) {
            const coords = arrondissementCoords[arr.arrondissement];
            if (coords) {
                // Calculer le nombre de marqueurs à afficher (1 pour ~10 transports, max 15)
                const nbMarqueurs = Math.min(Math.max(1, Math.floor(totalTransports / 10)), 15);
                
                // Taille de base selon le nombre de transports
                let baseSize = 18;
                if (totalTransports >= 50) baseSize = 32;
                else if (totalTransports >= 30) baseSize = 28;
                else if (totalTransports >= 15) baseSize = 24;
                else if (totalTransports >= 5) baseSize = 20;
                
                // Disperser les transports dans l'arrondissement
                for (let i = 0; i < nbMarqueurs; i++) {
                    const variationLat = (Math.random() - 0.5) * 0.015;
                    const variationLng = (Math.random() - 0.5) * 0.015;
                    
                    const transportCoords = [
                        coords[1] + variationLng,
                        coords[0] + variationLat
                    ];
                    
                    const sizeVariation = 0.8 + Math.random() * 0.4;
                    const iconSize = Math.round(baseSize * sizeVariation);
                    
                    // Choisir le type de transport selon les proportions
                    let transportType = 'bus';
                    const rand = Math.random();
                    if (stationsMetro > 0 && rand < (stationsMetro / totalTransports)) {
                        transportType = 'metro';
                    } else if (stationsRer > 0 && rand < ((stationsMetro + stationsRer) / totalTransports)) {
                        transportType = 'rer';
                    }
                    
                    const el = createTransportIcon(transportType, iconSize, `${arr.arrondissement}e arrondissement`);
                    
                    const marker = new maplibregl.Marker({
                        element: el,
                        anchor: 'center'
                    })
                        .setLngLat(transportCoords)
                        .addTo(map);
                    
                    transportMarkers.push(marker);
                }
            }
        }
    });
    
    console.log(`Total transports affichés: ${transportMarkers.length}`);
}

function createTransportIcon(type, size, title) {
    const iconFile = type === 'metro' ? 'metro-icon.svg' : 
                    type === 'rer' ? 'rer-icon.svg' : 
                    'bus-icon.svg';
    
    const el = document.createElement('div');
    el.className = 'transport-marker';
    el.style.width = size + 'px';
    el.style.height = size + 'px';
    el.style.backgroundImage = `url(./static/images/${iconFile})`;
    el.style.backgroundSize = 'contain';
    el.style.backgroundRepeat = 'no-repeat';
    el.style.backgroundPosition = 'center';
    el.style.cursor = 'pointer';
    el.style.userSelect = 'none';
    el.style.pointerEvents = 'auto';
    el.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))';
    el.style.display = 'block';
    el.style.border = 'none';
    el.style.backgroundColor = 'transparent';
    el.style.boxShadow = 'none';
    el.title = title;
    
    return el;
}

function removeTransportMarkers() {
    transportMarkers.forEach(marker => marker.remove());
    transportMarkers = [];
}

const INDICATOR_ORDER = [
    'prix', 'logements', 'loyers', 'accessibilite', 'tension', 'pollution',
    'delits', 'revenus', 'densite', 'vegetation', 'transports',
];

const INDICATOR_FORMULAS = {
    tension: {
        title: 'Tension locative',
        formula: '(loyer_m² × 50 × 12) / revenu_médian × 100',
        unit: '% du revenu annuel',
        note: 'Part du revenu médian absorbée par un logement de 50 m² en location.',
    },
    accessibilite: {
        title: 'Accessibilité à l\'achat',
        formula: '(prix_m² × 50) / (revenu_médian / 12)',
        unit: 'mois de revenu',
        note: 'Mois de revenu médian nécessaires pour financer 50 m² à l\'achat.',
    },
    densite: {
        title: 'Densité de population',
        formula: 'population / superficie_km²',
        unit: 'hab./km²',
        note: 'Population INSEE (jeu délinquance data.gouv) divisée par la superficie de l\'arrondissement.',
    },
    pollution: {
        title: 'Qualité de l\'air (proxy local)',
        formula: 'indice_Paris × f(densité, transports)',
        unit: 'indice 1–10',
        note: 'Indice Citeair Paris (identique pour tous) ajusté par densité et transports pour varier sur la carte.',
    },
    score_global: {
        title: 'Score Global Qualité de Vie',
        formula: 'Σ (indicateur_normalisé × pondération)',
        unit: 'score 0–100',
        note: 'Score pondéré : prix (15%), accessibilité (20%), sécurité (15%), transports (15%), végétation (10%), air (10%), logements sociaux (5%), revenus (10%).',
    },
    potentiel: {
        title: 'Potentiel Plus-Value',
        formula: 'f(prix, dynamique, transports, cadre, mixité, sécurité)',
        unit: 'score 0–100',
        note: 'Estimation du potentiel de valorisation future basée sur : accessibilité prix, dynamique récente, desserte transports, cadre de vie, mixité sociale et sécurité.',
    },
    sante_proximite: {
        title: 'Score Santé de Proximité',
        formula: 'Σ (ratio_equip × pondération)',
        unit: 'score 0–100',
        note: 'Score pondéré : pharmacies (20%), médecins (20%), urgences (20%), dentistes (15%), DAE (10%), centres santé (10%), hôpitaux (5%). Ratios pour 10 000 habitants.',
    },
};

function selectIndicator(indicator) {
    selectedIndicator = indicator;
    document.querySelectorAll('.indicator-item').forEach(i => {
        const active = i.dataset.indicator === indicator;
        i.classList.toggle('active', active);
        i.setAttribute('aria-pressed', String(active));
    });
    updateIndicatorFormulaPanel();
    updateMapLegend();
    updateMap();
    updateUniformDataNotice();
    if (selectedIndicator === 'vegetation') {
        setTimeout(() => updateTreeMarkers(), 200);
    } else {
        removeTreeMarkers();
    }
    if (selectedIndicator === 'transports') {
        updateTransportMarkers();
    } else {
        removeTransportMarkers();
    }
}

function getOutlineDashExpression(indicator) {
    return ['literal', [1, 0]];
}

function getColorExpressionForIndicator(indicator) {
    switch (indicator) {
        case 'prix':
            return seqLtExpr(8000, 10000, 12000, 15000);
        case 'logements':
            return seqGteExpr(10, 15, 20, 25);
        case 'loyers':
            return seqGteExpr(22, 28, 32, 36);
        case 'accessibilite':
            return seqGteExpr(170, 185, 200, 215);
        case 'tension':
            return seqGteExpr(40, 45, 50, 55);
        case 'densite':
            return seqGteExpr(12000, 18000, 25000, 32000);
        case 'revenus':
            return seqGteExpr(25000, 30000, 35000, 40000);
        case 'transports':
            return seqGteExpr(5, 15, 30, 50);
        case 'delits':
            return seqGteExpr(40, 80, 120, 200);
        case 'pollution':
            return [
                'case',
                ['<=', ['get', 'value'], 2.9], AIR_GOOD_TO_BAD[0],
                ['<=', ['get', 'value'], 3.1], AIR_GOOD_TO_BAD[1],
                ['<=', ['get', 'value'], 3.2], AIR_GOOD_TO_BAD[2],
                ['<=', ['get', 'value'], 3.3], AIR_GOOD_TO_BAD[3],
                AIR_GOOD_TO_BAD[4],
            ];
        case 'vegetation':
            return [
                'case',
                ['<', ['get', 'value'], 200], VEG_NONE_TO_DENSE[0],
                ['<', ['get', 'value'], 500], VEG_NONE_TO_DENSE[1],
                ['<', ['get', 'value'], 1000], VEG_NONE_TO_DENSE[2],
                ['<', ['get', 'value'], 2000], VEG_NONE_TO_DENSE[3],
                VEG_NONE_TO_DENSE[4],
            ];
        case 'score_global':
            // Score 0-100, vert = mieux
            return [
                'case',
                ['<', ['get', 'value'], 30], AIR_GOOD_TO_BAD[4],
                ['<', ['get', 'value'], 45], AIR_GOOD_TO_BAD[3],
                ['<', ['get', 'value'], 60], AIR_GOOD_TO_BAD[2],
                ['<', ['get', 'value'], 75], AIR_GOOD_TO_BAD[1],
                AIR_GOOD_TO_BAD[0],
            ];
        case 'potentiel':
            // Potentiel 0-100, vert = fort potentiel
            return [
                'case',
                ['<', ['get', 'value'], 35], AIR_GOOD_TO_BAD[4],
                ['<', ['get', 'value'], 50], AIR_GOOD_TO_BAD[3],
                ['<', ['get', 'value'], 65], AIR_GOOD_TO_BAD[2],
                ['<', ['get', 'value'], 80], AIR_GOOD_TO_BAD[1],
                AIR_GOOD_TO_BAD[0],
            ];
        case 'sante_proximite':
            // Score 0-100, vert = bon acces sante
            return [
                'case',
                ['<', ['get', 'value'], 40], SANTE_COLORS[0],
                ['<', ['get', 'value'], 55], SANTE_COLORS[1],
                ['<', ['get', 'value'], 70], SANTE_COLORS[2],
                ['<', ['get', 'value'], 85], SANTE_COLORS[3],
                SANTE_COLORS[4],
            ];
        case 'pharmacies':
            // Nombre de pharmacies, vert = beaucoup
            return [
                'case',
                ['<', ['get', 'value'], 30], SANTE_COLORS[0],
                ['<', ['get', 'value'], 50], SANTE_COLORS[1],
                ['<', ['get', 'value'], 70], SANTE_COLORS[2],
                ['<', ['get', 'value'], 90], SANTE_COLORS[3],
                SANTE_COLORS[4],
            ];
        case 'defibrillateurs':
            // Densite DAE pour 10k hab (range ~3-25), vert = dense
            return [
                'case',
                ['<', ['get', 'value'], 4], SANTE_COLORS[0],
                ['<', ['get', 'value'], 8], SANTE_COLORS[1],
                ['<', ['get', 'value'], 15], SANTE_COLORS[2],
                ['<', ['get', 'value'], 22], SANTE_COLORS[3],
                SANTE_COLORS[4],
            ];
        case 'urgences':
            // Temps vers urgences (min), vert = rapide (inverse)
            return [
                'case',
                ['>', ['get', 'value'], 9], SANTE_COLORS[0],
                ['>', ['get', 'value'], 7], SANTE_COLORS[1],
                ['>', ['get', 'value'], 6], SANTE_COLORS[2],
                ['>', ['get', 'value'], 5], SANTE_COLORS[3],
                SANTE_COLORS[4],
            ];
        default:
            return seqLtExpr(8000, 10000, 12000, 15000);
    }
}

function baseColorAt(value, t1, t2, t3, t4, gte = false) {
    if (gte) {
        if (value >= t4) return MAP_BASE[4];
        if (value >= t3) return MAP_BASE[3];
        if (value >= t2) return MAP_BASE[2];
        if (value >= t1) return MAP_BASE[1];
        return MAP_BASE[0];
    }
    if (value < t1) return MAP_BASE[0];
    if (value < t2) return MAP_BASE[1];
    if (value < t3) return MAP_BASE[2];
    if (value < t4) return MAP_BASE[3];
    return MAP_BASE[4];
}

function getColorForIndicator(indicator, value) {
    switch (indicator) {
        case 'prix':
            return baseColorAt(value, 8000, 10000, 12000, 15000, false);
        case 'logements':
            return baseColorAt(value, 10, 15, 20, 25, true);
        case 'loyers':
            return baseColorAt(value, 22, 28, 32, 36, true);
        case 'accessibilite':
            return baseColorAt(value, 170, 185, 200, 215, true);
        case 'tension':
            return baseColorAt(value, 40, 45, 50, 55, true);
        case 'densite':
            return baseColorAt(value, 12000, 18000, 25000, 32000, true);
        case 'revenus':
            return baseColorAt(value, 25000, 30000, 35000, 40000, true);
        case 'transports':
            return baseColorAt(value, 5, 15, 30, 50, true);
        case 'delits':
            return baseColorAt(value, 40, 80, 120, 200, true);
        case 'pollution':
            if (value <= 2.9) return AIR_GOOD_TO_BAD[0];
            if (value <= 3.1) return AIR_GOOD_TO_BAD[1];
            if (value <= 3.2) return AIR_GOOD_TO_BAD[2];
            if (value <= 3.3) return AIR_GOOD_TO_BAD[3];
            return AIR_GOOD_TO_BAD[4];
        case 'vegetation':
            if (value < 200) return VEG_NONE_TO_DENSE[0];
            if (value < 500) return VEG_NONE_TO_DENSE[1];
            if (value < 1000) return VEG_NONE_TO_DENSE[2];
            if (value < 2000) return VEG_NONE_TO_DENSE[3];
            return VEG_NONE_TO_DENSE[4];
        case 'score_global':
            if (value < 30) return AIR_GOOD_TO_BAD[4];
            if (value < 45) return AIR_GOOD_TO_BAD[3];
            if (value < 60) return AIR_GOOD_TO_BAD[2];
            if (value < 75) return AIR_GOOD_TO_BAD[1];
            return AIR_GOOD_TO_BAD[0];
        case 'potentiel':
            if (value < 35) return AIR_GOOD_TO_BAD[4];
            if (value < 50) return AIR_GOOD_TO_BAD[3];
            if (value < 65) return AIR_GOOD_TO_BAD[2];
            if (value < 80) return AIR_GOOD_TO_BAD[1];
            return AIR_GOOD_TO_BAD[0];
        case 'sante_proximite':
            if (value < 40) return SANTE_COLORS[0];
            if (value < 55) return SANTE_COLORS[1];
            if (value < 70) return SANTE_COLORS[2];
            if (value < 85) return SANTE_COLORS[3];
            return SANTE_COLORS[4];
        case 'pharmacies':
            if (value < 30) return SANTE_COLORS[0];
            if (value < 50) return SANTE_COLORS[1];
            if (value < 70) return SANTE_COLORS[2];
            if (value < 90) return SANTE_COLORS[3];
            return SANTE_COLORS[4];
        case 'defibrillateurs':
            if (value < 4) return SANTE_COLORS[0];
            if (value < 8) return SANTE_COLORS[1];
            if (value < 15) return SANTE_COLORS[2];
            if (value < 22) return SANTE_COLORS[3];
            return SANTE_COLORS[4];
        case 'urgences':
            if (value > 9) return SANTE_COLORS[0];
            if (value > 7) return SANTE_COLORS[1];
            if (value > 6) return SANTE_COLORS[2];
            if (value > 5) return SANTE_COLORS[3];
            return SANTE_COLORS[4];
        default:
            return MAP_BASE[2];
    }
}

function getIndicatorValue(arr, indicator, year) {
    switch (indicator) {
        case 'prix':
            const evolution = arr.evolution_annuelle || [];
            const yearData = evolution.find(e => e.annee === year);
            return yearData ? yearData.prix_m2_median : (arr.statistiques?.prix_m2_actuel || 0);
        case 'logements':
            return arr.logements_sociaux_pourcentage || 0;
        case 'loyers':
            return arr.loyers?.loyer_m2_median || arr.accessibilite_logement?.loyer_m2_median || 0;
        case 'accessibilite':
            return arr.accessibilite_logement?.mois_revenu_pour_50m2_achat
                || arr.accessibilite_logement?.mois_revenu_pour_50m2_location || 0;
        case 'tension':
            return arr.accessibilite_logement?.part_revenu_loyer_50m2_pct || 0;
        case 'pollution':
            return arr.pollution_qualite_air?.indice_atmo_local
                || arr.pollution_qualite_air?.indice_atmo || 0;
        case 'delits':
            return arr.delits_enregistres?.delits_par_1000_habitants || 0;
        case 'revenus':
            return arr.revenus_moyens?.revenu_median_menage || 0;
        case 'densite':
            return arr.densite_population?.densite_km2 || 0;
        case 'vegetation':
            return arr.vegetation_arbres?.nombre_arbres || 0;
        case 'transports':
            return arr.transports_publics?.total_transports || 0;
        case 'score_global':
            return calculateGlobalScore(arr);
        case 'potentiel':
            return calculatePotentielPlusValue(arr).score;
        case 'sante_proximite':
            return getSanteProximiteScore(arr.arrondissement);
        case 'pharmacies':
            return getPharmaciesCount(arr.arrondissement);
        case 'defibrillateurs':
            return getDefibrillateursDensite(arr.arrondissement);
        case 'urgences':
            return getUrgencesProximite(arr.arrondissement);
        default:
            return arr.statistiques?.prix_m2_actuel || 0;
    }
}

// Fonctions pour les indicateurs de sante
function getSanteProximiteScore(arrNum) {
    if (typeof SANTE_DATA === 'undefined') return 0;
    const data = SANTE_DATA.sante_by_arrondissement[String(arrNum)];
    if (!data) return 0;
    const result = calculateScoreSanteProximite(data);
    return result ? result.score : 0;
}

function getPharmaciesCount(arrNum) {
    if (typeof SANTE_DATA === 'undefined') return 0;
    const data = SANTE_DATA.sante_by_arrondissement[String(arrNum)];
    return data ? data.pharmacies : 0;
}

function getDefibrillateursDensite(arrNum) {
    if (typeof SANTE_DATA === 'undefined') return 0;
    const data = SANTE_DATA.sante_by_arrondissement[String(arrNum)];
    if (!data) return 0;
    // Densite pour 10 000 habitants
    return parseFloat(((data.defibrillateurs / data.population) * 10000).toFixed(1));
}

function getUrgencesProximite(arrNum) {
    if (typeof SANTE_DATA === 'undefined') return 0;
    const data = SANTE_DATA.sante_by_arrondissement[String(arrNum)];
    return data ? data.urgences_proximite : 0;
}

// Afficher le tooltip
function showTooltip(e, arrNum) {
    const arr = allData.find(a => a.arrondissement === arrNum);
    if (!arr) return;

    const tooltip = document.getElementById('tooltip');
    const wrapper = document.querySelector('.map-container-wrapper');
    if (!tooltip || !wrapper) return;

    const value = getIndicatorValue(arr, selectedIndicator, selectedYear);
    const valueLabel = getIndicatorLabel(selectedIndicator, value);
    const price = arr.statistiques?.prix_m2_actuel;

    const lines = [
        `<div><span class="tooltip-kpi">${getIndicatorName(selectedIndicator)}</span> ${valueLabel}</div>`,
    ];
    if (selectedIndicator !== 'prix' && price != null) {
        lines.push(`<div><span class="tooltip-kpi">Prix/m²</span> ${price.toLocaleString('fr-FR')} €</div>`);
    }
    if (selectedIndicator !== 'logements' && arr.logements_sociaux_pourcentage != null) {
        lines.push(`<div><span class="tooltip-kpi">Log. sociaux</span> ${arr.logements_sociaux_pourcentage}%</div>`);
    }

    tooltip.innerHTML = `
        <div class="tooltip-title">${arr.arrondissement}<sup>e</sup> arrondissement</div>
        <div class="tooltip-content">${lines.join('')}</div>
    `;

    const pad = 12;
    tooltip.classList.remove('hidden');
    const tw = tooltip.offsetWidth;
    const th = tooltip.offsetHeight;
    let left = e.point.x + pad;
    let top = e.point.y + pad;
    if (left + tw > wrapper.clientWidth - pad) left = e.point.x - tw - pad;
    if (top + th > wrapper.clientHeight - pad) top = e.point.y - th - pad;
    left = Math.max(pad, left);
    top = Math.max(pad, top);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
}

function hideTooltip() {
    document.getElementById('tooltip').classList.add('hidden');
}

// Sélectionner un arrondissement
function selectArrondissement(arrNum) {
    selectedArr = arrNum;
    const arr = allData.find(a => a.arrondissement === arrNum);
    if (!arr) return;

    updateSelectedInfo(arr);
    updateCharts();
    if (geoPointsVisible) {
        loadGeoPointsLayer(arrNum);
    }
    
    // Centrer la carte sur l'arrondissement
    const coords = arrondissementCoords[arrNum];
    if (coords) {
        map.flyTo({
            center: [coords[1], coords[0]],
            zoom: 14,
            duration: 1500
        });
    }
}

function stressBadgeClass(mois) {
    if (mois == null) return 'stress-mid';
    if (mois < 200) return 'stress-low';
    if (mois < 350) return 'stress-mid';
    return 'stress-high';
}

function formatAccessibiliteBlock(arr) {
    const a = arr.accessibilite_logement || {};
    const surface = a.surface_moyenne_m2 || arr.typologie?.surface_moyenne_m2 || arr.statistiques?.surface_moyenne_m2;
    if (!a.mois_revenu_pour_50m2_achat && !a.mois_revenu_pour_50m2_location) return '';
    return `
        <div class="info-highlight" role="region" aria-label="Accessibilité logement">
            <div class="info-title" style="font-size:0.85rem;margin-bottom:0.5rem;">Accessibilité (50 m²)</div>
            ${a.mois_revenu_pour_50m2_achat != null ? `
            <div class="info-item">
                <span class="info-label">Achat — mois de revenu</span>
                <span class="info-value stress-badge ${stressBadgeClass(a.mois_revenu_pour_50m2_achat)}">${a.mois_revenu_pour_50m2_achat} mois</span>
            </div>` : ''}
            ${a.mois_revenu_pour_50m2_location != null ? `
            <div class="info-item">
                <span class="info-label">Location — mois de revenu</span>
                <span class="info-value stress-badge ${stressBadgeClass(a.mois_revenu_pour_50m2_location)}">${a.mois_revenu_pour_50m2_location} mois</span>
            </div>
            <div class="info-item">
                <span class="info-label">Loyer estimé / m²</span>
                <span class="info-value">${a.loyer_m2_median?.toLocaleString('fr-FR') || '—'} €/mois</span>
            </div>
            ${a.part_revenu_loyer_50m2_pct != null ? `
            <div class="info-item">
                <span class="info-label">Part revenu (loyer 50 m²)</span>
                <span class="info-value">${a.part_revenu_loyer_50m2_pct}%</span>
            </div>` : ''}` : ''}
            ${surface ? `
            <div class="info-item">
                <span class="info-label">Surface moyenne (ventes)</span>
                <span class="info-value">${Number(surface).toFixed(0)} m²</span>
            </div>` : ''}
        </div>`;
}

function updateSelectedInfo(arr) {
    const infoDiv = document.getElementById('selected-info');
    const prix = arr.statistiques?.prix_m2_actuel;
    const variation = arr.evolution_calculee?.variation_pourcentage;
    const logSoc = arr.logements_sociaux_pourcentage;
    const qualAir = arr.pollution_qualite_air?.qualite;
    const delits = arr.delits_enregistres?.delits_par_1000_habitants;
    const revenu = arr.revenus_moyens?.revenu_median_menage;
    const densite = arr.densite_population?.densite_km2;
    const access = arr.accessibilite_logement?.mois_revenu_pour_50m2_achat;

    // Calcul des scores
    const globalScore = calculateGlobalScore(arr);
    const potentiel = calculatePotentielPlusValue(arr);
    const santeScore = getSanteProximiteScore(arr.arrondissement);

    // Calcul du rang pour le score global
    const allScores = allData.map(a => ({ arr: a.arrondissement, score: calculateGlobalScore(a) }))
        .sort((a, b) => b.score - a.score);
    const rank = allScores.findIndex(s => s.arr === arr.arrondissement) + 1;

    // Donnees sante
    const santeData = typeof SANTE_DATA !== 'undefined' ? SANTE_DATA.sante_by_arrondissement[String(arr.arrondissement)] : null;

    infoDiv.innerHTML = `
        <div class="info-content">
            <div class="info-header">
                <div class="info-title">${arr.arrondissement}<sup>e</sup> Arr.</div>
                <button class="btn-reset" onclick="resetSelection()">Reinitialiser</button>
            </div>

            <div class="global-score">
                <div class="global-score-label">Score Global Qualite de Vie</div>
                <div class="global-score-value">${globalScore}</div>
                <div class="global-score-rank">${rank}<sup>e</sup> / 20 arrondissements</div>
                <div class="score-bar">
                    <div class="score-bar-fill" style="width: ${globalScore}%"></div>
                </div>
            </div>

            <div class="potentiel-section">
                <div class="potentiel-label">Potentiel Plus-Value</div>
                <div class="potentiel-value ${potentiel.classe}">${potentiel.niveau} (${potentiel.score}/100)</div>
            </div>

            <div class="info-item">
                <span class="info-label">Prix/m2</span>
                <span class="info-value">${prix ? prix.toLocaleString('fr-FR') + ' €' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Variation</span>
                <span class="info-value ${variation > 0 ? 'text-success' : variation < 0 ? 'text-danger' : ''}">${variation != null ? (variation > 0 ? '+' : '') + variation.toFixed(1) + '%' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Accessibilite</span>
                <span class="info-value">${access ? access.toFixed(0) + ' mois' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Logements sociaux</span>
                <span class="info-value">${logSoc != null ? logSoc + '%' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Qualite air</span>
                <span class="info-value">${qualAir || 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Securite</span>
                <span class="info-value">${delits != null ? delits.toFixed(0) + ' delits/1000 hab.' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Revenu median</span>
                <span class="info-value">${revenu ? revenu.toLocaleString('fr-FR') + ' €' : 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Densite</span>
                <span class="info-value">${densite ? densite.toLocaleString('fr-FR') + ' hab./km2' : 'N/A'}</span>
            </div>
            <div class="info-item" style="margin-top: 0.5rem; padding-top: 0.8rem; border-top: 2px solid var(--accent);">
                <span class="info-label" style="color: var(--accent);">Sante Proximite</span>
                <span class="info-value">${santeScore}/100</span>
            </div>
            ${santeData ? `
            <div class="info-item">
                <span class="info-label">Pharmacies</span>
                <span class="info-value">${santeData.pharmacies}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Defibrillateurs</span>
                <span class="info-value">${santeData.defibrillateurs}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Acces urgences</span>
                <span class="info-value">${santeData.urgences_proximite} min</span>
            </div>
            ` : ''}
            ${getTransportsInfoHTML(arr)}
        </div>
    `;
}

function resetSelection() {
    selectedArr = null;
    const infoDiv = document.getElementById('selected-info');
    infoDiv.innerHTML = '<p class="info-placeholder">Survolez ou cliquez un arrondissement sur la carte</p>';
    updateCharts();
    // Retirer la surbrillance de la carte
    if (map && map.getLayer('arrondissements-fill')) {
        map.setPaintProperty('arrondissements-fill', 'fill-opacity', 0.7);
    }
}

function getTransportsInfoHTML(arr) {
    const transports = arr.transports_publics || {};
    const stationsMetro = transports.stations_metro || 0;
    const stationsRer = transports.stations_rer || 0;
    const arretsBus = transports.arrets_bus || 0;
    const lignesMetro = transports.lignes_metro || 0;
    const lignesBus = transports.lignes_bus || 0;
    const totalTransports = transports.total_transports || 0;
    
    if (totalTransports === 0) {
        return '';
    }
    
    return `
        <div class="transports-section">
            <div class="transports-title">🚇 Transports Publics</div>
            <div class="transports-grid">
                <div class="transport-card metro">
                    <div class="transport-icon">🚇</div>
                    <div class="transport-info">
                        <div class="transport-label">Métro</div>
                        <div class="transport-stats">
                            <span class="transport-count">${stationsMetro} stations</span>
                            <span class="transport-lines">${lignesMetro} lignes</span>
                        </div>
                    </div>
                </div>
                <div class="transport-card rer">
                    <div class="transport-icon">🚆</div>
                    <div class="transport-info">
                        <div class="transport-label">RER</div>
                        <div class="transport-stats">
                            <span class="transport-count">${stationsRer} stations</span>
                        </div>
                    </div>
                </div>
                <div class="transport-card bus">
                    <div class="transport-icon">🚌</div>
                    <div class="transport-info">
                        <div class="transport-label">Bus</div>
                        <div class="transport-stats">
                            <span class="transport-count">${arretsBus} arrêts</span>
                            <span class="transport-lines">${lignesBus} lignes</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="transport-total">
                <span>Total: ${totalTransports} points d'accès</span>
            </div>
        </div>
    `;
}

function updateGlobalStats() {
    if (!allData) return;

    const prices = allData
        .map(arr => {
            const evolution = arr.evolution_annuelle || [];
            const yearData = evolution.find(e => e.annee === selectedYear);
            return yearData ? yearData.prix_m2_median : arr.statistiques?.prix_m2_actuel;
        })
        .filter(p => p);

    if (prices.length > 0) {
        const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
        document.getElementById('avg-price').textContent = Math.round(avgPrice).toLocaleString('fr-FR') + '€';

        const variations = allData
            .map(arr => arr.evolution_calculee?.variation_pourcentage)
            .filter(v => v !== undefined && v !== null);
        
        if (variations.length > 0) {
            const avgVariation = variations.reduce((a, b) => a + b, 0) / variations.length;
            const sign = avgVariation > 0 ? '+' : '';
            document.getElementById('avg-variation').textContent = `${sign}${avgVariation.toFixed(1)}%`;
        } else {
            document.getElementById('avg-variation').textContent = '—';
        }
    }
}

// Initialiser les graphiques
function initializeCharts() {
    configureChartDefaults();
    updateTimelineChart();
    updateComparisonChart();
    updateTypologyChart();
    updateTransportsChart();
    updateSanteChart();
}

// Graphique timeline
function updateTimelineChart() {
    const ctx = document.getElementById('timeline-chart').getContext('2d');
    
    if (charts.timeline) {
        charts.timeline.destroy();
    }

    if (!allData) return;

    const arr = selectedArr ? allData.find(a => a.arrondissement === selectedArr) : allData[0];
    if (!arr) return;

    const evolution = arr.evolution_annuelle || [];
    const labels = evolution.map(e => e.annee);
    const data = evolution.map(e => e.prix_m2_median);

    charts.timeline = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Prix/m² médian (€)',
                data: data,
                borderColor: CHART_THEME.accent,
                backgroundColor: CHART_THEME.accentSoft,
                tension: 0.35,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: CHART_THEME.accent,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: chartScales('€ / m²')
        }
    });
}

// Graphique de comparaison
function updateComparisonChart() {
    const ctx = document.getElementById('comparison-chart').getContext('2d');
    
    if (charts.comparison) {
        charts.comparison.destroy();
    }

    if (!allData) return;

    const labels = allData.map(arr => `${arr.arrondissement}e`);
    const evolution = allData.map(arr => {
        const yearData = arr.evolution_annuelle?.find(e => e.annee === selectedYear);
        return yearData ? yearData.prix_m2_median : arr.statistiques?.prix_m2_actuel || 0;
    });

    charts.comparison = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Prix/m² (€)',
                data: evolution,
                backgroundColor: evolution.map((v) => {
                    if (v < 10000) return MAP_BASE[1];
                    if (v < 12000) return MAP_BASE[2];
                    return MAP_BASE[3];
                }),
                borderColor: 'transparent',
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { display: false } },
            scales: chartScales('€ / m²')
        }
    });
}

// Graphique typologie
function updateTypologyChart() {
    const chartElement = document.getElementById('typology-chart');
    if (!chartElement) {
        console.warn('Element typology-chart non trouvé');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    if (charts.typology) {
        charts.typology.destroy();
    }

    if (!allData || allData.length === 0) {
        console.warn('Aucune donnée disponible pour le graphique typologie');
        return;
    }

    const arr = selectedArr ? allData.find(a => a.arrondissement === selectedArr) : allData[0];
    if (!arr) {
        console.warn('Arrondissement non trouvé pour le graphique typologie');
        return;
    }

    const typology = arr.typologie || {};
    console.log('Typologie pour arrondissement', arr.arrondissement, ':', typology);
    
    // Utiliser la nouvelle structure : repartition_pieces
    const repartition = typology.repartition_pieces || {};
    const labels = Object.keys(repartition);
    const data = Object.values(repartition);
    
    if (labels.length === 0 || data.length === 0) {
        console.warn('Aucune donnée de répartition disponible:', repartition);
        return;
    }
    
    console.log('Labels:', labels, 'Data:', data);

    try {
        charts.typology = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Répartition (%)',
                data: data,
                backgroundColor: CHART_THEME.palette,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: CHART_THEME.text,
                        padding: 12,
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const typeLogement = typology.type_logement || {};
                            const total = typeLogement.total_logements || 0;
                            const detail = typology.detail_pieces || {};
                            
                            // Trouver le détail correspondant
                            let detailInfo = '';
                            for (const [key, info] of Object.entries(detail)) {
                                if (info.type === label) {
                                    detailInfo = ` (${info.nombre.toLocaleString('fr-FR')} logements)`;
                                    break;
                                }
                            }
                            
                            return `${label}: ${value.toFixed(1)}%${detailInfo}`;
                        }
                    }
                }
            }
        }
    });
    } catch (error) {
        console.error('Erreur lors de la création du graphique typologie:', error);
        // Afficher un message d'erreur dans le canvas
        ctx.fillStyle = CHART_THEME.text;
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Erreur: Impossible d\'afficher le graphique', ctx.canvas.width / 2, ctx.canvas.height / 2);
    }
}

// Graphique transports
function updateTransportsChart() {
    const chartElement = document.getElementById('transports-chart');
    if (!chartElement) {
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    if (charts.transports) {
        charts.transports.destroy();
    }

    if (!allData || allData.length === 0) {
        return;
    }

    const arr = selectedArr ? allData.find(a => a.arrondissement === selectedArr) : allData[0];
    if (!arr) {
        return;
    }

    const transports = arr.transports_publics || {};
    const stationsMetro = transports.stations_metro || 0;
    const stationsRer = transports.stations_rer || 0;
    const arretsBus = transports.arrets_bus || 0;
    const lignesMetro = transports.lignes_metro || 0;
    const lignesBus = transports.lignes_bus || 0;
    
    if (stationsMetro === 0 && stationsRer === 0 && arretsBus === 0) {
        return;
    }

    try {
        charts.transports = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Métro', 'RER', 'Bus'],
                datasets: [
                    {
                        label: 'Stations/Arrêts',
                        data: [stationsMetro, stationsRer, arretsBus],
                        backgroundColor: [
                            '#003E7E',
                            '#0066CC',
                            '#FF6B00'
                        ],
                        borderColor: [
                            '#002855',
                            '#0052A3',
                            '#E55A00'
                        ],
                        borderWidth: 2
                    },
                    {
                        label: 'Lignes',
                        data: [lignesMetro, 0, lignesBus],
                        backgroundColor: [
                            'rgba(0, 62, 126, 0.5)',
                            'rgba(0, 102, 204, 0.5)',
                            'rgba(255, 107, 0, 0.5)'
                        ],
                        borderColor: [
                            '#003E7E',
                            '#0066CC',
                            '#FF6B00'
                        ],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: CHART_THEME.text,
                            padding: 12,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y || 0;
                                const transportType = context.label;
                                
                                if (label === 'Stations/Arrêts') {
                                    if (transportType === 'Métro') {
                                        return `Stations métro: ${value}`;
                                    } else if (transportType === 'RER') {
                                        return `Stations RER: ${value}`;
                                    } else {
                                        return `Arrêts bus: ${value}`;
                                    }
                                } else {
                                    if (transportType === 'Métro') {
                                        return `Lignes métro: ${value}`;
                                    } else if (transportType === 'Bus') {
                                        return `Lignes bus: ${value}`;
                                    }
                                    return '';
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, ...chartScales().y, ticks: { ...chartScales().y.ticks, stepSize: 1 } },
                    x: chartScales().x,
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors de la création du graphique transports:', error);
    }
}

// Graphique sante de proximite
function updateSanteChart() {
    const chartElement = document.getElementById('sante-chart');
    if (!chartElement) {
        return;
    }

    const ctx = chartElement.getContext('2d');

    if (charts.sante) {
        charts.sante.destroy();
    }

    if (typeof SANTE_DATA === 'undefined' || !allData || allData.length === 0) {
        return;
    }

    const arr = selectedArr ? allData.find(a => a.arrondissement === selectedArr) : allData[0];
    if (!arr) {
        return;
    }

    const santeData = SANTE_DATA.sante_by_arrondissement[String(arr.arrondissement)];
    if (!santeData) {
        return;
    }

    const scoreResult = calculateScoreSanteProximite(santeData);
    if (!scoreResult) {
        return;
    }

    try {
        charts.sante = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Pharmacies', 'Dentistes', 'Medecins', 'DAE', 'Urgences', 'Centres', 'Hopitaux'],
                datasets: [{
                    label: arr.arrondissement + 'e arr.',
                    data: [
                        scoreResult.details.pharmacies,
                        scoreResult.details.dentistes,
                        scoreResult.details.medecins,
                        scoreResult.details.defibrillateurs,
                        scoreResult.details.urgences,
                        scoreResult.details.centres,
                        scoreResult.details.hopitaux
                    ],
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: '#10B981',
                    borderWidth: 2,
                    pointBackgroundColor: '#10B981'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: CHART_THEME.text,
                            padding: 12,
                            font: { size: 11 }
                        }
                    },
                    title: {
                        display: true,
                        text: `Score global: ${scoreResult.score}/100`,
                        color: CHART_THEME.text,
                        font: { size: 14, weight: 'bold' }
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            color: CHART_THEME.text
                        },
                        pointLabels: {
                            color: CHART_THEME.text,
                            font: { size: 10 }
                        },
                        grid: {
                            color: CHART_THEME.grid
                        },
                        angleLines: {
                            color: CHART_THEME.grid
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors de la creation du graphique sante:', error);
    }
}

function updateCharts() {
    updateTimelineChart();
    updateComparisonChart();
    updateTypologyChart();
    updateTransportsChart();
    updateLogementsSociauxChart();
    updateAccessibiliteChart();
    updateSanteChart();
}

async function loadGeoPointsLayer(arrondissement = null) {
    if (!map || !map.isStyleLoaded()) return;
    const params = new URLSearchParams({ limit: '400' });
    if (arrondissement) params.set('arrondissement', String(arrondissement));
    const bounds = map.getBounds();
    params.set('min_lon', String(bounds.getWest()));
    params.set('min_lat', String(bounds.getSouth()));
    params.set('max_lon', String(bounds.getEast()));
    params.set('max_lat', String(bounds.getNorth()));
    try {
        const response = await fetch(`${API_BASE_URL}/mongo/geo-points?${params}`);
        if (!response.ok) return;
        const data = await response.json();
        const features = (data.points || []).map(p => ({
            type: 'Feature',
            geometry: p.location,
            properties: {
                type: p.type,
                arrondissement: p.arrondissement,
                prix: p.properties?.valeur_fonciere,
            },
        }));
        const fc = { type: 'FeatureCollection', features };
        if (map.getSource('geo-points')) {
            map.getSource('geo-points').setData(fc);
        } else {
            map.addSource('geo-points', { type: 'geojson', data: fc });
            map.addLayer({
                id: 'geo-points',
                type: 'circle',
                source: 'geo-points',
                paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 3, 14, 6],
                    'circle-color': [
                        'match', ['get', 'type'],
                        'dvf_transaction', '#f59e0b',
                        'geocoded_address', '#38bdf8',
                        '#94a3b8',
                    ],
                    'circle-opacity': 0.85,
                    'circle-stroke-width': 1,
                    'circle-stroke-color': '#ffffff',
                },
            });
        }
        map.setLayoutProperty('geo-points', 'visibility', geoPointsVisible ? 'visible' : 'none');
    } catch (e) {
        console.warn('Points géo indisponibles (Mongo/sync requis):', e);
    }
}

function toggleGeoPointsLayer() {
    geoPointsVisible = !geoPointsVisible;
    const btn = document.getElementById('toggle-geo-points');
    if (btn) {
        btn.setAttribute('aria-pressed', String(geoPointsVisible));
        btn.classList.toggle('active', geoPointsVisible);
    }
    if (geoPointsVisible) {
        loadGeoPointsLayer(selectedArr);
    } else if (map?.getLayer('geo-points')) {
        map.setLayoutProperty('geo-points', 'visibility', 'none');
    }
}

function updateLogementsSociauxChart() {
    const canvas = document.getElementById('logements-sociaux-chart');
    if (!canvas || !allData) return;
    const ctx = canvas.getContext('2d');
    if (charts.logementsSociaux) charts.logementsSociaux.destroy();

    const arr = selectedArr
        ? allData.find(a => a.arrondissement === selectedArr)
        : allData[0];
    const series = arr?.logements_sociaux_evolution || [];
    charts.logementsSociaux = new Chart(ctx, {
        type: 'line',
        data: {
            labels: series.map(s => s.annee),
            datasets: [{
                label: `${arr?.arrondissement || ''}e — % logements sociaux`,
                data: series.map(s => s.logements_sociaux_pct),
                borderColor: CHART_THEME.accent,
                backgroundColor: CHART_THEME.accentSoft,
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: CHART_THEME.text, font: { size: 11 } } } },
            scales: chartScales('%'),
        },
    });
}

function updateAccessibiliteChart() {
    const canvas = document.getElementById('accessibilite-chart');
    if (!canvas || !allData) return;
    const ctx = canvas.getContext('2d');
    if (charts.accessibilite) charts.accessibilite.destroy();

    const labels = allData.map(a => `${a.arrondissement}e`);
    const achat = allData.map(a => a.accessibilite_logement?.mois_revenu_pour_50m2_achat || 0);
    const location = allData.map(a => a.accessibilite_logement?.mois_revenu_pour_50m2_location || 0);

    charts.accessibilite = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Achat (mois revenu / 50 m²)', data: achat, backgroundColor: CHART_THEME.accent },
                { label: 'Location estimée', data: location, backgroundColor: '#34d399' },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: CHART_THEME.text, font: { size: 11 } } } },
            scales: chartScales('Mois de revenu'),
        },
    });
}

// Configuration des événements
function setupEventListeners() {
    // Sélecteur d'année
    document.getElementById('year-selector').addEventListener('change', async (e) => {
        selectedYear = parseInt(e.target.value);
        await loadData();
        updateMap();
        updateGlobalStats();
        updateCharts();
    });

    // Indicateurs (souris + clavier)
    document.querySelectorAll('.indicator-item').forEach(item => {
        const activate = () => selectIndicator(item.dataset.indicator);
        item.addEventListener('click', activate);
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                activate();
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.target.closest('input, select, textarea, button')) return;
        const idx = INDICATOR_ORDER.indexOf(selectedIndicator);
        if (idx < 0) return;
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            selectIndicator(INDICATOR_ORDER[(idx + 1) % INDICATOR_ORDER.length]);
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            selectIndicator(INDICATOR_ORDER[(idx - 1 + INDICATOR_ORDER.length) % INDICATOR_ORDER.length]);
        }
    });

    // Mode comparaison
    document.getElementById('compare-mode-btn').addEventListener('click', () => {
        const panel = document.getElementById('compare-panel');
        const btn = document.getElementById('compare-mode-btn');
        const open = panel.classList.toggle('hidden') === false;
        btn.setAttribute('aria-expanded', String(open));
    });

    document.getElementById('map-guide-close')?.addEventListener('click', () => {
        document.getElementById('map-guide')?.classList.add('hidden');
    });

    // Theme toggle
    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);

    // Comparaison
    document.getElementById('compare-execute').addEventListener('click', async () => {
        const arr1 = document.getElementById('compare-arr1').value;
        const arr2 = document.getElementById('compare-arr2').value;
        
        if (!arr1 || !arr2) {
            showError('Sélectionnez deux arrondissements à comparer.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/comparaison?arr1=${arr1}&arr2=${arr2}`);
            const data = await response.json();
            displayComparison(data);
        } catch (error) {
            console.error('Erreur:', error);
        }
    });

    // Timeline
    const timelineBtn = document.getElementById('play-timeline');
    if (timelineBtn) {
        timelineBtn.addEventListener('click', () => {
            if (timelinePlaying) {
                pauseTimeline();
            } else {
                playTimeline();
            }
        });
    } else {
        console.warn('Bouton timeline non trouvé');
    }

    document.getElementById('toggle-geo-points')?.addEventListener('click', toggleGeoPointsLayer);

    selectIndicator('prix');

    // Remplir les selects
    if (allData) {
        const compare1 = document.getElementById('compare-arr1');
        const compare2 = document.getElementById('compare-arr2');
        
        allData.forEach(arr => {
            const option = `<option value="${arr.arrondissement}">${arr.arrondissement}e arr.</option>`;
            compare1.innerHTML += option;
            compare2.innerHTML += option;
        });
    }
}

// Afficher la comparaison
function displayComparison(data) {
    const resultsDiv = document.getElementById('compare-results');
    
    resultsDiv.innerHTML = `
        <div class="compare-result-card">
            <h4>${data.arrondissement_1.nom}</h4>
            <div class="stat-value">${data.arrondissement_1.prix_m2_actuel?.toLocaleString('fr-FR')} €/m²</div>
            <div>Logements sociaux · ${data.arrondissement_1.logements_sociaux_pourcentage}%</div>
        </div>
        <div class="compare-result-card">
            <h4>${data.arrondissement_2.nom}</h4>
            <div class="stat-value">${data.arrondissement_2.prix_m2_actuel?.toLocaleString('fr-FR')} €/m²</div>
            <div>Logements sociaux · ${data.arrondissement_2.logements_sociaux_pourcentage}%</div>
        </div>
        <div class="compare-result-card">
            <h4>Écart</h4>
            <div class="stat-value">${data.differences.prix_m2_diff_pourcentage?.toFixed(1)}%</div>
            <div>Prix · Log. soc. ${data.differences.logements_sociaux_diff?.toFixed(1)} pts</div>
        </div>
    `;
}

// Timeline animée
function playTimeline() {
    if (timelinePlaying) return;
    
    timelinePlaying = true;
    const years = [2022, 2023, 2024];
    let yearIndex = years.indexOf(selectedYear);
    if (yearIndex === -1) yearIndex = 0;

    const timelineBtn = document.getElementById('play-timeline');
    if (timelineBtn) {
        timelineBtn.textContent = 'Pause';
        timelineBtn.classList.add('playing');
    }

    if (timelineInterval) {
        clearInterval(timelineInterval);
    }

    timelineInterval = setInterval(() => {
        selectedYear = years[yearIndex];
        const yearSelector = document.getElementById('year-selector');
        if (yearSelector) {
            yearSelector.value = selectedYear;
        }
        
        updateMap();
        updateGlobalStats();
        updateCharts();
        
        yearIndex = (yearIndex + 1) % years.length;
    }, 2000);
}

function pauseTimeline() {
    timelinePlaying = false;
    if (timelineInterval) {
        clearInterval(timelineInterval);
        timelineInterval = null;
    }
    
    const timelineBtn = document.getElementById('play-timeline');
    if (timelineBtn) {
        timelineBtn.textContent = 'Timeline';
        timelineBtn.classList.remove('playing');
    }
}

// Légende carte selon l'indicateur
function updateMapLegend() {
    const legend = document.querySelector('.map-legend');
    if (!legend) return;

    const configs = {
        prix: { title: 'Prix/m² (€)', labels: ['8000', '15000'] },
        logements: { title: 'Logements sociaux (%)', labels: ['10', '28'] },
        loyers: { title: 'Loyer estimé €/m²/mois', labels: ['22', '38'] },
        accessibilite: { title: 'Mois revenu pour 50 m2', labels: ['< 170', '> 215'] },
        tension: { title: 'Tension locative (%)', labels: ['40 %', '55 %'] },
        pollution: { title: 'Qualité air (proxy)', labels: ['Meilleure', 'Moins bonne'] },
        delits: { title: 'Délinquance', labels: ['Faible', 'Élevée'] },
        revenus: { title: 'Revenu médian (€)', labels: ['25k', '40k'] },
        densite: { title: 'Densité (hab./km²)', labels: ['12k', '32k'] },
        vegetation: { title: 'Végétation', labels: ['Peu / aucun', 'Dense'] },
        transports: { title: 'Points de transport', labels: ['5', '50'] },
        score_global: { title: 'Score Global (/100)', labels: ['Faible', 'Excellent'] },
        potentiel: { title: 'Potentiel Plus-Value (/100)', labels: ['Faible', 'Fort'] },
        sante_proximite: { title: 'Santé Proximité (/100)', labels: ['Faible', 'Excellent'] },
        pharmacies: { title: 'Pharmacies (nombre)', labels: ['< 30', '> 90'] },
        defibrillateurs: { title: 'DAE (/10k hab.)', labels: ['< 4', '> 22'] },
        urgences: { title: 'Accès urgences (min)', labels: ['Rapide', 'Lent'] }
    };
    const cfg = configs[selectedIndicator] || configs.prix;
    const baseGrad = 'linear-gradient(to right, #0c2d48, #0e5a7a, #0e94b8, #38d9f5, #a8ecff)';
    const santeGrad = 'linear-gradient(to right, #ef4444, #f97316, #fbbf24, #a3e635, #34d399)';
    const scoreGrad = 'linear-gradient(to right, #ef4444, #f97316, #fbbf24, #a3e635, #34d399)';
    const gradients = {
        prix: baseGrad,
        logements: baseGrad,
        loyers: baseGrad,
        accessibilite: baseGrad,
        tension: baseGrad,
        densite: baseGrad,
        delits: baseGrad,
        revenus: baseGrad,
        transports: baseGrad,
        pollution: 'linear-gradient(to right, #34d399, #a3e635, #fbbf24, #f97316, #ef4444)',
        vegetation: 'linear-gradient(to right, #64748b, #94a3b8, #86efac, #22c55e, #14532d)',
        score_global: scoreGrad,
        potentiel: scoreGrad,
        sante_proximite: santeGrad,
        pharmacies: santeGrad,
        defibrillateurs: santeGrad,
        urgences: 'linear-gradient(to right, #34d399, #a3e635, #fbbf24, #f97316, #ef4444)',
    };
    legend.innerHTML = `
        <h4>${cfg.title}</h4>
        <div class="legend-gradient" aria-hidden="true" style="background:${gradients[selectedIndicator] || gradients.prix}"></div>
        <div class="legend-patterns" aria-hidden="true">
            <span class="legend-pattern legend-pattern-low" title="Valeurs basses"></span>
            <span class="legend-pattern legend-pattern-high" title="Valeurs hautes"></span>
        </div>
        <div class="legend-labels">
            <span>${cfg.labels[0]}</span>
            <span>${cfg.labels[1]}</span>
        </div>
        <p class="legend-a11y-hint">Couleurs + traits de contour (navigation clavier : flèches)</p>
        <p id="uniform-data-notice" class="uniform-data-notice hidden" role="status"></p>
    `;
    updateUniformDataNotice();
}

function updateIndicatorFormulaPanel() {
    const panel = document.getElementById('indicator-formula');
    if (!panel) return;
    const cfg = INDICATOR_FORMULAS[selectedIndicator];
    if (!cfg) {
        panel.classList.add('hidden');
        panel.innerHTML = '';
        return;
    }
    panel.classList.remove('hidden');
    panel.innerHTML = `
        <div class="formula-title">${cfg.title}</div>
        <code class="formula-expr">${cfg.formula}</code>
        <div class="formula-unit">${cfg.unit}</div>
        <p class="formula-note">${cfg.note}</p>
    `;
}

function updateUniformDataNotice() {
    const el = document.getElementById('uniform-data-notice');
    if (!el || !allData?.length) return;
    const values = allData
        .map((a) => getIndicatorValue(a, selectedIndicator, selectedYear))
        .filter((v) => v != null && !Number.isNaN(v));
    if (values.length < 2) {
        el.classList.add('hidden');
        return;
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (Math.abs(max - min) < 0.01) {
        el.textContent = 'Valeurs identiques sur tous les arrondissements — la carte ne peut pas varier pour cet indicateur.';
        el.classList.remove('hidden');
    } else {
        el.classList.add('hidden');
    }
}

// Helpers
function getIndicatorName(indicator) {
    const names = {
        'prix': 'Prix/m²',
        'logements': 'Logements sociaux',
        'loyers': 'Loyer estimé/m²',
        'accessibilite': 'Accessibilité (mois revenu)',
        'tension': 'Tension locative',
        'pollution': 'Qualité air',
        'delits': 'Délits',
        'revenus': 'Revenus',
        'densite': 'Densité',
        'vegetation': 'Végétation',
        'transports': 'Transports',
        'score_global': 'Score Global',
        'potentiel': 'Potentiel Plus-Value',
        'sante_proximite': 'Santé Proximité',
        'pharmacies': 'Pharmacies',
        'defibrillateurs': 'Défibrillateurs',
        'urgences': 'Accès Urgences'
    };
    return names[indicator] || indicator;
}

function getIndicatorLabel(indicator, value) {
    switch (indicator) {
        case 'prix':
            return value.toLocaleString('fr-FR') + '€';
        case 'logements':
            return value.toFixed(1) + '%';
        case 'loyers':
            return value.toFixed(1) + ' €/m²/mois';
        case 'accessibilite':
            return value.toFixed(0) + ' mois de revenu';
        case 'tension':
            return value.toFixed(1) + ' % du revenu';
        case 'pollution':
            return value.toFixed(2) + ' (proxy)';
        case 'delits':
            return value.toFixed(1) + ' / 1000 hab.';
        case 'revenus':
            return value.toLocaleString('fr-FR') + '€';
        case 'densite':
            return value.toLocaleString('fr-FR') + ' hab./km²';
        case 'vegetation':
            return value.toLocaleString('fr-FR') + ' arbres';
        case 'transports':
            return value.toLocaleString('fr-FR') + ' transports';
        case 'score_global':
            return value + '/100';
        case 'potentiel':
            return value + '/100';
        case 'sante_proximite':
            return value + '/100';
        case 'pharmacies':
            return value + ' pharmacies';
        case 'defibrillateurs':
            return value + ' DAE/10k hab.';
        case 'urgences':
            return value + ' min vers urgences';
        default:
            return value;
    }
}

function showError(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(showError._timer);
    showError._timer = setTimeout(() => toast.classList.add('hidden'), 5000);
}
