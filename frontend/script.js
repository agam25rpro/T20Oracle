/* 
  T20 Oracle - Frontend Logic
*/
const API_BASE = "https://t20-oracle-api.onrender.com";
// DOM Elements
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

// Initialize page
async function init() {
    try {
        await Promise.all([loadTeams(), loadVenues()]);
        setupEventListeners();
    } catch (err) {
        showError("Failed to connect to the AI server. Is it running?");
    }
}

// Fetch and load Teams
async function loadTeams() {
    const res = await fetch(`${API_BASE}/teams`);
    if (!res.ok) throw new Error("Failed to load teams");
    const teams = await res.json();

    populateSelect(team1Select, teams, "Select Home Team");
    populateSelect(team2Select, teams, "Select Away Team");
}

// Fetch and load Venues
async function loadVenues() {
    const res = await fetch(`${API_BASE}/venues`);
    if (!res.ok) throw new Error("Failed to load venues");
    const venues = await res.json();

    populateSelect(venueSelect, venues, "Select Match Venue");
}

// Helper: populate select dropdowns
function populateSelect(element, dataArray, defaultText) {
    element.innerHTML = `<option value="" disabled selected>${defaultText}</option>`;
    dataArray.forEach(item => {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        element.appendChild(option);
    });
}

// Handle Team Selection (Updates Toss + Batting options based on selected teams)
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

// Handle Prediction Request
async function handlePrediction(e) {
    e.preventDefault();

    // UI State -> Loading
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
        const res = await fetch(`${API_BASE}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`Server returned ${res.status}`);
        }

        const data = await res.json();
        showResult(data);

    } catch (err) {
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

    // Format confidence
    const confValue = Math.round(data.confidence);
    resConfidence.textContent = `${confValue}%`;

    // Update SVG stroke-dasharray for circular chart
    // full circle is 100, format: "X, 100"
    setTimeout(() => {
        confCircle.setAttribute("stroke-dasharray", `${confValue}, 100`);
    }, 100);

    resultPanel.classList.remove("hidden");

    // Smooth scroll to result
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Kickoff
init();
