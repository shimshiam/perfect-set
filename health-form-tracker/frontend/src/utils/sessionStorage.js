const STORAGE_KEY_V2 = 'perfect-set/session/v2';
const STORAGE_KEY_V1 = 'perfect-set/session/v1';

export const EXERCISES = {
  pushup: 'Pushups',
  squat: 'Squats',
};

function emptyTotals() {
  return {
    pushup: { completedReps: 0, abortedReps: 0 },
    squat: { completedReps: 0, abortedReps: 0 },
  };
}

export function createEmptySession(activeExercise = 'pushup') {
  return {
    version: 2,
    activeExercise,
    totals: emptyTotals(),
    events: [],
  };
}

function isValidEvent(event) {
  return (
    event &&
    typeof event === 'object' &&
    typeof event.id === 'string' &&
    EXERCISES[event.exercise] &&
    Number.isInteger(event.attempt) &&
    event.attempt > 0 &&
    Number.isFinite(event.timestamp) &&
    (event.result === 'completed' || event.result === 'aborted') &&
    typeof event.perfectForm === 'boolean'
  );
}

function isValidSession(value) {
  if (!value || typeof value !== 'object') return false;
  if (value.version !== 2) return false;
  if (!EXERCISES[value.activeExercise]) return false;
  if (!value.totals || typeof value.totals !== 'object') return false;
  if (!Array.isArray(value.events)) return false;

  return Object.keys(EXERCISES).every((exercise) => {
    const totals = value.totals[exercise];
    return (
      totals &&
      Number.isInteger(totals.completedReps) &&
      totals.completedReps >= 0 &&
      Number.isInteger(totals.abortedReps) &&
      totals.abortedReps >= 0
    );
  }) && value.events.every(isValidEvent);
}

function migrateV1Session(value) {
  if (!value || typeof value !== 'object') return null;
  if (!Number.isInteger(value.completedReps) || value.completedReps < 0) return null;
  if (!Number.isInteger(value.abortedReps) || value.abortedReps < 0) return null;
  if (!Array.isArray(value.events)) return null;

  const session = createEmptySession('pushup');
  session.totals.pushup.completedReps = value.completedReps;
  session.totals.pushup.abortedReps = value.abortedReps;
  session.events = value.events
    .filter((event) => (
      event &&
      typeof event === 'object' &&
      Number.isInteger(event.attempt) &&
      Number.isFinite(event.timestamp) &&
      typeof event.perfectForm === 'boolean'
    ))
    .map((event) => ({
      id: `pushup-${event.attempt}-${event.timestamp}`,
      exercise: 'pushup',
      attempt: event.attempt,
      timestamp: event.timestamp,
      result: event.perfectForm ? 'completed' : 'aborted',
      perfectForm: event.perfectForm,
      quality: null,
      faultCodes: [],
    }));
  return session;
}

export function getExerciseTotals(session, exercise) {
  return session.totals[exercise] ?? { completedReps: 0, abortedReps: 0 };
}

export function setActiveExercise(session, exercise) {
  if (!EXERCISES[exercise]) return session;
  return { ...session, activeExercise: exercise };
}

export function appendRepEvent(session, exercise, result, payload = {}) {
  const totals = getExerciseTotals(session, exercise);
  const nextAttempt = totals.completedReps + totals.abortedReps + 1;
  const nextTotals = {
    ...session.totals,
    [exercise]: {
      completedReps: totals.completedReps + (result === 'completed' ? 1 : 0),
      abortedReps: totals.abortedReps + (result === 'aborted' ? 1 : 0),
    },
  };
  const quality = payload.rep_quality ?? null;
  const faultCodes = quality?.fault_codes ?? [];
  const timestamp = Date.now();

  return {
    ...session,
    totals: nextTotals,
    events: [
      {
        id: `${exercise}-${nextAttempt}-${timestamp}`,
        exercise,
        attempt: nextAttempt,
        timestamp,
        result,
        perfectForm: result === 'completed',
        quality,
        faultCodes,
      },
      ...session.events,
    ],
  };
}

export function loadSession() {
  if (typeof window === 'undefined') {
    return createEmptySession();
  }

  try {
    const rawV2 = window.localStorage.getItem(STORAGE_KEY_V2);
    if (rawV2) {
      const parsedV2 = JSON.parse(rawV2);
      if (isValidSession(parsedV2)) return parsedV2;
    }

    const rawV1 = window.localStorage.getItem(STORAGE_KEY_V1);
    if (rawV1) {
      const migrated = migrateV1Session(JSON.parse(rawV1));
      if (migrated) return migrated;
    }
  } catch {
    return createEmptySession();
  }

  return createEmptySession();
}

export function saveSession(session) {
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(STORAGE_KEY_V2, JSON.stringify(session));
  } catch {
    // Ignore storage failures so live tracking keeps working.
  }
}
