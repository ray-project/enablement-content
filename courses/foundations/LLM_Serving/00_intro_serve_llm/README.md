# Introduction to Ray Serve LLM: Foundations of Large Language Model Serving

© 2025, Anyscale. All Rights Reserved


💻 **Launch Locally**: You can run this notebook locally, but performance will be reduced.

🚀 **Launch on Cloud**: A Ray Cluster with GPUs (Click [here](http://console.anyscale.com/register) to easily start a Ray cluster on Anyscale) is recommended to run this notebook.


This notebook provides a comprehensive introduction to serving Large Language Models (LLMs) with Ray Serve LLM. We'll explore the fundamentals of LLM serving, understand the challenges, and learn how Ray Serve LLM provides production-grade solutions for deploying LLMs at scale.

<div class="alert alert-block alert-info">
<b> Here is the roadmap for this notebook:</b>
<ul>
    <li>What is LLM Serving?</li>
    <li>Challenges in LLM Serving</li>
    <li>Ray Serve LLM Architecture</li>
    <li>Key Concepts and Optimizations</li>
    <li>Getting Started with Ray Serve LLM</li>
    <li>Your First LLM Deployment</li>
</ul>
</div>


## What is LLM Serving?

Large Language Model (LLM) serving refers to the process of deploying trained language models to production environments where they can handle user requests and generate responses in real-time. This is fundamentally different from training models - serving focuses on making models available, scalable, and performant for end users.

### The LLM Text Generation Process

LLMs operate as **next-token predictors**. Here's how they work:

1. **Tokenization**: Input text is converted into tokens (words, subwords, or characters)
2. **Processing**: The model processes these tokens to understand context
3. **Generation**: The model generates output one token at a time
4. **Completion**: Generation stops when reaching stopping criteria or maximum length

<img src="https://anyscale-materials.s3.us-west-2.amazonaws.com/public-images/ray-serve-llm/diagrams/LLM-text-generation.png" width="800">

### Two Phases of LLM Inference

LLM inference operates through two distinct phases that determine performance characteristics:

#### Prefill Phase
- The model encodes **all input tokens simultaneously**
- High efficiency through parallelized computations
- Maximizes GPU utilization
- Precomputes and caches key-value (KV) vectors as intermediate token representations

#### Decode Phase
- The model generates tokens **sequentially** using the key-value cache (KV cache)
- Each token depends on all previous tokens
- Limited by memory bandwidth rather than compute capacity
- Underutilizes GPU resources compared to prefill phase

|<img src="https://cdn-uploads.huggingface.co/production/uploads/65263bfb3177c2a794997821/BGKtYLqM1X9o72oc9NW8Y.png" width="70%" loading="lazy">|
|:--|
|prefill: parallel processing of prompt tokens, decode: sequential processing of single output tokens.|

## Key Concepts and Optimizations

These key concepts will help you design an LLM serving pipeline that meets your service level objectives (SLOs).

### 1. Key-Value (KV) Caching

KV caching eliminates redundant computations during text generation:

**Without KV Cache**:
- Recalculate keys and values for entire sequence each time
- Extremely inefficient for long sequences

**With KV Cache**:
- Cache computed K and V values for all previous tokens
- Only compute K and V for the new token
- Reuse cached values for context

### 2. Continuous Batching

Continuous batching optimizes throughput by eliminating GPU idle time:

**Vanilla Static Batching**:
- Wait for all requests in batch to complete
- Creates idle time when requests finish at different rates
- Underutilizes GPU resources

### 3. Model parallelization or alternatives

Large LLMs (>70B) might provides more accurate answers but might not fit entirely on one GPU or one node. You can parallelize your model accross multiple GPUs or nodes to virtually increase your memory resources at the cost of some latency due to communication overhead.

You can also use alternative options such as quantization, distillation, or multi-LoRA adapters to

### 4. Context Window Considerations

The context window defines the maximum tokens a model can process:

| Context Length | Use Cases | Memory Impact |
|----------------|-----------|---------------|
| **4K-8K tokens** | Q&A, simple chat | Low KV cache requirements |
| **32K-128K tokens** | Document analysis, summarization | Moderate memory usage |
| **128K+ tokens** | Multi-step agents, complex reasoning | High memory requirements |

A large context window might provide more accurate answers but also increase the memory pressure and how many requests can be processed concurrently.

|<img src="https://images.ctfassets.net/xjan103pcp94/1LJioEsEdQQpDCxYNWirU6/82b9fbfc5b78b10c1d4508b60e72fdcf/cb_02_diagram-static-batching.png" width="70%" loading="lazy">|
|:--|
|Completing four sequences using static batching. On the first iteration (left), each sequence generates one token (blue) from the prompt tokens (yellow). After several iterations (right), the completed sequences each have different sizes because each emits their end-of-sequence-token (red) at different iterations. Even though sequence 3 finished after two iterations, static batching means that the GPU will be underutilized until the last sequence in the batch finishes generation (in this example, sequence 2 after six iterations).|

**Continuous Batching**:
- Immediately replace completed requests with new ones
- Maintains constant GPU utilization
- Increases concurrent user capacity

|<img src="https://images.ctfassets.net/xjan103pcp94/744TAv4dJIQqeHcEaz5lko/b823cc2d92bbb0d82eb252901e1dce6d/cb_03_diagram-continuous-batching.png" width="70%" loading="lazy">|
|:--|
|Completing seven sequences using continuous batching. Left shows the batch after a single iteration, right shows the batch after several iterations. Once a sequence emits an end-of-sequence token, we insert a new sequence in its place (i.e. sequences S5, S6, and S7). This achieves higher GPU utilization since the GPU does not wait for all sequences to complete before starting a new one.|

## Challenges in LLM Serving

Serving LLMs in production presents several unique challenges that traditional model serving doesn't face. Let's explore these challenges and understand why they matter.

### 1. Memory Management

Deploying LLMs is a **memory-intensive** task. A non-exhaustive list of memory constraints are:
| Component | Description | Memory Impact |
|-----------|-------------|---------------|
| **Model Weights** | Model parameters | 7B model ≈ 14GB (FP16) |
| **KV Cache** | Token representations | Depends on context length |
| **Activations** | Temporary buffers | Varies with batch size |

**Example**: A 7B parameter model in FP16 precision requires approximately 14GB just for the model weights, not including the KV cache or activations.

<img src="https://anyscale-materials.s3.us-west-2.amazonaws.com/public-images/ray-serve-llm/diagrams/gpu-memory.png" width="800">

You can distribute your deployment on multiple GPUs or nodes. For example you could split the model accross multiple GPUs on a single node or accross multiple GPUs on multiple nodes.  



See examples below for examples of different types of deployment:
- Single node, single GPU: [Deploy a small-sized LLM](https://docs.ray.io/en/latest/serve/tutorials/deployment-serve-llm/small-size-llm/README.html)
- Single node, multiple GPU with tensor parallelism: [Deploy a medium-sized LLM](https://docs.ray.io/en/latest/serve/tutorials/deployment-serve-llm/medium-size-llm/README.html)
- Multiple nodes, multiple GPU with tensor and pipeline parallelism: [Deploy a large-sized LLM](https://docs.ray.io/en/latest/serve/tutorials/deployment-serve-llm/large-size-llm/README.html)

### 2. Latency Requirements

Users expect **fast, interactive responses** from LLM applications:

- **Time to First Token (TTFT)**: How long until the first token appears
- **Time Per Output Token (TPOT)**: How long between subsequent tokens
- **Total Response Time**: End-to-end latency

### 3. Scalability Demands

Production traffic is **unpredictable and bursty**:
- Traffic spikes during peak hours
- Need to scale up quickly during high demand
- Scale down to zero during idle periods to save costs

### 4. Cost Optimization

GPUs represent **significant infrastructure costs**:
- Maximize hardware utilization
- Scale to zero during idle periods
- Choose appropriate GPU types for your workload

### Why not Kubernetes ?

You could either use Ray Serve or Kubernetes microservices to solve the challenges above. They aree not mutually exclusive, as Ray Serve can run on Kubernetes. The differences are mostly about who does the orchestration and how much abstraction you want from the inference pipeline.

**Ray Serve LLM**

* Python-native orchestration (routing, batching, streaming).
* Built-in autoscaling, backpressure, health checks or [LLM-optimized routing](https://docs.ray.io/en/latest/serve/llm/prefix-aware-request-router.html).
* Actor-based sharding across nodes/GPUs.
* Easy multi-model serving behind one endpoint.

**Kubernetes**

* Pod = unit per node; multi-node model parallelism needs extra controllers/operators.
* Batching/routing/backpressure are DIY (app or sidecars).
* Strong platform features (networking, security, quotas), but inference control isn’t built-in.


## Ray Serve LLM + Anyscale Architecture

Here is a diagram of how Ray Serve LLM + Anyscale provides a production-grade solution to your LLM deployment:

<img src="https://anyscale-materials.s3.us-west-2.amazonaws.com/public-images/ray-serve-llm/diagrams/anyscale-serve-vllm.png" width="800">

**Notes:**

- The above shows only one replica per model, but Ray Serve can easily scale to deploying multiple replicas.
- A model's single replica also supports multiple LoRA adapters that can be configured on the Model 1 LLM Server.

Ray Serve LLM + Anyscale provides a production-grade solution through three integrated components:

### 1. Ray Serve for Orchestration

Ray Serve handles the **orchestration and scaling** of your LLM deployment:

- **Automatic scaling**: Adds/removes model replicas based on traffic
- **Load balancing**: Distributes requests across available replicas
- **Unified multi-model deployment**: Deploy and manage multiple models
- **OpenAI-compatible API**: Drop-in replacement for OpenAI clients

Here is a diagram of how Ray Serve LLM interact with a client's request

<img src="https://anyscale-materials.s3.us-west-2.amazonaws.com/ray-serve-deep-dive/Ray+Serve+LLM.png" width="800">

### 2. vLLM as the inference engine

LLM inference is a non-trivial problem that requires tuning low-level hardware use and high-level algorithms. An **inference engine** abstracts this complexity and optimizes model execution. Ray Serve LLM natively integrates **vLLM** as its inference engine for several reasons:

- **Fast GPU computation** with CUDA kernels specifically optimized for LLM inference.
- **Continuous batching**: Continuously schedule tokens to be processed to maximize GPU utilization.
- **Smart memory use**: Optimize memory usage with state-of-the-art algorithms like PagedAttention

Ray Serve LLM gives you high flexibility on how to configure your vLLM engine (more on that later).

### 3. Anyscale for Infrastructure

Anyscale provides **managed infrastructure** and enterprise features:

- **Managed infrastructure**: Optimized Ray clusters in your cloud
- **Cost optimization**: Pay-as-you-go, scale-to-zero
- **Enterprise security**: VPC, SSO, audit logs
- **Seamless scaling**: Handle traffic spikes automatically

## Getting Started with Ray Serve LLM

Now that we understand the fundamentals, let's see how to get started with Ray Serve LLM. The process involves three main steps:

1. **Configure** your LLM deployment
2. **Deploy** the service
3. **Query** the deployed model

### Step 1: Configuration

Let's create a simple configuration:


```python
#serve_llama.py
import os
from ray.serve.llm import LLMConfig, build_openai_app

llm_config = LLMConfig(
    # Model loading configuration
    model_loading_config=dict(
        model_id="my-llama", # custom name for the model
        model_source="unsloth/Meta-Llama-3.1-8B-Instruct", # huggingface model repo
    ),
    accelerator_type="L4", # device to use (picked from your ray cluster)
    ## Optional: configure Ray Serve autoscaling
    deployment_config=dict(
        autoscaling_config=dict(
            min_replicas=1, # keep at least 1 replica up to avoid cold starts
            max_replicas=2, # no more than 2 replicas to control cost
        )
    ),
    # Configure your vLLM engine. Follow the same API as vLLM
    # https://docs.vllm.ai/en/stable/configuration/engine_args.html
    engine_kwargs=dict(max_model_len=8192),
)

app = build_openai_app({"llm_configs": [llm_config]})
```

### Step 2: Deployment

Deployment can be done locally or on Anyscale Services:

**Local Deployment**:


```python
!serve run serve_llama:app --non-blocking
```

**Anyscale Services**:

To deploy your LLM with Anyscale Service, configure your cloud and compute configuration and point to your LLM configuration:
```yaml
# service.yaml
name: deploy-llama-3-8b
image_uri: anyscale/ray-llm:2.49.0-py311-cu128 # Anyscale Ray Serve LLM image. Use `containerfile: ./Dockerfile` to use a custom Dockerfile.
compute_config:
  auto_select_worker_config: true 
working_dir: .
cloud:
applications:
  # Point to your app in your Python module
  - import_path: serve_llama:app
```

Deploy your service:


```python
!anyscale service deploy -f service.yaml
```

### Step 3: Querying

Once deployed, you can use the OpenAI Python client with `base_url` pointing to your Ray Serve endpoint.


```python
from openai import OpenAI

# because deployed locally, we use localhost:8000 and a dummy placeholder API key
client = OpenAI(base_url="http://localhost:8000", api_key="FAKE_KEY") # Or use your Anyscale Service endpoint and API key   

response = client.chat.completions.create(
    model="my-llama",
    messages=[{"role": "user", "content": "Hello! What's the capital of France ?"}],
    stream=True
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
```

## Key Takeaways

In this module, we've covered the essential foundations of LLM serving with Ray Serve LLM:

1. **Understanding LLM Serving**: How LLMs generate text through prefill and decode phases
2. **Challenges**: Memory management, latency, scalability, and cost optimization
3. **Ray Serve LLM Architecture**: Three-component solution with Ray Serve, vLLM, and Anyscale
4. **Key Optimizations**: KV caching, paged attention, and continuous batching
5. **Getting Started**: Simple configuration and deployment process

### Next Steps

In the next modules, we'll dive deeper into:
- **Hands-on deployment** of small, medium, and large LLMs
- **Advanced configurations** and optimizations
- **Monitoring and observability** for production deployments
- **Best practices** for production LLM serving

### Resources

- [Ray Serve LLM with Anyscale Documentation](https://docs.anyscale.com/llm/serving)
- [Deploy LLM templates](https://console.anyscale.com/template-preview/deployment-serve-llm?utm_source=anyscale_docs&utm_medium=docs&utm_campaign=examples_page&utm_content=deployment-serve-llm?utm_source=anyscale&utm_medium=docs&utm_campaign=examples_page&utm_content=deployment-serve-llm)
- [Ray Serve LLM Documentation](https://docs.ray.io/en/latest/serve/llm/index.html)
- [vLLM Documentation](https://docs.vllm.ai/)

Ready to start serving LLMs with Ray? Let's move on to the next module!

