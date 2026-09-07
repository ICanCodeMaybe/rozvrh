// Pure render: build the calendar DOM from state. No fetching, no event wiring.

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const SLOT_MINUTES = 15;
const SLOTS_PER_DAY = 96;
const SLOT_HEIGHT_PX = 14;
const DAY_MS = 86_400_000;

function minutesSinceMidnight(isoDatetime) {
  const time = isoDatetime.slice(11);
  const [hh, mm] = time.split(":").map(Number);
  return hh * 60 + mm;
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

// Blocks overlapping the week edge (e.g. Sun 23:00 -> Mon next week) are clamped
// into the visible week rather than rendered off-grid.
function blockDiv(block, weekStartIso) {
  const div = document.createElement("div");
  div.className = "block";
  div.dataset.blockId = String(block.id);
  div.style.backgroundColor = block.color;
  const dayIndex = Math.round((Date.parse(block.start.slice(0, 10)) - Date.parse(weekStartIso)) / DAY_MS);
  const startMinutes = minutesSinceMidnight(block.start);
  const endMinutes = minutesSinceMidnight(block.end);
  const startSlots = Math.max(0, Math.floor(startMinutes / SLOT_MINUTES));
  const endSlots = Math.min(SLOTS_PER_DAY, Math.ceil(endMinutes / SLOT_MINUTES));
  const column = Math.min(6, Math.max(0, dayIndex)) + 2;
  const span = Math.max(1, endSlots - startSlots);
  div.style.gridColumn = String(column);
  div.style.gridRow = `${startSlots + 2} / span ${span}`;
  div.textContent = block.label;
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
  return calendar;
}
