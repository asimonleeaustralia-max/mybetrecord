/* Marketing site — locale boot and language selector. */
(function () {
  "use strict";

  function applyHomeTitle() {
    document.title = window.i18n.t("home.meta.title");
  }

  async function boot() {
    const loc = window.i18n.getLoginLocale();
    await window.i18n.initI18n(loc);
    applyHomeTitle();

    const select = document.getElementById("localeSelect");
    if (select) {
      select.innerHTML = window.i18n.languageOptions(window.i18n.currentLocale());
      select.addEventListener("change", async () => {
        await window.i18n.setLocale(select.value, { persistCookie: true });
        applyHomeTitle();
      });
    }

    window.i18n.applyI18n(document);
  }

  document.addEventListener("DOMContentLoaded", () => {
    boot().catch(e => console.error("Marketing i18n boot failed:", e));
  });
})();
