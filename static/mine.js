const search = document.querySelector("#filterBox");
const body = document.querySelector("#library_table");
const rows = Array.from(body.rows);
const counter = document.querySelector("#book_counter");
const empty = document.querySelector("#empty");

function filterBooks() {
  const term = search.value.trim().toLowerCase();
  let count = 0;
  for (const row of rows) {
    row.hidden = !row.textContent.toLowerCase().includes(term);
    if (!row.hidden) count++;
  }
  counter.textContent = count + (count === 1 ? " book" : " books");
  empty.hidden = count > 0;
}
search.addEventListener("input", filterBooks);
filterBooks();

const headers = document.querySelectorAll("th");
const collator = new Intl.Collator("sv", { numeric: true, sensitivity: "base" });
headers.forEach((header, index) => {
  header.querySelector("button").addEventListener("click", () => {
    const descending = header.getAttribute("aria-sort") === "ascending";
    headers.forEach(other => other.removeAttribute("aria-sort"));
    header.setAttribute("aria-sort", descending ? "descending" : "ascending");
    const sorted = rows.map(row => ({ row, key: row.cells[index].textContent }));
    sorted.sort((a, b) => collator.compare(a.key, b.key) * (descending ? -1 : 1));
    const fragment = document.createDocumentFragment();
    sorted.forEach(({ row }) => fragment.append(row));
    body.append(fragment);
  });
});

const form = document.querySelector("#add_book");
function updateAddButton() {
  form.querySelector("button").disabled =
    !form.elements.tbx_isbn.value.trim() && !form.elements.tbx_librisid.value.trim();
}
form.addEventListener("input", updateAddButton);
updateAddButton();

const notice = document.querySelector("#info_box");
if (notice) {
  fetch("/mute_notification", { method: "POST", redirect: "manual" });
  setTimeout(() => { notice.hidden = true; }, 5000);
}
