/**
 * Administrator Dashboard Controller.
 * Manages participant rosters, real-time filtering, removal confirmation,
 * event configuration, team generation (Modes A & B), and result publishing.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // -------------------------------------------------------------
    // DOM Elements
    // -------------------------------------------------------------
    const adminUserBadge = document.getElementById("admin-user-badge");
    const btnLogout = document.getElementById("btn-logout");

    // Metrics
    const metricParticipants = document.getElementById("metric-participants");
    const metricCapacity = document.getElementById("metric-capacity");
    const metricTeams = document.getElementById("metric-teams");
    const metricPublished = document.getElementById("metric-published");

    // Tabs
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Tab 1: Participants
    const participantsTableBody = document.getElementById("participants-table-body");
    const participantSearch = document.getElementById("participant-search");
    const btnRefreshRoster = document.getElementById("btn-refresh-roster");

    // Tab 2: Team Generator
    const genModeSelect = document.getElementById("gen-mode-select");
    const wrapperTeamCount = document.getElementById("wrapper-team-count");
    const wrapperMaxSize = document.getElementById("wrapper-max-size");
    const genTeamCount = document.getElementById("gen-team-count");
    const genMaxSize = document.getElementById("gen-max-size");
    const modeExplanation = document.getElementById("mode-explanation");
    const btnGenerateTeams = document.getElementById("btn-generate-teams");
    const btnRegenerateTeams = document.getElementById("btn-regenerate-teams");
    const btnPublishTeams = document.getElementById("btn-publish-teams");
    const btnUnpublishTeams = document.getElementById("btn-unpublish-teams");
    const teamsPreviewContainer = document.getElementById("teams-preview-container");

    // Tab 3: Config
    const configForm = document.getElementById("config-form");
    const confSessionName = document.getElementById("conf-session-name");
    const confExpected = document.getElementById("conf-expected");
    const confEmojiReuse = document.getElementById("conf-emoji-reuse");
    const btnToggleRegOpen = document.getElementById("btn-toggle-reg-open");
    const btnToggleRegClosed = document.getElementById("btn-toggle-reg-closed");
    const regStatusHint = document.getElementById("reg-status-hint");
    const btnTriggerReset = document.getElementById("btn-trigger-reset");

    // Modals
    const deleteModal = document.getElementById("delete-modal");
    const deleteModalMsg = document.getElementById("delete-modal-msg");
    const btnCancelDelete = document.getElementById("btn-cancel-delete");
    const btnConfirmDelete = document.getElementById("btn-confirm-delete");

    const resetModal = document.getElementById("reset-modal");
    const btnCancelReset = document.getElementById("btn-cancel-reset");
    const btnConfirmReset = document.getElementById("btn-confirm-reset");

    let currentParticipants = [];
    let participantToDeleteId = null;
    let sessionData = null;

    // -------------------------------------------------------------
    // 1. Initial Authentication & Dashboard Data Loading
    // -------------------------------------------------------------
    async function loadDashboard() {
        try {
            const dashRes = await API.get("/api/admin/dashboard");
            if (!dashRes.success) throw new Error(dashRes.error);

            sessionData = dashRes.data.session;
            API.setCsrfToken(dashRes.data.csrf_token);

            // Update top metrics
            metricParticipants.textContent = dashRes.data.participant_count;
            metricCapacity.textContent = sessionData.expected_participants || "Open";
            metricTeams.textContent = dashRes.data.generated_teams_count;

            if (sessionData.results_published) {
                metricPublished.textContent = "Published 📢";
                metricPublished.style.color = "var(--success)";
            } else {
                metricPublished.textContent = "Unpublished 🔒";
                metricPublished.style.color = "var(--text-muted)";
            }

            // Sync Config Form
            confSessionName.value = sessionData.session_name;
            confExpected.value = sessionData.expected_participants;
            confEmojiReuse.value = sessionData.allow_emoji_reuse ? "1" : "0";
            updateRegStatusUI(sessionData.registration_status);

            // Sync Generator Mode
            genModeSelect.value = sessionData.team_formation_mode || "team_count";
            genTeamCount.value = sessionData.team_count || 4;
            genMaxSize.value = sessionData.max_team_size || 5;
            syncModeInputs();

            // Load roster & teams preview
            await loadParticipantsRoster();
            await loadTeamsPreview();
        } catch (err) {
            console.error("Dashboard init error:", err);
            if (err.status === 401) {
                window.location.href = "/admin/login";
            } else {
                showToast("Failed to load dashboard data.", "error");
            }
        }
    }

    // -------------------------------------------------------------
    // 2. Tab Navigation
    // -------------------------------------------------------------
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(btn.dataset.tab);
            if (targetPane) targetPane.classList.add("active");
        });
    });

    // -------------------------------------------------------------
    // 3. Participants Roster & Removal
    // -------------------------------------------------------------
    async function loadParticipantsRoster() {
        try {
            const res = await API.get("/api/admin/participants");
            if (res.success) {
                currentParticipants = res.data.participants;
                renderParticipantsTable(currentParticipants);
            }
        } catch (err) {
            participantsTableBody.innerHTML = `
                <tr><td colspan="5" style="text-align: center; color: #dc2626; padding: 2rem;">
                    Failed to load participants.
                </td></tr>
            `;
        }
    }

    function renderParticipantsTable(list) {
        participantsTableBody.innerHTML = "";

        if (list.length === 0) {
            participantsTableBody.innerHTML = `
                <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
                    No registered participants found.
                </td></tr>
            `;
            return;
        }

        list.forEach(p => {
            const tr = document.createElement("tr");

            // Avatar
            const tdEmoji = document.createElement("td");
            tdEmoji.style.fontSize = "1.75rem";
            tdEmoji.textContent = p.selected_emoji;

            // Name
            const tdName = document.createElement("td");
            tdName.innerHTML = `<strong>${escapeHtml(p.name)}</strong>`;

            // Team
            const tdTeam = document.createElement("td");
            if (p.team_name) {
                tdTeam.innerHTML = `<span class="badge badge-info">${escapeHtml(p.team_name)}</span>`;
            } else {
                tdTeam.innerHTML = '<span style="color: var(--text-muted); font-size: 0.85rem;">Unassigned</span>';
            }

            // Time
            const tdTime = document.createElement("td");
            tdTime.style.color = "var(--text-muted)";
            tdTime.style.fontSize = "0.85rem";
            tdTime.textContent = p.created_at ? p.created_at.replace("T", " ").substring(0, 19) : "--";

            // Action
            const tdAction = document.createElement("td");
            tdAction.style.textAlign = "right";

            const btnRemove = document.createElement("button");
            btnRemove.className = "btn btn-danger btn-sm";
            btnRemove.textContent = "Remove";
            btnRemove.addEventListener("click", () => {
                participantToDeleteId = p.id;
                deleteModalMsg.textContent = `Remove participant "${p.name}" (${p.selected_emoji}) from this session? Their name and emoji will become available again.`;
                deleteModal.classList.add("active");
            });

            tdAction.appendChild(btnRemove);

            tr.appendChild(tdEmoji);
            tr.appendChild(tdName);
            tr.appendChild(tdTeam);
            tr.appendChild(tdTime);
            tr.appendChild(tdAction);

            participantsTableBody.appendChild(tr);
        });
    }

    participantSearch.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = currentParticipants.filter(p => p.name.toLowerCase().includes(query));
        renderParticipantsTable(filtered);
    });

    btnRefreshRoster.addEventListener("click", async () => {
        btnRefreshRoster.disabled = true;
        await loadParticipantsRoster();
        btnRefreshRoster.disabled = false;
        showToast("Roster refreshed.", "info");
    });

    // Delete Modal Actions
    btnCancelDelete.addEventListener("click", () => {
        deleteModal.classList.remove("active");
        participantToDeleteId = null;
    });

    btnConfirmDelete.addEventListener("click", async () => {
        if (!participantToDeleteId) return;
        btnConfirmDelete.disabled = true;

        try {
            const res = await API.delete(`/api/admin/participants/${participantToDeleteId}`);
            if (res.success) {
                showToast(res.message, "success");
                deleteModal.classList.remove("active");
                participantToDeleteId = null;
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnConfirmDelete.disabled = false;
        }
    });

    // -------------------------------------------------------------
    // 4. Team Formation Mode & Generation
    // -------------------------------------------------------------
    function syncModeInputs() {
        const mode = genModeSelect.value;
        if (mode === "team_count") {
            wrapperTeamCount.style.display = "block";
            wrapperMaxSize.style.display = "none";
            modeExplanation.textContent = "Mode A: Distributes all participants across a fixed number of teams as evenly as possible.";
        } else {
            wrapperTeamCount.style.display = "none";
            wrapperMaxSize.style.display = "block";
            modeExplanation.textContent = "Mode B: Calculates required teams so that no team exceeds the target maximum size.";
        }
    }

    genModeSelect.addEventListener("change", syncModeInputs);

    async function loadTeamsPreview() {
        try {
            const res = await API.get("/api/admin/teams");
            if (res.success) {
                renderTeamsPreview(res.data.teams, res.data.published);
            }
        } catch (err) {
            console.error("Preview load error:", err);
        }
    }

    function renderTeamsPreview(teams, isPublished) {
        teamsPreviewContainer.innerHTML = "";

        if (!teams || teams.length === 0) {
            teamsPreviewContainer.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 2.5rem; color: var(--text-muted); background: var(--bg-main); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
                    No teams have been generated yet. Choose settings and click "Generate Balanced Teams" above.
                </div>
            `;
            btnRegenerateTeams.style.display = "none";
            btnPublishTeams.style.display = "none";
            btnUnpublishTeams.style.display = "none";
            return;
        }

        // Show action buttons
        btnRegenerateTeams.style.display = "inline-flex";
        if (isPublished) {
            btnPublishTeams.style.display = "none";
            btnUnpublishTeams.style.display = "inline-flex";
        } else {
            btnPublishTeams.style.display = "inline-flex";
            btnUnpublishTeams.style.display = "none";
        }

        teams.forEach(team => {
            const card = document.createElement("div");
            card.className = "team-card";

            const header = document.createElement("div");
            header.className = "team-card-header";

            const title = document.createElement("div");
            title.className = "team-title";
            title.textContent = team.team_name;

            const badge = document.createElement("span");
            badge.className = "badge badge-info";
            badge.textContent = `${team.member_count} members`;

            header.appendChild(title);
            header.appendChild(badge);
            card.appendChild(header);

            const ul = document.createElement("ul");
            ul.className = "team-members-list";

            team.members.forEach(m => {
                const li = document.createElement("li");
                li.className = "team-member-item";

                const emojiSpan = document.createElement("span");
                emojiSpan.className = "member-emoji";
                emojiSpan.textContent = m.selected_emoji;

                const nameSpan = document.createElement("span");
                nameSpan.className = "member-name";
                nameSpan.textContent = m.name;

                li.appendChild(emojiSpan);
                li.appendChild(nameSpan);
                ul.appendChild(li);
            });

            card.appendChild(ul);
            teamsPreviewContainer.appendChild(card);
        });
    }

    async function executeTeamGeneration() {
        const mode = genModeSelect.value;
        const count = parseInt(genTeamCount.value, 10);
        const maxSz = parseInt(genMaxSize.value, 10);

        btnGenerateTeams.disabled = true;
        btnRegenerateTeams.disabled = true;

        try {
            const res = await API.post("/api/admin/teams/generate", {
                mode: mode,
                team_count: count,
                max_team_size: maxSz
            });

            if (res.success) {
                showToast(res.message, "success");
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnGenerateTeams.disabled = false;
            btnRegenerateTeams.disabled = false;
        }
    }

    btnGenerateTeams.addEventListener("click", executeTeamGeneration);
    btnRegenerateTeams.addEventListener("click", executeTeamGeneration);

    btnPublishTeams.addEventListener("click", async () => {
        btnPublishTeams.disabled = true;
        try {
            const res = await API.post("/api/admin/teams/publish");
            if (res.success) {
                showToast("Team results are now visible to all participants! 🎉", "success");
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnPublishTeams.disabled = false;
        }
    });

    btnUnpublishTeams.addEventListener("click", async () => {
        btnUnpublishTeams.disabled = true;
        try {
            const res = await API.post("/api/admin/teams/unpublish");
            if (res.success) {
                showToast("Results hidden from participants.", "info");
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnUnpublishTeams.disabled = false;
        }
    });

    // -------------------------------------------------------------
    // 5. Configuration & Registration Toggles
    // -------------------------------------------------------------
    function updateRegStatusUI(status) {
        if (status === "open") {
            regStatusHint.innerHTML = '<span class="badge badge-open"><span class="dot dot-green"></span> Registration is currently Open</span>';
            btnToggleRegOpen.style.opacity = "1";
            btnToggleRegClosed.style.opacity = "0.6";
        } else {
            regStatusHint.innerHTML = '<span class="badge badge-closed"><span class="dot dot-red"></span> Registration is currently Closed</span>';
            btnToggleRegOpen.style.opacity = "0.6";
            btnToggleRegClosed.style.opacity = "1";
        }
    }

    btnToggleRegOpen.addEventListener("click", async () => {
        try {
            const res = await API.post("/api/admin/session/registration", { status: "open" });
            if (res.success) {
                updateRegStatusUI("open");
                showToast("Registration is now open for new participants.", "success");
            }
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    btnToggleRegClosed.addEventListener("click", async () => {
        try {
            const res = await API.post("/api/admin/session/registration", { status: "closed" });
            if (res.success) {
                updateRegStatusUI("closed");
                showToast("Registration closed.", "info");
            }
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    configForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const session_name = confSessionName.value.trim();
        const expected_participants = parseInt(confExpected.value, 10);
        const allow_emoji_reuse = confEmojiReuse.value === "1";

        try {
            const res = await API.patch("/api/admin/session/config", {
                session_name,
                expected_participants,
                allow_emoji_reuse
            });

            if (res.success) {
                showToast("Session configuration saved successfully.", "success");
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    // -------------------------------------------------------------
    // 6. Session Reset Handling
    // -------------------------------------------------------------
    btnTriggerReset.addEventListener("click", () => {
        resetModal.classList.add("active");
    });

    btnCancelReset.addEventListener("click", () => {
        resetModal.classList.remove("active");
    });

    btnConfirmReset.addEventListener("click", async () => {
        btnConfirmReset.disabled = true;
        try {
            const res = await API.post("/api/admin/session/reset", { confirm: true });
            if (res.success) {
                showToast("Session data has been completely reset.", "success");
                resetModal.classList.remove("active");
                await loadDashboard();
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnConfirmReset.disabled = false;
        }
    });

    // -------------------------------------------------------------
    // 7. Admin Logout
    // -------------------------------------------------------------
    btnLogout.addEventListener("click", async () => {
        try {
            await API.post("/api/admin/logout");
        } finally {
            API.setCsrfToken("");
            window.location.href = "/admin/login";
        }
    });

    // Run initial load
    await loadDashboard();
});
