#serve_llama.py
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