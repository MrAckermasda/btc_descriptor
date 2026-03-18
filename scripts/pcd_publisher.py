#!/usr/bin/env python3
import os
import time
import struct
import rospy
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
import sensor_msgs.point_cloud2 as pc2


def read_pcd(path):
    # Returns list of (x,y,z) tuples; supports binary and ascii PCD with x y z [intensity]
    with open(path, 'rb') as f:
        header = {}
        while True:
            line = f.readline().decode('ascii', errors='ignore')
            if not line:
                break
            line = line.strip()
            if line == '':
                continue
            parts = line.split()
            key = parts[0].upper()
            if key in ('FIELDS','SIZE','TYPE','COUNT'):
                header[key] = parts[1:]
            elif key == 'WIDTH':
                header['WIDTH'] = int(parts[1])
            elif key == 'POINTS':
                header['POINTS'] = int(parts[1])
            elif key == 'DATA':
                header['DATA'] = parts[1]
                break
        pts = []
        n = header.get('POINTS', None)
        has_int = False
        if 'FIELDS' in header:
            fields = header['FIELDS']
            if 'intensity' in fields or 'rgba' in fields or 'rgb' in fields:
                has_int = True
        if header.get('DATA','ascii').lower() == 'ascii':
            for _ in range(n):
                line = f.readline().decode('ascii', errors='ignore')
                if not line:
                    break
                vals = line.strip().split()
                if len(vals) >= 3:
                    x,y,z = float(vals[0]), float(vals[1]), float(vals[2])
                    pts.append((x,y,z))
        else:
            # binary little-endian
            fmt = '<fff' + ('f' if has_int else '')
            size = struct.calcsize(fmt)
            for i in range(n):
                data = f.read(size)
                if not data:
                    break
                vals = struct.unpack(fmt, data)
                pts.append((vals[0], vals[1], vals[2]))
        return pts


def publish_loop(pcd_dir, pose_file, rate_hz=1.0):
    pub_cloud = rospy.Publisher('/cloud_current', PointCloud2, queue_size=1)
    pub_pose = rospy.Publisher('/current_pose', Header, queue_size=1)
    rospy.init_node('pcd_publisher', anonymous=True)
    rate = rospy.Rate(rate_hz)

    # load poses
    poses = []
    with open(pose_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 8:
                continue
            idx = int(parts[0])
            x,y,z = float(parts[1]), float(parts[2]), float(parts[3])
            poses.append((idx, x, y, z))

    num = len(poses)
    i = 0
    while not rospy.is_shutdown() and i < num:
        idx, x,y,z = poses[i]
        pcd_path = os.path.join(pcd_dir, f"{idx:06d}.pcd")
        if not os.path.exists(pcd_path):
            rospy.logwarn(f"PCD not found: {pcd_path}")
            i += 1
            rate.sleep()
            continue
        pts = read_pcd(pcd_path)
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = 'camera_init'
        cloud_msg = pc2.create_cloud_xyz32(header, pts)
        pub_cloud.publish(cloud_msg)
        # publish a simple header as pose placeholder (for visualization timing)
        pose_hdr = Header()
        pose_hdr.stamp = rospy.Time.now()
        pose_hdr.frame_id = f"pose {idx} {x:.3f} {y:.3f} {z:.3f}"
        pub_pose.publish(pose_hdr)
        rospy.loginfo(f"Published {pcd_path} with {len(pts)} points")
        i += 1
        rate.sleep()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pcd_dir', required=True)
    parser.add_argument('--pose_file', required=True)
    parser.add_argument('--hz', type=float, default=1.0)
    args = parser.parse_args()
    publish_loop(args.pcd_dir, args.pose_file, rate_hz=args.hz)
