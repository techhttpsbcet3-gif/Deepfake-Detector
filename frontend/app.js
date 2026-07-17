// Frontend Application Logic for Deepfake Detector

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const tabTitle = document.getElementById("tab-title");
    const tabSubtitle = document.getElementById("tab-subtitle");
    
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const dropZonePrompt = document.getElementById("drop-zone-prompt");
    const previewContainer = document.getElementById("preview-container");
    const imagePreview = document.getElementById("image-preview");
    const scanLine = document.getElementById("scan-line");
    
    const analyzeBtn = document.getElementById("analyze-btn");
    const clearBtn = document.getElementById("clear-btn");
    
    const emptyResults = document.getElementById("empty-results");
    const resultsDashboard = document.getElementById("results-dashboard");
    const gaugeFill = document.getElementById("gauge-fill");
    const gaugeValue = document.getElementById("gauge-value");
    const verdictBadge = document.getElementById("verdict-badge");
    const verdictDesc = document.getElementById("verdict-desc");
    
    const xaiOriginal = document.getElementById("xai-original");
    const xaiHeatmap = document.getElementById("xai-heatmap");
    const historyTbody = document.getElementById("history-tbody");
    
    // Auth Elements
    const loginWrapper = document.getElementById("login-wrapper");
    const appContainer = document.getElementById("app-container");
    const loginForm = document.getElementById("login-form");
    const loginEmail = document.getElementById("login-email");
    const loginPassword = document.getElementById("login-password");
    const logoutBtn = document.getElementById("logout-btn");
    const loginCard = document.querySelector(".login-card");
    
    // Registration elements
    const authTitle = document.getElementById("auth-title");
    const authSubtitle = document.getElementById("auth-subtitle");
    const loginNameGroup = document.getElementById("login-name-group");
    const loginName = document.getElementById("login-name");
    const loginBtnText = document.getElementById("login-btn-text");
    const authTogglePrompt = document.getElementById("auth-toggle-prompt");
    const demoCredsHint = document.getElementById("demo-creds-hint");
    
    let authMode = "login"; // "login" or "register"
    
    let selectedFile = null;

    // 1. Tab Navigation
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Toggle buttons
            navButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            // Toggle panes
            tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === `tab-${targetTab}`) {
                    pane.classList.add("active");
                }
            });
            
            // Update Headers
            if (targetTab === "detector") {
                tabTitle.textContent = "Deepfake Detection Dashboard";
                tabSubtitle.textContent = "Real-time analysis powered by Vision Transformers";
            } else if (targetTab === "diagnostics") {
                tabTitle.textContent = "System & Model Diagnostics";
                tabSubtitle.textContent = "Validation metrics, confusion matrices, and reliability scores";
            } else if (targetTab === "about") {
                tabTitle.textContent = "Model Architecture Specifications";
                tabSubtitle.textContent = "Detailed layer configs, parameter counts, and pipeline descriptions";
            }
        });
    });

    // 2. Drag and Drop File Handlers
    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add("drag-over");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove("drag-over");
        }, false);
    });

    dropZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            handleFileSelect(files[0]);
        }
    });

    // Programmatic click routing for drop-zone container
    dropZone.addEventListener("click", (e) => {
        if (e.target !== fileInput && e.target.id !== "browse-btn" && !e.target.closest("#browse-btn")) {
            fileInput.click();
        }
    });

    const browseBtn = document.getElementById("browse-btn");
    if (browseBtn) {
        browseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith("image/")) {
            showNotification("Please upload an image file (PNG, JPG, JPEG, WEBP).", "error");
            return;
        }
        
        selectedFile = file;
        
        // Show Image Preview
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            xaiOriginal.src = e.target.result;
            
            // Hide prompt, show preview
            dropZonePrompt.classList.add("hidden");
            previewContainer.classList.remove("hidden");
            
            // Enable analyze button, show clear button
            analyzeBtn.removeAttribute("disabled");
            clearBtn.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    // 3. Clear Files Action
    clearBtn.addEventListener("click", () => {
        resetDetector();
    });

    function resetDetector() {
        selectedFile = null;
        fileInput.value = "";
        
        imagePreview.src = "#";
        xaiOriginal.src = "#";
        xaiHeatmap.src = "#";
        
        dropZonePrompt.classList.remove("hidden");
        previewContainer.classList.add("hidden");
        scanLine.classList.add("hidden");
        
        analyzeBtn.setAttribute("disabled", "true");
        clearBtn.classList.add("hidden");
        
        resultsDashboard.classList.add("hidden");
        emptyResults.classList.remove("empty-results-hidden");
        emptyResults.style.display = "flex";
    }

    // 4. Run Analysis
    analyzeBtn.addEventListener("click", async () => {
        if (!selectedFile) return;
        
        // UI states (Loading/Scanning)
        scanLine.classList.remove("hidden");
        analyzeBtn.setAttribute("disabled", "true");
        clearBtn.classList.add("hidden");
        
        const formData = new FormData();
        formData.append("file", selectedFile);
        
        const token = localStorage.getItem("sentryeye_token");
        
        try {
            const response = await fetch("/api/predict", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });
            
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Server error occurred during prediction.");
            }
            
            const result = await response.json();
            displayResults(result);
            loadHistory();
            showNotification("Analysis completed successfully!", "success");
            
        } catch (error) {
            console.error("Inference Error:", error);
            showNotification(error.message || "Failed to contact backend API.", "error");
        } finally {
            scanLine.classList.add("hidden");
            analyzeBtn.removeAttribute("disabled");
            clearBtn.classList.remove("hidden");
        }
    });

    // 5. Display Prediction Results
    function displayResults(data) {
        // Hide empty state
        emptyResults.style.display = "none";
        resultsDashboard.classList.remove("hidden");
        
        const label = data.label;
        const confidencePercent = Math.round(data.confidence * 100);
        
        // Update Gauge
        const maxOffset = 314; // Circle circumference (2 * pi * r) where r=50
        const strokeOffset = maxOffset - (maxOffset * confidencePercent) / 100;
        
        gaugeFill.style.strokeDashoffset = strokeOffset;
        
        // Gauge color & labels
        if (label.toLowerCase().includes("real")) {
            verdictBadge.textContent = "REAL";
            verdictBadge.className = "verdict-badge real";
            gaugeFill.style.stroke = "var(--real-color)";
            gaugeFill.style.filter = "drop-shadow(0 0 5px var(--real-glow))";
            verdictDesc.textContent = `High-frequency analysis shows no evidence of image synthesis. The image features natural pixel distribution and seamless boundaries.`;
        } else {
            verdictBadge.textContent = "DEEPFAKE";
            verdictBadge.className = "verdict-badge fake";
            gaugeFill.style.stroke = "var(--fake-color)";
            gaugeFill.style.filter = "drop-shadow(0 0 5px var(--fake-glow))";
            verdictDesc.textContent = `Warning: Model detected anomalies in local blending regions and textures. Attention map highlights suspicious facial contours.`;
        }
        
        // Animate count up
        animateCountUp(confidencePercent, gaugeValue);
        
        // Update Explainable AI Heatmap
        if (data.heatmap) {
            xaiHeatmap.src = data.heatmap;
        } else {
            xaiHeatmap.src = xaiOriginal.src; // Fallback
        }
    }

    function animateCountUp(target, element) {
        let current = 0;
        const duration = 800; // ms
        const stepTime = Math.abs(Math.floor(duration / target));
        
        const timer = setInterval(() => {
            current += 1;
            element.textContent = `${current}%`;
            if (current >= target) {
                clearInterval(timer);
                element.textContent = `${target}%`;
            }
        }, stepTime);
    }

    // 6. Load Scan History
    async function loadHistory() {
        const token = localStorage.getItem("sentryeye_token");
        if (!token) return;
        
        try {
            const response = await fetch("/api/history", {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });
            if (response.ok) {
                const history = await response.json();
                renderHistory(history);
            }
        } catch (error) {
            console.error("Failed to load history:", error);
        }
    }

    function renderHistory(history) {
        if (!history || history.length === 0) {
            historyTbody.innerHTML = `
                <tr>
                    <td colspan="5" class="table-empty">No scanned images in this session.</td>
                </tr>
            `;
            return;
        }
        
        historyTbody.innerHTML = history.map(item => {
            const labelClass = item.label.toLowerCase().includes("real") ? "badge-real" : "badge-fake";
            return `
                <tr>
                    <td>${item.timestamp}</td>
                    <td style="font-weight: 500;">${item.filename}</td>
                    <td><span class="badge ${labelClass}">${item.label.toUpperCase()}</span></td>
                    <td style="font-weight: 600;">${item.confidence}%</td>
                    <td><span class="badge badge-completed"><i class="fa-solid fa-circle-check"></i> Scanned</span></td>
                </tr>
            `;
        }).join("");
    }

    // 7. Load Technical Information
    async function loadTechnicalInfo() {
        try {
            const response = await fetch("/api/info");
            if (response.ok) {
                const info = await response.json();
                // We can log this or populate UI dynamically if needed.
                console.log("[Detector] System Meta:", info);
            }
        } catch (error) {
            console.error("Failed to fetch model info:", error);
        }
    }

    // 8. Show Toast Notification
    function showNotification(message, type = "info") {
        const container = document.getElementById("notification-container");
        
        const toast = document.createElement("div");
        toast.className = `notification ${type}`;
        
        let icon = '<i class="fa-solid fa-circle-info"></i>';
        if (type === "error") icon = '<i class="fa-solid fa-circle-exclamation"></i>';
        if (type === "success") icon = '<i class="fa-solid fa-circle-check"></i>';
        
        toast.innerHTML = `${icon}<span>${message}</span>`;
        container.appendChild(toast);
        
        // Remove toast after 4s
        setTimeout(() => {
            toast.style.animation = "slideIn 0.3s ease reverse forwards";
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3700);
    }

    // 9. Authentication Event Handlers & State Controls
    function toggleAuthMode() {
        if (authMode === "login") {
            authMode = "register";
            authTitle.textContent = "Create Account";
            authSubtitle.textContent = "Sign up to register your SentryEye credentials.";
            loginNameGroup.classList.remove("hidden");
            loginName.setAttribute("required", "true");
            loginBtnText.innerHTML = '<i class="fa-solid fa-user-plus"></i> Register';
            authTogglePrompt.innerHTML = 'Already have an account? <a href="#" id="auth-toggle-btn" style="color: var(--primary); font-weight: 600; text-decoration: none;">Log In</a>';
            if (demoCredsHint) demoCredsHint.classList.add("hidden");
        } else {
            authMode = "login";
            authTitle.textContent = "System Authentication";
            authSubtitle.textContent = "Please authenticate to access the classification systems.";
            loginNameGroup.classList.add("hidden");
            loginName.removeAttribute("required");
            loginBtnText.innerHTML = '<i class="fa-solid fa-key"></i> Authenticate';
            authTogglePrompt.innerHTML = 'Don\'t have an account? <a href="#" id="auth-toggle-btn" style="color: var(--primary); font-weight: 600; text-decoration: none;">Sign Up</a>';
            if (demoCredsHint) demoCredsHint.classList.remove("hidden");
        }
    }

    if (authTogglePrompt) {
        authTogglePrompt.addEventListener("click", (e) => {
            if (e.target && e.target.id === "auth-toggle-btn") {
                e.preventDefault();
                toggleAuthMode();
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const email = loginEmail.value.trim();
            const password = loginPassword.value;
            
            if (authMode === "login") {
                try {
                    const response = await fetch("/api/auth/login", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ email, password })
                    });
                    
                    if (!response.ok) {
                        throw new Error("Invalid username or password.");
                    }
                    
                    const data = await response.json();
                    localStorage.setItem("sentryeye_token", data.token);
                    
                    // Show Main Dashboard
                    loginWrapper.classList.add("hidden");
                    appContainer.classList.remove("hidden");
                    
                    // Trigger Init Loads
                    loadHistory();
                    loadTechnicalInfo();
                    showNotification("Welcome to SentryEye System Dashboard!", "success");
                    
                } catch (error) {
                    console.error("[Auth] Login Failed:", error);
                    loginCard.classList.add("shake");
                    setTimeout(() => { loginCard.classList.remove("shake"); }, 400);
                    showNotification(error.message || "Failed to authenticate.", "error");
                }
            } else {
                // Register Mode
                const name = loginName.value.trim();
                try {
                    const response = await fetch("/api/auth/register", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ name, email, password })
                    });
                    
                    if (!response.ok) {
                        const errData = await response.json();
                        throw new Error(errData.detail || "Registration failed.");
                    }
                    
                    showNotification("Registration successful! Please log in.", "success");
                    toggleAuthMode(); // Switch back to login
                    loginEmail.value = email; // Prepopulate registered email
                    loginPassword.value = "";
                    loginName.value = "";
                    
                } catch (error) {
                    console.error("[Auth] Registration Failed:", error);
                    loginCard.classList.add("shake");
                    setTimeout(() => { loginCard.classList.remove("shake"); }, 400);
                    showNotification(error.message || "Failed to register account.", "error");
                }
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            localStorage.removeItem("sentryeye_token");
            showNotification("Logged out successfully.", "info");
            setTimeout(() => {
                window.location.reload();
            }, 800);
        });
    }

    // Initialize Page
    const token = localStorage.getItem("sentryeye_token");
    if (token) {
        if (loginWrapper) loginWrapper.classList.add("hidden");
        if (appContainer) appContainer.classList.remove("hidden");
        loadHistory();
        loadTechnicalInfo();
    } else {
        if (loginWrapper) loginWrapper.classList.remove("hidden");
        if (appContainer) appContainer.classList.add("hidden");
    }
});
