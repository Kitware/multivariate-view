import rawCSV from "../data/data10.csv?raw";

// ----------------------------------------------------------------------------
// Helper local methods
// ----------------------------------------------------------------------------
let seed = 1;
function random() {
  var x = Math.sin(seed++) * 10000;
  return x - Math.floor(x);
}

function clamp(v, min, max) {
  if (v < min) {
    return min;
  }
  if (v > max) {
    return max;
  }
  return v;
}

// ----------------------------------------------------------------------------
// Format data in a specific fashion
// ----------------------------------------------------------------------------
export function getData(nbSamples = 100) {
  const allLines = rawCSV.split(/\r\n|\n/);
  const header = allLines[0].split(",");
  const data = [];
  const sampleSize = Math.min(nbSamples, allLines.length - 1);

  for (let i = 1; i <= sampleSize; i++) {
    const entry = allLines[i].split(",").map(Number);
    console.log("Data entry size", entry.length);
    data.push(entry);
  }
  // header: ['Ce','Co','Fe','Gd']
  // data: [
  //   [0.266, 0.266, 0.384, 0.082],
  //   ...
  // ]
  return { header, data };
}

// ----------------------------------------------------------------------------
export function dataTopologyReduction(data, nbBins = 6) {
  // extract components coordinates
  const components = [];
  while (data[0].length !== data[data.length - 1].length) {
    components.unshift(data.pop());
  }

  // Create data structure
  const bins = [];
  const binMap = {};
  for (let i = 0; i < nbBins; i++) {
    binMap[i] = {};
    for (let j = 0; j < nbBins; j++) {
      const bin = { i, j, nbBins, entries: [] };
      binMap[i][j] = bin;
      bins.push(bin);
    }
  }

  // Start 2D binning
  const delta = 2 / nbBins;
  const cMin = 0;
  const cMax = nbBins - 1;
  for (let idx = 0; idx < data.length; idx++) {
    const entry = data[idx];
    const i = clamp(Math.floor((entry[0] + 1) / delta), cMin, cMax);
    const j = clamp(Math.floor((entry[1] + 1) / delta), cMin, cMax);
    // console.log(`x=${entry[0]}, y=${entry[1]}, i=${i}, j=${j}`);
    console.log("add entry", entry.length);
    binMap[i][j].entries.push(entry);
  }

  // Extract Q
  const q = [];
  for (let i = 0; i < bins.length; i++) {
    // console.log("seek q", bins[i]);
    const entries = bins[i].entries;
    const nbEntries = entries.length;
    const sampleIdx = new Set();

    // Figure out sampling size
    let targetSize = nbEntries / 2;
    if (targetSize > 1000) {
      targetSize = 5 * Math.log2(nbEntries);
    } else if (targetSize > 100) {
      targetSize = Math.log2(nbEntries);
    }

    // Skip empty bins
    if (nbEntries === 0) continue;

    // Extract sampling
    while (sampleIdx.size < targetSize) {
      const rd = Math.floor(random() * nbEntries);
      if (sampleIdx.has(rd)) continue;
      sampleIdx.add(rd);
      q.push(entries[rd]);
    }
  }
  return { components, q };
}

// ----------------------------------------------------------------------------
// The last nth correspond to the location of headers
// ----------------------------------------------------------------------------
export function computeGBC(datam, rotateRadianAngle) {
  const m = datam.length; // nb points
  const n = datam[0].length; // nb vars

  const angle = new Array(n);
  angle[0] = Math.PI / 2 + rotateRadianAngle;

  var GBCL = new Array();

  for (i = 0; i < m + n; i++) {
    GBCL[i] = new Array();
    for (j = 0; j < 2; j++) {
      GBCL[i][j] = 0;
    }
    for (k = 2; k < 2 + n; k++) {
      if (i < m) {
        GBCL[i][k] = parseFloat(datam[i][k - 2]);
      }
    }
  }

  GBCL[m][0] = Math.cos(angle[0]);
  GBCL[m][1] = Math.sin(angle[0]);

  for (let i = 1; i < n; i++) {
    angle[i] = angle[i - 1] - (2 * Math.PI) / n;
    GBCL[m + i][0] = Math.cos(angle[i]) * 0.997;
    GBCL[m + i][1] = Math.sin(angle[i]) * 0.997;
  }

  for (let i = 0; i < n; i++) {
    if (angle[i] < 0) {
      angle[i] = angle[i] + Math.PI * 2;
    }
    if (angle[i] > Math.PI * 2) {
      angle[i] = angle[i] - Math.PI * 2;
    }
  }

  angle.sort();

  for (var i = 0; i < m; i++) {
    var tempsum = 0;
    for (var j = 0; j < n; j++) {
      tempsum = tempsum + parseFloat(datam[i][j]);
    }

    if (tempsum == 0) {
      GBCL[i][0] = 0;
      GBCL[i][1] = 0;
    } else {
      for (var k = 0; k < n; k++) {
        GBCL[i][0] = GBCL[i][0] + (datam[i][k] / tempsum) * GBCL[m + k][0];
        GBCL[i][1] = GBCL[i][1] + (datam[i][k] / tempsum) * GBCL[m + k][1];
      }

      var tempangle = Math.atan2(GBCL[i][1], GBCL[i][0]);
      if (tempangle < 0) {
        tempangle = tempangle + Math.PI * 2;
      }
      var flag = false;
      var tempA = 0;
      var tempB = 0;
      for (let j = 0; j < n - 1; j++) {
        if (
          (tempangle > angle[j] || tempangle == angle[j]) &&
          tempangle < angle[j + 1]
        ) {
          tempA = angle[j + 1];
          tempB = angle[j];
          flag = true;
        }
        if (flag == true) break;
      }
      if (flag == false) {
        tempA = angle[0] + Math.PI * 2;
        tempB = angle[n - 1];
      }
      var lth =
        (Math.sqrt(GBCL[i][0] * GBCL[i][0] + GBCL[i][1] * GBCL[i][1]) /
          Math.cos((tempA - tempB) / 2)) *
        Math.cos(-(tempA + tempB) / 2 + tempangle);
      GBCL[i][0] = lth * Math.cos(tempangle);
      GBCL[i][1] = lth * Math.sin(tempangle);
    }
  }

  var dimorder = new Array(n);
  for (let i = 0; i < n; i++) {
    dimorder[i] = i;
  }

  return GBCL;
}
