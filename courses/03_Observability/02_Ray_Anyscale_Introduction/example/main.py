import ray
import numpy as np
import os
import time
from typing import Dict, Any


"""
Each image is about 1MB. (HxWxC = 580x580x3 = 1MB)
So 1 billion images would be 1 PB. (10^9 * 1MB = 1PB)
"""
NUM_IMAGES = 10**9
IMAGE_WIDTH = 580
IMAGE_HEIGHT = 580
CHANNELS = 3


def generate_synthetic_image(image_id: int, width: int = 580, height: int = 580, channels: int = 3) -> Dict[str, Any]:
    image_array = np.random.randint(0, 256, size=(height, width, channels), dtype=np.uint8)
    return {
        "image_id": image_id,
        "image_array": image_array,
        "metadata": {
            "dtype": str(image_array.dtype),
            "shape": image_array.shape,
            "generated_by": "ray_data_synthetic"
        }
    }


if __name__ == "__main__":
    image_ids = list(range(NUM_IMAGES))
    output_path = os.path.join(os.environ["ANYSCALE_ARTIFACT_STORAGE"], "rkn/synthetic_image_output")

    ds = ray.data.from_items(image_ids)
    ds = ds.repartition(target_num_rows_per_block=1000)
    ds = ds.map(lambda x: generate_synthetic_image(x["item"], IMAGE_WIDTH, IMAGE_HEIGHT, CHANNELS))
    ds.write_parquet(output_path)

