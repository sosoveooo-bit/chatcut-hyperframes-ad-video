const roles = ["", "hook", "try_on", "detail", "motion", "proof", "ending", "transition"];
const statuses = ["queued", "ready", "hold", "rejected"];
let library = { items: [], batches: [] };
let syncData = { requests: [] };

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) throw new Error(payload.error || ("HTTP " + response.status));
  return payload;
}

function toast(message, isError = false) {
  const node = byId("toast");
  node.textContent = message;
  node.className = "show" + (isError ? " error" : "");
  window.setTimeout(() => { node.className = ""; }, 3200);
}

function optionList(values, selected) {
  return values.map((value) =>
    '<option value="' + escapeHtml(value) + '" ' + (value === selected ? "selected" : "") + ">" +
    escapeHtml(value || "未设置") +
    "</option>"
  ).join("");
}

function filteredItems() {
  const batch = byId("batchFilter").value;
  const query = byId("searchInput").value.trim().toLowerCase();
  return library.items.filter((item) => {
    if (batch && item.batchId !== batch) return false;
    const haystack = (item.name + " " + (item.tags || []).join(" ") + " " + item.role).toLowerCase();
    return !query || haystack.includes(query);
  });
}

function renderMaterials() {
  const items = filteredItems();
  byId("materialCount").textContent = items.length + " 条素材";
  byId("materialGrid").innerHTML = items.length ? items.map((item) => {
    const megabytes = (Number(item.size || 0) / 1024 / 1024).toFixed(1);
    return '<article class="card" data-item-id="' + escapeHtml(item.id) + '">' +
      '<video controls preload="metadata" src="/media/' + encodeURIComponent(item.id) + '"></video>' +
      '<div class="card-body">' +
        '<div class="select-row">' +
          '<h3 class="card-title">' + escapeHtml(item.name) + '</h3>' +
          '<input class="sync-select" type="checkbox" aria-label="选择同步 ' + escapeHtml(item.name) + '">' +
        '</div>' +
        '<div class="meta">' + escapeHtml(item.batchName) + " · " + megabytes + ' MB</div>' +
        '<div class="row">' +
          '<label>角色<select class="role-select">' + optionList(roles, item.role || "") + '</select></label>' +
          '<label>审核<select class="status-select">' + optionList(statuses, item.analysisStatus || "queued") + '</select></label>' +
        '</div>' +
        '<label>标签<input class="tags-input" value="' + escapeHtml((item.tags || []).join(", ")) + '" placeholder="可剪辑, 优先混剪"></label>' +
        '<button class="small save-item" type="button">保存标签</button>' +
      '</div>' +
    '</article>';
  }).join("") : '<div class="empty">暂无素材。先导入一个本地文件夹。</div>';
}

function renderBatches() {
  const selected = byId("batchFilter").value;
  byId("batchFilter").innerHTML = '<option value="">全部批次</option>' + library.batches.map((batch) =>
    '<option value="' + escapeHtml(batch.id) + '">' + escapeHtml(batch.name) + '</option>'
  ).join("");
  byId("batchFilter").value = selected;
}

function renderMonitor(monitor) {
  byId("monitorTitle").textContent = monitor.score + " 分 · ready " + monitor.readyCount + " 条";
  byId("monitorRoles").innerHTML = roles.filter(Boolean).map((role) => {
    const count = monitor.roleCounts[role] || 0;
    return '<span class="chip ' + (count ? "" : "missing") + '">' + role + " " + count + "</span>";
  }).join("");
}

function renderQueue() {
  const requests = [...(syncData.requests || [])].reverse();
  byId("syncQueue").innerHTML = requests.length ? requests.map((request) =>
    '<div class="queue-item">' +
      '<div><strong>' + escapeHtml(request.productKey) + '</strong><div class="meta">' +
      escapeHtml(request.projectId) + " · " + request.items.length + " 条</div></div>" +
      '<span class="chip">' + escapeHtml(request.status) + '</span>' +
    '</div>'
  ).join("") : '<div class="empty">暂无同步请求。</div>';
}

async function refresh() {
  try {
    const payloads = await Promise.all([
      requestJson("/api/material-library"),
      requestJson("/api/material-library/director-monitor"),
      requestJson("/api/material-library/chatcut-sync"),
    ]);
    library = payloads[0];
    syncData = payloads[2];
    renderBatches();
    renderMaterials();
    renderMonitor(payloads[1]);
    renderQueue();
  } catch (error) {
    toast(error.message, true);
  }
}

byId("importForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = await requestJson("/api/material-library/import-local-folder", {
      method: "POST",
      body: JSON.stringify({
        folder: byId("folderInput").value,
        batchName: byId("batchInput").value,
        recursive: byId("recursiveInput").checked,
      }),
    });
    toast("已导入 " + payload.result.count + " 条素材");
    await refresh();
  } catch (error) {
    toast(error.message, true);
  }
});

byId("materialGrid").addEventListener("click", async (event) => {
  const button = event.target.closest(".save-item");
  if (!button) return;
  const card = button.closest(".card");
  try {
    await requestJson("/api/material-library/item/update", {
      method: "POST",
      body: JSON.stringify({
        itemId: card.dataset.itemId,
        role: card.querySelector(".role-select").value,
        analysisStatus: card.querySelector(".status-select").value,
        tags: card.querySelector(".tags-input").value,
      }),
    });
    toast("标签已保存");
    await refresh();
  } catch (error) {
    toast(error.message, true);
  }
});

byId("syncForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const itemIds = [...document.querySelectorAll(".card .sync-select:checked")]
    .map((checkbox) => checkbox.closest(".card").dataset.itemId);
  if (!itemIds.length) {
    toast("请先勾选 ready 素材", true);
    return;
  }
  try {
    const payload = await requestJson("/api/material-library/chatcut-sync/request", {
      method: "POST",
      body: JSON.stringify({
        projectUrl: byId("projectUrlInput").value,
        productKey: byId("productKeyInput").value,
        itemIds,
      }),
    });
    toast("已创建同步请求 " + payload.result.id);
    await refresh();
  } catch (error) {
    toast(error.message, true);
  }
});

byId("batchFilter").addEventListener("change", renderMaterials);
byId("searchInput").addEventListener("input", renderMaterials);
byId("refreshButton").addEventListener("click", refresh);
refresh();
