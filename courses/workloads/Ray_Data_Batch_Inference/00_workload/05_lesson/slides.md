---
theme: seriph
background: /slides_background.png
class: text-center
drawings:
    persist: 
# slide transition: https://sli.dev/guide/animations.html#slide-transitions
# transition: fade
# enable MDC Syntax: https://sli.dev/features/mdc
mdc: true
# duration of the presentation
duration: 15min
addons:
    - fancy-arrow
    - slidev-addon-tldraw
    - slidev-component-spotlight
    - slidev-component-poll
    - slidev-addon-typst
---


# Running inference on the entire dataset

---

## Run inference on the entire dataset
Execute and materialize this dataset into object store memory. This operation will trigger execution of the lazy transformations performed on this dataset. The embedding model 'TextEmbedder' in map_batches() is called on the entire dataset.

# Run inference on the entire dataset
# Note that this does not mutate the original Dataset.
materialized_ds = ds.materialize()

# metadata after inference
print('** Original dataset:', ds)
print('\n** Materialized dataset:', materialized_ds)

# Show a few rows of the materialized dataset with embeddings
materialized_ds.show(3)

---

### Out of memory errors
GPU (or MPS or CPU) memory has to keep the machine learning model and the batch of data in memory during the inference. If the batch_size is too large, it can run out of memory and throw out of memory errors. In that case, reduce the batch_size.

### Shutdown Ray cluster

# avoids collisons with other notebooks running ray jobs on the same machine
ray.shutdown()

---

### Summary
This notebook demonstrates how to perform efficient batch inference on large datasets using Ray Data. It walks through loading a public dataset from Hugging Face, converting it into a Ray Dataset, and defining a callable class to load and apply a machine learning model (SentenceTransformer) for embedding text. The notebook shows how to use Ray Data’s `map_batches` API to process data in parallel batches, leveraging available CPUs or GPUs for high-throughput inference. It also covers best practices for scaling, handling memory constraints, and summarizes how Ray Data enables scalable, distributed batch inference for modern ML workflows.

---

```python

```