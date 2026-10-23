/**
 * Emoji Team Generator - Frontend API Utility and Shared Helpers.
 * Handles Fetch requests, toast notifications, DOM escaping, and confetti.
 */

const API = {
    csrfToken: sessionStorage.getItem("admin_csrf_token") || "",

    setCsrfToken(token) {
        this.csrfToken = token;
        if (token) {
            sessionStorage.setItem("admin_csrf_token", token);
        } else {
            sessionStorage.removeItem("admin_csrf_token");
        }
    },

    /**
     * Centralized HTTP client using the native Fetch API.
     */
    async request(url, options = {}) {
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            ...(options.headers || {})
        };

        if (this.csrfToken && !headers["X-CSRF-Token"]) {
            headers["X-CSRF-Token"] = this.csrfToken;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            let data = null;

            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                data = await response.json();
            } else {
                const text = await response.text();
                data = { success: response.ok, message: text };
            }

            if (!response.ok) {
                const errorMessage = data && data.error ? data.error : `Request failed with status ${response.status}`;
                const error = new Error(errorMessage);
                error.status = response.status;
                error.data = data;
                throw error;
            }

            return data;
        } catch (err) {
            console.error(`[API Error] ${options.method || "GET"} ${url}:`, err);
            throw err;
        }
    },

    get(url) {
        return this.request(url, { method: "GET" });
    },

    post(url, body) {
        return this.request(url, {
            method: "POST",
            body: JSON.stringify(body || {})
        });
    },

    patch(url, body) {
        return this.request(url, {
            method: "PATCH",
            body: JSON.stringify(body || {})
        });
    },

    delete(url) {
        return this.request(url, { method: "DELETE" });
    }
};

/**
 * Toast Notification Helper.
 */
function showToast(message, type = "info", duration = 3500) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const iconSpan = document.createElement("span");
    iconSpan.style.fontSize = "1.25rem";
    if (type === "success") iconSpan.textContent = "✅";
    else if (type === "error") iconSpan.textContent = "❌";
    else if (type === "warning") iconSpan.textContent = "⚠️";
    else iconSpan.textContent = "ℹ️";

    const msgSpan = document.createElement("span");
    msgSpan.textContent = message;

    toast.appendChild(iconSpan);
    toast.appendChild(msgSpan);
    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add("show");
    });

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Safe HTML escaping utility to prevent XSS.
 */
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

/**
 * Pure JavaScript Confetti Effect for Results Celebration.
 */
function launchConfetti(durationSeconds = 4) {
    const canvas = document.getElementById("confetti-canvas") || document.createElement("canvas");
    canvas.id = "confetti-canvas";
    document.body.appendChild(canvas);

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    const colors = ["#6366f1", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#3b82f6"];
    const pieces = [];
    const count = 120;

    for (let i = 0; i < count; i++) {
        pieces.push({
            x: Math.random() * width,
            y: Math.random() * -height,
            size: Math.random() * 8 + 4,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            rotationSpeed: (Math.random() - 0.5) * 8,
            speedY: Math.random() * 4 + 2,
            speedX: (Math.random() - 0.5) * 3
        });
    }

    let animationFrameId;
    const startTime = Date.now();

    function render() {
        ctx.clearRect(0, 0, width, height);
        const elapsed = (Date.now() - startTime) / 1000;

        pieces.forEach((p) => {
            p.y += p.speedY;
            p.x += p.speedX;
            p.rotation += p.rotationSpeed;

            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate((p.rotation * Math.PI) / 180);
            ctx.fillStyle = p.color;
            ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.4);
            ctx.restore();

            if (p.y > height) {
                p.y = -20;
                p.x = Math.random() * width;
            }
        });

        if (elapsed < durationSeconds) {
            animationFrameId = requestAnimationFrame(render);
        } else {
            ctx.clearRect(0, 0, width, height);
            canvas.remove();
        }
    }

    render();
}
