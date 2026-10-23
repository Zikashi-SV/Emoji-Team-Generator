# 🎲 Emoji Team Generator

A complete, full-stack web application designed for interactive workshops, classroom activities, game nights, and corporate team-building events. Participants join effortlessly using only their name and a favorite emoji avatar (zero login, OTP, or passwords required), while administrators configure sessions, monitor live waiting rooms, balance teams using two distinct algorithms, and publish results.

Built with **Python 3, Flask, SQLite, HTML5, CSS3, and Vanilla JavaScript (ES6+)**.

---

## 🌟 Key Features

### 1. Participant Flow (Zero Login / Zero Friction)
- **Fast 2-Step Joining**: Enter name $\rightarrow$ Pick emoji $\rightarrow$ Enter waiting room.
- **Strict Duplicate-Name Prevention**: Case-insensitive and whitespace-normalized name comparison (e.g., `Arun`, `arun`, and `  ARUN  ` are safely caught and rejected).
- **Curated Emoji Selection**: 40 curated emojis across 4 categories (*Animals*, *Food*, *Cosmic*, *Fantasy*).
- **Emoji Uniqueness Enforced**: Prevents two participants from claiming the same emoji (unless the organizer enables emoji reuse).
- **Live Waiting Room**: Real-time participant counter, capacity progress bar, and status indicator that polls automatically without full page refreshes.
- **Session Restoration**: Uses signed, HttpOnly session tokens so participants never have to re-enter their names when navigating between pages.

### 2. Administrator Dashboard & Management
- **Secure Authentication**: Salted password hashing (`werkzeug.security`), session management, CSRF token validation on state-changing requests, and brute-force rate-limiting.
- **Zero Hardcoded Credentials**: Initial admin created securely via CLI (`create_admin.py`) or `.env` configuration.
- **Participant Roster**: Search, sort, and remove participants with confirmation modals (releasing their name and emoji immediately).
- **Session Controls**: Rename events, configure capacity limits, toggle registration open/closed, and toggle emoji reuse.
- **Two Team Formation Algorithms**:
  - **Mode A (Team Count)**: Evenly distributes participants across $K$ teams (differing by at most 1 participant).
  - **Mode B (Max Team Size)**: Ensures no team exceeds $M$ participants without creating unnecessary empty teams.
- **Preview & Reshuffle**: Review generated team balances before revealing them to attendees.
- **Publish & Unpublish**: Team rosters remain completely hidden from attendees until officially published.
- **Celebration & Reveal**: Published results include dynamic team cards and pure CSS/Canvas celebratory confetti.

---

## 📂 Project Structure

```text
Emoji team Project/
├── app.py                     # Main Flask application and RESTful JSON API endpoints
├── config.py                  # App configuration, curated emojis catalog, and environment loading
├── database.py                # SQLite connection lifecycle, schema initialization, and queries
├── auth.py                    # Admin password hashing, decorators, CSRF & participant token resolver
├── team_allocator.py          # Team formation algorithms (Mode A & Mode B) and transactional storage
├── create_admin.py            # Secure CLI tool for provisioning administrator credentials
├── requirements.txt           # Python package dependencies
├── .env.example               # Example environment variable template
├── .gitignore                 # Git ignore rules for virtualenvs, SQLite files, and cache
├── README.md                  # Complete documentation and setup manual
├── instance/
│   └── emoji_team.db          # SQLite database (auto-created on first run)
├── templates/                 # Server-rendered HTML templates
│   ├── index.html             # Participant landing & name entry
│   ├── emoji-selection.html   # Curated emoji grid selection
│   ├── waiting-room.html      # Live registration counter & waiting room
│   ├── results.html           # Published team cards & confetti reveal
│   ├── admin-login.html       # Administrator login screen
│   └── admin-dashboard.html   # Full participant, team & session control panel
├── static/
│   ├── css/
│   │   └── style.css          # Responsive design, gradients, badges, cards & modal styles
│   └── js/
│       ├── api.js             # Reusable Fetch wrapper, CSRF handler, toasts & confetti
│       ├── registration.js    # Name validation & session checks for index.html
│       ├── emoji-selection.js # Emoji catalog rendering, filters & submission
│       ├── waiting-room.js    # Real-time counter polling & publish listener
│       ├── results.js         # Team cards rendering & participant search
│       ├── admin-login.js     # Admin login handler & token persistence
│       └── admin-dashboard.js # Admin dashboard tabs, tables, modals & generation
└── tests/                     # 28 Automated test cases with Pytest
    ├── __init__.py
    ├── conftest.py            # Temporary SQLite database fixtures & test clients
    ├── test_registration.py   # Name limits, duplicates, emoji exclusivity & cookie checks
    ├── test_auth.py           # Password hashing, login, logout, CSRF & rate limiting
    ├── test_teams.py          # Mode A & Mode B algorithms, zero participants, persistence
    ├── test_results.py        # Published/unpublished access controls & session reset
    └── test_pages.py          # HTML page routes and template rendering tests
```

---

## 🚀 Installation & Localhost Setup (Windows)

Follow these steps using **Command Prompt** or **PowerShell**:

### Step 1: Open the Project Directory
```powershell
cd "c:\Users\Manivannan\OneDrive\Desktop\Emoji team Project"
```

