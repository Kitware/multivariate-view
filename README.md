# MultivariateView

![full](https://github.com/Kitware/multivariate-view/assets/9558430/3393742f-cb6f-4c1a-b67c-bf189f04f783)

A multivariate/multimodal volume visualizer!

This [RadVolViz](https://doi.org/10.1109/TVCG.2023.3263856)-inspired prototype utilizes [trame](https://kitware.github.io/trame/) and [VTK](https://vtk.org/) to render multi-channel volumetric datasets.

# Install and Run

To install, first ensure you are in an environment using Python3.10 or newer, and then run the following command:

```bash
pip install multivariate-view
```

Next, run `multivariate-view`, or `mv-view`, to start the application. If no `--data` path is provided, it will
automatically download and load the example dataset pictured above.

## Development build

```bash
cd vue-components
npm i
npm run build
cd -
pip install -U pip
pip install -e .
```

# Example Data
The example dataset pictured above is from the reconstruction of an X-ray fluorescence tomography of a mixed ionic-electronic conductor (MIEC) from the following article:

*Ge, M., Huang, X., Yan, H. et al. Three-dimensional imaging of grain boundaries via quantitative fluorescence X-ray tomography analysis. Commun Mater 3, 37 (2022). https://doi.org/10.1038/s43246-022-00259-x*

This example dataset is downloaded automatically and loaded if the application is started without providing a `--data` path. Utilizing the lens in MultivariateView produces visualizations of the following phases:

## CGO Phase (ionic conductor)
![cgo](https://github.com/Kitware/multivariate-view/assets/9558430/10632b37-e893-4a07-8468-da6fc6bfb513)

## CFO Phase (electronic conductor)
![cfo](https://github.com/Kitware/multivariate-view/assets/9558430/d7806e34-a13c-4608-8100-9c0df88d5b40)

## EP2 Phase (emergent phase)
![ep2](https://github.com/Kitware/multivariate-view/assets/9558430/bc48c45c-0ecd-4853-86c3-d82779c28e44)

*Note: the EP1 phase from the paper is comprised of fewer voxels and is more difficult to visualize without data filters*

# Data Loading

Two of the easiest formats to use are HDF5 and NPZ. For both of these file types, each channel of the volume should have its own dataset at the top level, and each dataset must be identical in shape and datatype. There should be no other datasets present.

If the application is started with `multivariate-view --data /path/to/data.h5`, then all root level datasets will be loaded automatically and visualized.
