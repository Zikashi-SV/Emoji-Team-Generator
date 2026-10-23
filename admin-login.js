/**
 * Administrator Login Controller.
 * Authenticates admin credentials, saves CSRF token, and redirects to dashboard.
 */

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("admin-login-form");
    const usernameInput = document.getElementById("admin-username");
    const passwordInput = document.getElementById("admin-password");
    const btnLogin = document.getElementById("btn-login");
    const btnLoginText = document.getElementById("btn-login-text");
    const loginError = document.getElementById("login-error");

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        if (!username || !password) {
            loginError.textContent = "Please enter both username and password.";
            loginError.style.display = "block";
            return;
        }

        btnLogin.disabled = true;
        btnLoginText.textContent = "Verifying...";
        loginError.style.display = "none";

        try {
            const res = await API.post("/api/admin/login", { username, password });

            if (res.success && res.data) {
                // Save CSRF token for subsequent requests
                API.setCsrfToken(res.data.csrf_token);
                showToast(`Welcome back, ${res.data.username}!`, "success");

                // Redirect to admin dashboard
                window.location.href = "/admin/dashboard";
            }
        } catch (err) {
            btnLogin.disabled = false;
            btnLoginText.textContent = "Sign In to Dashboard";

            const errorMsg = err.data && err.data.error ? err.data.error : "Invalid username or password.";
            loginError.textContent = errorMsg;
            loginError.style.display = "block";

            passwordInput.value = "";
            passwordInput.focus();
        }
    });
});
