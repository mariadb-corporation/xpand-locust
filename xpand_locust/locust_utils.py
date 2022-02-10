import os
import sys

import numpy as np
import pandas as pd
import yaml


class YamlConfigException(Exception):
    pass


def load_yaml_config(yaml_config_file):
    if os.path.exists(yaml_config_file):
        try:
            with open(yaml_config_file, "rt") as f:
                yaml_config_dict = yaml.load(f, Loader=yaml.Loader)
                return yaml_config_dict
        except (yaml.YAMLError, yaml.MarkedYAMLError) as exc:
            raise YamlConfigException(
                f"Error occurred during parsing config file {yaml_config_file}"
            )

    else:
        raise YamlConfigException(f"Config file {yaml_config_file} does not exist")


def load_seed_file(seed_file, num_rows_required=10000):
    df = pd.read_csv(seed_file, header=None)
    values = df[0].values.tolist()
    arr = np.random.choice(values, num_rows_required)
    return iter(arr)


def is_worker():
    return "--worker" in sys.argv


def is_master():
    return "--master" in sys.argv


def histogram(data: list, buckets: int = 25, cut_pct: int = 5):
    """
    This code is from https://github.com/Kobold/text_histogram/blob/master/text_histogram.py
    """
    x_pd = pd.Series(data)
    x_data = x_pd.clip(
        lower=x_pd.quantile(cut_pct / 100), upper=x_pd.quantile(1 - cut_pct / 100)
    )

    bucket_scale = 1
    min_v = min(x_data)
    max_v = max(x_data)
    diff = max_v - min_v

    boundaries = []
    bucket_counts = []

    if buckets <= 0:
        raise ValueError("# of buckets must be > 0")
    step = diff / buckets
    bucket_counts = [0 for x in range(buckets)]
    for x in range(buckets):
        boundaries.append(min_v + (step * (x + 1)))

    skipped = 0
    samples = 0
    accepted_data = []

    for value in x_data:
        samples += 1

        # find the bucket this goes in
        if value < min_v or value > max_v:
            skipped += 1
            continue
        for bucket_postion, boundary in enumerate(boundaries):
            if value <= boundary:
                bucket_counts[bucket_postion] += 1
                break

    # auto-pick the hash scale
    if max(bucket_counts) > 75:
        bucket_scale = int(max(bucket_counts) / 75)

    # print "# NumSamples = %d; Min = %0.2f; Max = %0.2f" % (samples, min_v, max_v)
    # if skipped:
    #    print "# %d value%s outside of min/max" % (skipped, skipped > 1 and 's' or '')

    print(f"# each ∎ represents a count of {bucket_scale}. Cut pct is {cut_pct}%")
    bucket_min = min_v
    bucket_max = min_v
    for bucket in range(buckets):
        bucket_min = bucket_max
        bucket_max = boundaries[bucket]
        bucket_count = bucket_counts[bucket]
        star_count = 0
        if bucket_count:
            star_count = int(bucket_count / bucket_scale)
        print(
            "{:>8.1f} - {:>8.1f} {:8d}: {:s}".format(
                bucket_min, bucket_max, bucket_count, "∎" * star_count
            )
        )
    print("# Summary statistics:")
    print(x_pd.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))
