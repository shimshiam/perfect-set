const STORAGE_KEY = 'perfect-set/session/v1';

export function createEmptySession() {
  return {
    completedReps: 0,
    abortedReps: 0,
    events: [],
  };
}

function isValidSession(value) {
  if (!value || typeof value !== 'object') return false;
  if (!Number.isInteger(value.completedReps) || value.completedReps < 0) return false;
  if (!Number.isInteger(value.abortedReps) || value.abortedReps < 0) return false;
  if (!Array.isArray(value.events)) return false;

  return value.events.every((event) => (
    event &&
    typeof event === 'object' &&
    Number.isInteger(event.attempt) &&
    event.attempt > 0 &&
    Number.isFinite(event.timestamp) &&
    typeof event.perfectForm === 'boolean'
  ));
}

export function loadSession() {
  if (typeof window === 'undefined') {
    return createEmptySession();
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return createEmptySession();

    const parsed = JSON.parse(raw);
    return isValidSession(parsed) ? parsed : createEmptySession();
  } catch {
    return createEmptySession();
  }
}

export function saveSession(session) {
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Ignore storage failures so live tracking keeps working.
  }
}
