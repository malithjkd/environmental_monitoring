/* ============================================================
   Smart Yogurt Maker — Dashboard Application Logic
   ============================================================ */

// ---- Chart Setup ----
const MAX_CHART_POINTS = 900; // ~30 min at 2s intervals
let chart = null;
let chartData = {
    labels: [],
    temperature: [],
    setpoint: [],
    duty: [],
};

function initChart() {
    const ctx = document.getElementById("tempChart").getContext("2d");

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "Temperature (°C)",
                    data: chartData.temperature,
                    borderColor: "#ff5722",
                    backgroundColor: "rgba(255, 87, 34, 0.08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true,
                    yAxisID: "y",
                },
                {
                    label: "Setpoint (°C)",
                    data: chartData.setpoint,
                    borderColor: "#4caf50",
                    borderWidth: 1.5,
                    borderDash: [6, 4],
                    pointRadius: 0,
                    tension: 0,
                    fill: false,
                    yAxisID: "y",
                },
                {
                    label: "Duty Cycle (%)",
                    data: chartData.duty,
                    borderColor: "#2196f3",
                    backgroundColor: "rgba(33, 150, 243, 0.06)",
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true,
                    yAxisID: "y1",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: "index",
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(18, 18, 30, 0.95)",
                    titleColor: "#e8e8f0",
                    bodyColor: "#8888a0",
                    borderColor: "rgba(255,255,255,0.1)",
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { family: "Inter", size: 12, weight: 600 },
                    bodyFont: { family: "Inter", size: 11 },
                },
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        color: "#555570",
                        font: { family: "Inter", size: 10 },
                        maxTicksLimit: 10,
                        maxRotation: 0,
                    },
                    grid: { color: "rgba(255,255,255,0.03)" },
                },
                y: {
                    type: "linear",
                    position: "left",
                    title: {
                        display: true,
                        text: "Temperature (°C)",
                        color: "#ff5722",
                        font: { family: "Inter", size: 11 },
                    },
                    ticks: {
                        color: "#ff5722",
                        font: { family: "Inter", size: 10 },
                    },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y1: {
                    type: "linear",
                    position: "right",
                    title: {
                        display: true,
                        text: "Duty Cycle (%)",
                        color: "#2196f3",
                        font: { family: "Inter", size: 11 },
                    },
                    min: 0,
                    max: 100,
                    ticks: {
                        color: "#2196f3",
                        font: { family: "Inter", size: 10 },
                    },
                    grid: { drawOnChartArea: false },
                },
            },
            animation: { duration: 300 },
        },
    });
}

// ---- Machine Profiles ----
let machineConfig = null;

async function loadMachines() {
    try {
        const resp = await fetch("/api/machines");
        machineConfig = await resp.json();

        const select = document.getElementById("machineSelect");
        select.innerHTML = "";

        for (const [id, machine] of Object.entries(machineConfig.machines)) {
            const option = document.createElement("option");
            option.value = id;
            option.textContent = machine.name;
            select.appendChild(option);
        }
    } catch (err) {
        console.error("Failed to load machines:", err);
    }
}

// ---- Server-Sent Events ----
let eventSource = null;

function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource("/api/events");

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (err) {
            console.error("SSE parse error:", err);
        }
    };

    eventSource.onerror = () => {
        updateConnectionStatus(false);
        // Auto-reconnect is built into EventSource
    };
}

