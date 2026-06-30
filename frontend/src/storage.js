/* Safe localStorage wrapper — in-memory fallback for private browsing. */
(function (root) {
  "use strict";

  const TOKEN_KEY = "mbr_token";
  const memory = {};
  let _storage = null;
  let _ephemeral = false;

  function createMemoryStorage() {
    return {
      getItem(key) {
        return Object.prototype.hasOwnProperty.call(memory, key) ? memory[key] : null;
      },
      setItem(key, value) {
        memory[key] = String(value);
      },
      removeItem(key) {
        delete memory[key];
      },
    };
  }

  function safeStorage() {
    if (_storage) return _storage;
    try {
      const test = "__mbr_storage_test__";
      root.localStorage.setItem(test, "1");
      root.localStorage.removeItem(test);
      _storage = root.localStorage;
    } catch {
      _storage = createMemoryStorage();
      _ephemeral = true;
    }
    return _storage;
  }

  function isEphemeralStorage() {
    safeStorage();
    return _ephemeral;
  }

  root.mbrStorage = { safeStorage, isEphemeralStorage, TOKEN_KEY };
})(typeof window !== "undefined" ? window : globalThis);
