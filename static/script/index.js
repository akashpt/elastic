let bridge = null;

// ================= INIT =================
document.addEventListener("DOMContentLoaded", function () {
  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;

    console.log("✅ Bridge connected");

    // receive frame from Python
    bridge.frame_signal.connect(function (imageData) {
      const img = document.getElementById("cam-video");

      img.src = "data:image/jpeg;base64," + imageData;
      img.style.display = "block";

      document.getElementById("no-feed-msg").style.display = "none";
    });
 
      bridge.defect_signal.connect(function (imagePath) {

    const container = document.getElementById("defect-container");

    const img = document.createElement("img");

    // show preview
    img.src = "file:///" + imagePath.replace(/\\/g, "/");
    img.style.width = "100px";
    img.style.margin = "5px";
    img.style.cursor = "pointer";

    // 🔥 CLICK → OPEN VIEWER
    img.onclick = function () {
      bridge.openImageViewer(imagePath);
    };

    container.prepend(img);
});

  startClock();
});
});

// ================= CLOCK =================
function startClock() {
  (function tick() {
    const n = new Date();
    document.getElementById("clock").textContent =
      String(n.getHours()).padStart(2, "0") +
      ":" +
      String(n.getMinutes()).padStart(2, "0") +
      ":" +
      String(n.getSeconds()).padStart(2, "0");
    setTimeout(tick, 1000);
  })();
}

// ================= GLOBAL STATE =================
let detRunning = false;


// ================= DETECTION =================
function startDetection() {
  if (!bridge) {
    console.error("❌ Bridge not ready");
    return;
  }

  if (detRunning) return;

  detRunning = true;

  console.log("🚀 Detection started");

  document.getElementById("hdr-status").textContent = "RUNNING";
  document.getElementById("feed-card").classList.add("feed-running");

  bridge.startDetection();
}

function stopDetection() {
  if (!bridge) return;

  detRunning = false;

  console.log("🛑 Detection stopped");

  document.getElementById("hdr-status").textContent = "STANDBY";
  document.getElementById("feed-card").classList.remove("feed-running");
  bridge.stopDetection();

  document.getElementById("cam-video").style.display = "none";
  document.getElementById("no-feed-msg").style.display = "flex";
}


// ================= TRAINING =================
let trainRunning = false;

function startTraining() {
  if (!bridge) return;
  if (trainRunning) return;

  trainRunning = true;

  document.getElementById("hdr-status").textContent = "TRAINING";

  // ✅ FIX BUTTONS
  document.getElementById("train-start-btn").disabled = true;
  document.getElementById("train-stop-btn").disabled = false;

  bridge.startTraining();
}

function stopTraining() {
  if (!bridge) return;
  if (!trainRunning) return;

  trainRunning = false;

  document.getElementById("hdr-status").textContent = "STANDBY";

  // ✅ FIX BUTTONS
  document.getElementById("train-start-btn").disabled = false;
  document.getElementById("train-stop-btn").disabled = true;

  bridge.stopTraining();
}
// ================= TAB SWITCH =================
function switchTab(tab) {
  if (detRunning || trainRunning) return;

  document.getElementById("body-detection").style.display =
    tab === "detection" ? "flex" : "none";

  document.getElementById("body-training").style.display =
    tab === "training" ? "flex" : "none";

  document.getElementById("tab-det").classList.toggle(
    "active",
    tab === "detection"
  );
  document.getElementById("tab-trn").classList.toggle(
    "active",
    tab === "training"
  );
}

