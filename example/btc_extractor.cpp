/**
 * btc_extractor.cpp
 *
 * 离线描述子提取程序：
 *   读取点云文件 → GenerateBtcDescs() → SaveFrame() 保存到本地
 *
 * ROS 参数：
 *   setting_path      : YAML 配置文件路径
 *   pcds_dir          : 点云目录（KITTI .bin 或 .pcd 格式）
 *   pose_file         : 位姿文件路径（用于坐标变换，置空则不做变换）
 *   output_dir        : 描述子输出目录
 *   read_bin          : true = 读 KITTI .bin, false = 读 .pcd
 *   save_plane_cloud  : true = 同时保存 _planes.pcd（默认 false，轻量模式）
 *   rate_hz           : 处理帧率限制，0 表示不限速（默认 100.0）
 */

#include <nav_msgs/Odometry.h>
#include <pcl_conversions/pcl_conversions.h>
#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <visualization_msgs/MarkerArray.h>

#include <boost/filesystem.hpp>
#include <iomanip>
#include <numeric>
#include <sstream>

#include "include/btc.h"
#include "include/utils.h"

// Read KITTI binary point cloud file
static std::vector<float> read_lidar_data(const std::string &path) {
  std::ifstream f(path, std::ifstream::in | std::ifstream::binary);
  if (!f) return {};
  f.seekg(0, std::ios::end);
  const size_t n = f.tellg() / sizeof(float);
  f.seekg(0, std::ios::beg);
  std::vector<float> buf(n);
  f.read(reinterpret_cast<char *>(buf.data()), n * sizeof(float));
  return buf;
}

