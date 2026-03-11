/**
 * btc_recognizer.cpp
 *
 * 离线地点识别程序：
 *   读取 btc_extractor 保存的描述子文件 → LoadFrame() → SearchLoop() → AddBtcDescs()
 *
 * ROS 参数：
 *   setting_path      : YAML 配置文件路径
 *   desc_dir          : 描述子文件目录（btc_extractor 的 output_dir）
 *   pose_file         : 位姿文件路径（可选；用于路径可视化和 GT 重叠率计算）
 *   cloud_overlap_thr : GT 重叠率判断阈值（默认 0.5）
 *   rate_hz           : 处理帧率限制，0 表示不限速（默认 100.0）
 *
 * 轻量模式兼容：
 *   若 btc_extractor 以 save_plane_cloud=false 运行，则 _planes.pcd 不存在。
 *   本节点启动时自动检测，无平面点云时跳过 TP/FP 分类，用黄色标记检测到的 loop。
 */

#include <nav_msgs/Odometry.h>
#include <nav_msgs/Path.h>
#include <pcl_conversions/pcl_conversions.h>
#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <visualization_msgs/MarkerArray.h>

#include <iomanip>
#include <numeric>
#include <sstream>

#include "include/btc.h"
#include "include/utils.h"

int main(int argc, char **argv) {
  ros::init(argc, argv, "btc_recognizer");
  ros::NodeHandle nh;
  ros::NodeHandle nh_private("~");

  std::string setting_path, desc_dir, pose_file;
  double cloud_overlap_thr = 0.5;
  double rate_hz = 100.0;

  nh_private.param<std::string>("setting_path", setting_path, "");
  nh_private.param<std::string>("desc_dir", desc_dir, "");
  nh_private.param<std::string>("pose_file", pose_file, "");
  nh_private.param<double>("cloud_overlap_thr", cloud_overlap_thr, 0.5);
  nh_private.param<double>("rate_hz", rate_hz, 100.0);

  if (desc_dir.empty()) {
    ROS_ERROR("[Recognizer] desc_dir is not set!");
    return -1;
  }

  // --------------- ROS Publishers ---------------
  ros::Publisher pub_key_points =
      nh.advertise<sensor_msgs::PointCloud2>("/cloud_key_points", 100);
  ros::Publisher pub_matched_key_points =
      nh.advertise<sensor_msgs::PointCloud2>("/cloud_matched_key_points", 100);
  ros::Publisher pub_matched_cloud =
      nh.advertise<sensor_msgs::PointCloud2>("/cloud_matched", 100);
  ros::Publisher pub_current_pose =
      nh.advertise<nav_msgs::Odometry>("/current_pose", 10);
  ros::Publisher pub_matched_pose =
      nh.advertise<nav_msgs::Odometry>("/matched_pose", 10);
  ros::Publisher pub_loop_status =
      nh.advertise<visualization_msgs::MarkerArray>("/loop_status", 100);
  ros::Publisher pub_btc =
      nh.advertise<visualization_msgs::MarkerArray>("descriptor_line", 10);

  // Color palette
  // color_tp    : green  — true positive (plane cloud available)
  // color_fp    : red    — false positive (plane cloud available)
  // color_loop  : yellow — loop detected, TP/FP unknown (no plane cloud)
  // color_path  : white  — no loop
  std_msgs::ColorRGBA color_tp, color_fp, color_loop, color_path;
  color_tp.a = 1.0;   color_tp.r = 0.0;   color_tp.g = 1.0;   color_tp.b = 0.0;
  color_fp.a = 1.0;   color_fp.r = 1.0;   color_fp.g = 0.0;   color_fp.b = 0.0;
  color_loop.a = 1.0; color_loop.r = 1.0; color_loop.g = 1.0; color_loop.b = 0.0;
  color_path.a = 0.8; color_path.r = 1.0; color_path.g = 1.0; color_path.b = 1.0;
  double scale_tp = 4.0, scale_fp = 5.0, scale_loop = 4.0, scale_path = 3.0;

  // --------------- Load Config ---------------
  ConfigSetting config_setting;
  load_config_setting(setting_path, config_setting);

  // --------------- Load Poses (optional) ---------------
  std::vector<std::pair<Eigen::Vector3d, Eigen::Matrix3d>> pose_list;
  std::vector<double> time_list;
  bool has_pose = !pose_file.empty();
  if (has_pose) {
    load_evo_pose_with_time(pose_file, pose_list, time_list);
    ROS_INFO_STREAM("[Recognizer] Loaded " << pose_list.size() << " poses");
  }

  BtcDescManager btc_manager(config_setting);

  std::vector<double> query_time;
  std::vector<double> update_time;
  int triggle_loop_num = 0;
  int true_loop_num = 0;

  const bool use_rate = (rate_hz > 0.0);
  ros::Rate loop_rate(use_rate ? rate_hz : 1e6);
  ros::Rate slow_loop(1000);

  visualization_msgs::MarkerArray marker_array;

  // Detect plane cloud availability before the main loop by checking frame 0
  bool has_plane_cloud = false;
  {
    std::ostringstream ss;
    ss << desc_dir << "/frame_" << std::setfill('0') << std::setw(6) << 0
       << "_planes.pcd";
    std::ifstream test(ss.str());
    has_plane_cloud = test.good();
  }
  if (has_plane_cloud) {
    ROS_INFO("[Recognizer] Plane clouds available: TP/FP classification enabled");
  } else {
    ROS_WARN("[Recognizer] No plane clouds found (lightweight mode). "
             "Detected loops shown in yellow without TP/FP classification.");
  }

  for (int frame_id = 0; ros::ok(); ++frame_id) {
    // --------------- Load Frame ---------------
    std::vector<BTC> btcs_vec;
    if (!btc_manager.LoadFrame(desc_dir, frame_id, btcs_vec, has_plane_cloud)) {
      ROS_INFO_STREAM("[Recognizer] No more frames after " << frame_id);
      break;
    }

    ROS_INFO_STREAM("[Recognizer] Frame " << frame_id
                                          << ", btcs: " << btcs_vec.size());

    // --------------- Search Loop ---------------
    auto t0 = std::chrono::high_resolution_clock::now();
    std::pair<int, double> search_result(-1, 0);
    std::pair<Eigen::Vector3d, Eigen::Matrix3d> loop_transform;
    loop_transform.first.setZero();
    loop_transform.second = Eigen::Matrix3d::Identity();
    std::vector<std::pair<BTC, BTC>> loop_std_pair;

    if (frame_id > config_setting.skip_near_num_ && !btcs_vec.empty()) {
      btc_manager.SearchLoop(btcs_vec, search_result, loop_transform,
                             loop_std_pair);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    query_time.push_back(time_inc(t1, t0));

    if (search_result.first > 0) {
      ROS_INFO_STREAM("[Recognizer] Loop detected: frame " << frame_id << " -- "
                                                           << search_result.first
                                                           << ", score: "
                                                           << search_result.second);
    }

    // --------------- Add to Database ---------------
    auto t2 = std::chrono::high_resolution_clock::now();
    btc_manager.AddBtcDescs(btcs_vec);
    auto t3 = std::chrono::high_resolution_clock::now();
    update_time.push_back(time_inc(t3, t2));

    ROS_INFO_STREAM("[Recognizer] Frame " << frame_id
                                          << ": query=" << time_inc(t1, t0)
                                          << "ms, update=" << time_inc(t3, t2)
                                          << "ms");

    // --------------- Visualization ---------------
    // Current key points
    sensor_msgs::PointCloud2 pub_cloud_msg;
    pcl::PointCloud<pcl::PointXYZ> key_pts;
    for (const auto &bd : btc_manager.history_binary_list_.back()) {
      pcl::PointXYZ p;
      p.x = bd.location_[0]; p.y = bd.location_[1]; p.z = bd.location_[2];
      key_pts.push_back(p);
    }
    pcl::toROSMsg(key_pts, pub_cloud_msg);
    pub_cloud_msg.header.frame_id = "camera_init";
    pub_key_points.publish(pub_cloud_msg);

    // Current pose marker
    if (has_pose && frame_id < static_cast<int>(pose_list.size())) {
      nav_msgs::Odometry odom;
      odom.header.frame_id = "camera_init";
      odom.pose.pose.position.x = pose_list[frame_id].first[0];
      odom.pose.pose.position.y = pose_list[frame_id].first[1];
      odom.pose.pose.position.z = pose_list[frame_id].first[2];
      pub_current_pose.publish(odom);
    }

    // Loop status marker
    visualization_msgs::Marker marker;
    marker.header.frame_id = "camera_init";
    marker.ns = "colored_path";
    marker.id = frame_id;
    marker.type = visualization_msgs::Marker::LINE_LIST;
    marker.action = visualization_msgs::Marker::ADD;
    marker.pose.orientation.w = 1.0;

    if (search_result.first >= 0) {
      triggle_loop_num++;

      // Publish matched descriptors
      Eigen::Matrix4d T1 = Eigen::Matrix4d::Identity();
      Eigen::Matrix4d T2 = Eigen::Matrix4d::Identity();
      publish_std(loop_std_pair, T1, T2, pub_btc);
      slow_loop.sleep();

      // Matched frame key points
      pcl::PointCloud<pcl::PointXYZ> match_key_pts;
      for (const auto &bd :
           btc_manager.history_binary_list_[search_result.first]) {
        pcl::PointXYZ p;
        p.x = bd.location_[0]; p.y = bd.location_[1]; p.z = bd.location_[2];
        match_key_pts.push_back(p);
      }
      pcl::toROSMsg(match_key_pts, pub_cloud_msg);
      pub_cloud_msg.header.frame_id = "camera_init";
      pub_matched_key_points.publish(pub_cloud_msg);

      // Matched pose marker
      if (has_pose &&
          search_result.first < static_cast<int>(pose_list.size())) {
        nav_msgs::Odometry odom_matched;
        odom_matched.header.frame_id = "camera_init";
        odom_matched.pose.pose.position.x =
            pose_list[search_result.first].first[0];
        odom_matched.pose.pose.position.y =
            pose_list[search_result.first].first[1];
        odom_matched.pose.pose.position.z =
            pose_list[search_result.first].first[2];
        pub_matched_pose.publish(odom_matched);
      }

      if (has_plane_cloud) {
        // --------------- TP/FP classification via plane cloud overlap ---------------
        bool is_true_positive = false;
        if (has_pose && frame_id < static_cast<int>(pose_list.size()) &&
            search_result.first < static_cast<int>(pose_list.size())) {
          pcl::PointCloud<pcl::PointXYZI>::Ptr curr_proxy(
              new pcl::PointCloud<pcl::PointXYZI>());
          if (frame_id < static_cast<int>(btc_manager.plane_cloud_vec_.size())) {
            for (const auto &pt : *btc_manager.plane_cloud_vec_[frame_id]) {
              pcl::PointXYZI pi;
              pi.x = pt.x; pi.y = pt.y; pi.z = pt.z; pi.intensity = 0;
              curr_proxy->push_back(pi);
            }
          }
          pcl::PointCloud<pcl::PointXYZI>::Ptr match_proxy(
              new pcl::PointCloud<pcl::PointXYZI>());
          if (search_result.first <
              static_cast<int>(btc_manager.plane_cloud_vec_.size())) {
            for (const auto &pt :
                 *btc_manager.plane_cloud_vec_[search_result.first]) {
              pcl::PointXYZI pi;
              pi.x = pt.x; pi.y = pt.y; pi.z = pt.z; pi.intensity = 0;
              match_proxy->push_back(pi);
            }
          }
          if (!curr_proxy->empty() && !match_proxy->empty()) {
            double overlap = calc_overlap(curr_proxy, match_proxy, 0.5);
            is_true_positive = (overlap >= cloud_overlap_thr);
          }
        }

        if (is_true_positive) {
          true_loop_num++;
          marker.scale.x = scale_tp;
          marker.color = color_tp;
        } else {
          marker.scale.x = scale_fp;
          marker.color = color_fp;
        }

        // Publish matched plane cloud
        if (search_result.first <
            static_cast<int>(btc_manager.plane_cloud_vec_.size()) &&
            !btc_manager.plane_cloud_vec_[search_result.first]->empty()) {
          pcl::PointCloud<pcl::PointXYZRGB> matched_vis;
          for (const auto &pt :
               *btc_manager.plane_cloud_vec_[search_result.first]) {
            pcl::PointXYZRGB p;
            p.x = pt.x; p.y = pt.y; p.z = pt.z;
            if (is_true_positive) { p.r = 0;   p.g = 255; p.b = 0; }
            else                  { p.r = 255; p.g = 0;   p.b = 0; }
            matched_vis.push_back(p);
          }
          pcl::toROSMsg(matched_vis, pub_cloud_msg);
          pub_cloud_msg.header.frame_id = "camera_init";
          pub_matched_cloud.publish(pub_cloud_msg);
          slow_loop.sleep();
        }
      } else {
        // Lightweight mode: no plane cloud, mark as detected (yellow)
        marker.scale.x = scale_loop;
        marker.color = color_loop;
      }
    } else {
      marker.scale.x = scale_path;
      marker.color = color_path;
    }

    // Add path segment
    if (has_pose && frame_id > 0 &&
        frame_id < static_cast<int>(pose_list.size())) {
      geometry_msgs::Point p1, p2;
      p1.x = pose_list[frame_id - 1].first[0];
      p1.y = pose_list[frame_id - 1].first[1];
      p1.z = pose_list[frame_id - 1].first[2];
      p2.x = pose_list[frame_id].first[0];
      p2.y = pose_list[frame_id].first[1];
      p2.z = pose_list[frame_id].first[2];
      marker.points.push_back(p1);
      marker.points.push_back(p2);
    }
    marker_array.markers.push_back(marker);
    pub_loop_status.publish(marker_array);

    if (use_rate) loop_rate.sleep();
  }

  // --------------- Statistics ---------------
  double mean_query =
      query_time.empty()
          ? 0.0
          : std::accumulate(query_time.begin(), query_time.end(), 0.0) /
                query_time.size();
  double mean_update =
      update_time.empty()
          ? 0.0
          : std::accumulate(update_time.begin(), update_time.end(), 0.0) /
                update_time.size();

  ROS_INFO_STREAM("[Recognizer] Total frames: " << query_time.size()
                                                << ", loops triggered: "
                                                << triggle_loop_num
                                                << ", true loops: "
                                                << true_loop_num
                                                << (has_plane_cloud ? "" : " (N/A, no plane cloud)"));
  ROS_INFO_STREAM("[Recognizer] Mean query: " << mean_query
                                              << "ms, mean update: "
                                              << mean_update << "ms, total: "
                                              << mean_query + mean_update
                                              << "ms");
  return 0;
}
