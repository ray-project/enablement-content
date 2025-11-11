import ray
import time
import pyarrow.fs as fs


default_cluster_storage = "/mnt/cluster_storage/observed_data/"

"""
s3://anyscale-public-materials/nyc-taxi-cab/yellow_tripdata_2011-05.parquet
"""
s3_fs = fs.S3FileSystem(anonymous=True)
ds = ray.data.read_parquet(
    "s3://anyscale-public-materials/nyc-taxi-cab/yellow_tripdata_2011-05.parquet",
    filesystem=s3_fs
)

def slow_adjust_total_amount(batch):
    time.sleep(10)
    batch["adjusted_total_amount"] = batch["total_amount"] - batch["tip_amount"]
    return batch

ds = ds.map_batches(slow_adjust_total_amount)
ds.write_parquet(default_cluster_storage)

print("Done!")
