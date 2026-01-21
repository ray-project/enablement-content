# Data Processing and ML examples with Ray

This folder consists of notebooks with examples targeted towards Machine Learning beginners learning Ray libraries. These examples cover:

* [Batch inference with Ray Data](01_Ray_Data_batch_inference.ipynb)
This notebook shows how to use Ray Data with a ML model to generate batch embeddings.

* [Data processing with Ray Data](02_Ray_Data_data_processing.ipynb) 
Examples on how to preprocess data with Ray data.

* [Online serving with Ray Serve](03_Ray_Serve_online_serving.ipynb)
Example to showcase an online model inference service with Ray Serve.

* [Distributed training with Ray Train, PyTorch and HuggingFace](04_Ray_Train_distributed_training.ipynb)
This notebook shows distributed training of a bert model with Ray Train.

### Distributed training with Ray Train, PyTorch and HuggingFace
(super simple train a bert model)

## Installation
``` bash
mamba create -n ray-examples python=3.12
```

* Add the new package to `requirements.txt`
* Generate a new lock file:
``` bash
uv pip compile requirements.txt -o requirements.lock
```
* Install using the updated lock file:
``` bash
uv pip install -r requirements.lock
```

This workflow ensures that all dependencies are properly tracked and versions are locked for reproducibility. For more details on initial setup please see `../00_Developer_Intro_to_Ray/README.md`

```


