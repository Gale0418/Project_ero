document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const form = document.getElementById("gen-form");
    const modelSelect = document.getElementById("model");
    const submitBtn = document.getElementById("submit-btn");
    const btnText = document.querySelector(".btn-text");
    const spinner = document.querySelector(".spinner");
    
    // Status
    const statusDot = document.getElementById("sd-status-dot");
    const statusText = document.getElementById("sd-status-text");

    // Mode Toggle
    const btnQuick = document.getElementById("btn-quick");
    const btnExpert = document.getElementById("btn-expert");
    const expertPanel = document.getElementById("expert-panel");

    // Templates
    const templateSelect = document.getElementById("template-select");
    const btnSaveTemplate = document.getElementById("btn-save-template");
    const templateModal = document.getElementById("template-modal");
    const confirmSaveTmpl = document.getElementById("confirm-save-template");
    const cancelSaveTmpl = document.getElementById("cancel-save-template");
    const templateNameInput = document.getElementById("template-name");

    // Columns
    const colPending = document.getElementById("col-pending");
    const colRunning = document.getElementById("col-running");
    const colCompleted = document.getElementById("col-completed");
    const countPending = document.getElementById("count-pending");
    const countRunning = document.getElementById("count-running");
    const countCompleted = document.getElementById("count-completed");

    // Image Modal
    const imgModal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-img");
    const closeBtn = document.getElementsByClassName("close-modal")[0];

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, ch => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "\"": "&quot;",
            "'": "&#39;"
        })[ch]);
    }

    function jsArg(value) {
        return escapeHtml(JSON.stringify(String(value ?? "")));
    }

    let lastFocusedElement = null;
    let activeModal = null;
    let activeModalKeyHandler = null;

    function getFocusableElements(modal) {
        return Array.from(modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )).filter(el => !el.disabled && el.offsetParent !== null);
    }

    function openDialog(modal, initialFocus) {
        lastFocusedElement = document.activeElement;
        activeModal = modal;
        modal.style.display = "block";
        modal.focus();

        activeModalKeyHandler = (event) => {
            if (event.key === "Escape") {
                closeDialog(modal);
                return;
            }
            if (event.key !== "Tab") return;

            const focusable = getFocusableElements(modal);
            if (!focusable.length) {
                event.preventDefault();
                return;
            }

            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };
        modal.addEventListener("keydown", activeModalKeyHandler);

        const target = initialFocus || getFocusableElements(modal)[0] || modal;
        target.focus();
    }

    function closeDialog(modal) {
        modal.style.display = "none";
        if (activeModal === modal && activeModalKeyHandler) {
            modal.removeEventListener("keydown", activeModalKeyHandler);
        }
        activeModal = null;
        activeModalKeyHandler = null;
        if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
            lastFocusedElement.focus();
        }
        lastFocusedElement = null;
    }

    // Initialize
    fetchModels();
    fetchTemplates();
    pollStatus();
    pollJobs();
    
    setInterval(pollStatus, 5000);
    setInterval(pollJobs, 2000);

    // --- Mode Toggle Logic ---
    btnQuick.addEventListener("click", () => {
        btnQuick.classList.add("active");
        btnExpert.classList.remove("active");
        expertPanel.classList.add("hidden");
        btnQuick.setAttribute("aria-pressed", "true");
        btnExpert.setAttribute("aria-pressed", "false");
        expertPanel.setAttribute("aria-hidden", "true");
    });

    btnExpert.addEventListener("click", () => {
        btnExpert.classList.add("active");
        btnQuick.classList.remove("active");
        expertPanel.classList.remove("hidden");
        btnExpert.setAttribute("aria-pressed", "true");
        btnQuick.setAttribute("aria-pressed", "false");
        expertPanel.setAttribute("aria-hidden", "false");
    });

    let currentMode = "standard";
    const modeBtns = document.querySelectorAll(".mode-tabs .mode-btn");
    modeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            modeBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentMode = btn.dataset.mode;
            
            document.querySelectorAll(".twophase-only").forEach(el => el.classList.add("hidden"));
            document.querySelectorAll(".remix-only").forEach(el => el.classList.add("hidden"));
            document.getElementById("lbl-model").textContent = "Model";

            if (currentMode === "twophase") {
                document.querySelectorAll(".twophase-only").forEach(el => el.classList.remove("hidden"));
                document.getElementById("lbl-model").textContent = "Draft Model";
            } else if (currentMode === "remix") {
                document.querySelectorAll(".remix-only").forEach(el => el.classList.remove("hidden"));
                document.getElementById("lbl-model").textContent = "Target Model";
            }
        });
    });

    // Image Upload Logic for Remix
    const dropZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");
    const uploadPreview = document.getElementById("upload-preview");
    const uploadText = document.getElementById("upload-text");
    let initImageBase64 = null;

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInput.click();
        }
    });
    fileInput.addEventListener("change", handleFile);
    
    function handleFile(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const result = e.target.result;
                if (typeof result !== "string" || !result.startsWith("data:image/") || !result.includes("base64,")) {
                    initImageBase64 = null;
                    uploadPreview.src = "";
                    uploadPreview.classList.add("hidden");
                    uploadText.classList.remove("hidden");
                    console.warn("Invalid image data URL.");
                    return;
                }
                initImageBase64 = result.split(",")[1]; // Get b64 data
                uploadPreview.src = result;
                uploadPreview.classList.remove("hidden");
                uploadText.classList.add("hidden");
            }
            reader.readAsDataURL(file);
        }
    }

    // --- Template Logic ---
    let templatesData = [];
    const finalModelSelect = document.getElementById("final-model");

    async function fetchModels() {
        try {
            const res = await fetch("/api/models");
            if (res.ok) {
                const models = await res.json();
                modelSelect.innerHTML = "";
                finalModelSelect.innerHTML = '<option value="">-- Select Final Model --</option>';
                models.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m;
                    opt.textContent = m.split(" ")[0]; // short name
                    const opt2 = opt.cloneNode(true);
                    
                    if (m.toLowerCase().includes("animagine")) opt.selected = true;
                    if (m.toLowerCase().includes("illustrious")) opt2.selected = true;
                    
                    modelSelect.appendChild(opt);
                    finalModelSelect.appendChild(opt2);
                });
            }
        } catch (e) {
            modelSelect.innerHTML = "<option value=''>Error</option>";
            finalModelSelect.innerHTML = "<option value=''>Error</option>";
        }
    }

    async function fetchTemplates() {
        try {
            const res = await fetch("/api/templates");
            templatesData = await res.json();
            templateSelect.innerHTML = '<option value="">-- Load Template --</option>';
            templatesData.forEach((t, idx) => {
                const opt = document.createElement("option");
                opt.value = idx;
                opt.textContent = t.name;
                templateSelect.appendChild(opt);
            });
        } catch(e) {}
    }

    async function pollStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            const newDot = data.status === "online" ? "dot green" : "dot red";
            const newText = data.status === "online" ? "SD WebUI: Online" : "SD WebUI: Offline";
            if (statusDot.className !== newDot) statusDot.className = newDot;
            if (statusText.textContent !== newText) statusText.textContent = newText;
        } catch(e) {
            const newDot = "dot red";
            const newText = "Backend Offline";
            if (statusDot.className !== newDot) statusDot.className = newDot;
            if (statusText.textContent !== newText) statusText.textContent = newText;
        }
    }

    templateSelect.addEventListener("change", (e) => {
        const idx = e.target.value;
        if (idx !== "") {
            const t = templatesData[idx];
            document.getElementById("global_prompt").value = t.global_prompt;
            document.getElementById("char_prompt").value = t.char_prompt;
            document.getElementById("action_prompt").value = t.action_prompt;
            document.getElementById("negative_prompt").value = t.negative_prompt;
        }
    });

    btnSaveTemplate.addEventListener("click", () => { openDialog(templateModal, templateNameInput); });
    cancelSaveTmpl.addEventListener("click", () => { closeDialog(templateModal); templateNameInput.value = ""; });

    confirmSaveTmpl.addEventListener("click", async () => {
        const name = templateNameInput.value.trim();
        if (!name) return;
        const tmpl = {
            name: name,
            global_prompt: document.getElementById("global_prompt").value,
            char_prompt: document.getElementById("char_prompt").value,
            action_prompt: document.getElementById("action_prompt").value,
            negative_prompt: document.getElementById("negative_prompt").value
        };
        await fetch("/api/templates", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(tmpl) });
        closeDialog(templateModal);
        templateNameInput.value = "";
        fetchTemplates();
    });

    // --- Form Submission & Validation ---
    document.getElementById("btn-open-folder").addEventListener("click", () => {
        fetch("/api/open-folder", { method: "POST" });
    });

    document.addEventListener("keydown", (e) => {
        if (e.ctrlKey && e.key === "Enter") {
            form.dispatchEvent(new Event("submit"));
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        if (currentMode === "twophase" && !document.getElementById("final-model").value) {
            alert("Please select a Final Model for Phase 2 Refinement.");
            return;
        }

        if (currentMode === "remix" && !initImageBase64) {
            alert("Please upload a base image for Remix mode.");
            return;
        }

        // Use safe defaults for Expert Mode fields that may be hidden (Quick Mode)
        const getVal = (id, fallback, parser = parseInt) => {
            const el = document.getElementById(id);
            const v = el ? parser(el.value) : NaN;
            return isNaN(v) ? fallback : v;
        };
        const getFloat = (id, fallback) => getVal(id, fallback, parseFloat);
        const getCheck = (id, fallback = true) => {
            const el = document.getElementById(id);
            return el ? el.checked : fallback;
        };

        const reqData = {
            mode: currentMode,
            task_name: document.getElementById("task_name").value || "Task",
            model: modelSelect.value,
            final_model: document.getElementById("final-model").value,
            global_prompt: document.getElementById("global_prompt").value,
            char_prompt: document.getElementById("char_prompt").value,
            action_prompt: document.getElementById("action_prompt").value,
            negative_prompt: document.getElementById("negative_prompt").value,
            steps: getVal("steps", 28),
            width: getVal("width", 832),
            height: getVal("height", 1216),
            cfg_scale: getFloat("cfg_scale", 5.0),
            denoise_str: getFloat("denoise_str", 0.5),
            cn_weight: getFloat("cn_weight", 0.7),
            total_images: getVal("total_images", 1),
            auto_hires: getCheck("auto_hires", true),
            ad_modes: Array.from(document.querySelectorAll('input[name="ad_modes"]:checked')).map(cb => cb.value),
            init_image: initImageBase64
        };

        btnText.textContent = "Queueing...";
        spinner.classList.remove("hidden");
        submitBtn.disabled = true;

        try {
            const res = await fetch("/api/jobs", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(reqData)
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                const detail = errData.detail || JSON.stringify(errData);
                alert(`❌ Failed to enqueue job (${res.status}):\n${detail}`);
            } else {
                pollJobs();
            }
        } catch (err) {
            alert(`❌ Network error: ${err.message}`);
        } finally {
            btnText.textContent = "Enqueue Generation Task";
            spinner.classList.add("hidden");
            submitBtn.disabled = false;
        }
    });

    // --- Kanban Logic ---
    async function retryJob(jobId) {
        try {
            await fetch(`/api/jobs/${jobId}/retry`, { method: "POST" });
            pollJobs();
        } catch(e) { console.error("Retry failed"); }
    }
    window.retryJob = retryJob;

    async function deleteJob(jobId) {
        try {
            await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
            pollJobs();
        } catch(e) { console.error("Delete/Cancel failed"); }
    }
    window.deleteJob = deleteJob;

    async function pollJobs() {
        try {
            const [resJobs, resProg] = await Promise.all([
                fetch("/api/jobs"),
                fetch("/api/progress")
            ]);
            if (!resJobs.ok) return; // backend offline, skip
            const jobs = await resJobs.json();
            const prog = resProg.ok ? await resProg.json() : {};
            
            const pending = [], running = [], completed = [];
            jobs.forEach(job => {
                if (job.status === "Pending") pending.push(job);
                else if (job.status === "Running" || job.status === "Canceling") running.push(job);
                else completed.push(job); 
            });

            countPending.textContent = pending.length;
            countRunning.textContent = running.length;
            countCompleted.textContent = completed.length;

            renderCol(colPending, pending, prog, true);
            renderCol(colRunning, running, prog, false);
            renderCol(colCompleted, completed, null, false);
        } catch(e) {
            // backend unreachable, silently skip
        }
    }

    function extractSeed(infoText) {
        if (!infoText) return "N/A";
        const match = infoText.match(/Seed: (\d+)/);
        return match ? match[1] : "N/A";
    }

    let draggedJobId = null;

    function renderCol(container, jobs, progData, isPendingCol) {
        // Initialize column drag events only once
        if (isPendingCol && !container.dataset.eventsBound) {
            container.dataset.eventsBound = "true";
            container.addEventListener('dragover', (e) => {
                e.preventDefault();
                container.classList.add('drag-over');
            });
            container.addEventListener('dragleave', () => {
                container.classList.remove('drag-over');
            });
            container.addEventListener('drop', async (e) => {
                e.preventDefault();
                container.classList.remove('drag-over');
                if (!draggedJobId) return;
                
                const cards = [...container.querySelectorAll('.job-card:not(.dragging)')];
                let newIndex = cards.length;
                for (let i = 0; i < cards.length; i++) {
                    const rect = cards[i].getBoundingClientRect();
                    if (e.clientY < rect.top + rect.height / 2) {
                        newIndex = i;
                        break;
                    }
                }
                
                try {
                    await fetch(`/api/jobs/${draggedJobId}/move`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ new_index: newIndex })
                    });
                    pollJobs();
                } catch(err) { console.error("Move failed"); }
            });
        }

        // Map existing cards for reuse
        const existingCards = Array.from(container.children);
        const cardMap = new Map();
        existingCards.forEach(c => cardMap.set(c.dataset.jobId, c));

        jobs.forEach(job => {
            let card = cardMap.get(job.id);
            const isNew = !card;
            if (isNew) {
                card = document.createElement("div");
                card.className = "job-card job-card-enter";
                card.dataset.jobId = job.id;
                card.addEventListener("animationend", () => card.classList.remove("job-card-enter"), { once: true });
                
                if (isPendingCol) {
                    card.draggable = true;
                    card.classList.add("draggable");
                    card.addEventListener('dragstart', () => {
                        draggedJobId = job.id;
                        card.classList.add('dragging');
                    });
                    card.addEventListener('dragend', () => {
                        card.classList.remove('dragging');
                        draggedJobId = null;
                    });
                }
                // New card must be inserted into the DOM so querySelector can find it later
                container.appendChild(card);
            } else {
                cardMap.delete(job.id); // mark as retained (not stale)
            }
            
            const req = job.request;
            const taskName = req.task_name || "Task";
            const modelShort = req.model ? req.model.split(" ")[0].substring(0, 15) : "Unknown";
            const totalImgs = req.total_images || 1;
            const jobArg = jsArg(job.id);
            const safeJobId = escapeHtml(job.id);
            const safeTaskName = escapeHtml(taskName);
            const safeModelShort = escapeHtml(modelShort);
            const safeTotalImgs = escapeHtml(totalImgs);
            
            let footerHtml = "";
            let phaseText = job.phase_text ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${escapeHtml(job.phase_text)}</div>` : "";

            if (job.status === "Pending") {
                footerHtml = `<div style="flex:1;"></div><button class="icon-btn" style="padding:4px 8px;font-size:12px;color:var(--danger-color);" onclick="deleteJob(${jobArg})" title="Cancel Job">❌</button>`;
            } else if (job.status === "Running" || job.status === "Canceling") {
                let progHtml = "";
                if (progData && progData.progress > 0) {
                    const p = Math.round(progData.progress * 100);
                    const eta = Math.round(progData.eta_relative);
                    const previewSrc = progData.current_image ? escapeHtml(`data:image/jpeg;base64,${progData.current_image}`) : "";
                    let previewHtml = previewSrc ? `<img src="${previewSrc}" class="progress-preview" style="max-height:100px; border-radius:4px; align-self:center; margin-top:0.5rem">` : "";
                    progHtml = `
                        <div style="width: 100%; background: #333; border-radius: 4px; height: 6px; margin-top: 8px; overflow: hidden;">
                            <div style="width: ${p}%; background: var(--primary-color); height: 100%; transition: width 0.3s ease;"></div>
                        </div>
                        <div style="font-size: 0.7rem; color: #888; display: flex; justify-content: space-between; margin-top: 2px;">
                            <span>${p}%</span><span>ETA: ${eta}s</span>
                        </div>
                        ${previewHtml}
                    `;
                }
                let cancelBtn = job.status === "Running"
                    ? `<button class="icon-btn" style="padding:4px 8px;font-size:12px;color:var(--danger-color);" onclick="deleteJob(${jobArg})" title="Force Stop">🛑</button>`
                    : `<span style="font-size:12px;color:var(--danger-color);">Canceling...</span>`;
                footerHtml = `<div style="display:flex;flex-direction:column;gap:0.2rem;color:var(--primary-color);width:100%;">
                                <div style="display:flex;align-items:center;justify-content:space-between;width:100%;">
                                    <div style="display:flex;align-items:center;gap:0.5rem;"><div class="spinner" style="border-top-color:var(--primary-color);width:12px;height:12px;"></div> Generating ${safeTotalImgs} img...</div>
                                    ${cancelBtn}
                                </div>
                                ${phaseText}
                                ${progHtml}
                              </div>`;
            } else if (job.status === "Failed" || job.status === "Canceled") {
                const safeError = escapeHtml(job.error || "Canceled");
                footerHtml = `<div class="status-failed" style="flex:1;">❌ ${safeError}</div>
                              <button class="icon-btn" style="padding:4px 8px;font-size:12px" onclick="retryJob(${jobArg})">🔄</button>
                              <button class="icon-btn" style="padding:4px 8px;font-size:12px;color:var(--danger-color);" onclick="deleteJob(${jobArg})">🗑️</button>`;
            } else if (job.status === "Completed" && job.image_urls) {
                let imgsHtml = "";
                job.image_urls.forEach(url => {
                    const safeUrl = escapeHtml(url);
                    const urlArg = jsArg(url);
                    imgsHtml += `<img src="${safeUrl}" class="card-image" onclick="openModal(${urlArg})" loading="lazy">`;
                });
                footerHtml = `<div style="display:flex;gap:0.5rem;flex:1;flex-wrap:wrap;">${imgsHtml}</div>
                              <div style="display:flex;flex-direction:column;gap:4px;">
                                  <button class="icon-btn" style="padding:4px 8px;font-size:12px" onclick="retryJob(${jobArg})" title="Run again">🔄</button>
                                  <button class="icon-btn" style="padding:4px 8px;font-size:12px;color:var(--danger-color);" onclick="deleteJob(${jobArg})" title="Delete record">🗑️</button>
                              </div>`;
            }

            const promptText = [req.global_prompt, req.char_prompt, req.action_prompt].filter(Boolean).join(", ");
            const safePromptText = escapeHtml(promptText);
            const safeMode = escapeHtml(String(req.mode || "").toUpperCase());
            const modeBadge = `<span style="border:1px solid var(--primary-color); border-radius:4px; padding:0 4px; font-size:10px; color:var(--primary-color);">${safeMode}</span>`;
            const newHtml = `
                <div class="card-header">
                    <span>${safeTaskName} #${safeJobId} ${modeBadge}</span>
                    <span class="card-model">${safeModelShort} (x${safeTotalImgs})</span>
                </div>
                <div class="card-body" title="${safePromptText}">${safePromptText}</div>
                <div class="card-footer" style="justify-content:space-between; align-items:flex-end;">${footerHtml}</div>
            `;
            // Only touch the DOM if content actually changed
            if (card.innerHTML !== newHtml) {
                card.innerHTML = newHtml;
            }
        });

        // Re-order cards only when their position changed (avoids CSS transition bounce)
        jobs.forEach((job, desiredIdx) => {
            const card = container.querySelector(`[data-job-id="${job.id}"]`);
            if (!card) return;
            const currentAtIdx = container.children[desiredIdx];
            if (currentAtIdx !== card) {
                container.insertBefore(card, currentAtIdx || null);
            }
        });

        // Remove stale cards that are no longer in this column
        cardMap.forEach(staleCard => staleCard.remove());
    }

    // Modal logic
    window.openModal = function(url) {
        modalImg.src = url;
        openDialog(imgModal, closeBtn);
    }
    closeBtn.onclick = function() { closeDialog(imgModal); }
    closeBtn.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            closeDialog(imgModal);
        }
    });
    window.onclick = function(event) {
        if (event.target == imgModal) closeDialog(imgModal);
        if (event.target == templateModal) closeDialog(templateModal);
    }
});
