const API_BASE = "https://t20-oracle-api.onrender.com";

const form = document.getElementById("prediction-form");
const team1Select = document.getElementById("team1");
const team2Select = document.getElementById("team2");
const venueSelect = document.getElementById("venue");
const tossWinnerSelect = document.getElementById("toss_winner");
const battingFirstSelect = document.getElementById("batting_first");
const submitBtn = document.getElementById("submit-btn");
const btnText = submitBtn.querySelector(".btn-text");
const spinner = submitBtn.querySelector(".spinner");

const resultPanel = document.getElementById("result-panel");
const errorPanel = document.getElementById("error-panel");
const resWinner = document.getElementById("res-winner");
const resConfidence = document.getElementById("res-confidence");
const resReasoning = document.getElementById("res-reasoning");
const confCircle = document.getElementById("conf-circle");
const errorText = document.getElementById("error-text");

const MAX_RETRIES = 5;
const RETRY_DELAY = 5000;

async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
    for (let i = 0; i < retries; i++) {
        try {
            const res = await fetch(url, { ...options, signal: AbortSignal.timeout(30000) });
            if (res.ok) return res;
            if (res.status === 503 || res.status === 502) {
                showColdStartBanner(i + 1, retries);
                await sleep(RETRY_DELAY);
                continue;
            }
            throw new Error(`Server returned ${res.status}`);
        } catch (err) {
            if (i < retries - 1 && (err.name === "TimeoutError" || err.name === "TypeError" || err.message.includes("Failed to fetch"))) {
                showColdStartBanner(i + 1, retries);
                await sleep(RETRY_DELAY);
                continue;
            }
            throw err;
        }
    }
    throw new Error("Server is unavailable. Please try again in a minute.");
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function showColdStartBanner(attempt, max) {
    let banner = document.getElementById("cold-start-banner");
    if (!banner) {
        banner = document.createElement("div");
        banner.id = "cold-start-banner";
        banner.style.cssText = "position:fixed;top:0;left:0;right:0;background:linear-gradient(90deg,#2563EB,#10B981);color:#fff;text-align:center;padding:12px 16px;font-size:14px;font-weight:500;z-index:9999;font-family:Inter,sans-serif;";
        document.body.prepend(banner);
    }
    banner.textContent = `Waking up the server... (attempt ${attempt}/${max}). Free-tier servers sleep after inactivity.`;
}

function hideColdStartBanner() {
    const banner = document.getElementById("cold-start-banner");
    if (banner) banner.remove();
}

async function init() {
    try {
        await Promise.all([loadTeams(), loadVenues()]);
        hideColdStartBanner();
        setupEventListeners();
    } catch (err) {
        hideColdStartBanner();
        showError("Failed to connect to the AI server. Please refresh the page to try again.");
    }
}

async function loadTeams() {
    const res = await fetchWithRetry(`${API_BASE}/teams`);
    const teams = await res.json();
    populateSelect(team1Select, teams, "Select Home Team");
    populateSelect(team2Select, teams, "Select Away Team");
}

async function loadVenues() {
    const res = await fetchWithRetry(`${API_BASE}/venues`);
    const venues = await res.json();
    populateSelect(venueSelect, venues, "Select Match Venue");
}

function populateSelect(element, dataArray, defaultText) {
    element.innerHTML = `<option value="" disabled selected>${defaultText}</option>`;
    dataArray.forEach(item => {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        element.appendChild(option);
    });
}

function setupEventListeners() {
    [team1Select, team2Select].forEach(select => {
        select.addEventListener("change", updateTossOptions);
    });
    form.addEventListener("submit", handlePrediction);
}

function updateTossOptions() {
    const t1 = team1Select.value;
    const t2 = team2Select.value;
    if (t1 && t2) {
        if (t1 === t2) {
            alert("Team 1 and Team 2 must be different.");
            team2Select.value = "";
            return;
        }
        const teams = [t1, t2];
        populateSelect(tossWinnerSelect, teams, "Who won the toss?");
        populateSelect(battingFirstSelect, teams, "Who is batting first?");
        tossWinnerSelect.disabled = false;
        battingFirstSelect.disabled = false;
    } else {
        tossWinnerSelect.disabled = true;
        battingFirstSelect.disabled = true;
    }
}

async function handlePrediction(e) {
    e.preventDefault();
    hidePanels();
    setLoading(true);

    const payload = {
        team1: team1Select.value,
        team2: team2Select.value,
        venue: venueSelect.value,
        toss_winner: tossWinnerSelect.value,
        batting_first: battingFirstSelect.value
    };

    try {
        const res = await fetchWithRetry(`${API_BASE}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        hideColdStartBanner();
        showResult(data);
    } catch (err) {
        hideColdStartBanner();
        showError(err.message || "An error occurred while running the prediction.");
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    if (isLoading) {
        submitBtn.classList.add("loading");
        btnText.classList.add("hidden");
        spinner.classList.remove("hidden");
    } else {
        submitBtn.classList.remove("loading");
        btnText.classList.remove("hidden");
        spinner.classList.add("hidden");
    }
}

function hidePanels() {
    resultPanel.classList.add("hidden");
    errorPanel.classList.add("hidden");
}

function showError(msg) {
    errorText.textContent = msg;
    errorPanel.classList.remove("hidden");
}

function showResult(data) {
    resWinner.textContent = data.predicted_winner;
    resReasoning.textContent = data.reasoning;
    const confValue = Math.round(data.confidence);
    resConfidence.textContent = `${confValue}%`;
    setTimeout(() => {
        confCircle.setAttribute("stroke-dasharray", `${confValue}, 100`);
    }, 100);
    resultPanel.classList.remove("hidden");
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

init();
