/**
 * Participant Name Entry & Session Status Controller.
 */

document.addEventListener("DOMContentLoaded", async () => {
    const nameForm = document.getElementById("name-form");
    const nameInput = document.getElementById("participant-name");
    const btnNext = document.getElementById("btn-next");
    const sessionBadge = document.getElementById("session-badge");
    const sessionStatusText = document.getElementById("session-status-text");
    const sessionNameDisplay = document.getElementById("session-name-display");
    const participantCountDisplay = document.getElementById("participant-count-display");
    const expectedCountDisplay = document.getElementById("expected-count-display");
    const registrationWarning = document.getElementById("registration-warning");
    const alreadyRegisteredBox = document.getElementById("already-registered-box");
    const existingUserEmoji = document.getElementById("existing-user-emoji");
    const existingUserText = document.getElementById("existing-user-text");
    const btnSwitchUser = document.getElementById("btn-switch-user");

    // Restore previously typed name if participant backed out from emoji selection
    const cachedName = sessionStorage.getItem("pending_participant_name");
    if (cachedName) {
        nameInput.value = cachedName;
    }

    // 1. Fetch current session details
    try {
        const sessRes = await API.get("/api/session");
        if (sessRes.success) {
            const data = sessRes.data;
            sessionNameDisplay.textContent = data.session_name;
            participantCountDisplay.textContent = data.participant_count;
            expectedCountDisplay.textContent = data.expected_participants || "Open";

            if (data.registration_status === "open") {
                sessionBadge.className = "badge badge-open";
                sessionBadge.innerHTML = '<span class="dot dot-green"></span> Registration Open';
            } else {
                sessionBadge.className = "badge badge-closed";
                sessionBadge.innerHTML = '<span class="dot dot-red"></span> Registration Closed';
                registrationWarning.style.display = "block";
                registrationWarning.textContent = "Registration is currently closed by the administrator.";
                btnNext.disabled = true;
            }

            // Check if limit is reached
            if (data.expected_participants && data.participant_count >= data.expected_participants) {
                registrationWarning.style.display = "block";
                registrationWarning.textContent = `Event capacity full (${data.expected_participants} participants registered).`;
                btnNext.disabled = true;
            }
        }
    } catch (err) {
        sessionStatusText.textContent = "Offline";
        showToast("Unable to connect to the session server. Please try again.", "error");
    }

    // 2. Check if this browser already has an active participant registration
    try {
        const meRes = await API.get("/api/participants/me");
        if (meRes.success && meRes.data) {
            const participant = meRes.data;
            existingUserEmoji.textContent = participant.selected_emoji;
            existingUserText.textContent = `Welcome back, ${escapeHtml(participant.name)}!`;
            alreadyRegisteredBox.style.display = "block";
        }
    } catch (err) {
        // Participant session check is non-fatal
    }

    if (btnSwitchUser) {
        btnSwitchUser.addEventListener("click", () => {
            alreadyRegisteredBox.style.display = "none";
            sessionStorage.removeItem("pending_participant_name");
            nameInput.value = "";
            nameInput.focus();
        });
    }

    // 3. Form Submission
    nameForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const rawName = nameInput.value;
        const trimmed = rawName.trim();

        if (trimmed.length < 2) {
            showToast("Please enter a name with at least 2 characters.", "warning");
            nameInput.focus();
            return;
        }

        if (trimmed.length > 50) {
            showToast("Name cannot exceed 50 characters.", "warning");
            nameInput.focus();
            return;
        }

        // Store validated name temporarily for the emoji selection screen
        sessionStorage.setItem("pending_participant_name", trimmed);

        // Advance to emoji selection
        window.location.href = "/emoji-selection";
    });
});
