// ----------------------------------------------------------------------------
// Helper local methods
// ----------------------------------------------------------------------------

export function rotateCoordinates(coords, angle) {
  // Rotate coordinates about the center by the angle (radians)
  const cosAngle = Math.cos(angle);
  const sinAngle = Math.sin(angle);

  const out = new Array(coords.length);
  for (let i = 0; i < coords.length; i++) {
    out[i] = new Array(2);
    out[i][0] = cosAngle * coords[i][0] - sinAngle * coords[i][1];
    out[i][1] = sinAngle * coords[i][0] + cosAngle * coords[i][1];
  }

  return out;
}
