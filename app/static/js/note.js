/* note.js — salin isi catatan timeline ke clipboard + toast (12-ajax-js.md) */
(function () {
  "use strict";

  var ns = (window.DashXsadev = window.DashXsadev || {});

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "-9999px";
      document.body.appendChild(area);
      area.select();
      try {
        if (document.execCommand("copy")) {
          resolve();
        } else {
          reject(new Error("Salin tidak didukung browser ini."));
        }
      } catch (err) {
        reject(err);
      } finally {
        document.body.removeChild(area);
      }
    });
  }

  ns.initNoteCopy = function () {
    document.querySelectorAll("[data-copy-note]").forEach(function (button) {
      button.addEventListener("click", function () {
        var item = button.closest("[data-timeline-item]");
        var content = item ? item.querySelector("[data-note-content]") : null;
        if (!content) return;
        copyText(content.textContent)
          .then(function () {
            ns.toast("Catatan disalin ke clipboard.", "success");
          })
          .catch(function () {
            ns.toast("Gagal menyalin catatan.", "error");
          });
      });
    });
  };
})();
