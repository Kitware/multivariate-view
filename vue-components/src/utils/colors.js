import * as d3 from "d3";

const CANVAS_COLOR_MAP = document.createElement("canvas");

export function colorConstrainInUnit(cx, cy) {
  const r = Math.sqrt(Math.pow(cx, 2) + Math.pow(cy, 2));
  if (r > 1) {
    cx /= r;
    cy /= r;
  }
  return [cx, cy];
}

function GBCtoHCL2(cx, cy) {
  if (cx * cx + cy * cy > 0.999999) {
    return "rgba(0,0,0,0)";
  }

  let h = Math.atan2(cy, cx) + Math.PI / 2;
  if (h < 0) {
    h = h + Math.PI * 2;
  }
  if (h > Math.PI * 2) {
    h = h - Math.PI * 2;
  }

  h = (h / Math.PI) * 180;
  const s = Math.sqrt(Math.pow(cx, 2) + Math.pow(cy, 2));
  const l = 0.55;

  h = Math.floor(h);
  return d3.hsl(h, s, l).toString();
}

export function coordToColor(cx, cy) {
  [cx, cy] = colorConstrainInUnit(cx, cy);
  return GBCtoHCL2(cx, cy);
}

export function computeColorMapImage(size, brushMode) {
  const diameter = Math.round(size * 2.4) / 3.1;
  const xyOffset = (size - diameter) * 0.5;
  const scaleGBC = d3.scaleLinear([-1, 1], [xyOffset, xyOffset + diameter]);

  d3.select(CANVAS_COLOR_MAP).attr("width", size).attr("height", size);
  const ctx = CANVAS_COLOR_MAP.getContext("2d");

  for (let i = xyOffset; i < xyOffset + diameter; i++) {
    for (let j = xyOffset; j < xyOffset + diameter; j++) {
      if (brushMode == 1.0) {
        ctx.fillStyle = "#C7D9E8";
      } else {
        ctx.fillStyle = coordToColor(
          scaleGBC.invert(j),
          scaleGBC.invert(i),
          false
        );
      }
      ctx.fillRect(j, i, 1, 1);
    }
  }

  return CANVAS_COLOR_MAP.toDataURL("image/png");
}
