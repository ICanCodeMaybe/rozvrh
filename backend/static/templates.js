// Templates panel: save the current week as a template, list templates,
// apply one to the visible week (reporting skipped occupied slots), delete.
// Reads go through fetchTemplates(), mutations through the shared mutate();
// the grid refresh is owned by app.js's onMutate, which returns the API
// response so skipped blocks can be computed here.

import { fetchTemplates, mutate } from "./api.js";

function hhmm(isoDatetime) {
  return isoDatetime.slice(11, 16);
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function weekStartIso(weekStart) {
  return `${weekStart.getFullYear()}-${pad2(weekStart.getMonth() + 1)}-${pad2(weekStart.getDate())}`;
}

function dayOfWeek(block, startIso) {
  const day = Math.round((Date.parse(block.start.slice(0, 10)) - Date.parse(startIso)) / 86_400_000);
  // Clamped: a block spilling past Sunday (Sun 23:00 -> Mon 00:30) is saved on
  // Sunday, losing the overflow. Templates are weekly, so there is nowhere to
  // put it; the trade-off is silent truncation of a rare edge case.
  return Math.min(6, Math.max(0, day));
}

function templateBlocksFromWeek(blocks, startIso) {
  return blocks
    .slice()
    .sort((a, b) => a.start.localeCompare(b.start))
    .map((b) => ({
      day_of_week: dayOfWeek(b, startIso),
      start_time: hhmm(b.start),
      end_time: hhmm(b.end),
      label: b.label,
      color: b.color,
    }));
}

function describeTemplate(template) {
  if (template.blocks.length === 0) return "empty";
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return template.blocks
    .map((b) => `${days[b.day_of_week]} ${b.start_time}–${b.end_time} ${b.label}`)
    .join(", ");
}

// Blocks the apply endpoint did not create: their expected start datetime is
// missing from the response, meaning an existing block occupied the slot.
function skippedLabels(template, created, weekStart) {
  const createdStarts = new Set(created.map((b) => b.start));
  return template.blocks
    .filter((b) => {
      const dayDate = new Date(weekStart);
      dayDate.setDate(dayDate.getDate() + b.day_of_week);
      return !createdStarts.has(`${weekStartIso(dayDate)}T${b.start_time}`);
    })
    .map((b) => b.label);
}

function row(template, { list, getWeekInfo, onMutate, status }) {
  const rowEl = document.createElement("div");
  rowEl.className = "template-row";
  const name = document.createElement("span");
  name.className = "template-name";
  name.textContent = template.name;
  const detail = document.createElement("span");
  detail.className = "template-detail";
  detail.textContent = describeTemplate(template);
  const actions = document.createElement("div");
  actions.className = "template-actions";
  const apply = document.createElement("button");
  apply.type = "button";
  apply.textContent = "Apply";
  apply.addEventListener("click", async () => {
    // One read of the visible week drives both the URL and the skip report,
    // so navigating weeks while the panel is open cannot split them apart.
    const { weekStart } = getWeekInfo();
    const { year, week } = isoWeekOfDate(weekStart);
    const created = await onMutate({
      method: "POST",
      path: `/api/templates/${template.id}/apply/${year}/${week}`,
    });
    if (created === null) {
      status.textContent = `Apply failed for "${template.name}".`;
      return;
    }
    const skipped = skippedLabels(template, created, weekStart);
    status.textContent = skipped.length === 0
      ? `Applied "${template.name}": ${created.length} blocks added.`
      : `Applied "${template.name}": ${created.length} added, skipped (occupied): ${skipped.join(", ")}`;
  });
  const del = document.createElement("button");
  del.type = "button";
  del.textContent = "Delete";
  del.className = "danger";
  del.addEventListener("click", async () => {
    await onMutate({ method: "DELETE", path: `/api/templates/${template.id}` });
    await fill(list, { getWeekInfo, onMutate, status });
  });
  actions.append(apply, del);
  rowEl.append(name, detail, actions);
  return rowEl;
}

async function fill(list, { getWeekInfo, onMutate, status }) {
  const templates = await fetchTemplates();
  list.replaceChildren();
  if (templates === null) return;
  if (templates.length === 0) {
    const empty = document.createElement("p");
    empty.className = "templates-empty";
    empty.textContent = "No templates yet. Save this week as one.";
    list.append(empty);
    return;
  }
  for (const template of templates) {
    list.append(row(template, { list, getWeekInfo, onMutate, status }));
  }
}

export function openTemplatesPanel({ anchor, getWeekInfo, onMutate }) {
  const panel = document.createElement("div");
  panel.className = "templates-panel";
  const header = document.createElement("div");
  header.className = "templates-header";
  const title = document.createElement("h2");
  title.textContent = "Templates";
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Close templates");
  close.textContent = "×";
  close.addEventListener("click", () => panel.remove());
  header.append(title, close);

  const saveForm = document.createElement("form");
  saveForm.className = "templates-save";
  const nameInput = document.createElement("input");
  nameInput.maxLength = 100;
  nameInput.placeholder = "Template name";
  nameInput.required = true;
  const saveBtn = document.createElement("button");
  saveBtn.type = "submit";
  saveBtn.textContent = "Save current week";
  const saveStatus = document.createElement("span");
  saveStatus.className = "templates-status";
  saveForm.append(nameInput, saveBtn);
  saveForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const { weekStart, blocks } = getWeekInfo();
    const saved = await onMutate({
      method: "POST",
      path: "/api/templates",
      body: { name: nameInput.value, blocks: templateBlocksFromWeek(blocks, weekStartIso(weekStart)) },
    });
    if (saved === null) {
      saveStatus.textContent = "Save failed.";
      return;
    }
    nameInput.value = "";
    await fill(list, { getWeekInfo, onMutate, status });
    saveStatus.textContent = blocks.length === 0
      ? "Saved an empty template (the week had no blocks)."
      : `Saved "${saved.name}" with ${saved.blocks.length} blocks.`;
  });

  const list = document.createElement("div");
  list.className = "templates-list";
  const status = document.createElement("div");
  status.className = "templates-status";

  panel.append(header, saveForm, saveStatus, list, status);
  document.body.append(panel);
  // Clamp into the viewport at open and again on resize; a fixed-position
  // panel opened near the right edge would otherwise end up off-screen when
  // the window shrinks (or on a phone rotation).
  const clampIntoViewport = () => {
    const rect = panel.getBoundingClientRect();
    panel.style.left = `${Math.min(Math.max(rect.left, 8), Math.max(8, window.innerWidth - rect.width - 8))}px`;
    panel.style.top = `${Math.min(Math.max(rect.top, 8), Math.max(8, window.innerHeight - rect.height - 8))}px`;
  };
  clampIntoViewport();
  window.addEventListener("resize", clampIntoViewport);
  close.addEventListener("click", () => window.removeEventListener("resize", clampIntoViewport), { once: true });
  nameInput.focus();
  // fill() resolves after the list rows are in the DOM; the panel may have
  // grown, so clamp again once its final size is known.
  fill(list, { getWeekInfo, onMutate, status }).then(clampIntoViewport);
}

// ISO 8601 week number: week 1 of a year is the week containing the first
// Thursday, equivalently the one containing Jan 4; the Thursday of the visible
// week decides both year and number.
function isoWeekOfDate(weekStart) {
  const DAY_MS = 86_400_000;
  const thursday = new Date(weekStart);
  thursday.setDate(thursday.getDate() + 3);
  const jan4 = new Date(thursday.getFullYear(), 0, 4);
  const jan4Monday = new Date(jan4);
  jan4Monday.setHours(0, 0, 0, 0);
  jan4Monday.setDate(jan4Monday.getDate() - (jan4Monday.getDay() + 6) % 7);
  const week = 1 + Math.round((thursday.getTime() - jan4Monday.getTime()) / (7 * DAY_MS));
  return { year: thursday.getFullYear(), week };
}
