// Small inline editor used both for creating a block (empty-grid click)
// and editing one (block click). Only one editor is open at a time.

export const PALETTE = [
  "#4a90d9",
  "#e74c3c",
  "#2ecc71",
  "#f39c12",
  "#9b59b6",
  "#1abc9c",
  "#e67e22",
  "#34495e",
];

function swatchRow(selected, onPick) {
  const row = document.createElement("div");
  row.className = "editor-palette";
  for (const color of PALETTE) {
    const swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "swatch" + (color === selected ? " selected" : "");
    swatch.style.backgroundColor = color;
    swatch.setAttribute("aria-label", `Color ${color}`);
    swatch.addEventListener("click", () => {
      onPick(color);
      for (const s of row.children) {
        s.classList.toggle("selected", s === swatch);
      }
    });
    row.append(swatch);
  }
  return row;
}

export function closeEditor() {
  document.querySelector(".editor")?.remove();
}

// anchor: DOMRect or {left, top} to place the editor next to.
// onAction({label, color}, action) is called with action "save" (submit),
// "todo" (To-do button) or undefined for plain buttons like delete.
export function openEditor({ anchor, label = "", color = PALETTE[0], saveText, onSave, onDelete, onTodo, todoTitle }) {
  closeEditor();
  const form = document.createElement("form");
  form.className = "editor";
  const input = document.createElement("input");
  input.className = "editor-label";
  input.maxLength = 200;
  input.placeholder = "Label";
  input.value = label;
  let picked = color;
  const save = document.createElement("button");
  save.type = "submit";
  save.textContent = saveText;
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "Cancel";
  cancel.addEventListener("click", closeEditor);
  const actions = document.createElement("div");
  actions.className = "editor-actions";
  actions.append(save, cancel);
  if (onDelete) {
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.className = "danger";
    del.addEventListener("click", onDelete);
    actions.append(del);
  }
  if (onTodo) {
    const todo = document.createElement("button");
    todo.type = "button";
    todo.textContent = "To-do";
    todo.title = todoTitle ?? "Move to the to-do column (unschedule)";
    todo.addEventListener("click", () => onTodo({ label: input.value, color: picked }));
    actions.append(todo);
  }
  form.append(input, swatchRow(picked, (c) => (picked = c)), actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSave({ label: input.value, color: picked });
  });
  document.body.append(form);
  const left = Math.min(Math.max(anchor.left, 8), window.innerWidth - form.offsetWidth - 8);
  const top = Math.min(Math.max(anchor.top, 8), window.innerHeight - form.offsetHeight - 8);
  form.style.left = `${left}px`;
  form.style.top = `${top}px`;
  input.focus();
  form.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeEditor();
  });
  // Close when clicking outside; skip the click that opened the editor and
  // let buttons inside run their own handlers.
  setTimeout(() => {
    const onOutside = (event) => {
      if (!form.contains(event.target)) {
        document.removeEventListener("pointerdown", onOutside);
        closeEditor();
      }
    };
    document.addEventListener("pointerdown", onOutside);
  });
}
