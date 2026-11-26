function drawPie(layout) {
  const svg = layout.querySelector("svg");
  const tooltip = layout.querySelector(".pie-tooltip");
  const rows = Array.from(layout.querySelectorAll(".pie-legend li"));
  const total = rows.reduce((sum, row) => sum + Number(row.dataset.count), 0);
  let start = -Math.PI / 2;
  let active;

  function clear() {
    if (active) {
      active.slice.classList.remove("highlight");
      active.row.classList.remove("highlight");
      active = null;
    }
    tooltip.hidden = true;
  }

  for (const row of rows) {
    const count = Number(row.dataset.count);
    const share = count / total;
    const end = start + 2 * Math.PI * share;
    const slice = document.createElementNS(svg.namespaceURI, share === 1 ? "circle" : "path");
    if (share === 1) {
      slice.setAttribute("r", "1");
    } else {
      slice.setAttribute("d", [
        "M 0 0 L", Math.cos(start), Math.sin(start),
        "A 1 1 0", share > 0.5 ? 1 : 0, 1, Math.cos(end), Math.sin(end), "Z"
      ].join(" "));
    }
    start = end;
    const percent = (share * 100).toLocaleString(undefined, { maximumFractionDigits: 1 });
    const label = row.dataset.label + " · " + count + (count === 1 ? " book" : " books") + " (" + percent + "%)";
    slice.setAttribute("fill", row.querySelector(".swatch").style.backgroundColor);
    slice.setAttribute("aria-label", label);
    slice.setAttribute("role", "img");
    slice.setAttribute("tabindex", "0");
    svg.append(slice);

    function show() {
      clear();
      active = { slice, row };
      slice.classList.add("highlight");
      row.classList.add("highlight");
      tooltip.textContent = label;
      tooltip.hidden = false;
    }
    for (const target of [slice, row]) {
      target.addEventListener("pointerenter", show);
      target.addEventListener("focusin", show);
      target.addEventListener("pointerleave", clear);
      target.addEventListener("focusout", clear);
    }
  }
  layout.addEventListener("keydown", event => {
    if (event.key === "Escape") clear();
  });
}

document.querySelectorAll(".pie-layout").forEach(drawPie);