### Step 2: Create a Python Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment
- In **PowerShell**:
  ```powershell
  venv\Scripts\Activate.ps1
  ```
- Or in **Command Prompt**:
  ```cmd
  venv\Scripts\activate.bat
  ```

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Securely Create the Administrator Account
Run the included administrative CLI script. You will be prompted to enter a secure password without exposing it in source files or web forms:
```powershell
python create_admin.py --username admin --password MySecurePassword123!
```
*(You can also simply run `python create_admin.py` to enter the password interactively with hidden keystrokes).*

### Step 6: Start the Flask Application
```powershell
python app.py
```

### Step 7: Open in Your Browser
- **Participant Portal**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Administrator Portal**: [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)

---

## 🧪 Running Automated Tests

The application includes 28 test cases covering input validation, security controls, algorithms, and persistence.

Run the test suite using `pytest`:
```powershell
python -m pytest tests/ -v
```

Expected output:
```text
collected 28 items

tests/test_auth.py::test_password_hash_stored_not_plaintext PASSED
tests/test_auth.py::test_successful_admin_login_and_logout PASSED
tests/test_auth.py::test_incorrect_password_rejected PASSED
tests/test_auth.py::test_nonexistent_user_rejected PASSED
tests/test_auth.py::test_protected_endpoints_inaccessible_without_auth PASSED
tests/test_auth.py::test_participant_token_cannot_access_admin_endpoints PASSED
tests/test_auth.py::test_csrf_protection_on_admin_state_changing_requests PASSED
tests/test_pages.py::test_html_pages_render_successfully PASSED
tests/test_pages.py::test_admin_dashboard_redirects_unauthenticated PASSED
tests/test_pages.py::test_admin_dashboard_accessible_when_authenticated PASSED
tests/test_registration.py::test_valid_registration PASSED
tests/test_registration.py::test_empty_or_whitespace_name_rejected PASSED
tests/test_registration.py::test_name_length_boundaries PASSED
tests/test_registration.py::test_duplicate_name_case_insensitive_and_spaces PASSED
tests/test_registration.py::test_emoji_uniqueness_when_reuse_disabled PASSED
tests/test_registration.py::test_emoji_uniqueness_when_reuse_enabled PASSED
tests/test_registration.py::test_registration_when_closed PASSED
tests/test_registration.py::test_registration_at_participant_limit PASSED
tests/test_registration.py::test_participant_session_me_endpoint PASSED
tests/test_results.py::test_results_hidden_before_publication PASSED
tests/test_results.py::test_results_accessible_after_publication PASSED
tests/test_results.py::test_participant_removal_frees_name_and_emoji PASSED
tests/test_results.py::test_session_reset PASSED
tests/test_teams.py::test_mode_a_balanced_distribution PASSED
tests/test_teams.py::test_mode_b_max_size_enforcement PASSED
tests/test_teams.py::test_zero_participants_handling PASSED
tests/test_teams.py::test_invalid_team_settings_rejected PASSED
tests/test_teams.py::test_team_generation_and_persistence PASSED

============================= 28 passed in 16.5s =============================
```

---

## 📋 Manual Verification Checklist

Follow this workflow to verify the full user and administrator experience:

### 1. Participant Experience
1. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).
2. Enter your name (e.g. `Maya Lin`) and click **Next: Choose Your Emoji**.
3. Select an emoji (e.g. `🚀 Rocket`). Notice the animated border highlight and preview card.
4. Click **Join & Enter Waiting Room**.
5. Observe the confirmed registration badge, live registration counter, and progress bar.
6. Open an incognito window and join with another name (e.g. `Arun`). Try to pick the `🚀 Rocket` emoji—verify it shows as **Taken** and cannot be selected.
7. Try to enter `arun` or `  ARUN  `—verify the friendly duplicate name error appears.

### 2. Administrator Experience
1. Navigate to [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login).
2. Sign in with the credentials created earlier (`admin` / `MySecurePassword123!`).
3. Under the **👥 Participants Roster** tab, verify the registered participants appear in the table with their avatars and registration times.
4. Switch to the **🎲 Team Generator & Preview** tab:
   - Select **Mode A (Fixed Number of Teams)** with 2 teams. Click **Generate Balanced Teams**.
   - Notice the preview cards appear with balanced participant assignments.
   - Click **Regenerate / Reshuffle** to reshuffle.
5. In participant browser tabs, verify that team results remain hidden while unpublished.
6. In the admin dashboard, click **📢 Publish Results to Participants**.
7. In the participant windows, observe the live waiting room update automatically, showing the **"Teams Have Been Published!"** banner and confetti!
8. Click **View Team Results** in the participant window to explore the team rosters and search filter.

---

## 🛑 Server Operations & Troubleshooting

- **Stopping the server**: In the Command Prompt/PowerShell terminal running Flask, press `Ctrl + C`.
- **Restarting the server**: Run `python app.py`. All participant and team data persists in `instance/emoji_team.db`.
- **Port 5000 already in use**:
  If port 5000 is occupied, you can change the port in `app.py` line 440:
  ```python
  app.run(host="127.0.0.1", port=5001, debug=True)
  ```