int main(int argc, char **argv) {
  ros::init(argc, argv, "btc_extractor");
  ros::NodeHandle nh;
  ros::NodeHandle nh_private("~");

  std::string setting_path, pcds_dir, pose_file, output_dir;
  bool read_bin = true;
  bool save_plane_cloud = false;
  double rate_hz = 10.0;

  nh_private.param<std::string>("setting_path", setting_path, "");
  nh_private.param<std::string>("pcds_dir", pcds_dir, "");
  nh_private.param<std::string>("pose_file", pose_file, "");
  nh_private.param<std::string>("output_dir", output_dir, "/tmp/btc_descs");
  nh_private.param<bool>("read_bin", read_bin, true);
  nh_private.param<bool>("save_plane_cloud", save_plane_cloud, false);
  nh_private.param<double>("rate_hz", rate_hz, 10.0);

  // Create output directory
  boost::filesystem::create_directories(output_dir);
  ROS_INFO_STREAM("[Extractor] Output dir: " << output_dir);
  ROS_INFO_STREAM("[Extractor] save_plane_cloud=" << save_plane_cloud
                                                  << ", rate_hz=" << rate_hz);

  // ROS publishers (visualization)
  ros::Publisher pub_current_cloud =
      nh.advertise<sensor_msgs::PointCloud2>("/cloud_current", 100);
  ros::Publisher pub_key_points =
      nh.advertise<sensor_msgs::PointCloud2>("/cloud_key_points", 100);
  ros::Publisher pub_descriptor =
      nh.advertise<visualization_msgs::MarkerArray>("descriptor_line", 10);

  // Load config
  ConfigSetting config_setting;
  load_config_setting(setting_path, config_setting);

  // Load poses (optional; used only for transforming local → global coords)
  std::vector<std::pair<Eigen::Vector3d, Eigen::Matrix3d>> pose_list;
  std::vector<double> time_list;
  bool has_pose = !pose_file.empty();
  if (has_pose) {
    load_evo_pose_with_time(pose_file, pose_list, time_list);
    ROS_INFO_STREAM("[Extractor] Loaded " << pose_list.size() << " poses");
  }

  BtcDescManager btc_manager(config_setting);
  pcl::PCDReader reader;

  std::vector<double> descriptor_time;
  std::vector<double> save_time;

  // Rate limiter: rate_hz <= 0 means unlimited
  const bool use_rate = (rate_hz > 0.0);
  ros::Rate loop_rate(use_rate ? rate_hz : 1e6);

  size_t max_frames = has_pose ? pose_list.size() : SIZE_MAX;

  for (size_t frame_id = 0; ros::ok() && frame_id < max_frames; ++frame_id) {
    // --------------- Load point cloud ---------------
    pcl::PointCloud<pcl::PointXYZI> cloud_local;

    if (read_bin) {
      std::ostringstream ss;
      ss << pcds_dir << "/" << std::setfill('0') << std::setw(10) << frame_id
         << ".bin";
      ROS_INFO_STREAM("[Extractor] Trying to open: " << ss.str());
      auto lidar_data = read_lidar_data(ss.str());
      if (lidar_data.empty()) {
        ROS_WARN_STREAM("[Extractor] Failed to read .bin at frame " << frame_id
                        << ", path: " << ss.str());
        break;
      }
      for (size_t i = 0; i + 3 < lidar_data.size(); i += 4) {
        pcl::PointXYZI p;
        p.x = lidar_data[i];
        p.y = lidar_data[i + 1];
        p.z = lidar_data[i + 2];
        p.intensity = lidar_data[i + 3];
        cloud_local.push_back(p);
      }
    } else {
      std::ostringstream ss;
      ss << pcds_dir << "/" << std::setfill('0') << std::setw(6) << frame_id
         << ".pcd";
      if (reader.read(ss.str(), cloud_local) == -1) {
        ROS_INFO_STREAM("[Extractor] No more .pcd files at frame " << frame_id);
        break;
      }
    }

    // --------------- Apply pose transform (local → global) ---------------
    pcl::PointCloud<pcl::PointXYZI>::Ptr cloud(
        new pcl::PointCloud<pcl::PointXYZI>());
    if (has_pose && frame_id < pose_list.size()) {
      const Eigen::Vector3d &t = pose_list[frame_id].first;
      const Eigen::Matrix3d &R = pose_list[frame_id].second;
      cloud->resize(cloud_local.size());
      for (size_t i = 0; i < cloud_local.size(); ++i) {
        Eigen::Vector3d pv = point2vec(cloud_local.points[i]);
        pv = R * pv + t;
        cloud->points[i] = vec2point(pv);
      }
    } else {
      *cloud = cloud_local;
    }

    // --------------- Descriptor Extraction ---------------
    ROS_INFO_STREAM("[Extractor] Processing frame " << frame_id
                                                    << ", cloud size: "
                                                    << cloud->size());
    auto t0 = std::chrono::high_resolution_clock::now();
    std::vector<BTC> btcs_vec;
    btc_manager.GenerateBtcDescs(cloud, static_cast<int>(frame_id), btcs_vec);
    auto t1 = std::chrono::high_resolution_clock::now();
    descriptor_time.push_back(time_inc(t1, t0));

    // --------------- Save to disk ---------------
    auto t2 = std::chrono::high_resolution_clock::now();
    btc_manager.SaveFrame(output_dir, static_cast<int>(frame_id), btcs_vec,
                          save_plane_cloud);
    auto t3 = std::chrono::high_resolution_clock::now();
    save_time.push_back(time_inc(t3, t2));

    ROS_INFO_STREAM("[Extractor] Frame " << frame_id
                                         << ": extract=" << time_inc(t1, t0)
                                         << "ms, save=" << time_inc(t3, t2)
                                         << "ms, btcs=" << btcs_vec.size());

    // --------------- Visualization ---------------
    sensor_msgs::PointCloud2 pub_cloud_msg;
    pcl::toROSMsg(*cloud, pub_cloud_msg);
    pub_cloud_msg.header.frame_id = "camera_init";
    pub_current_cloud.publish(pub_cloud_msg);

    // Publish key points
    pcl::PointCloud<pcl::PointXYZ> key_pts;
    for (const auto &bd : btc_manager.history_binary_list_.back()) {
      pcl::PointXYZ p;
      p.x = bd.location_[0];
      p.y = bd.location_[1];
      p.z = bd.location_[2];
      key_pts.push_back(p);
    }
    pcl::toROSMsg(key_pts, pub_cloud_msg);
    pub_cloud_msg.header.frame_id = "camera_init";
    pub_key_points.publish(pub_cloud_msg);

    // Publish descriptor triangles
    publish_std_list(btcs_vec, pub_descriptor);

    if (use_rate) loop_rate.sleep();
  }

  // --------------- Statistics ---------------
  if (!descriptor_time.empty()) {
    double mean_desc =
        std::accumulate(descriptor_time.begin(), descriptor_time.end(), 0.0) /
        descriptor_time.size();
    double mean_save =
        std::accumulate(save_time.begin(), save_time.end(), 0.0) /
        save_time.size();
    ROS_INFO_STREAM("[Extractor] Done. Frames: "
                    << descriptor_time.size()
                    << "  Mean extraction: " << mean_desc
                    << "ms  Mean save: " << mean_save << "ms");
  }

  return 0;
}
