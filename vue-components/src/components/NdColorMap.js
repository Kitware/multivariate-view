import { ref, unref, toRefs, computed } from "Vue";
import * as d3 from "d3";

import { computeColorMapImage } from "../utils/colors";
import { computeGBC, getData, dataTopologyReduction } from "../utils/compute";

export default {
  emits: ["click", "change"],
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
  },
  setup(props, { emit }) {
    emit("created");
    const container = ref(null);
    const radRotationAngle = computed(() => props.rotation / 57.32);
    const dataToProcess = computed(() => getData(props.sampleSize));
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

    const { size } = toRefs(props);
    return {
      container,
      size,
      bgImage,
      dataToDraw,
      scaleGBC,
      dataToProcess,
    };
  },
  template: `
        <div ref="container">
          <svg :width="size" :height="size">
            <image :href="bgImage" x="0" y="0" :width="size" :height="size" />

            <g fill="#fff" stroke="black" stroke-opacity="0.5">
              <circle 
                :key="i" 
                v-for="d, i in dataToDraw.q"
                :cx="scaleGBC(d[0])"
                :cy="scaleGBC(d[1])"
                r="2.5"
              />
            </g>

            <g fill="#C7D9E8" stroke="#333">
              <circle 
                :key="i" 
                v-for="d, i in dataToDraw.components"
                :cx="scaleGBC(d[0] * 0.997)"
                :cy="scaleGBC(d[1] * 0.997)"
                r="6"
              />
            </g>

            <g font-size="30px" fill="#666" stroke="#111" stroke-opacity="1" opacity="1" style="user-select: none;">
              <text 
                :key="i" 
                v-for="d, i in dataToDraw.components"
                :x="scaleGBC(d[0] * 0.997)"
                :y="scaleGBC(d[1] * 0.997)"
                :dx="d[0] < 0 ? '-1.40em' : '.35em'"
                :dy="d[1] < 0 ? '-.230em' : '.531em'"
              >
                {{ dataToProcess.header[i] }}
              </text>
            </g>

          </svg>
        </div>
  `,
};
