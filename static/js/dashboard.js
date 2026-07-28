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

function initStatusChart() {
    const ctx = document.getElementById("graficoStatusContato");
    const data = parseJsonScript("grafico-status-data");
    if (!ctx || !data || !window.Chart) {
        return;
    }
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: data.map((item) => item.status_funil),
            datasets: [
                {
                    data: data.map((item) => item.total),
                    backgroundColor: ["#1d4ed8", "#2563eb", "#0f766e", "#16a34a", "#eab308", "#f97316", "#ef4444"],
                },
            ],
        },
        options: {
            plugins: {
                legend: {
                    position: "bottom",
                },
            },
        },
    });
}

function initCidadeChart() {
    const ctx = document.getElementById("graficoCidadeContato");
    const data = parseJsonScript("grafico-cidades-data");
    if (!ctx || !data || !window.Chart) {
        return;
    }
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map((item) => item.cidade),
            datasets: [
                {
                    label: "Contatos",
                    data: data.map((item) => item.total),
                    backgroundColor: "#1d4ed8",
                    borderRadius: 12,
                },
            ],
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                },
            },
        },
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    initStatusChart();
    initCidadeChart();
});
