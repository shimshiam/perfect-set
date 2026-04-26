/**
 * drawing.js — Canvas drawing helpers for rendering the pose skeleton.
 * All coordinates are normalized [0, 1] and get scaled to canvas dimensions.
 * The canvas is mirrored (scaleX -1) to match the mirrored video feed,
 * so we flip x: x_pixel = canvasWidth - (landmark.x * canvasWidth).
 */

const CONNECTIONS = [
  ['shoulder', 'elbow'],
  ['elbow', 'wrist'],
  ['shoulder', 'hip'],
  ['hip', 'ankle'],
];

const SIDE_COLORS = {
  left: '#00D4FF',
  right: '#FF6B00',
};

/**
 * Draws the full skeleton onto the given canvas context.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object|null} landmarks — normalized landmark dict from server
 * @param {number} width — canvas width
 * @param {number} height — canvas height
 */
export function drawSkeleton(ctx, landmarks, width, height) {
  if (!landmarks) return;

  const toPixel = (lm) => ({
    x: width - lm[0] * width,   // flip x for mirrored video
    y: lm[1] * height,
  });

  for (const side of ['left', 'right']) {
    const color = SIDE_COLORS[side];

    // Draw connection lines
    for (const [from, to] of CONNECTIONS) {
      const k1 = `${side}_${from}`;
      const k2 = `${side}_${to}`;
      if (landmarks[k1] && landmarks[k2]) {
        const p1 = toPixel(landmarks[k1]);
        const p2 = toPixel(landmarks[k2]);

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.stroke();
      }
    }

    // Draw joint dots
    const joints = ['shoulder', 'elbow', 'wrist', 'hip', 'ankle'];
    for (const joint of joints) {
      const key = `${side}_${joint}`;
      if (landmarks[key]) {
        const p = toPixel(landmarks[key]);

        // White border
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        // Colored fill
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      }
    }
  }
}
