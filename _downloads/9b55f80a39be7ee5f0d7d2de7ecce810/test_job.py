from rich.logging import RichHandler
import logging
import anyscale
import argparse
from anyscale.compute_config.models import (
    ComputeConfig,
    HeadNodeConfig,
    WorkerNodeGroupConfig,
)
from anyscale.job.models import JobConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            show_path=False,
            enable_link_path=False,
            rich_tracebacks=True,
        )
    ],
)
logger = logging.getLogger("rich")


def run_job(cloud_name, stack_type, cloud_provider="aws"):
    """
    Submit a job to Anyscale and wait for it to complete.
    
    Args:
        cloud_name (str): The Anyscale cloud name to use
        stack_type (str): The deployment stack type ('vm' or 'k8s')
        cloud_provider (str): The cloud provider ('aws' or 'gcp')
    """
    
    # Define instance types based on stack type and cloud provider
    if stack_type == "vm":
        if cloud_provider == "aws":
            # For AWS VM deployments, use EC2 instance types
            head_instance_type = "t3.medium"
            worker_instance_type = "t3.medium"
        elif cloud_provider == "gcp":
            # For GCP VM deployments, use GCE instance types
            head_instance_type = "n1-standard-2"  # 2 vCPUs, 7.5 GB memory
            worker_instance_type = "n1-standard-2"
        else:
            raise ValueError(f"Unsupported cloud provider for VM: {cloud_provider}. Use 'aws' or 'gcp'.")
    elif stack_type == "k8s":
        # For K8s deployments, use Anyscale logical instance types (same across all cloud providers)
        head_instance_type = "2CPU-8GB"
        worker_instance_type = "2CPU-8GB"
    else:
        raise ValueError(f"Unsupported stack type: {stack_type}. Use 'vm' or 'k8s'.")
    
    print(f"Using stack type: {stack_type}")
    print(f"Using cloud provider: {cloud_provider}")
    print(f"Head node instance type: {head_instance_type}")
    print(f"Worker node instance type: {worker_instance_type}")
    
    # Define the compute configuration with appropriate instance types
    compute_config = ComputeConfig(
        cloud=cloud_name,
        head_node=HeadNodeConfig(
            instance_type=head_instance_type,
        ),
        worker_nodes=[
            WorkerNodeGroupConfig(
                instance_type=worker_instance_type,
                min_nodes=1,
                max_nodes=1,
            )
        ],
    )
    # Define the job configuration
    config = JobConfig(
        name="e2e-job-test",
        entrypoint="python main-job-test.py",
        cloud=cloud_name,
        working_dir="./anyscale-job",
        compute_config=compute_config,
    )

    try:
        # Submit the job
        job_id = anyscale.job.submit(config)

        # Wait for the job to finish
        anyscale.job.wait(id=job_id)

        # Get the job status
        job_status = anyscale.job.status(id=job_id)

        print(f"Job {job_id} completed with status: {job_status}")

        # Get job logs (optional)
        logs = anyscale.job.logs(id=job_id)
        print("Job logs:")
        print(logs)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cloud-name",
        "-c",
        required=True,
        type=str.lower,
        dest="cloudName",
        help="The Anyscale cloud name to use",
    )
    parser.add_argument(
        "--stack-type",
        "-s",
        required=True,
        choices=["vm", "k8s"],
        type=str.lower,
        dest="stackType",
        help="The deployment stack type: 'vm' for VM-based deployments or 'k8s' for Kubernetes deployments",
    )
    parser.add_argument(
        "--cloud-provider",
        "-p",
        required=False,  # Make it optional for backward compatibility
        default="aws",   # Default to AWS
        choices=["aws", "gcp"],
        type=str.lower,
        dest="cloudProvider",
        help="The cloud provider: 'aws' for AWS or 'gcp' for GCP (default: aws)",
    )

    args, _ = parser.parse_known_args()
    cloud_name = args.cloudName
    stack_type = args.stackType
    cloud_provider = args.cloudProvider

    run_job(cloud_name, stack_type, cloud_provider)
