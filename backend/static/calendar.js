// Pure render: build the calendar DOM from state. No fetching, no event wiring.

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const SLOT_MINUTES = 15;
const SLOTS_PER_DAY = 96;
const SLOT_HEIGHT_PX = 14;

function minutesSinceMidnight(isoDatetime) {
  const time = isoDatetime.slice(11);
  const [hh, mm] = time.split(":").map(Number);
  return hh * 60 + mm;
}

// Cross-midnight durations (23:30 -> 00:15) must count the rolled-over minutes.
function durationMinutes(block) {
  const startDate = Date.parse(block.start.slice(0, 10));
  const dayDelta = Math.round((Date.parse(block.end.slice(0, 10)) - startDate) / 86_400_000);
  return minutesSinceMidnight(block.end) + dayDelta * 24 * 60 - minutesSinceMidnight(block.start);
}

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

function localDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function dayHeader(weekStart, dayIndex, todayIso) {
  const date = new Date(weekStart);
  date.setDate(date.getDate() + dayIndex);
  const iso = localDate(date);
  const th = document.createElement("div");
  th.className = "day-header" + (iso === todayIso ? " today" : "");
  th.textContent = `${DAYS[dayIndex]} ${date.getDate()}.`;
  return th;
}

function timeLabels() {
  const frag = document.createDocumentFragment();
  frag.append(Object.assign(document.createElement("div"), { className: "corner" }));
  for (let hour = 0; hour < 24; hour++) {
    const label = document.createElement("div");
    label.className = "time-label";
    label.textContent = String(hour).padStart(2, "0");
    // +2: row 1 is the header, each hour spans 4 slot rows
    label.style.gridRow = `${hour * 4 + 2} / span 4`;
    frag.append(label);
  }
  return frag;
}

function dayColumn(dayIndex) {
  const col = document.createElement("div");
  col.className = "day-column";
  col.style.gridColumn = String(dayIndex + 2);
  col.style.gridRow = `2 / span ${SLOTS_PER_DAY}`;
  for (let hour = 0; hour < 24; hour++) {
    const line = document.createElement("div");
    line.className = "hour-line";
    line.style.top = `${hour * 4 * SLOT_HEIGHT_PX}px`;
    col.append(line);
  }
  return col;
}

function todoColumn(todoBlocks) {
  const col = document.createElement("div");
  col.className = "todo-column";
  col.id = "todo-column";
  const header = document.createElement("div");
  header.className = "day-header";
  header.textContent = "To-do";
  col.append(header);
  for (const block of todoBlocks) {
    col.append(todoCard(block));
  }
  return col;
}

function todoCard(block) {
  const card = document.createElement("div");
  card.className = "todo-card";
  card.dataset.blockId = String(block.id);
  card.style.backgroundColor = block.color;
  card.textContent = block.label;
  return card;
}

// Blocks overlapping the week edge (e.g. Sun 23:00 -> Mon next week) are clamped
// into the visible week rather than rendered off-grid.
function blockDiv(block, weekStartIso) {
  const div = document.createElement("div");
  div.className = "block";
  div.dataset.blockId = String(block.id);
  div.style.backgroundColor = block.color;
  const dayIndex = Math.round((Date.parse(block.start.slice(0, 10)) - Date.parse(weekStartIso)) / 86_400_000);
  const startMinutes = minutesSinceMidnight(block.start);
  const endMinutes = minutesSinceMidnight(block.end);
  const startSlots = Math.max(0, Math.floor(startMinutes / SLOT_MINUTES));
  const endSlots = Math.min(SLOTS_PER_DAY, Math.ceil(endMinutes / SLOT_MINUTES));
  const column = Math.min(6, Math.max(0, dayIndex)) + 2;
  const span = Math.max(1, endSlots - startSlots);
  div.style.gridColumn = String(column);
  div.style.gridRow = `${startSlots + 2} / span ${span}`;
  const labelSpan = document.createElement("span");
  labelSpan.className = "block-label";
  labelSpan.textContent = block.label;
  const durationSpan = document.createElement("span");
  durationSpan.className = "block-duration";
  durationSpan.textContent = formatDuration(durationMinutes(block));
  div.append(labelSpan, durationSpan);
  return div;
}

export function render(state) {
  const calendar = document.createElement("div");
  calendar.id = "calendar";
  calendar.append(timeLabels());
  const todayIso = localDate(new Date());
  for (let day = 0; day < 7; day++) {
    calendar.append(dayHeader(state.weekStart, day, todayIso));
  }
  for (let day = 0; day < 7; day++) {
    calendar.append(dayColumn(day));
  }
  const weekStartIso = localDate(state.weekStart);
  for (const block of state.blocks) {
    calendar.append(blockDiv(block, weekStartIso));
  }
  calendar.append(todoColumn(state.todo));
  return calendar;
}
