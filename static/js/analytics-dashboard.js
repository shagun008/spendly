(function () {
    "use strict";

    var PRIMARY = "#1a472a";
    var SECONDARY = "#c17f24";
    var MUTED = "#6b6b6b";
    var MUTED_LIGHT = "#e4e1da";
    var CATEGORY_COLORS = [
        "#1a472a", "#c17f24", "#2c5f3a", "#d4943a",
        "#3d7a4e", "#e8b05a", "#5a9668", "#f0c478",
    ];

    function getCategoriesFromDOM() {
        var result = [];
        var rows = document.querySelectorAll(".category-row");
        rows.forEach(function (row) {
            var nameEl = row.querySelector(".category-name");
            var pctEl = row.querySelector(".category-bar-fill");
            if (nameEl && pctEl) {
                var pct = parseInt(pctEl.style.getPropertyValue("--pct"), 10);
                result.push({ name: nameEl.textContent.trim(), pct: isNaN(pct) ? 0 : pct });
            }
        });
        return result;
    }

    function renderTrends(ctx, data) {
        if (!data || !data.length) return null;
        return new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map(function (d) { return d.date; }),
                datasets: [{
                    label: "Spending",
                    data: data.map(function (d) { return d.total; }),
                    borderColor: PRIMARY,
                    backgroundColor: "rgba(26, 71, 42, 0.1)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointBackgroundColor: PRIMARY,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: {
                        ticks: { color: MUTED, font: { size: 11 } },
                        grid: { color: MUTED_LIGHT },
                    },
                    y: {
                        ticks: {
                            color: MUTED,
                            font: { size: 11 },
                            callback: function (v) { return "₹" + v.toLocaleString("en-IN"); },
                        },
                        grid: { color: MUTED_LIGHT },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    function renderCategories(ctx, data) {
        if (!data || !data.length) return null;
        return new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(function (d) { return d.name; }),
                datasets: [{
                    data: data.map(function (d) { return d.pct; }),
                    backgroundColor: CATEGORY_COLORS.slice(0, data.length),
                    borderColor: "#ffffff",
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: MUTED, font: { size: 11 }, padding: 12 },
                    },
                },
            },
        });
    }

    function renderMonthly(ctx, data) {
        if (!data) return null;
        return new Chart(ctx, {
            type: "bar",
            data: {
                labels: [data.previous_month.label, data.current_month.label],
                datasets: [{
                    label: "Total Spending",
                    data: [data.previous_month.total, data.current_month.total],
                    backgroundColor: [SECONDARY, PRIMARY],
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: {
                        ticks: { color: MUTED, font: { size: 11 } },
                        grid: { display: false },
                    },
                    y: {
                        ticks: {
                            color: MUTED,
                            font: { size: 11 },
                            callback: function (v) { return "₹" + v.toLocaleString("en-IN"); },
                        },
                        grid: { color: MUTED_LIGHT },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var container = document.querySelector(".analytics-dashboard");
        if (!container) return;

        var hasExpenses = container.getAttribute("data-has-expenses") === "true";
        var emptyEl = document.getElementById("analytics-empty");
        var canvas = document.getElementById("analytics-chart");
        var ctx = canvas.getContext("2d");

        if (!hasExpenses) {
            canvas.hidden = true;
            if (emptyEl) emptyEl.hidden = false;
            if (window.lucide) lucide.createIcons();
            return;
        }

        if (typeof Chart === "undefined") {
            canvas.hidden = true;
            if (emptyEl) {
                emptyEl.textContent = "Charts could not load. Please check your connection.";
                emptyEl.hidden = false;
            }
            return;
        }

        var trendsData, monthlyData, categoriesData;
        try {
            trendsData = JSON.parse(container.getAttribute("data-trends") || "[]");
            monthlyData = JSON.parse(container.getAttribute("data-monthly") || "{}");
            categoriesData = JSON.parse(container.getAttribute("data-categories") || "[]");
        } catch (e) {
            trendsData = [];
            monthlyData = {};
            categoriesData = [];
        }

        // Fallback: extract categories from DOM if embedded data is empty
        if (!categoriesData.length) {
            categoriesData = getCategoriesFromDOM();
        }

        var currentChart = null;

        function renderView(view) {
            if (currentChart) {
                currentChart.destroy();
                currentChart = null;
            }
            if (view === "trends") {
                currentChart = renderTrends(ctx, trendsData);
            } else if (view === "categories") {
                currentChart = renderCategories(ctx, categoriesData);
            } else if (view === "monthly") {
                currentChart = renderMonthly(ctx, monthlyData);
            }
        }

        // Initial view
        renderView("trends");

        // Tab switching
        var tabs = container.querySelectorAll(".analytics-tab");
        tabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                tabs.forEach(function (t) {
                    t.classList.remove("analytics-tab--active");
                    t.setAttribute("aria-selected", "false");
                });
                tab.classList.add("analytics-tab--active");
                tab.setAttribute("aria-selected", "true");
                renderView(tab.getAttribute("data-view"));
            });
        });
    });
})();
