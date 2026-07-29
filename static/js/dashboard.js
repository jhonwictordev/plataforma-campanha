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

function palette(name, fallback) {
    return resolveCssVar(name, fallback);
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
                    borderColor: palette("--primary", "#256f67"),
                    backgroundColor: "rgba(37, 111, 103, 0.16)",
                    tension: 0.35,
                    fill: true,
                },
                {
                    label: "Liderancas",
                    data: data.map((item) => item.liderancas),
                    borderColor: palette("--accent", "#c77a2b"),
                    backgroundColor: "rgba(199, 122, 43, 0.14)",
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
                    backgroundColor: ["#256f67", "#315d89", "#c77a2b", "#1f7a4d", "#b7791f", "#8a4f2d", "#b42318", "#5f6f52"],
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
                    backgroundColor: palette("--primary", "#256f67"),
                    borderRadius: 8,
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
                    backgroundColor: "#315d89",
                    borderRadius: 8,
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
                    backgroundColor: "#c77a2b",
                    borderRadius: 8,
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
                    backgroundColor: "#5f6f52",
                    borderRadius: 8,
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
                    backgroundColor: "#1f7a4d",
                    borderRadius: 8,
                },
                {
                    label: "Despesas",
                    data: data.map((item) => item.despesas),
                    backgroundColor: "#b42318",
                    borderRadius: 8,
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

function initAlertasChart() {
    const data = parseJsonScript("grafico-alertas-categoria-data");
    if (!data || !data.length) {
        return;
    }
    buildChart("graficoAlertasCategoria", {
        type: "doughnut",
        data: {
            labels: data.map((item) => item.rotulo),
            datasets: [
                {
                    data: data.map((item) => item.total),
                    backgroundColor: ["#b42318", "#c77a2b", "#256f67", "#315d89", "#5f6f52", "#1f7a4d", "#334155"],
                    borderWidth: 0,
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
            color: palette("--primary", "#256f67"),
            fillColor: palette("--primary", "#256f67"),
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
    initAlertasChart();
    initMapaCadastros();
});
