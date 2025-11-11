import os
import boto3
from huggingface_hub import snapshot_download

# Mapping of custom names to Hugging Face LoRA adapter repo IDs
adapters = {
    "nemoguard": "nvidia/llama-3.1-nemoguard-8b-topic-control",
    "cv_job_matching": "LlamaFactoryAI/Llama-3.1-8B-Instruct-cv-job-description-matching",
    "yara": "vtriple/Llama-3.1-8B-yara"
}

# S3 target
bucket_name = "llm-docs-aydin"
base_s3_path = "1-5-multi-lora/lora_checkpoints"

# Initialize S3 client
s3 = boto3.client("s3")

for custom_name, repo_id in adapters.items():
    print(f"\n📥 Downloading adapter '{custom_name}' from {repo_id}...")
    local_path = snapshot_download(repo_id)

    print(f"⬆️ Uploading files to s3://{bucket_name}/{base_s3_path}/{custom_name}/")

    for root, _, files in os.walk(local_path):
        for file_name in files:
            local_file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(local_file_path, local_path)
            s3_key = f"{base_s3_path}/{custom_name}/{rel_path}".replace("\\", "/")

            print(f"  → {s3_key}")
            s3.upload_file(local_file_path, bucket_name, s3_key)

print("\n✅ All adapters uploaded successfully.")

# List all objects in the bucket to confirm
response = s3.list_objects_v2(Bucket=bucket_name)

print(f"Files in s3://{bucket_name}/:")
for obj in response["Contents"]:
    print(obj["Key"])