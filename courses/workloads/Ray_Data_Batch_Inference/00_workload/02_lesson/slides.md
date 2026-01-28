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


# Loading a Dataset

---

## Load a dataset
Load a dataset from hugging face or local and convert into Ray Dataset. A Ray cluster automatically initialized on local or on Anyscale platform. You can also use **ray.init()** To explicitly create or connect to an existing Ray cluster.

https://docs.ray.io/en/latest/ray-core/api/doc/ray.init.html#ray.init

# load a Hugging Face dataset
hf_dataset = load_dataset("cardiffnlp/tweet_eval", "sentiment", split="train")
# Convert the Hugging Face dataset to a Ray Dataset
ds = ray.data.from_huggingface(hf_dataset).repartition(2) # repartition to 2 blocks for parallel processing. Not necessary if already partitioned due to the size of the dataset.

---

```python
# dataset metadata
print(ds)

# show the first 10 rows
# Each row has "text" and "label"
ds.show(10)
```