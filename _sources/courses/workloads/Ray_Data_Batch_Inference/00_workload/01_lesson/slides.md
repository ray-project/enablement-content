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

![Architecture Diagram](https://lz-public-demo.s3.us-east-1.amazonaws.com/anyscale101/01_examples/01_Ray_Data_batch_inf_arch.svg?sanitize=true)

---

### Import Libraries

import ray
import torch
from typing import Dict
import numpy as np

from sentence_transformers import SentenceTransformer # huggingface sentence transformers
from datasets import load_dataset # huggingface datasets