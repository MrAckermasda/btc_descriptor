#!/usr/bin/env python3
"""
Simple tool to extract sensor_msgs/PointCloud2 messages from a ROS bag
and write them to PCD files (ASCII or binary little-endian).

Usage example:
  python3 pointcloud2_to_pcd.py bagfile.bag --topic /velodyne_points --out_dir ./velodyne --binary

The script writes files named 000000.pcd, 000001.pcd, ...
"""
import os
import argparse
import struct
import rosbag
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2


def write_pcd_ascii(path, points, has_intensity):
    n = len(points)
    fields = "x y z" + (" intensity" if has_intensity else "")
    sizes = "4 4 4" + (" 4" if has_intensity else "")
    types = "F F F" + (" F" if has_intensity else "")
    counts = "1 1 1" + (" 1" if has_intensity else "")
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\n"
        "VERSION 0.7\n"
        f"FIELDS {fields}\n"
        f"SIZE {sizes}\n"
        f"TYPE {types}\n"
        f"COUNT {counts}\n"
        f"WIDTH {n}\n"
        "HEIGHT 1\n"
        f"POINTS {n}\n"
        "DATA ascii\n"
    )
    with open(path, "w") as f:
        f.write(header)
        for p in points:
            if has_intensity:
                f.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f} {p[3]:.6f}\n")
            else:
                f.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")


def write_pcd_binary(path, points, has_intensity):
    n = len(points)
    fields = "x y z" + (" intensity" if has_intensity else "")
    sizes = "4 4 4" + (" 4" if has_intensity else "")
    types = "F F F" + (" F" if has_intensity else "")
    counts = "1 1 1" + (" 1" if has_intensity else "")
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\n"
        "VERSION 0.7\n"
        f"FIELDS {fields}\n"
        f"SIZE {sizes}\n"
        f"TYPE {types}\n"
        f"COUNT {counts}\n"
        f"WIDTH {n}\n"
        "HEIGHT 1\n"
        f"POINTS {n}\n"
        "DATA binary\n"
    )
    with open(path, "wb") as f:
        f.write(header.encode('ascii'))
        if n == 0:
            return
        if has_intensity:
            for p in points:
                f.write(struct.pack('<ffff', float(p[0]), float(p[1]), float(p[2]), float(p[3])))
        else:
            for p in points:
                f.write(struct.pack('<fff', float(p[0]), float(p[1]), float(p[2])))


def extract_points(msg, keep_intensity=False):
    # Use pc2.read_points which yields tuples
    # We request x,y,z,(intensity) depending on availability
    if not isinstance(msg, PointCloud2):
        return []
    # Try to detect intensity field
    field_names = [f.name for f in msg.fields]
    has_intensity = 'intensity' in field_names or 'rgb' in field_names
    # read_points with skip_nans True
    if has_intensity and keep_intensity:
        gen = pc2.read_points(msg, field_names=("x", "y", "z", "intensity"), skip_nans=True)
        return [tuple(p) for p in gen]
    else:
        gen = pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)
        return [tuple(p) for p in gen]


def main():
    parser = argparse.ArgumentParser(description="Extract PointCloud2 messages from a bag to PCD files")
    parser.add_argument("bag", help="input bag file")
    parser.add_argument("--topic", required=True, help="PointCloud2 topic to read")
    parser.add_argument("--out_dir", required=True, help="output directory for PCD files")
    parser.add_argument("--binary", action="store_true", help="write binary PCD (default is ASCII)")
    parser.add_argument("--start_index", type=int, default=0, help="first index for output files")
    parser.add_argument("--keep_intensity", action="store_true", help="include intensity if present")
    parser.add_argument("--pad", type=int, default=6, help="zero pad width for filenames")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    bag = rosbag.Bag(args.bag, 'r')
    idx = args.start_index
    for topic, msg, t in bag.read_messages(topics=[args.topic]):
        pts = extract_points(msg, keep_intensity=args.keep_intensity)
        if len(pts) == 0:
            filename = os.path.join(args.out_dir, f"{idx:0{args.pad}d}.pcd")
            # write empty PCD
            if args.binary:
                write_pcd_binary(filename, [], False)
            else:
                write_pcd_ascii(filename, [], False)
            idx += 1
            continue
        has_int = len(pts[0]) >= 4
        filename = os.path.join(args.out_dir, f"{idx:0{args.pad}d}.pcd")
        if args.binary:
            write_pcd_binary(filename, pts, has_int if args.keep_intensity else False)
        else:
            write_pcd_ascii(filename, pts, has_int if args.keep_intensity else False)
        print("Wrote", filename, "points:", len(pts))
        idx += 1
    bag.close()


if __name__ == '__main__':
    main()
