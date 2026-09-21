/* combobox.js — dropdown kustom bertoken + fallback <select> native (21-form-controls.md).
   Port dari xsadev-kit core/js/app.js:initCombobox, disesuaikan token app:
   highlight opsi = bg-surface-soft, label kosong = text-steel. */
(function () {
  "use strict";

  var ns = (window.Dashboardku = window.Dashboardku || {});

  var ACTIVE_CLASS = "bg-surface-soft";
  var PLACEHOLDER_CLASS = "text-steel";

  function initRoot(root) {
    var select = root.querySelector("[data-combobox-native]");
    var control = root.querySelector("[data-combobox-control]");
    var input = root.querySelector("[data-combobox-input]");
    var trigger = root.querySelector("[data-combobox-trigger]");
    var labelEl = root.querySelector("[data-combobox-label]");
    var menu = root.querySelector("[data-combobox-menu]");
    var empty = root.querySelector("[data-combobox-empty]");
    var options = Array.prototype.slice.call(root.querySelectorAll("[data-combobox-option]"));
    var display = input || trigger;
    if (!select || !control || !display || !menu) return;

    var searchable = !!input;
    var placeholder = labelEl ? labelEl.getAttribute("data-placeholder") || "" : "";
    var activeIndex = -1;

    select.classList.add("hidden");
    control.classList.remove("hidden");

    function selectedOption() {
      return (
        options.filter(function (opt) {
          return opt.getAttribute("data-value") === select.value;
        })[0] || null
      );
    }

    function syncDisplay() {
      var opt = selectedOption();
      if (input) {
        input.value = opt ? opt.textContent.trim() : "";
      } else if (labelEl) {
        labelEl.textContent = opt ? opt.textContent.trim() : placeholder;
        labelEl.classList.toggle(PLACEHOLDER_CLASS, !opt);
      }
    }

    function matches(opt) {
      var kind = root.getAttribute("data-kind-filter") || "";
      if (kind && opt.getAttribute("data-kind") !== kind) return false;
      if (!searchable) return true;
      var query = input.value.trim().toLowerCase();
      // Saat fokus dengan label terpilih, tampilkan semua opsi (bukan hanya yang cocok).
      var selected = selectedOption();
      if (selected && query === selected.textContent.trim().toLowerCase()) query = "";
      return !query || opt.textContent.toLowerCase().indexOf(query) !== -1;
    }

    function applyFilter() {
      var shown = 0;
      options.forEach(function (opt) {
        var visible = matches(opt);
        opt.classList.toggle("hidden", !visible);
        opt.setAttribute("aria-selected", "false");
        opt.classList.remove(ACTIVE_CLASS);
        if (visible) shown += 1;
      });
      if (empty) empty.classList.toggle("hidden", shown !== 0);
      activeIndex = -1;
    }

    function highlight(visibleList) {
      options.forEach(function (opt) {
        opt.classList.remove(ACTIVE_CLASS);
      });
      if (activeIndex >= 0 && visibleList[activeIndex]) {
        visibleList[activeIndex].classList.add(ACTIVE_CLASS);
        visibleList[activeIndex].scrollIntoView({ block: "nearest" });
      }
    }

    function open() {
      applyFilter();
      menu.classList.remove("hidden");
      root.classList.add("is-open");
      display.setAttribute("aria-expanded", "true");
    }

    function close() {
      menu.classList.add("hidden");
      root.classList.remove("is-open");
      display.setAttribute("aria-expanded", "false");
    }

    function choose(opt) {
      options.forEach(function (o) {
        o.setAttribute("aria-selected", "false");
      });
      opt.setAttribute("aria-selected", "true");
      select.value = opt.getAttribute("data-value");
      syncDisplay();
      close();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function reset() {
      select.value = "";
      syncDisplay();
      close();
    }

    function refresh() {
      options = Array.prototype.slice.call(root.querySelectorAll("[data-combobox-option]"));
      applyFilter();
      syncDisplay();
    }

    if (searchable) {
      input.addEventListener("focus", function () {
        input.select();
        open();
      });
      input.addEventListener("input", open);
      input.addEventListener("blur", function () {
        window.setTimeout(function () {
          if (!root.contains(document.activeElement)) {
            syncDisplay();
            close();
          }
        }, 120);
      });
    } else {
      trigger.addEventListener("click", function () {
        if (menu.classList.contains("hidden")) open();
        else close();
      });
    }

    display.addEventListener("keydown", function (event) {
      var visibleList = options.filter(function (opt) {
        return !opt.classList.contains("hidden");
      });

      if (!searchable && menu.classList.contains("hidden") && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        open();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (menu.classList.contains("hidden")) {
          open();
          return;
        }
        activeIndex = Math.min(activeIndex + 1, visibleList.length - 1);
        highlight(visibleList);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        highlight(visibleList);
      } else if (event.key === "Enter") {
        if (!menu.classList.contains("hidden") && activeIndex >= 0 && visibleList[activeIndex]) {
          event.preventDefault();
          choose(visibleList[activeIndex]);
        }
      } else if (event.key === "Escape") {
        close();
      }
    });

    // Delegasi: opsi yang ditambahkan belakangan tetap berfungsi.
    menu.addEventListener("mousedown", function (event) {
      var opt = event.target.closest("[data-combobox-option]");
      if (!opt) return;
      event.preventDefault();
      choose(opt);
    });

    document.addEventListener("click", function (event) {
      if (!root.contains(event.target)) close();
    });

    select.addEventListener("change", syncDisplay);
    root.addEventListener("combobox:reset", reset);
    root.addEventListener("combobox:refresh", refresh);

    // Ketik label persis tanpa memilih dari list → sinkronkan nilai sebelum submit.
    if (searchable && select.form) {
      select.form.addEventListener("submit", function () {
        if (select.value) return;
        var typed = input.value.trim().toLowerCase();
        var match = options.filter(matches).filter(function (opt) {
          return opt.textContent.trim().toLowerCase() === typed;
        })[0];
        if (match) select.value = match.getAttribute("data-value");
      });
    }

    syncDisplay();
  }

  ns.initCombobox = function () {
    document.querySelectorAll("[data-combobox]").forEach(initRoot);
  };
})();
