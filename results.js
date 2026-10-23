/**
 * Team Results Controller.
 * Renders team assignment cards, handles participant search,
 * highlights current participant, and triggers celebratory confetti.
 */

document.addEventListener("DOMContentLoaded", async () => {
    const teamsContainer = document.getElementById("teams-container");
    const unpublishedNotice = document.getElementById("unpublished-notice");
    const searchInput = document.getElementById("search-input");
    const eventTitle = document.getElementById("event-title");

    let currentParticipant = null;
    let allTeams = [];

    // 1. Check current participant identity (if registered in this browser)
    try {
        const meRes = await API.get("/api/participants/me");
        if (meRes.success && meRes.data) {
            currentParticipant = meRes.data;
        }
    } catch (e) {}

    // 2. Fetch published results from backend
    async function loadResults() {
        try {
            const res = await API.get("/api/results");
            if (res.success && res.data) {
                allTeams = res.data.teams || [];
                eventTitle.textContent = `${res.data.session_name} — Team Rosters`;
                unpublishedNotice.style.display = "none";
                teamsContainer.style.display = "grid";

                renderTeams(allTeams);

                // Launch confetti on reveal!
                launchConfetti(4);
            }
        } catch (err) {
            if (err.status === 403) {
                // Results hidden from participants
                teamsContainer.style.display = "none";
                unpublishedNotice.style.display = "block";
            } else {
                teamsContainer.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #dc2626;">
                        Failed to load results. Please try again later.
                    </div>
                `;
            }
        }
    }

    // 3. Render teams cards with member lists
    function renderTeams(teamsToRender) {
        teamsContainer.innerHTML = "";

        if (teamsToRender.length === 0) {
            teamsContainer.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">
                    No matching teams or participants found.
                </div>
            `;
            return;
        }

        teamsToRender.forEach((team) => {
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

            team.members.forEach((member) => {
                const li = document.createElement("li");
                li.className = "team-member-item";

                const isMe = currentParticipant && (currentParticipant.id === member.id || currentParticipant.name === member.name);
                if (isMe) {
                    li.style.background = "var(--primary-light)";
                    li.style.borderRadius = "8px";
                }

                const emojiSpan = document.createElement("span");
                emojiSpan.className = "member-emoji";
                emojiSpan.textContent = member.selected_emoji;

                const nameSpan = document.createElement("span");
                nameSpan.className = "member-name";
                nameSpan.textContent = member.name;

                li.appendChild(emojiSpan);
                li.appendChild(nameSpan);

                if (isMe) {
                    const meBadge = document.createElement("span");
                    meBadge.className = "member-badge-me";
                    meBadge.textContent = "YOU ⭐";
                    li.appendChild(meBadge);
                }

                ul.appendChild(li);
            });

            card.appendChild(ul);
            teamsContainer.appendChild(card);
        });
    }

    // 4. Real-time search filter
    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            renderTeams(allTeams);
            return;
        }

        const filtered = allTeams.filter((team) => {
            const matchesTeam = team.team_name.toLowerCase().includes(query);
            const matchesMember = team.members.some(m => m.name.toLowerCase().includes(query));
            return matchesTeam || matchesMember;
        });

        renderTeams(filtered);
    });

    await loadResults();
});
