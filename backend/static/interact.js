// Pointer-event interactions: create on empty grid, drag to move, drag
// bottom edge to resize, plus the to-do column (create as todo, drag a card
// onto the grid to schedule, drop a block on the column to unschedule).
// All mutations go through callbacks into app.js.

import { openEditor, closeEditor } from "./editor.js";

const SLOT_MINUTES = 15;
const SLOT_HEIGHT_PX = 14;
const SLOTS_PER_DAY = 96;

function blockColor(block) {
  return rgbToHex(block.style.backgroundColor);
}

function rgbToHex(rgb) {
  const m = rgb.match(/\d+/g);
  if (!m) return "#4a90d9";
  return "#" + m.slice(0, 3).map((v) => Number(v).toString(16).padStart(2, "0")).join("");
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function isoAt(date, minutes) {
  // Minutes may run past midnight (e.g. a 23:30 block ending at 24:00); the
  // extra time rolls onto the next day.
  const days = Math.floor(minutes / (24 * 60));
  const dayDate = new Date(date);
  dayDate.setDate(dayDate.getDate() + days);
  const mins = minutes % (24 * 60);
  return `${dayDate.getFullYear()}-${pad2(dayDate.getMonth() + 1)}-${pad2(dayDate.getDate())}T` +
    `${pad2(Math.floor(mins / 60))}:${pad2(mins % 60)}`;
}

// Grid cell (day index, slot) under a pointer event, or null outside the grid.
// Uses the day-column rect (not the calendar's) so scrolling is handled for free.
// The column is found by hit-test, not closest(): blocks are grid siblings of
// the columns, so a pointer over a block never resolves via closest().
function cellFromEvent(event) {
  const col = colFromPoint(event.clientX, event.clientY);
  if (!col) return null;
  return cellFromPoint(event.clientX, event.clientY, col);
}

function colFromPoint(clientX, clientY) {
  for (const col of document.querySelectorAll(".day-column")) {
    const rect = col.getBoundingClientRect();
    if (clientX >= rect.left && clientX < rect.right) return col;
  }
  return null;
}

function cellFromPoint(clientX, clientY, col) {
  const rect = col.getBoundingClientRect();
  const day = Number(col.style.gridColumn) - 2;
  const slot = Math.floor((clientY - rect.top) / SLOT_HEIGHT_PX);
  if (day < 0 || day > 6 || slot < 0 || slot >= SLOTS_PER_DAY) return null;
  // Slots crossed from the column top (ceil): a pointer at a slot boundary
  // means the edge lands exactly there, not one slot below.
  const boundary = Math.ceil((clientY - rect.top) / SLOT_HEIGHT_PX);
  return { day, slot, boundary };
}

function slotMinutes(slot) {
  return slot * SLOT_MINUTES;
}

function startDrag(event, calendar, onMove) {
  event.preventDefault();
  const move = (e) => onMove(cellFromEvent(e));
  const up = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
}

export function wireInteractions(calendar, { weekStart, onMutate }) {
  calendar.addEventListener("pointerdown", (event) => {
    const block = event.target.closest(".block");
    const todoCard = event.target.closest(".todo-card");
    if (block) {
      handleBlockPointerDown(event, block, calendar, weekStart, onMutate);
    } else if (todoCard) {
      handleTodoPointerDown(event, todoCard, calendar, weekStart, onMutate);
    } else if (event.target.closest(".day-column")) {
      handleEmptyClick(event, calendar, weekStart, onMutate);
    }
  });
}

function handleEmptyClick(event, calendar, weekStart, onMutate) {
  const cell = cellFromEvent(event);
  if (!cell) return;
  const dayDate = new Date(weekStart);
  dayDate.setDate(dayDate.getDate() + cell.day);
  const startMinutes = slotMinutes(cell.slot);
  // Default 1h, clamped so a late-evening click does not end past midnight.
  const endMinutes = Math.min(startMinutes + 60, 24 * 60);
  openEditor({
    anchor: { left: event.clientX, top: event.clientY },
    saveText: "Create",
    onTodo: ({ label, color }) => {
      closeEditor();
      // default 1h duration; parked in the to-do column until scheduled
      onMutate({
        method: "POST",
        path: "/api/blocks",
        body: { start: isoAt(dayDate, startMinutes), end: isoAt(dayDate, endMinutes), label, color, source: "todo" },
      });
    },
    todoTitle: "Create as an unscheduled to-do",
    onSave: ({ label, color }) => {
      closeEditor();
      onMutate({
        method: "POST",
        path: "/api/blocks",
        body: {
          start: isoAt(dayDate, startMinutes),
          end: isoAt(dayDate, endMinutes),
          label,
          color,
        },
      });
    },
  });
}

function handleBlockPointerDown(event, block, calendar, weekStart, onMutate) {
  const blockId = Number(block.dataset.blockId);
  // The bottom 8px of the block is the resize handle. Measured against the
  // block's own rect: offsetY is relative to whatever child span was hit, and
  // on short blocks the spans cover the edge zone, so target-relative checks
  // misclassify resizes as moves.
  const offsetInBlock = event.clientY - block.getBoundingClientRect().top;
  const isResize = offsetInBlock > block.offsetHeight - 8;
  // The rendered grid styles are the source of truth; deriving slot/day from
  // pixels drifts by a slot when blocks have margins.
  const gcMatch = block.style.gridColumn.match(/\d+/);
  const grMatch = block.style.gridRow.match(/^(\d+) \/ span (\d+)$/);
  if (!gcMatch || !grMatch) return;
  const startDay = Number(gcMatch[0]) - 2;
  const startSlot = Number(grMatch[1]) - 2;
  const spanSlots = Number(grMatch[2]);
  // Where inside the block the grab happened, so a move shifts the block
  // instead of snapping its start under the pointer.
  const grabCell = cellFromEvent(event);
  const grabSlot = grabCell ? grabCell.slot : startSlot;
  const grabDay = grabCell ? grabCell.day : startDay;
  let sawMove = false;
  block.classList.add("dragging");
  if (isResize) block.classList.add("resizing");

  startDrag(event, calendar, (cell) => {
    if (!cell) return;
    sawMove = true;
    if (isResize) {
      // Bottom edge lands at the pointer: span = slots crossed from the
      // block's start, min 1. Using the boundary (ceil) keeps the edge exactly
      // under the pointer instead of one slot below it.
      const span = Math.max(1, cell.boundary - startSlot);
      moveBlockVisual(block, startDay, startSlot, span);
    } else {
      const dayDelta = cell.day - grabDay;
      const slotDelta = cell.slot - grabSlot;
      moveBlockVisual(block, startDay + dayDelta, startSlot + slotDelta, spanSlots);
    }
  });
  window.addEventListener("pointerup", (upEvent) => {
    block.classList.remove("dragging", "resizing");
    if (!isResize && droppedOnTodo(upEvent)) {
      unscheduleBlock(blockId, onMutate);
      return;
    }
    // The final pointermove can race the pointerup, leaving the visual one
    // slot behind the pointer; recompute from the up event's position. A pure
    // click (no pointermove) must not touch the visual at all, or the block
    // would jump and a click would count as a move.
    if (sawMove) {
      const upCell = cellFromEvent(upEvent);
      if (upCell) {
        if (isResize) {
          moveBlockVisual(block, startDay, startSlot, Math.max(1, upCell.boundary - startSlot));
        } else {
          moveBlockVisual(
            block,
            startDay + (upCell.day - grabDay),
            startSlot + (upCell.slot - grabSlot),
            spanSlots,
          );
        }
      }
    }
    const moved = block.style.gridColumn !== String(startDay + 2) ||
      block.style.gridRow !== `${startSlot + 2} / span ${spanSlots}`;
    if (moved) {
      commitBlock(block, weekStart, onMutate, blockId);
    } else if (!isResize) {
      openBlockEditor(blockId, block, onMutate);
    }
  }, { once: true });
}

function droppedOnTodo(upEvent) {
  const target = document.elementFromPoint(upEvent.clientX, upEvent.clientY);
  return target?.closest(".todo-column") != null;
}

function unscheduleBlock(blockId, onMutate) {
  // Parking keeps the block's slot and duration; only the source marker
  // changes, so scheduling it again later is lossless.
  onMutate({
    method: "PATCH",
    path: `/api/blocks/${blockId}`,
    body: { source: "todo" },
  });
}

function moveBlockVisual(block, day, slot, span) {
  const clampedDay = Math.min(6, Math.max(0, day));
  const clampedSlot = Math.min(SLOTS_PER_DAY - span, Math.max(0, slot));
  block.style.gridColumn = String(clampedDay + 2);
  block.style.gridRow = `${clampedSlot + 2} / span ${span}`;
}

function commitBlock(block, weekStart, onMutate, blockId) {
  const day = Number(block.style.gridColumn) - 2;
  const rowMatch = block.style.gridRow.match(/^(\d+) \/ span (\d+)$/);
  if (!rowMatch) return;
  const slot = Number(rowMatch[1]) - 2;
  const span = Number(rowMatch[2]);
  const dayDate = new Date(weekStart);
  dayDate.setDate(dayDate.getDate() + day);
  const startMinutes = slotMinutes(slot);
  const endMinutes = startMinutes + span * SLOT_MINUTES;
  onMutate({
    method: "PATCH",
    path: `/api/blocks/${blockId}`,
    body: { start: isoAt(dayDate, startMinutes), end: isoAt(dayDate, endMinutes) },
  });
}

function openBlockEditor(blockId, block, onMutate) {
  openEditor({
    anchor: block.getBoundingClientRect(),
    label: block.querySelector(".block-label")?.textContent ?? "",
    color: blockColor(block),
    saveText: "Save",
    onSave: ({ label, color }) => {
      closeEditor();
      onMutate({ method: "PATCH", path: `/api/blocks/${blockId}`, body: { label, color } });
    },
    onDelete: () => {
      closeEditor();
      onMutate({ method: "DELETE", path: `/api/blocks/${blockId}` });
    },
    onTodo: () => {
      closeEditor();
      unscheduleBlock(blockId, onMutate);
    },
  });
}

function handleTodoPointerDown(event, card, calendar, weekStart, onMutate) {
  const blockId = Number(card.dataset.blockId);
  card.classList.add("dragging");

  startDrag(event, calendar, () => {});
  window.addEventListener("pointerup", (upEvent) => {
    card.classList.remove("dragging");
    const target = document.elementFromPoint(upEvent.clientX, upEvent.clientY);
    const dayCol = target?.closest(".day-column");
    if (dayCol) {
      scheduleTodo(blockId, dayCol, upEvent, weekStart, onMutate);
    } else {
      openTodoEditor(blockId, card, onMutate);
    }
  }, { once: true });
}

function scheduleTodo(blockId, dayCol, upEvent, weekStart, onMutate) {
  const cell = cellFromPoint(upEvent.clientX, upEvent.clientY, dayCol);
  if (!cell) return;
  // start-only: the server moves the block, preserving its duration
  const dayDate = new Date(weekStart);
  dayDate.setDate(dayDate.getDate() + cell.day);
  onMutate({
    method: "PATCH",
    path: `/api/blocks/${blockId}`,
    body: { start: isoAt(dayDate, slotMinutes(cell.slot)) },
  });
}

function openTodoEditor(blockId, card, onMutate) {
  openEditor({
    anchor: card.getBoundingClientRect(),
    label: card.querySelector(".todo-label")?.textContent ?? "",
    color: blockColor(card),
    saveText: "Save",
    onSave: ({ label, color }) => {
      closeEditor();
      onMutate({ method: "PATCH", path: `/api/blocks/${blockId}`, body: { label, color } });
    },
    onDelete: () => {
      closeEditor();
      onMutate({ method: "DELETE", path: `/api/blocks/${blockId}` });
    },
  });
}
