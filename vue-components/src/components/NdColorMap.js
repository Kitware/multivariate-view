import { ref, unref, onMounted, computed, watch } from "Vue";
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

    function render() {
      if (!container.value) {
        return;
      }
      emit("render");

      const headers = unref(dataToProcess).header;
      const diameter = Math.round(props.size * 2.4) / 3.1;
      const xyOffset = (props.size - diameter) * 0.5;
      const scaleGBC = d3.scaleLinear([-1, 1], [xyOffset, xyOffset + diameter]);

      // Root SVG
      const svgColorSpace = d3
        .select(container.value)
        .append("svg")
        .attr("width", props.size)
        .attr("height", props.size);

      // Background colorMap
      svgColorSpace
        .append("image")
        .attr("xlink:href", unref(bgImage))
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", props.size)
        .attr("height", props.size);

      // Scatter points
      const scatterPoints = svgColorSpace.append("g");
      scatterPoints
        .append("svg:g")
        .selectAll("scatter-dots")
        .data(dataToDraw.value.q)
        .enter()
        .append("circle")
        .attr("cx", (d) => scaleGBC(d[0]))
        .attr("cy", (d) => scaleGBC(d[1]))
        .attr("r", "2.5")
        .style("fill", "#fff")
        .style("stroke", "black")
        .style("stroke-opacity", 0.5);

      // Components points
      const componentPoints = svgColorSpace.append("g");
      componentPoints
        .append("svg:g")
        .selectAll("scatter-dots")
        .data(unref(dataToDraw).components)
        .enter()
        .append("circle")
        .attr("cx", (d) => scaleGBC(d[0] * 0.997))
        .attr("cy", (d) => scaleGBC(d[1] * 0.997))
        .attr("r", "6")
        .style("fill", "#C7D9E8")
        .style("stroke", "#333");

      const labelComponentPoints = svgColorSpace.append("g");
      labelComponentPoints
        .append("svg:g")
        .selectAll("g")
        .data(unref(dataToDraw).components)
        .enter()
        .append("text")
        .attr("x", (d) => scaleGBC(d[0] * 0.997))
        .attr("y", (d) => scaleGBC(d[1] * 0.997))
        .attr("dx", (d) => (d[0] < 0 ? "-1.40em" : ".35em"))
        .attr("dy", (d) => (d[1] < 0 ? "-.230em" : ".531em"))
        .text((d, i) => headers[i])
        .style("font-size", "30px")
        .style("fill", "#666")
        .style("stroke", "#111")
        .style("stroke-opacity", 1)
        .style("opacity", 1);
    }

    onMounted(render);
    watch(() => [props.size, bgImage.value, dataToDraw.value], render);

    return {
      container,
    };
  },
  template: `
        <div ref="container"></div>`,
};
