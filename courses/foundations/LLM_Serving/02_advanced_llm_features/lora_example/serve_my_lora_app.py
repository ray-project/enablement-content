import os
from ray.serve.llm import LLMConfig, build_openai_app

# Configure LLM with LoRA support
llm_config = LLMConfig(
    model_loading_config=dict(
        model_id="my-llama",
        # Make sure your huggingface token has access/authorization
        # Go to https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct and request access otherwise
        # Or switch to the unsloth/ version for an ungated LLama 
        model_source="meta-llama/Llama-3.1-8B-Instruct" # Base model
    ),
    accelerator_type="L4",
    # LoRA configuration
    lora_config=dict(
        dynamic_lora_loading_path="s3://llm-docs-aydin/1-5-multi-lora/lora_checkpoints/",  # Your S3/GCS path
        max_num_adapters_per_replica=3  # Limit adapters per replica
    ),
    runtime_env=dict(
        env_vars={
            "HF_TOKEN": os.environ.get("HF_TOKEN"), # Set your token beforehand: export HF_TOKEN=<YOUR-HUGGINGFACE-TOKEN>
            "AWS_REGION": "us-west-2"  # Your AWS region
        }
    ),
    engine_kwargs=dict(
        max_model_len=8192,
        # Enable LoRA support
        enable_lora=True,
        max_lora_rank=32,  # Maximum LoRA rank. Set to the largest rank you plan to use.
        max_loras=3,  # Must match max_num_adapters_per_replica
    ),
)

app = build_openai_app({"llm_configs": [llm_config]})