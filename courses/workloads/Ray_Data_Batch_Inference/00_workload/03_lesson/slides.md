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


# Defining the Batch Inference Class

---

## Batch Inference Class
Many machine learning models are optimized for processing a batch of inputs at once. When working with a large dataset, there could be many batches of data. Instead of loading machine learning models repeatedly to run each batch of data, you want to spin up a number of actor processes that are **initialized once** with your model **and reused** to process multiple batches. 

To implement this, you can use the `map_batches` API with a "Callable" class method that implements:

- `__init__`: Initialize any expensive state.
- `__call__`: Perform the stateful transformation.

In this example, a lightweight sentence transformer model, **all-MiniLM-L6-v2** is used to generate embeddings of text data.

---

```python
# Create an Ray actor class to embed text using the SentenceTransformer model
class TextEmbedder:
    def __init__(self):
        # load a pretrained sentence transformer model
        model_name = "all-MiniLM-L6-v2"  # A popular, lightweight sentence transformer model
        self.model = SentenceTransformer(model_name) # automatically detects cuda, mps, cpu

    def __call__(self, batch: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        sentences = batch["text"] # use the "text" column
        batch['embedding'] = self.model.encode(sentences) # create embedding
        return batch

```