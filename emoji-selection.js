/**
 * Emoji Selection Controller.
 * Handles emoji grid rendering, category filtering, selection animations,
 * and atomic registration submission to Flask.
 */

document.addEventListener("DOMContentLoaded", async () => {
    const participantName = sessionStorage.getItem("pending_participant_name");

    // If no name was entered, redirect back to index
    if (!participantName) {
        window.location.href = "/";
        return;
    }

    const displayName = document.getElementById("display-name");
    const emojiGrid = document.getElementById("emoji-grid");
    const categoryFilter = document.getElementById("category-filter");
    const previewEmojiChar = document.getElementById("preview-emoji-char");
    const previewEmojiName = document.getElementById("preview-emoji-name");
    const previewStatusText = document.getElementById("preview-status-text");
    const selectedBadge = document.getElementById("selected-badge");
    const btnBack = document.getElementById("btn-back");
    const btnSubmit = document.getElementById("btn-submit");
    const btnSubmitText = document.getElementById("btn-submit-text");
    const submissionError = document.getElementById("submission-error");

    displayName.textContent = participantName;

    let allEmojis = [];
    let selectedEmoji = null;
    let currentCategory = "All";

    // 1. Fetch available emojis from backend
    async function loadEmojiCatalog() {
        try {
            const res = await API.get("/api/emojis");
            if (res.success) {
                allEmojis = res.data.emojis;
                renderGrid();
            }
        } catch (err) {
            emojiGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 2rem; color: #dc2626;">
                    Failed to load emojis. Please refresh the page.
                </div>
            `;
            showToast("Failed to load emoji collection.", "error");
        }
    }

    // 2. Render emoji grid according to filter and selection
    function renderGrid() {
        emojiGrid.innerHTML = "";

        const filtered = allEmojis.filter(item => {
            if (currentCategory === "All") return true;
            return item.category === currentCategory;
        });

        if (filtered.length === 0) {
            emojiGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 2rem; color: var(--text-muted);">
                    No emojis found in this category.
                </div>
            `;
            return;
        }

        filtered.forEach(item => {
            const card = document.createElement("div");
            card.className = "emoji-card";
            card.setAttribute("role", "radio");
            card.setAttribute("tabindex", item.available ? "0" : "-1");
            card.setAttribute("aria-label", `${item.label} emoji`);

            if (!item.available) {
                card.classList.add("taken");
                card.setAttribute("aria-disabled", "true");
            } else if (selectedEmoji && selectedEmoji.emoji === item.emoji) {
                card.classList.add("selected");
                card.setAttribute("aria-checked", "true");
            } else {
                card.setAttribute("aria-checked", "false");
            }

            const charSpan = document.createElement("span");
            charSpan.className = "emoji-char";
            charSpan.textContent = item.emoji;

            const labelSpan = document.createElement("span");
            labelSpan.className = "emoji-label";
            labelSpan.textContent = item.label;

            card.appendChild(charSpan);
            card.appendChild(labelSpan);

            // Click & Keydown listeners
            if (item.available) {
                const selectHandler = () => handleSelectEmoji(item);
                card.addEventListener("click", selectHandler);
                card.addEventListener("keydown", (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        selectHandler();
                    }
                });
            }

            emojiGrid.appendChild(card);
        });
    }

    // 3. Selection handler
    function handleSelectEmoji(item) {
        selectedEmoji = item;
        submissionError.style.display = "none";

        // Update preview bar
        previewEmojiChar.textContent = item.emoji;
        previewEmojiName.textContent = item.label;
        previewStatusText.textContent = "Ready to join the waiting room!";
        selectedBadge.style.display = "inline-flex";
        selectedBadge.className = "badge badge-open";
        selectedBadge.textContent = "Selected";

        // Enable submit button
        btnSubmit.disabled = false;

        // Re-render grid to reflect selected border
        renderGrid();
    }

    // 4. Category filter listeners
    categoryFilter.addEventListener("click", (e) => {
        const chip = e.target.closest(".filter-chip");
        if (!chip) return;

        categoryFilter.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        currentCategory = chip.dataset.category;
        renderGrid();
    });

    // 5. Back button returns to name entry without submitting anything
    btnBack.addEventListener("click", () => {
        window.location.href = "/";
    });

    // 6. Form Submission: atomic registration
    btnSubmit.addEventListener("click", async () => {
        if (!selectedEmoji) {
            showToast("Please choose an emoji first!", "warning");
            return;
        }

        // Prevent duplicate submits
        btnSubmit.disabled = true;
        btnBack.disabled = true;
        btnSubmitText.textContent = "Registering...";
        submissionError.style.display = "none";

        try {
            const res = await API.post("/api/participants/register", {
                name: participantName,
                selected_emoji: selectedEmoji.emoji
            });

            if (res.success) {
                // Clear temporary cached name
                sessionStorage.removeItem("pending_participant_name");

                // Save confirmed participant data
                sessionStorage.setItem("confirmed_participant", JSON.stringify(res.data.participant));

                showToast(`Welcome aboard, ${participantName}! 🚀`, "success");

                // Enter waiting room
                window.location.href = "/waiting-room";
            }
        } catch (err) {
            btnSubmit.disabled = false;
            btnBack.disabled = false;
            btnSubmitText.textContent = "Join & Enter Waiting Room";

            const errorMsg = err.data && err.data.error ? err.data.error : err.message;
            submissionError.textContent = errorMsg;
            submissionError.style.display = "block";
            showToast(errorMsg, "error");

            // Refresh emoji availability in case another user claimed it
            await loadEmojiCatalog();
        }
    });

    // Initial catalog load
    await loadEmojiCatalog();
});
