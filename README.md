# MultivariateView

![image](https://github.com/Kitware/multivariate-view/assets/9558430/a3bc8f29-5544-42b9-8f55-5c326318b803)

A multivariate/multimodal volume visualizer!

# Install and Run

To install, first ensure you are in an environment using Python3.10 or newer, and then run the following command:

```bash
pip install multivariate-view
```

Next, run `multivariate-view`, or `mv-view`, to start the application. If no `--data` path is provided, it will
automatically download and load the example dataset pictured above.

# Example Data
The example dataset pictured above is from the reconstruction of an X-ray fluorescence tomography of a mixed ionic-electronic conductor (MIEC) from the following article:

*Ge, M., Huang, X., Yan, H. et al. Three-dimensional imaging of grain boundaries via quantitative fluorescence X-ray tomography analysis. Commun Mater 3, 37 (2022). https://doi.org/10.1038/s43246-022-00259-x*

This example dataset is downloaded automatically and loaded if the application is started without providing a `--data` path. Utilizing the lens in MultivariateView produces visualizations of the following phases:

## CGO Phase (ionic conductor)
![cgo](https://github.com/Kitware/multivariate-view/assets/9558430/346df5f8-08c3-4248-a8db-65fefe5ac3bd)

## CFO Phase (electronic conductor)
![cfo](https://github.com/Kitware/multivariate-view/assets/9558430/68b96c7b-a4e1-49ce-a713-5ff7dd3f3b43)

## EP2 Phase (emergent phase)
![ep2](https://github.com/Kitware/multivariate-view/assets/9558430/228d87af-0e1b-4b6d-929e-3253a82d90e5)

*Note: the EP1 phase from the paper is comprised of fewer voxels and is more difficult to visualize without data filters*
