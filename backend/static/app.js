import { fetchWeek } from "./api.js";
import { render } from "./calendar.js";

// state = { weekStart: Date (Monday 00:00 local), blocks: [...] } — re-render after every change.

const DAY_MS = 86_400_000;

function mondayOf(date) {
  const monday = new Date(date);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - (monday.getDay() + 6) % 7);
  return monday;
}

function isoWeekOf(date) {
  // Thursday of this ISO week determines year and week number.
  const monday = mondayOf(date);
  const thursday = new Date(monday.getTime() + 3 * DAY_MS);
  const jan4 = new Date(thursday.getFullYear(), 0, 4);
  const jan4Monday = mondayOf(jan4);
  const week = Math.max(1, 1 + Math.round((monday.getTime() - jan4Monday.getTime()) / (7 * DAY_MS)));
  return { year: thursday.getFullYear(), week };
}

function mondayOfIsoWeek(year, week) {
  const jan4Monday = mondayOf(new Date(year, 0, 4));
  return new Date(jan4Monday.getTime() + (week - 1) * 7 * DAY_MS);
}

function weekPickerValue(monday) {
  const { year, week } = isoWeekOf(monday);
  return `${year}-W${String(week).padStart(2, "0")}`;
}

function weekTitle(monday) {
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);
  const fmt = (d) => d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return `${fmt(monday)} – ${fmt(sunday)}`;
}

const state = { weekStart: mondayOf(new Date()), blocks: [] };

function mount(calendar) {
  document.getElementById("calendar").replaceWith(calendar);
  document.getElementById("week-picker").value = weekPickerValue(state.weekStart);
  document.getElementById("week-title").textContent = weekTitle(state.weekStart);
}

async function refresh() {
  const { year, week } = isoWeekOf(state.weekStart);
  state.blocks = await fetchWeek(year, week);
  mount(render(state));
}

function shiftWeek(delta) {
  state.weekStart.setDate(state.weekStart.getDate() + delta * 7);
  refresh();
}

document.getElementById("prev-week").addEventListener("click", () => shiftWeek(-1));
document.getElementById("next-week").addEventListener("click", () => shiftWeek(1));
document.getElementById("today").addEventListener("click", () => {
  state.weekStart = mondayOf(new Date());
  refresh();
});
document.getElementById("week-picker").addEventListener("change", (event) => {
  const [year, week] = event.target.value.split("-W").map(Number);
  state.weekStart = mondayOfIsoWeek(year, week);
  refresh();
});

refresh();
