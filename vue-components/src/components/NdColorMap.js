import * as d3 from "d3";
import { computeColorMapImage } from "../utils/colors";
import { computeGBC, dataTopologyReduction } from "../utils/compute";

const { ref, unref, toRefs, computed, watch } = window.Vue;

export default {
  emits: ["lense"],
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
    showLense: {
      type: Boolean,
      default: true,
    },
    lenseRadius: {
      type: Number,
      default: 10,
    },
    data: {
      type: Array,
    },
    components: {
      type: Array,
    },
  },
  setup(props, { emit }) {
    const container = ref(null);
    const radRotationAngle = computed(() => props.rotation / 57.32);
    const dataToProcess = computed(() => ({
      header: props.components,
      data: props.data.slice(0, props.sampleSize),
    }));
    const gbcData = computed(() =>
      computeGBC(unref(dataToProcess).data, unref(radRotationAngle))
    );
    const dataToDraw = computed(() =>
      dataTopologyReduction(unref(gbcData), props.numberOfBins)
    );
    const bgImage = computed(() =>
      computeColorMapImage(props.size, props.brushMode)
    );
    const diameter = computed(() => Math.round(props.size * 2.4) / 3.1);
    const xyOffset = computed(() => (props.size - unref(diameter)) * 0.5);
    const scaleGBC = computed(() =>
      d3.scaleLinear(
        [-1, 1],
        [unref(xyOffset), unref(xyOffset) + unref(diameter)]
      )
    );

    // Lense handling
    const lenseLocation = ref([0, 0]);
    const lenseState = {
      originLense: [0, 0],
      originEvent: [0, 0],
    };

    function onMousePress(e) {
      lenseState.drag = true;
      lenseState.originLense = [...unref(lenseLocation)];
      lenseState.originEvent = [e.clientX, e.clientY];
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseRelease);
    }

    function keepLenseInside(xy) {
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
      let x = lenseState.originLense[0] + e.clientX - lenseState.originEvent[0];
      let y = lenseState.originLense[1] + e.clientY - lenseState.originEvent[1];

      // Keep x,y in circle
      const newLoc = [x, y];
      keepLenseInside(newLoc);

      lenseLocation.value = newLoc;
      emit("lense", { x, y, r: unref(lenseRadius), s: props.size });
    }
    function onMouseRelease() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseRelease);
    }

    watch(
      () => props.size,
      () => {
        lenseLocation.value = keepLenseInside([...lenseLocation.value]);
      }
    );

    const { size, showLense, lenseRadius } = toRefs(props);
    return {
      container,
      size,
      bgImage,
      dataToDraw,
      scaleGBC,
      dataToProcess,
      showLense,
      lenseRadius,
      lenseLocation,
      onMousePress,
    };
  },
  template: `
        <div ref="container">
          <svg :width="size" :height="size">
            <image :href="bgImage" x="0" y="0" :width="size" :height="size" />

            <g fill="#fff" stroke="black" stroke-opacity="0.5">
              <circle 
                :key="'scatter-' + i" 
                v-for="d, i in dataToDraw.q"
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
                {{ dataToProcess.header[i] }}
              </text>
            </g>

            <circle
              v-if="showLense"
              :cx="0.5 * size + lenseLocation[0]"
              :cy="0.5 * size + lenseLocation[1]"
              :r="lenseRadius"
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
