# serve_llama_3_1_70b.py
from ray.serve.llm import LLMConfig, build_openai_app
import os

llm_config = LLMConfig(
    model_loading_config=dict(
        model_id="my-llama-3.1-70b",
        # Or unsloth/Meta-Llama-3.1-70B-Instruct for an ungated model
        model_source="meta-llama/Llama-3.1-70B-Instruct",
    ),
    deployment_config=dict(
        autoscaling_config=dict(
            min_replicas=1,
            max_replicas=4,
        )
    ),
    accelerator_type="L40S", # Or with similar VRAM like "A100-40G"
    # Type `export HF_TOKEN=<YOUR-HUGGINGFACE-TOKEN>` in a terminal
    runtime_env=dict(env_vars={"HF_TOKEN": os.environ.get("HF_TOKEN")}),
    engine_kwargs=dict(
        max_model_len=32768, # See model's Hugging Face card for max context length
        # Split weights among 8 GPUs in the node
        tensor_parallel_size=8,
    ),
    log_engine_metrics=True,
)

app = build_openai_app({"llm_configs": [llm_config]})