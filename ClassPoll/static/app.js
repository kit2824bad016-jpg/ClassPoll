document.addEventListener("DOMContentLoaded", () => {
  const addButton = document.getElementById("add-option");
  const optionsWrap = document.getElementById("options-wrap");
  if (addButton && optionsWrap) {
    addButton.addEventListener("click", () => {
      const count = optionsWrap.querySelectorAll('input[name="options"]').length;
      if (count >= 8) {
        alert("A poll can have up to 8 options.");
        return;
      }
      const label = document.createElement("label");
      label.className = "option-input";
      label.textContent = `Option ${count + 1}`;
      const input = document.createElement("input");
      input.name = "options";
      input.maxLength = 255;
      input.required = true;
      input.placeholder = `Answer ${count + 1}`;
      label.appendChild(input);
      optionsWrap.appendChild(label);
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const search = document.getElementById("table-search");
  const table = document.getElementById("participation-table");
  if (search && table) {
    search.addEventListener("input", () => {
      const term = search.value.toLowerCase();
      table.querySelectorAll("tbody tr").forEach((row) => {
        row.hidden = !row.textContent.toLowerCase().includes(term);
      });
    });
  }

  const codeInput = document.querySelector('input[name="class_code"]');
  if (codeInput) {
    codeInput.addEventListener("input", () => {
      codeInput.value = codeInput.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
    });
  }
});
