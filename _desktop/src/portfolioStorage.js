const PREFIX = 'personal-win95-v1:';
const memory = new Map();
export const portfolioStorage = {
  getItem(key) { try { return window.localStorage.getItem(PREFIX + key); } catch { return memory.get(key) ?? null; } },
  setItem(key, value) { memory.set(key, String(value)); try { window.localStorage.setItem(PREFIX + key, String(value)); } catch { /* A private session still works. */ } },
  removeItem(key) { memory.delete(key); try { window.localStorage.removeItem(PREFIX + key); } catch { /* No persistent storage. */ } },
  clear() { memory.clear(); try { Object.keys(window.localStorage).filter(key => key.startsWith(PREFIX)).forEach(key => window.localStorage.removeItem(key)); } catch { /* No persistent storage. */ } },
};
