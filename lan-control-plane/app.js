const tbody = document.getElementById("tbody");
const statusEl = document.getElementById("status");
const scanBtn = document.getElementById("scanBtn");
const pingSweep = document.getElementById("pingSweep");

function fmtTime(iso) {
  if (!iso) return "never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function render(data) {
  document.getElementById("statCount").textContent = data.count ?? 0;
  document.getElementById("statGateway").textContent = data.gateway || "—";
  document.getElementById("statLocal").textContent = data.local_ip || "—";
  document.getElementById("statTime").textContent = fmtTime(data.scanned_at);

  const devices = data.devices || [];
  if (!devices.length) {
    tbody.innerHTML = `<tr class="empty"><td colspan="8">${data.message || "No devices found."}</td></tr>`;
    return;
  }

  tbody.innerHTML = devices
    .map((d) => {
      const name = d.nickname || d.hostname || d.vendor || "Unknown device";
      const dotClass = d.is_gateway ? "gw" : d.online ? "on" : "";
      const status = d.is_gateway ? "gateway" : d.is_self ? "this host" : d.online ? "online" : "seen";
      const tags = (d.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("") || "—";
      const caps = (d.capabilities || []).map((c) => `<span class="tag">${escapeHtml(c)}</span>`).join("") || "—";
      return `<tr>
        <td><span class="dot ${dotClass}"></span>${status}</td>
        <td>${escapeHtml(name)}${d.vendor ? ` <span style="color:var(--muted);font-size:0.8rem">· ${escapeHtml(d.vendor)}</span>` : ""}</td>
        <td class="mono">${escapeHtml(d.ip)}</td>
        <td class="mono">${escapeHtml(d.mac || "—")}</td>
        <td class="mono">${escapeHtml(d.hostname || "—")}</td>
        <td>${escapeHtml(d.room || "—")}</td>
        <td>${tags}</td>
        <td>${caps}</td>
      </tr>`;
    })
    .join("");
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadCached() {
  const res = await fetch("/api/devices");
  const data = await res.json();
  render(data);
}

async function runScan() {
  scanBtn.disabled = true;
  statusEl.textContent = pingSweep.checked
    ? "Scanning… ping sweep can take ~30–60s on /24"
    : "Scanning ARP table…";
  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ping_sweep: pingSweep.checked }),
    });
    const data = await res.json();
    if (!res.ok) {
      statusEl.textContent = data.error || "Scan failed";
      return;
    }
    render(data);
    statusEl.textContent = `Found ${data.count} devices in ${data.duration_ms} ms`;
  } catch (err) {
    statusEl.textContent = `Scan error: ${err.message}`;
  } finally {
    scanBtn.disabled = false;
  }
}

scanBtn.addEventListener("click", runScan);
loadCached();
