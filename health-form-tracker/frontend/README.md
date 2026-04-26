# Perfect Set Frontend

React + Vite client for the Perfect Set physical form tracker. The frontend captures webcam frames, streams them to the FastAPI backend over WebSocket, renders the pose overlay, and keeps the current session in browser `localStorage`.

## Features

- Webcam capture with a mirrored local preview
- Real-time pushup status updates over WebSocket
- Skeleton overlay and dashboard telemetry
- Persistent session history with JSON export
- Audio cues for completed reps and form warnings

## Development

Install dependencies and start the Vite dev server:

```bash
npm install
npm run dev
```

The app expects the backend WebSocket server at `ws://localhost:8000/ws/pushups`.

## Session Storage

Session state is stored locally in the browser under `perfect-set/session/v1`. Reloading the page restores:

- completed rep count
- aborted rep count
- session event history used by the log and export flow
