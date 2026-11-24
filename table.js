export function makeTable(headers, rows) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-scroll";
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  for (const label of headers) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    head.append(cell);
  }
  const body = table.createTBody();
  for (const row of rows) {
    const element = body.insertRow();
    for (const [index, value] of row.entries()) {
      const cell = document.createElement(index ? "td" : "th");
      if (!index) cell.scope = "row";
      cell.textContent = value;
      element.append(cell);
    }
  }
  wrapper.append(table);
  return wrapper;
}
