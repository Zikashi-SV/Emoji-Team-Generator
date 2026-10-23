/**
 * Waiting Room Controller.
 * Periodically polls the server for live registration counts, status updates,
 * and automatically notifies participants when results are published.
 */

document.addEventListener("DOMContentLoaded", async () => {
    const participantEmoji = document.getElementById("participant-emoji");
    const participantName = document.getElementById("participant-name");
    const sessionBadge = document.getElementById("session-badge");
    const statRegisteredCount = document.getElementById("stat-registered-count");
    const statExpectedCount = document.getElementById("stat-expected-count");
    const statTeamsCount = document.getElementById("stat-teams-count");
    const registrationProgress = document.getElementById("registration-progress");
    const capacityPercentage = document.getElementById("capacity-percentage");
    const eventName = document.getElementById("event-name");
    const resultsReadyBanner = document.getElementById("results-ready-banner");
    const waitingNotice = document.getElementById("waiting-notice");

    let pollInterval = null;
    let resultsPublishedAnnounced = false;

    // 1. Resolve current participant identity from backend
    async function resolveParticipant() {
        try {
            const res = await API.get("/api/participants/me");
            if (res.success && res.data) {
                participantEmoji.textContent = res.data.selected_emoji;
                participantName.textContent = res.data.name;
                return true;
            }
        } catch (err) {
            console.warn("Could not resolve participant from token:", err);
        }

        // Fallback to confirmed_participant stored during registration
        const cached = sessionStorage.getItem("confirmed_participant");
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                participantEmoji.textContent = parsed.selected_emoji || "👤";
                participantName.textContent = parsed.name || "Participant";
                return true;
            } catch (e) {}
        }

        // If neither exists, redirect to registration
        window.location.href = "/";
        return false;
    }

    // 2. Poll session status and live participant counter
    async function refreshSessionStatus() {
        try {
            const res = await API.get("/api/session");
            if (!res.success) return;

            const data = res.data;
            eventName.textContent = data.session_name;
            statRegisteredCount.textContent = data.participant_count;
            statExpectedCount.textContent = data.expected_participants || "∞";
            statTeamsCount.textContent = data.team_count || "--";

            // Update registration status pill
            if (data.registration_status === "open") {
                sessionBadge.className = "badge badge-open";
                sessionBadge.innerHTML = '<span class="dot dot-green"></span> Registration Open';
            } else {
                sessionBadge.className = "badge badge-closed";
                sessionBadge.innerHTML = '<span class="dot dot-red"></span> Registration Closed';
            }

            // Calculate capacity percentage
            if (data.expected_participants && data.expected_participants > 0) {
                const pct = Math.min(100, Math.round((data.participant_count / data.expected_participants) * 100));
                registrationProgress.style.width = `${pct}%`;
                capacityPercentage.textContent = `${pct}% filled`;
            } else {
                registrationProgress.style.width = "100%";
                capacityPercentage.textContent = `${data.participant_count} joined`;
            }

            // Check if results were published by the organizer
            if (data.results_published) {
                resultsReadyBanner.style.display = "block";
                waitingNotice.style.display = "none";

                if (!resultsPublishedAnnounced) {
                    resultsPublishedAnnounced = true;
                    showToast("🎉 Team results have just been published!", "success", 5000);
                    launchConfetti(3);
                }
            } else {
                resultsReadyBanner.style.display = "none";
                waitingNotice.style.display = "flex";
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }

    const resolved = await resolveParticipant();
    if (resolved) {
        await refreshSessionStatus();
        // Poll every 3 seconds for live counter without reloading page
        pollInterval = setInterval(refreshSessionStatus, 3000);
    }

    window.addEventListener("beforeunload", () => {
        if (pollInterval) clearInterval(pollInterval);
    });
});
