"use strict";

const root = document.documentElement;
const themeButtons = document.querySelectorAll("[data-theme]");
const tokenButtons = document.querySelectorAll("[data-token]");
const status = document.querySelector(".copy-status");

function updateCodes() {
  const style = getComputedStyle(root);
  for (const button of tokenButtons) {
    const value = style.getPropertyValue(`--lu-${button.dataset.token}`).trim();
    button.dataset.copy = value;
    button.querySelector(".color-value").textContent = value;
    button.setAttribute("aria-label", `Copy ${button.dataset.label}, ${value}`);
  }
}

for (const button of themeButtons) {
  button.disabled = false;
  button.addEventListener("click", () => {
    root.dataset.luTheme = button.dataset.theme;
    for (const option of themeButtons) {
      option.setAttribute("aria-pressed", String(option === button));
    }
    updateCodes();
    status.textContent = "";
  });
}

updateCodes();
for (const button of document.querySelectorAll("[data-copy]")) {
  button.disabled = false;
  button.addEventListener("click", async () => {
    const value = button.dataset.copy;
    try {
      await navigator.clipboard.writeText(value);
      status.textContent = `Copied ${value}.`;
    } catch {
      // A theme change may replace this code while a permission prompt is open.
      if (button.dataset.copy !== value) return;
      // Local files and denied clipboard permissions still allow manual copying.
      const range = document.createRange();
      range.selectNodeContents(button.querySelector("code"));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = `Selected ${value}. Press ⌘C or Ctrl+C to copy.`;
    }
  });
}
