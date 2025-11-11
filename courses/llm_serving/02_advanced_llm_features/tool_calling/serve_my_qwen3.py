# serve_my_qwen3.py
from ray.serve.llm import LLMConfig, build_openai_app

llm_config = LLMConfig(
    model_loading_config=dict(
        model_id="my-qwen3",
        model_source="Qwen/Qwen3-32B",
    ),
    accelerator_type="L40S",
    deployment_config=dict(
        autoscaling_config=dict(
            min_replicas=1,
            max_replicas=2,
        )
    ),
    ### Uncomment if your model is gated and needs your Hugging Face token to access it.
    # runtime_env=dict(env_vars={"HF_TOKEN": os.environ.get("HF_TOKEN")}),
    engine_kwargs=dict(
        tensor_parallel_size=4, 
        max_model_len=32768, 
        reasoning_parser="qwen3",
        enable_auto_tool_choice= True,
        tool_call_parser= "hermes"
    ),
)
app = build_openai_app({"llm_configs": [llm_config]})