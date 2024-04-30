import * as d3 from "d3";
import { computeColorMapImage } from "../utils/colors";
import { rotateCoordinates } from "../utils/compute";

const { ref, unref, toRefs, computed, watch } = window.Vue;

export default {
  emits: ["lens"],
  props: {
    size: {
      type: Number,
      default: 400,
    },
    brushMode: {
      type: Number,
      default: 0,
    },
    rotation: {
      type: Number,
      default: 0,
      help: "Degree angle 0-360",
    },
    sampleSize: {
      type: Number,
      default: 1000,
      help: "Number of points to randomly process",
    },
    numberOfBins: {
      type: Number,
      default: 6,
      help: "Side bin count for 2D histogram (grid = numberOfBins * numberOfBins)",
    },
    showLens: {
      type: Boolean,
      default: true,
    },
    lensRadius: {
      type: Number,
      // Use unit cell units for lens radius
      default: 0.5,
    },
    componentLabels: {
      type: Array,
    },
    unrotatedComponentCoords: {
      type: Array,
    },
    unrotatedBinData: {
      type: Array,
    },
  },
  setup(props, { emit }) {
    const container = ref(null);
    const radRotationAngle = computed(() => props.rotation * Math.PI / 180);
    const bgImage = computed(() =>
      computeColorMapImage(props.size, props.brushMode)
    );
    const dataToDraw = computed(() =>
      ({
        data: rotateCoordinates(props.unrotatedBinData, unref(radRotationAngle)),
        components: rotateCoordinates(props.unrotatedComponentCoords, unref(radRotationAngle))
      })
    );
    const diameter = computed(() => Math.round(props.size * 2.4) / 3.1);
    const lensRadiusDisplayUnits = computed(() => props.lensRadius * unref(diameter) / 2);
    const xyOffset = computed(() => (props.size - unref(diameter)) * 0.5);
    const scaleGBC = computed(() =>
      d3.scaleLinear(
        [-1, 1],
        [unref(xyOffset), unref(xyOffset) + unref(diameter)]
      )
    );

    // Lens handling
    const lensLocation = ref([0, 0]);
    const lensState = {
      originLens: [0, 0],
      originEvent: [0, 0],
    };

    function onMousePress(e) {
      lensState.drag = true;
      lensState.originLens = [...unref(lensLocation)];
      lensState.originEvent = [e.clientX, e.clientY];
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseRelease);
    }

    function keepLensInside(xy) {
      const r = Math.sqrt(xy[0] * xy[0] + xy[1] * xy[1]);
      const maxR = unref(diameter) * 0.5;
      if (r > maxR) {
        const ratio = maxR / r;
        xy[0] *= ratio;
        xy[1] *= ratio;
      }
      return xy;
    }

    function onMouseMove(e) {
      let x = lensState.originLens[0] + e.clientX - lensState.originEvent[0];
      let y = lensState.originLens[1] + e.clientY - lensState.originEvent[1];

      // Keep x,y in circle
      const newLoc = [x, y];
      [x, y] = keepLensInside(newLoc);

      lensLocation.value = newLoc;

      // Emit the lens center in unit circle coordinates
      emit("lens", [x / unref(diameter) * 2,
                    y / unref(diameter) * 2]);
    }
    function onMouseRelease() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseRelease);
    }

    watch(
      () => props.size,
      () => {
        lensLocation.value = keepLensInside([...lensLocation.value]);
      }
    );

    const { componentLabels, lensRadius, showLens, size } = toRefs(props);
    return {
      bgImage,
      componentLabels,
      container,
      dataToDraw,
      lensLocation,
      lensRadius,
      lensRadiusDisplayUnits,
      onMousePress,
      scaleGBC,
      showLens,
      size,
    };
  },
  template: `
        <div ref="container">
          <svg :width="size" :height="size">
            <image :href="bgImage" x="0" y="0" :width="size" :height="size" />

            <g fill="#fff" stroke="black" stroke-opacity="0.5">
              <circle
                :key="'scatter-' + i"
                v-for="d, i in dataToDraw.data"
                :cx="scaleGBC(d[0])"
                :cy="scaleGBC(d[1])"
                r="2.5"
              />
            </g>

            <g fill="#C7D9E8" stroke="#333">
              <circle
                :key="'component-' + i"
                v-for="d, i in dataToDraw.components"
                :cx="scaleGBC(d[0] * 0.997)"
                :cy="scaleGBC(d[1] * 0.997)"
                r="6"
              />
            </g>

            <g font-size="30px" fill="#666" stroke="#111" stroke-opacity="1" opacity="1" style="user-select: none;">
              <text
                :key="'label-' + i"
                v-for="d, i in dataToDraw.components"
                :x="scaleGBC(d[0] * 0.997)"
                :y="scaleGBC(d[1] * 0.997)"
                :dx="d[0] < 0 ? '-1.40em' : '.35em'"
                :dy="d[1] < 0 ? '-.230em' : '.531em'"
              >
                {{ componentLabels[i] }}
              </text>
            </g>

            <circle
              v-if="showLens"
              :cx="0.5 * size + lensLocation[0]"
              :cy="0.5 * size + lensLocation[1]"
              :r="lensRadiusDisplayUnits"
              fill="rgba(255, 255, 255, 0.2)"
              opacity="0.5"
              stroke="red"
              stroke-width="10"
              stroke-opacity="0.9"
              @mousedown="onMousePress"
            />
          </svg>
        </div>
  `,
};
