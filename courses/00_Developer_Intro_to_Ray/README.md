# Introduction to Ray: Developer

## Course Welcome and Overview

This course provides a comprehensive introduction to Ray with hands-on examples and practical use cases, designed to help developers quickly master distributed computing and scale their Python applications from development to production.

## 📋 Notebook Compute Requirements Legend

Throughout this course, you'll see these symbols in each notebook to indicate the recommended compute environment:

| Symbol | Meaning | Description |
|--------|---------|-------------|
| 💻 | **Launch Locally** | Whether the notebook can run efficiently on your laptop/local machine |
| 🚀 | **Launch on Cloud** | Benefits from GPU acceleration, cloud recommended |

**Note**: For 🚀 notebooks, we recommend using [Anyscale](http://console.anyscale.com/register) with a Ray cluster that has GPUs.

## Why Ray?

Today's ML workloads are increasingly compute-intensive. As convenient as they are, single-node development environments such as your laptop cannot scale to meet these demands.

Ray is a unified way to scale Python and AI applications from a laptop to a cluster.

With Ray, you can seamlessly scale the same code from a laptop to a cluster. Ray is designed to be general-purpose, meaning that it can performantly run any kind of workload. If your application is written in Python, you can scale it with Ray, no other infrastructure required.

## Setting Up a Local Ray server using Jupyter Notebook

### Prerequisites

This guide helps you set up a local Jupyter Notebook environment using **Conda** and install **Ray** for parallel and distributed computing.

---

## ✅ 1. Install Conda

If you don't already have Conda, you can install **Miniforge** or **Miniconda** on macOS with Apple Silicon (ARM-based M1/M2/M3 chips):

### 🧩 Miniforge Installation (It depends on your OS. In this case, we use ARM Macs)

Open your terminal and run:

```bash
curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash Miniforge3-MacOSX-arm64.sh
```

Follow the prompts to accept the license, choose the install location, and initialize Miniforge.

Then restart your terminal or run:

```bash
source ~/.zprofile  # or ~/.bash_profile if you're using bash
```

Verify installation:

```bash
conda --version
```

Alternatively, download from:
- Miniforge: https://github.com/conda-forge/miniforge#miniforge3
- Miniconda (ARM builds available): https://docs.conda.io/en/latest/miniconda.html

---

## 🛠️ 2. Create a New Conda Environment

```bash
conda create -n ray-jupyter python=3.11 -y
```

> Ray supports Python 3.7 to 3.11 (Python 3.12 is not supported as of Ray 2.20).

---

## ▶️ 3. Activate the Environment

```bash
conda activate ray-jupyter
```

---

## 📦 4. Install UV and Dependencies

First, install UV:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the dependencies using the lock file:
```bash
uv pip install -r requirements.lock
```

This will install all dependencies with their exact versions as specified in the lock file, ensuring reproducible builds across different environments.

### Managing Dependencies

When you need to add new dependencies:

1. Add the new package to `requirements.txt`
2. Generate a new lock file:
   ```bash
   uv pip compile requirements.txt -o requirements.lock
   ```
3. Install using the updated lock file:
   ```bash
   uv pip install -r requirements.lock
   ```

This workflow ensures that all dependencies are properly tracked and versions are locked for reproducibility.

---

## 🖥️ 5. (Optional but Recommended) Add Your Conda Environment to Jupyter

To use your `ray-jupyter` environment as a kernel in Jupyter Notebook, run:

```bash
pip install ipykernel
python -m ipykernel install --user --name ray-jupyter --display-name "Python (ray-jupyter)"
```

This will make your environment available as a selectable kernel in Jupyter.

---

## 🚀 6. Launch Jupyter Notebook

```bash
jupyter notebook
```

This will open a browser window for you to create and manage notebooks.

---

## ✅ 7. Verify Ray Installation with a Simple Example

After launching Jupyter Notebook and selecting your `ray-jupyter` kernel, create a new notebook and run the following code to verify Ray is working:

```python
import ray
ray.init()

@ray.remote
def hello_world():
    return "Ray is working!"

result = ray.get(hello_world.remote())
print(result)
```

You should see the output:

```
2025-06-10 10:41:31,774	INFO worker.py:1879 -- Started a local Ray instance. View the dashboard at http://127.0.0.1:8265 

Ray is working!
```

If you see this message, Ray is set up correctly! You can now view the local Ray Dashboard at: http://127.0.0.1:8265

---

## 🧹 8. Shut Down and Clean Up

To stop the Jupyter Notebook server:

- Press `Ctrl+C` in the terminal

To deactivate the environment:

```bash
conda deactivate
```

To remove the environment completely:

```bash
conda remove --name ray-jupyter --all
```

---

You're now ready to start developing Ray applications in a local Jupyter Notebook environment!