// ---- Dashboard Updates ----
function updateDashboard(data) {
    const connected = data.connected || false;
    updateConnectionStatus(connected);

    // Temperature
    const tempEl = document.getElementById("currentTemp");
    tempEl.textContent = typeof data.t === "number" ? data.t.toFixed(1) : "--.-";

    // Target
    const targetEl = document.getElementById("targetTemp");
    targetEl.textContent = data.sp ? data.sp.toFixed(1) : "--.-";

    // Duty cycle
    const dutyPercent = (data.duty || 0) * 100;
    document.getElementById("dutyPercent").textContent = dutyPercent.toFixed(1);
    document.getElementById("dutyBar").style.width = dutyPercent + "%";

    // Relay
    const relayEl = document.getElementById("relayState");
    if (data.relay) {
        relayEl.textContent = "ON";
        relayEl.className = "relay-on";
    } else {
        relayEl.textContent = "OFF";
        relayEl.className = "relay-off";
    }

    // Stage
    document.getElementById("currentStage").textContent = data.stage || "IDLE";
    updateStageProgress(data.stage);

    // Elapsed times
    document.getElementById("stageElapsed").textContent = formatDuration(data.stage_elapsed || 0);
    document.getElementById("totalElapsed").textContent = formatDuration(data.elapsed || 0);

    // Update chart
    if (connected && typeof data.t === "number") {
        addChartPoint(data);
    }

    // Update sensor location and CSV status displays
    const sensorDisplay = document.getElementById("sensorLocationDisplay");
    if (sensorDisplay && data.sensor_location) {
        sensorDisplay.textContent = data.sensor_location === "inside_pot" ? "Inside Pot" : "Water Bath";
        sensorDisplay.style.color = data.sensor_location === "inside_pot" ? "#ff9800" : "#4ecdc4";
    }

    const csvDisplay = document.getElementById("csvStatusDisplay");
    if (csvDisplay && data.csv_paused !== undefined) {
        csvDisplay.textContent = data.csv_paused ? "PAUSED" : "Recording";
        csvDisplay.style.color = data.csv_paused ? "#ff5252" : "#4caf50";
        const toggleBtn = document.getElementById("btnToggleCsv");
        if (toggleBtn) {
            toggleBtn.textContent = data.csv_paused ? "▶ Resume Logging" : "⏸ Pause Logging";
        }
    }

    // Water swap notification when entering COOL_DOWN
    if (data.stage === "COOL_DOWN" && !window._coolDownNotified) {
        window._coolDownNotified = true;
        const swapBtn = document.getElementById("btnWaterSwap");
        if (swapBtn) {
            swapBtn.style.animation = "pulse 1s infinite";
            swapBtn.style.background = "rgba(33,150,243,0.6)";
        }
    } else if (data.stage !== "COOL_DOWN") {
        window._coolDownNotified = false;
        const swapBtn = document.getElementById("btnWaterSwap");
        if (swapBtn) {
            swapBtn.style.animation = "";
            swapBtn.style.background = "rgba(33,150,243,0.3)";
        }
    }
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("connectionText");

    if (connected) {
        dot.classList.add("connected");
        text.textContent = "Connected";
    } else {
        dot.classList.remove("connected");
        text.textContent = "Disconnected";
    }
}

function updateStageProgress(currentStage) {
    const stages = ["RAPID_HEAT", "PASTEURIZE", "HOLD_85", "COOL_DOWN", "FERMENT", "DONE"];
    const currentIdx = stages.indexOf(currentStage);

    stages.forEach((stage, idx) => {
        const el = document.getElementById("stage-" + stage);
        if (!el) return;

        el.classList.remove("active", "completed");

        if (idx === currentIdx) {
            el.classList.add("active");
        } else if (idx < currentIdx) {
            el.classList.add("completed");
        }
    });
}

function addChartPoint(data) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });

    chartData.labels.push(timeStr);
    chartData.temperature.push(data.t);
    chartData.setpoint.push(data.sp || null);
    chartData.duty.push((data.duty || 0) * 100);

    // Trim to max points
    while (chartData.labels.length > MAX_CHART_POINTS) {
        chartData.labels.shift();
        chartData.temperature.shift();
        chartData.setpoint.shift();
        chartData.duty.shift();
    }

    if (chart) {
        chart.update("none"); // 'none' disables animation for smooth streaming
    }
}

