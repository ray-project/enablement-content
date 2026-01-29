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


# Shutdown and Summary

---

### Shutdown the Ray Serve instances and Ray Cluster

# stop ray serve
serve.shutdown()  # Shutdown Ray Serve when done, ray cluster will still be running

ray.shutdown()  # Shutdown Ray cluster

---

### Summary
In this notebook, we deployed a sentiment analysis model from Hugging Face using Ray Serve and FastAPI. Using *num_replicas* we scaled the number of instances of the model. There are many more options to autoscale to increase the replicas when the traffic is high and downscale to zero when there is no traffic.