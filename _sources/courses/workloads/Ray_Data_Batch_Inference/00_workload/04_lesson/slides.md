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


# Creating a Data Batch and Calling the Model

---

## Create a batch data and call the model
Define a Ray Data map_batches function to embed text using the SentenceTransformer model. This function will be applied to each batch of data in the Ray Data dataset. It will take a batch of sentences, encode them into embeddings, and return the batch with the embeddings added.

Showcasing two options of to do batch inference based on if the ray cluster has have GPU nodes or if it has just CPU nodes. The second option also works on a local ray cluster on an Apple Silicon Mac with MPS.

# setting manually so that code works on ray clusters with both CPU or GPU workers, or on a local mac with MPS
worker_device = "cpu" # or "cuda" if you have a nvidia gpu on worker nodes
# batch_size should be set based on VRAM 
if worker_device == "cuda": # if you have a nvidia gpu on worker nodes
    # adjust batch_size based on the VRAM available on the GPU
    ds = ds.map_batches(TextEmbedder, num_gpus=1, concurrency=2, batch_size=64) # 2 nodes with 1 GPU each
else:
    ds = ds.map_batches(TextEmbedder, concurrency=2, batch_size=64) # either cpu or mps (on a mac)

---

### Deploying at scale
- The batch size for encoding can be adjusted based on the available memory and performance requirements.
- The `device` parameter ensures that the model runs on the correct device (CPU, GPU, or MPS).
- The `concurrency` parameter controls how many batches are processed in parallel. If there are 2 nodes with 1 GPU each or 1 node with 2 GPUs, then set concurrency = 2 and num_gpus=1.
- map_batches() is a lazy function and not executed until needed (example, using take or show).

Run inference on a batch of 128 rows. This will return a batch of 128 rows with the embeddings added to the caller's machine.

# Run inference on a batch of 128 rows for testing.
ds.take_batch(128)