// ---- Control Actions ----
async function startProcess() {
    const machine = document.getElementById("machineSelect").value;
    if (!machine) {
        alert("Please select a machine.");
        return;
    }

    const payload = {
        machine: machine,
        water_volume_liters: parseFloat(document.getElementById("waterVolume").value),
        pasteurize_temp: parseFloat(document.getElementById("pasteurizeTemp").value),
        hold_85_duration_min: parseInt(document.getElementById("holdDuration").value),
        ferment_temp: parseFloat(document.getElementById("fermentTemp").value),
        ferment_duration_hours: parseInt(document.getElementById("fermentDuration").value),
        ambient_temp: parseFloat(document.getElementById("ambientTemp").value),
        start_stage: document.getElementById("startStage").value,
    };

    document.getElementById("btnStart").disabled = true;
    document.getElementById("btnStart").textContent = "⏳ Deploying...";

    try {
        const resp = await fetch("/api/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await resp.json();

        if (resp.ok) {
            document.getElementById("btnStart").textContent = "✓ Running";
            document.getElementById("btnStop").disabled = false;

            // Clear chart for new run (mutate original arrays so Chart.js keeps the reference)
            chartData.labels.length = 0;
            chartData.temperature.length = 0;
            chartData.setpoint.length = 0;
            chartData.duty.length = 0;
            if (chart) chart.update();
        } else {
            alert("Error: " + (result.detail || "Unknown error"));
            document.getElementById("btnStart").disabled = false;
            document.getElementById("btnStart").textContent = "▶ Start Process";
        }
    } catch (err) {
        alert("Failed to connect to server: " + err.message);
        document.getElementById("btnStart").disabled = false;
        document.getElementById("btnStart").textContent = "▶ Start Process";
    }
}

async function stopProcess() {
    if (!confirm("Are you sure you want to stop the process? The heater will be turned OFF.")) {
        return;
    }

    try {
        await fetch("/api/stop", { method: "POST" });
        document.getElementById("btnStart").disabled = false;
        document.getElementById("btnStart").textContent = "▶ Start Process";
        document.getElementById("btnStop").disabled = true;
    } catch (err) {
        alert("Failed to stop: " + err.message);
    }
}

async function submitManualTemp() {
    const tempInput = document.getElementById("manualTempInput");
    const tempVal = parseFloat(tempInput.value);
    
    if (isNaN(tempVal)) {
        alert("Please enter a valid temperature.");
        return;
    }
    
    try {
        const resp = await fetch("/api/manual_temp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ temperature: tempVal })
        });
        
        if (resp.ok) {
            tempInput.value = ""; // clear after success
            // Optional: visual feedback
            const btn = tempInput.nextElementSibling;
            const originalText = btn.textContent;
            btn.textContent = "Logged!";
            btn.style.backgroundColor = "#4caf50";
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.backgroundColor = "";
            }, 2000);
        } else {
            alert("Failed to log manual temp");
        }
    } catch (err) {
        alert("Error connecting to server: " + err.message);
    }
}

async function setSensorLocation() {
    const select = document.getElementById("sensorLocation");
    const location = select.value;

    try {
        const resp = await fetch("/api/sensor_location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location: location }),
        });

        if (resp.ok) {
            const display = document.getElementById("sensorLocationDisplay");
            display.textContent = location === "inside_pot" ? "Inside Pot" : "Water Bath";
            display.style.color = location === "inside_pot" ? "#ff9800" : "#4ecdc4";
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function toggleCSVLogging() {
    try {
        const resp = await fetch("/api/toggle_csv", { method: "POST" });
        const result = await resp.json();

        const btn = document.getElementById("btnToggleCsv");
        const display = document.getElementById("csvStatusDisplay");

        if (result.csv_paused) {
            btn.textContent = "▶ Resume Logging";
            display.textContent = "PAUSED";
            display.style.color = "#ff5252";
        } else {
            btn.textContent = "⏸ Pause Logging";
            display.textContent = "Recording";
            display.style.color = "#4caf50";
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function logWaterSwap() {
    try {
        const resp = await fetch("/api/water_swap", { method: "POST" });

        if (resp.ok) {
            const btn = document.getElementById("btnWaterSwap");
            const originalText = btn.textContent;
            btn.textContent = "✅ Logged!";
            btn.style.background = "rgba(76,175,80,0.4)";
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = "rgba(33,150,243,0.3)";
            }, 3000);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// ---- Utilities ----
function formatDuration(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);
    return [hours, minutes, seconds]
        .map((v) => v.toString().padStart(2, "0"))
        .join(":");
}

// ---- Load History on Page Load ----
async function loadHistory() {
    try {
        const resp = await fetch("/api/history?minutes=60");
        const history = await resp.json();

        for (const point of history) {
            const ts = point.timestamp || "";
            const timePart = ts.split(" ")[1] || ts;
            chartData.labels.push(timePart);
            chartData.temperature.push(point.t || 0);
            chartData.setpoint.push(point.sp || null);
            chartData.duty.push((point.duty || 0) * 100);
        }

        if (chart) chart.update();
    } catch (err) {
        console.log("No history available yet.");
    }
}

// ---- Initialization ----
document.addEventListener("DOMContentLoaded", () => {
    initChart();
    loadMachines();
    loadHistory();
    connectSSE();
});
