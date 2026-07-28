function readMapaJson(id) {
    const node = document.getElementById(id);
    if (!node) {
        return null;
    }
    try {
        return JSON.parse(node.textContent);
    } catch (error) {
        console.error("Falha ao interpretar dados do mapa eleitoral", error);
        return null;
    }
}

function layerStyle(layerName) {
    const palette = {
        contatos: { color: "#1d4ed8", radius: 11 },
        liderancas: { color: "#f59e0b", radius: 12 },
        eventos: { color: "#16a34a", radius: 10 },
        equipes: { color: "#0891b2", radius: 12 },
    };
    return palette[layerName] || { color: "#334155", radius: 10 };
}

function createMapMarker(layerName, item) {
    const style = layerStyle(layerName);
    const marker = L.circleMarker([item.lat, item.lng], {
        radius: style.radius,
        color: style.color,
        fillColor: style.color,
        fillOpacity: 0.24,
        weight: 2,
    });
    marker.bindPopup(item.popup || "Marcador territorial");
    return marker;
}

function buildClusterGroup(layerName, items) {
    const cluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: true,
        maxClusterRadius: 44,
    });
    const bounds = [];
    (items || []).forEach((item) => {
        if (typeof item.lat !== "number" || typeof item.lng !== "number") {
            return;
        }
        cluster.addLayer(createMapMarker(layerName, item));
        bounds.push([item.lat, item.lng]);
    });
    return { cluster, bounds };
}

function initMapaEleitoral() {
    const container = document.getElementById("mapaEleitoralPrincipal");
    const camadas = readMapaJson("mapa-eleitoral-camadas-data");
    const visibilidade = readMapaJson("mapa-eleitoral-visibilidade-data");
    if (!container || !window.L || !camadas) {
        return;
    }

    const mapa = L.map(container, {
        scrollWheelZoom: false,
        zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(mapa);

    const grupos = {};
    const todosBounds = [];
    ["contatos", "liderancas", "eventos", "equipes"].forEach((layerName) => {
        const { cluster, bounds } = buildClusterGroup(layerName, camadas[layerName]);
        grupos[layerName] = cluster;
        bounds.forEach((bound) => todosBounds.push(bound));
        if (visibilidade && visibilidade[layerName]) {
            cluster.addTo(mapa);
        }
    });

    if (todosBounds.length === 1) {
        mapa.setView(todosBounds[0], 11);
    } else if (todosBounds.length > 1) {
        mapa.fitBounds(todosBounds, { padding: [24, 24] });
    } else {
        mapa.setView([-3.731862, -38.526669], 8);
    }

    document.querySelectorAll("[data-layer-toggle]").forEach((toggle) => {
        toggle.addEventListener("change", () => {
            const layerName = toggle.value;
            const grupo = grupos[layerName];
            if (!grupo) {
                return;
            }
            if (toggle.checked) {
                grupo.addTo(mapa);
            } else {
                mapa.removeLayer(grupo);
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", initMapaEleitoral);