// ---------------------------------------
 
   

      let activeTab = "detection";
      let configSaved = false; // Important: controls START button

      function switchTab(tab) {
        if (detRunning || trainRunning) return;
        activeTab = tab;
        document
          .getElementById("tab-det")
          .classList.toggle("active", tab === "detection");
        document
          .getElementById("tab-trn")
          .classList.toggle("active", tab === "training");
        document.getElementById("body-detection").style.display =
          tab === "detection" ? "flex" : "none";
        document.getElementById("body-training").style.display =
          tab === "training" ? "flex" : "none";
      }
      function lockOtherTab(lock) {
        const other = activeTab === "detection" ? "tab-trn" : "tab-det";
        document.getElementById(other).classList.toggle("tab-hidden", lock);
      }

      function syncDetectionButtons() {
        document.getElementById("start-btn").disabled =
          detRunning || !configSaved;
        document.getElementById("stop-btn").disabled = !detRunning;
      }

      function syncTrainingButtons() {
        document.getElementById("train-start-btn").disabled = trainRunning;
        document.getElementById("train-stop-btn").disabled = !trainRunning;
      }

      // Enable START button only after Save
      function enableStartButton() {
        configSaved = true;
        syncDetectionButtons();
      }

      function syncJobId() {
        const input = document.getElementById("jobid-input");
        const select = document.getElementById("jobid-select");
        if (document.activeElement !== input && select.value) {
          input.value = select.value;
        } else {
          const matchedOption = Array.from(select.options).find(
            (option) => option.value === input.value.trim(),
          );
          select.value = matchedOption ? matchedOption.value : "";
        }
        syncCustomDropdownState(select);
        document.getElementById("hdr-jobid").textContent = input.value || "—";
      }
      function syncThresh() {
        const input = document.getElementById("thresh-input");
        const select = document.getElementById("thresh-select");
        if (document.activeElement !== input && select.value) {
          input.value = select.value;
        } else {
          const matchedOption = Array.from(select.options).find(
            (option) => option.value === input.value.trim(),
          );
          select.value = matchedOption ? matchedOption.value : "";
        }
        syncCustomDropdownState(select);
      }

      function getOptionMeta(option) {
        const label = option.textContent.trim();
        const parts = label.split("—").map((part) => part.trim());

        if (parts.length > 1) {
          return {
            title: parts[0],
            subtitle: parts.slice(1).join(" — "),
          };
        }

        return {
          title: label,
          subtitle: "Click to use this option",
        };
      }

      function closeCustomDropdowns(exceptSelectId = "") {
        document.querySelectorAll(".combined-input.open").forEach((wrap) => {
          const select = wrap.querySelector("select");
          if (select && select.id !== exceptSelectId) {
            wrap.classList.remove("open");
            const panelCard = wrap.closest(".panel-card");
            if (panelCard) panelCard.classList.remove("dropdown-active");
          }
        });
      }

      function syncCustomDropdownState(select) {
        if (!select) return;
        const wrap = select.closest(".combined-input");
        if (!wrap) return;

        const triggerText = wrap.querySelector(".combo-trigger-text");
        const options = wrap.querySelectorAll(".combo-option");
        const selectedOption =
          select.options[select.selectedIndex] || select.options[0];

        if (triggerText) {
          triggerText.textContent =
            selectedOption && selectedOption.value
              ? selectedOption.value
              : "Choose";
        }

        options.forEach((optionBtn) => {
          optionBtn.classList.toggle(
            "is-active",
            optionBtn.dataset.value === select.value,
          );
        });
      }

      function initCustomDropdown(selectId, inputId, syncFn) {
        const select = document.getElementById(selectId);
        const input = document.getElementById(inputId);
        if (!select || !input) return;

        const wrap = select.closest(".combined-input");
        if (!wrap || wrap.querySelector(".combo-trigger")) return;

        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "combo-trigger";
        trigger.innerHTML =
          '<span class="combo-trigger-text">Choose</span><span class="combo-trigger-icon"></span>';

        const menu = document.createElement("div");
        menu.className = "combo-menu";

        Array.from(select.options)
          .filter((option) => option.value)
          .forEach((option) => {
            const meta = getOptionMeta(option);
            const optionBtn = document.createElement("button");
            optionBtn.type = "button";
            optionBtn.className = "combo-option";
            optionBtn.dataset.value = option.value;
            optionBtn.innerHTML =
              `<span class="combo-option-title">${meta.title}</span>` +
              `<span class="combo-option-subtitle">${meta.subtitle}</span>`;

            optionBtn.addEventListener("click", () => {
              select.value = option.value;
              input.value = option.value;
              wrap.classList.remove("open");
              syncFn();
            });

            menu.appendChild(optionBtn);
          });

        trigger.addEventListener("click", () => {
          const isOpen = wrap.classList.contains("open");
          closeCustomDropdowns(selectId);
          wrap.classList.toggle("open", !isOpen);
          const panelCard = wrap.closest(".panel-card");
          if (panelCard) {
            panelCard.classList.toggle("dropdown-active", !isOpen);
          }
        });

        wrap.appendChild(trigger);
        wrap.appendChild(menu);
        syncCustomDropdownState(select);
      }

      const API_CONFIG = {
        enabled: false,
        endpoints: {
          saveConfig: "/api/config/save",
          startDetection: "/api/detection/start",
          stopDetection: "/api/detection/stop",
          startTraining: "/api/training/start",
          stopTraining: "/api/training/stop",
          dashboard: "/api/dashboard",
        },
      };

      function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      }

      async function apiRequest(endpoint, options = {}) {
        if (!API_CONFIG.enabled || !endpoint) {
          return { skipped: true, data: null };
        }

        const requestOptions = {
          method: options.method || "GET",
          headers: {
            Accept: "application/json",
          },
        };

        if (options.body !== undefined) {
          requestOptions.headers["Content-Type"] = "application/json";
          requestOptions.body = JSON.stringify(options.body);
        }

        const response = await fetch(endpoint, requestOptions);
        const raw = await response.text();
        let data = null;

        try {
          data = raw ? JSON.parse(raw) : null;
        } catch (error) {
          data = raw;
        }

        if (!response.ok) {
          const message =
            data && typeof data === "object" && data.message
              ? data.message
              : `Request failed with status ${response.status}`;
          throw new Error(message);
        }

        return { skipped: false, data };
      }

      async function fetchDashboardData() {
        try {
          const result = await apiRequest(API_CONFIG.endpoints.dashboard);
          if (result.skipped || !result.data) return;

          const data = result.data;
          if (typeof data.jobId === "string") setText("hdr-jobid", data.jobId);
          if (typeof data.status === "string")
            setText("hdr-status", data.status.toUpperCase());
          if (typeof data.defects !== "undefined")
            setText("hdr-defects", String(data.defects));
        } catch (error) {
          showToast(
            error.message || "Unable to fetch dashboard data.",
            "error",
          );
        }
      }

      // Webcam
      const video = document.getElementById("cam-video");
      let camStream = null;
   
     
    function captureFrame() {
    const img = document.getElementById("cam-video");

      if (!img.src) return null;

      const canvas = document.getElementById("snap-canvas");
      const ctx = canvas.getContext("2d");

      canvas.width = img.width;
      canvas.height = img.height;

      ctx.drawImage(img, 0, 0);

      return canvas.toDataURL("image/jpeg", 0.75);
    }

      // Defects
      let defectCount = 0;
      function addDefectThumb(dataUrl) {
        defectCount++;
        document.getElementById("defect-empty").style.display = "none";
        document.getElementById("defect-count-badge").textContent =
          defectCount + " captured";
        const thumb = document.createElement("div");
        thumb.className = "defect-thumb";
        if (dataUrl) {
          const img = document.createElement("img");
          img.src = dataUrl;
          thumb.appendChild(img);
        }
        const lbl = document.createElement("div");
        lbl.className = "defect-label";
        lbl.textContent = "DEFECT #" + defectCount;
        const tsEl = document.createElement("div");
        tsEl.className = "defect-ts";
        tsEl.textContent = new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
        thumb.append(lbl, tsEl);
        document.getElementById("defect-grid").appendChild(thumb);
        document.getElementById("defect-scroll-wrap").scrollTop =
          document.getElementById("defect-scroll-wrap").scrollHeight;
      }

      function showToast(msg, type = "info") {
        let t = document.getElementById("toast");
        if (!t) {
          t = document.createElement("div");
          t.id = "toast";
          t.style.cssText =
            "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);color:#fff;padding:10px 22px;border-radius:8px;font-size:13px;z-index:999;opacity:0;transition:opacity 0.3s;";
          document.body.appendChild(t);
        }
        const colors = {
          info: "#222",
          success: "#1e8449",
          error: "#c0392b",
          warning: "#f39c12",
        };
        t.style.background = colors[type] || colors.info;
        t.textContent = msg;
        t.style.opacity = "1";
        setTimeout(() => (t.style.opacity = "0"), 2800);
      }

      /* Detection */
    
        detInterval = null;
      async function startDetection() {
        if (detRunning || !configSaved) return;
        const jid = document.getElementById("jobid-input").value.trim();
        const thr = document.getElementById("thresh-input").value.trim();
        if (!jid) {
          showToast("Please enter or select a Job ID first.", "warning");
          return;
        }

        try {
          await apiRequest(API_CONFIG.endpoints.startDetection, {
            method: "POST",
            body: {
              jobId: jid,
              threshold: thr,
            },
          });

          detRunning = true;
          syncDetectionButtons();
          lockOtherTab(true);
          document.getElementById("hdr-status").textContent = "RUNNING";
          document.getElementById("status-dot").style.cssText =
            "background:#f39c12;box-shadow:0 0 6px #f39c12;";
          document.getElementById("feed-card").classList.add("feed-running");

          setText("cnt-inspected", "0");
          setText("cnt-good", "0");
          setText("cnt-defective", "0");
          setText("hdr-defects", "0");

          bridge.startCamera();
          showToast(`Detection started for ${jid}.`, "success");

          let i = 0,
            g = 0,
            d = 0;
          detInterval = setInterval(() => {
            i++;
            const isDef = Math.random() < 0.22;
            if (isDef) {
              d++;
              setText("hdr-defects", String(d));
              setText("cnt-defective", String(d));
              addDefectThumb(captureFrame());
            } else g++;
            setText("cnt-inspected", String(i));
            setText("cnt-good", String(g));
          }, 1400);
        } catch (error) {
          showToast(error.message || "Unable to start detection.", "error");
        }
      }

      async function stopDetection() {
        if (!detRunning) return;
        try {
          await apiRequest(API_CONFIG.endpoints.stopDetection, {
            method: "POST",
          });

          detRunning = false;
          syncDetectionButtons();
          clearInterval(detInterval);
          bridge.stopCamera();
          lockOtherTab(false);
          document.getElementById("hdr-status").textContent = "STANDBY";
          document.getElementById("status-dot").style.cssText = "";
          document.getElementById("feed-card").classList.remove("feed-running");
          showToast("Detection stopped.", "info");
        } catch (error) {
          showToast(error.message || "Unable to stop detection.", "error");
        }
      }

      
  

      /* Save Configuration - Enables START button */
      async function saveConfig() {
        const jid = document.getElementById("jobid-input").value.trim();
        const thr = document.getElementById("thresh-input").value.trim();
        if (!jid || !thr) {
          showToast(
            "Please fill Job ID and Threshold before saving.",
            "warning",
          );
          return;
        }
        try {
          await apiRequest(API_CONFIG.endpoints.saveConfig, {
            method: "POST",
            body: {
              jobId: jid,
              threshold: thr,
            },
          });

          const btn = document.querySelector(".save-btn");
          const orig = btn.innerHTML;
          btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
          btn.style.background = "linear-gradient(135deg,#1e8449,#27ae60)";

          enableStartButton();
          showToast("Configuration saved successfully.", "success");

          setTimeout(() => {
            btn.innerHTML = orig;
            btn.style.background = "";
          }, 1800);
        } catch (error) {
          showToast(error.message || "Unable to save configuration.", "error");
        }
      }

      syncDetectionButtons();
      syncTrainingButtons();
      initCustomDropdown("jobid-select", "jobid-input", syncJobId);
      initCustomDropdown("thresh-select", "thresh-input", syncThresh);
      document.addEventListener("click", (event) => {
        if (!event.target.closest(".combined-input")) {
          closeCustomDropdowns();
        }
      });
      fetchDashboardData();
    