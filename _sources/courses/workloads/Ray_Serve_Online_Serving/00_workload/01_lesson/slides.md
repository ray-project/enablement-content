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


# Architecture Overview

---

## Architecture

### Import libraries
In addition to ray and serve, we also import FastAPI to create webservice and Hugging Face transformers to download ML models.

# Import ray serve and FastAPI libraries
import ray
from ray import serve
from fastapi import FastAPI

# library for pre-trained models
from transformers import pipeline

---

![Architecture Diagram](https://lz-public-demo.s3.us-east-1.amazonaws.com/anyscale101/01_examples/03_Ray_Serve_architecture.svg?sanitize=true)