function parseJsonScript(id) {
    const node = document.getElementById(id);
    if (!node) {
        return null;
    }
    try {
        return JSON.parse(node.textContent);
    } catch (error) {
        console.error("Falha ao interpretar JSON do dashboard", error);
        return null;
    }
}

function resolveCssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function initThemeToggle() {
    const toggle = document.querySelector("[data-tema-toggle]");
    if (!toggle) {
        return;
    }
    const root = document.documentElement;
    const savedTheme = localStorage.getItem("tema-aplicacao");
    if (savedTheme) {
        root.setAttribute("data-bs-theme", savedTheme);
    }
    toggle.addEventListener("click", () => {
        const currentTheme = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-bs-theme", currentTheme);
        localStorage.setItem("tema-aplicacao", currentTheme);
    });
}

function chartTextColor() {
    return resolveCssVar("--text-soft", "#64748b");
}

function chartGridColor() {
    return resolveCssVar("--line-color", "rgba(148, 163, 184, 0.2)");
}

function buildChart(id, config) {
    const ctx = document.getElementById(id);
    if (!ctx || !window.Chart) {
        return null;
    }
    return new Chart(ctx, config);
}

function initEvolucaoChart() {
    const data = parseJsonScript("grafico-evolucao-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoEvolucaoCadastros", {
        type: "line",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "Contatos",
                    data: data.map((item) => item.contatos),
                    borderColor: resolveCssVar("--primary", "#1d4ed8"),
                    backgroundColor: "rgba(29, 78, 216, 0.18)",
                    tension: 0.35,
                    fill: true,
                },
                {
                    label: "Liderancas",
                    data: data.map((item) => item.liderancas),
                    borderColor: "#0f766e",
                    backgroundColor: "rgba(15, 118, 110, 0.12)",
                    tension: 0.35,
                    fill: true,
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: chartTextColor(),
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: chartTextColor() },
                    grid: { color: chartGridColor() },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor(), precision: 0 },
                    grid: { color: chartGridColor() },
                },
            },
        },
    });
}

function initStatusChart() {
    const data = parseJsonScript("grafico-status-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoStatusContato", {
        type: "doughnut",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    data: data.map((item) => item.total),
                    backgroundColor: ["#1d4ed8", "#2563eb", "#0f766e", "#16a34a", "#eab308", "#f97316", "#ef4444", "#7c3aed"],
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: chartTextColor(),
                    },
                },
            },
        },
    });
}

function initCidadeChart() {
    const data = parseJsonScript("grafico-cidades-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoCidadeContato", {
        type: "bar",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "Contatos",
                    data: data.map((item) => item.total),
                    backgroundColor: resolveCssVar("--primary", "#1d4ed8"),
                    borderRadius: 12,
                },
            ],
        },
        options: {
            indexAxis: "y",
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor(), precision: 0 },
                    grid: { color: chartGridColor() },
                },
                y: {
                    ticks: { color: chartTextColor() },
                    grid: { display: false },
                },
            },
        },
    });
}

function initBairroChart() {
    const data = parseJsonScript("grafico-bairros-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoBairroContato", {
        type: "bar",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "Contatos",
                    data: data.map((item) => item.total),
                    backgroundColor: "#0f766e",
                    borderRadius: 12,
                },
            ],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    ticks: { color: chartTextColor() },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor(), precision: 0 },
                    grid: { color: chartGridColor() },
                },
            },
        },
    });
}

function initLiderancasRegiaoChart() {
    const data = parseJsonScript("grafico-liderancas-regiao-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoLiderancasRegiao", {
        type: "bar",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "Liderancas",
                    data: data.map((item) => item.total),
                    backgroundColor: "#f97316",
                    borderRadius: 12,
                },
            ],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    ticks: { color: chartTextColor() },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor(), precision: 0 },
                    grid: { color: chartGridColor() },
                },
            },
        },
    });
}

function initMetasEquipeChart() {
    const data = parseJsonScript("grafico-metas-equipe-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoMetasEquipe", {
        type: "bar",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "% de conclusao",
                    data: data.map((item) => item.percentual),
                    backgroundColor: "#7c3aed",
                    borderRadius: 12,
                },
            ],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    ticks: { color: chartTextColor() },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: chartTextColor() },
                    grid: { color: chartGridColor() },
                },
            },
        },
    });
}

function initFinanceiroChart() {
    const data = parseJsonScript("grafico-financeiro-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoFinanceiroMensal", {
        type: "bar",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    label: "Receitas",
                    data: data.map((item) => item.receitas),
                    backgroundColor: "#16a34a",
                    borderRadius: 12,
                },
                {
                    label: "Despesas",
                    data: data.map((item) => item.despesas),
                    backgroundColor: "#ef4444",
                    borderRadius: 12,
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: chartTextColor() },
                },
            },
            scales: {
                x: {
                    ticks: { color: chartTextColor() },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor() },
                    grid: { color: chartGridColor() },
                },
            },
        },
    });
}

function initMapaCadastros() {
    const container = document.getElementById("mapaCadastrosAutorizados");
    const data = parseJsonScript("mapa-cadastros-data");
    if (!container || !window.L || !data || !data.length) {
        return;
    }

    const mapa = L.map(container, {
        scrollWheelZoom: false,
        zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(mapa);

    const bounds = [];
    data.forEach((item) => {
        const radius = Math.min(18, 6 + item.total * 1.5);
        const marker = L.circleMarker([item.lat, item.lng], {
            radius,
            color: resolveCssVar("--primary", "#1d4ed8"),
            fillColor: resolveCssVar("--primary", "#1d4ed8"),
            fillOpacity: 0.24,
            weight: 2,
        });
        marker.bindPopup(
            `<strong>${item.cidade}</strong><br>${item.bairro}<br>${item.total} cadastros autorizados`
        );
        marker.addTo(mapa);
        bounds.push([item.lat, item.lng]);
    });

    if (bounds.length === 1) {
        mapa.setView(bounds[0], 12);
    } else {
        mapa.fitBounds(bounds, { padding: [24, 24] });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    initEvolucaoChart();
    initStatusChart();
    initCidadeChart();
    initBairroChart();
    initLiderancasRegiaoChart();
    initMetasEquipeChart();
    initFinanceiroChart();
    initMapaCadastros();
});
