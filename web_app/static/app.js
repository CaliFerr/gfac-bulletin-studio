const landingView = document.getElementById("landingView");
const editorView = document.getElementById("editorView");
const sectionsRoot = document.getElementById("sectionsRoot");
const sectionTemplate = document.getElementById("sectionTemplate");
const rowTemplate = document.getElementById("rowTemplate");
const csvInput = document.getElementById("csvInput");
const themeToggleButton = document.getElementById("themeToggleButton");

const state = {
  sections: [],
  hasProgram: false,
};

const sectionTone = {
  "Filipino Service": "filipino",
  "Sabbath School": "sabbath",
  "Hour Of Worship": "worship",
};

const THEME_KEY = "gfac-web-theme";

document.getElementById("createProgramButton").addEventListener("click", async () => {
  await loadDefaults();
  showEditor();
});

document.getElementById("importCsvButton").addEventListener("click", () => csvInput.click());
document.getElementById("downloadCsvButton").addEventListener("click", () => exportPayload("/api/export/csv", "program_web.csv"));
document.getElementById("bulletinButton").addEventListener("click", () => exportPayload("/api/export/bulletin", "program_web_bulletin.pdf"));
document.getElementById("resetButton").addEventListener("click", loadDefaults);
document.getElementById("backToStartButton").addEventListener("click", showLanding);

document.getElementById("desktopDownloadButton").addEventListener("click", downloadDesktop);
document.getElementById("desktopDownloadButtonTop").addEventListener("click", downloadDesktop);
themeToggleButton.addEventListener("click", toggleTheme);

csvInput.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/import-csv", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = await safeJson(response);
    alert(payload?.detail || "Could not import CSV.");
    return;
  }

  const payload = await response.json();
  state.sections = payload.sections;
  state.hasProgram = true;
  renderSections();
  showEditor();
  csvInput.value = "";
});

async function loadDefaults() {
  const response = await fetch("/api/default-program");
  const payload = await response.json();
  state.sections = payload.sections;
  state.hasProgram = true;
  renderSections();
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.body.classList.toggle("dark-mode", isDark);
  themeToggleButton.textContent = isDark ? "Light Mode" : "Dark Mode";
  localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
}

function toggleTheme() {
  applyTheme(document.body.classList.contains("dark-mode") ? "light" : "dark");
}

function showLanding() {
  landingView.classList.remove("hidden");
  editorView.classList.add("hidden");
}

function showEditor() {
  landingView.classList.add("hidden");
  editorView.classList.remove("hidden");
}

async function downloadDesktop() {
  const response = await fetch("/api/download/desktop");
  if (!response.ok) {
    const payload = await safeJson(response);
    alert(payload?.detail || "Desktop download is not available yet.");
    return;
  }

  const blob = await response.blob();
  const link = document.createElement("a");
  const disposition = response.headers.get("content-disposition");
  const fileName = disposition?.match(/filename=\"?([^"]+)\"?/)?.[1] || "GFAC Bulletin Studio Desktop.zip";
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function exportPayload(url, fallbackName) {
  if (!state.hasProgram) {
    alert("Create or import a program first.");
    return;
  }

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sections: state.sections }),
  });

  if (!response.ok) {
    const payload = await safeJson(response);
    alert(payload?.detail || "Export failed.");
    return;
  }

  const blob = await response.blob();
  const link = document.createElement("a");
  const disposition = response.headers.get("content-disposition");
  const fileName = disposition?.match(/filename=\"?([^"]+)\"?/)?.[1] || fallbackName;
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(link.href);
}

function renderSections() {
  sectionsRoot.innerHTML = "";
  state.sections.forEach((section, sectionIndex) => {
    const fragment = sectionTemplate.content.cloneNode(true);
    const banner = fragment.querySelector(".section-banner");
    const title = fragment.querySelector(".section-title");
    const timeInput = fragment.querySelector(".section-time");
    const rowList = fragment.querySelector(".row-list");
    const addRowButton = fragment.querySelector(".add-row-button");

    banner.classList.add(sectionTone[section.title] || "worship");
    title.textContent = section.title;
    timeInput.value = section.time;
    timeInput.addEventListener("input", (event) => {
      state.sections[sectionIndex].time = event.target.value;
    });

    section.rows.forEach((row, rowIndex) => {
      rowList.appendChild(buildRow(sectionIndex, rowIndex, row));
    });

    addRowButton.addEventListener("click", () => {
      state.sections[sectionIndex].rows.push({ title: "", subheading: "", small_subheading: "" });
      renderSections();
    });

    sectionsRoot.appendChild(fragment);
  });
}

function buildRow(sectionIndex, rowIndex, row) {
  const fragment = rowTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".program-row");
  const titleInput = fragment.querySelector(".row-title");
  const subheadingInput = fragment.querySelector(".row-subheading");
  const smallSubheadingInput = fragment.querySelector(".row-small-subheading");
  const removeButton = fragment.querySelector(".row-remove");
  const dragHandle = fragment.querySelector(".drag-handle");

  titleInput.value = row.title;
  subheadingInput.value = row.subheading;
  smallSubheadingInput.value = row.small_subheading;

  titleInput.addEventListener("input", (event) => {
    state.sections[sectionIndex].rows[rowIndex].title = event.target.value;
  });
  subheadingInput.addEventListener("input", (event) => {
    state.sections[sectionIndex].rows[rowIndex].subheading = event.target.value;
  });
  smallSubheadingInput.addEventListener("input", (event) => {
    state.sections[sectionIndex].rows[rowIndex].small_subheading = event.target.value;
  });

  removeButton.addEventListener("click", () => {
    state.sections[sectionIndex].rows.splice(rowIndex, 1);
    if (state.sections[sectionIndex].rows.length === 0) {
      state.sections[sectionIndex].rows.push({ title: "", subheading: "", small_subheading: "" });
    }
    renderSections();
  });

  card.addEventListener("dragstart", (event) => {
    if (event.target !== dragHandle && event.target !== card) return;
    card.classList.add("dragging");
    event.dataTransfer.setData("text/plain", JSON.stringify({ sectionIndex, rowIndex }));
    event.dataTransfer.effectAllowed = "move";
  });

  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");
    clearPlaceholders();
  });

  card.addEventListener("dragover", (event) => {
    event.preventDefault();
    showPlaceholder(card);
  });

  card.addEventListener("dragleave", () => {
    card.classList.remove("placeholder");
  });

  card.addEventListener("drop", (event) => {
    event.preventDefault();
    const data = JSON.parse(event.dataTransfer.getData("text/plain"));
    if (data.sectionIndex !== sectionIndex || data.rowIndex === rowIndex) {
      clearPlaceholders();
      return;
    }

    const rows = state.sections[sectionIndex].rows;
    const [moved] = rows.splice(data.rowIndex, 1);
    const targetIndex = data.rowIndex < rowIndex ? rowIndex - 1 : rowIndex;
    rows.splice(targetIndex, 0, moved);
    clearPlaceholders();
    renderSections();
  });

  return fragment;
}

function showPlaceholder(activeCard) {
  clearPlaceholders();
  activeCard.classList.add("placeholder");
}

function clearPlaceholders() {
  document.querySelectorAll(".program-row.placeholder").forEach((node) => node.classList.remove("placeholder"));
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

applyTheme(localStorage.getItem(THEME_KEY) || "light");
