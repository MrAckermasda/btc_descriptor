# BTC 项目改动说明

## 概述

本文档记录了对原始 BTC 项目的所有改动。核心变化是将原本**单一在线节点**（`place_recognition.cpp`）拆分为两个独立的**离线阶段**：

```
原有流程（单节点）：
  读取点云 → GenerateBtcDescs() → SearchLoop() → AddBtcDescs() → 可视化

新流程（两节点）：
  [阶段一] btc_extractor：读取点云 → GenerateBtcDescs() → SaveFrame() → 保存到本地
  [阶段二] btc_recognizer：LoadFrame() → SearchLoop() → AddBtcDescs() → 可视化
```

拆分的好处：提取阶段只需运行一次，识别阶段可以多次运行、调参，不必重复处理原始点云。

---

## 一、新增/修改的 C++ 文件

### 1. `example/btc_extractor.cpp`（新增）

**功能**：离线描述子提取，读取点云文件，生成 BTC 描述子并保存到磁盘。

**与 `place_recognition.cpp` 的主要差异**：

| 项目 | place_recognition.cpp | btc_extractor.cpp |
|---|---|---|
| 参数读取 | `nh.param`（全局命名空间） | `nh_private.param`（私有命名空间，`~`） |
| 位姿文件 | 必须提供 | 可选（`pose_file` 留空则不做坐标变换） |
| 核心步骤 | Extract + Search + Add | 仅 Extract + **SaveFrame** |
| 帧率控制 | `ros::Rate(50000)` 无限速 | `rate_hz` 参数可配置 |

**ROS 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `setting_path` | string | `""` | YAML 配置文件路径 |
| `pcds_dir` | string | `""` | 点云目录（`.bin` 或 `.pcd`） |
| `pose_file` | string | `""` | 位姿文件路径（可选） |
| `output_dir` | string | `/tmp/btc_descs` | 描述子输出目录 |
| `read_bin` | bool | `true` | `true` = KITTI `.bin`，`false` = `.pcd` |
| `save_plane_cloud` | bool | `false` | 是否同时保存 `_planes.pcd`（轻量模式默认关闭） |
| `rate_hz` | double | `100.0` | 帧处理速率上限，`0` 表示不限速 |

**轻量化说明**：

`SaveFrame()` 原本为每帧保存两个文件：
- `frame_XXXXXX.bin`：BTC 描述子 + BinaryDescriptor（紧凑二进制，约几 KB）
- `frame_XXXXXX_planes.pcd`：平面点云（`PointXYZINormal` 格式，含法向量，约几十 KB）

默认 `save_plane_cloud=false` 时，只保存 `.bin` 文件，跳过 PCD 输出，显著减小磁盘占用。

---

### 2. `example/btc_recognizer.cpp`（新增）

**功能**：离线地点识别，读取 `btc_extractor` 保存的描述子文件，执行 `SearchLoop`。

**与 `place_recognition.cpp` 的主要差异**：

| 项目 | place_recognition.cpp | btc_recognizer.cpp |
|---|---|---|
| 参数读取 | `nh.param`（全局命名空间） | `nh_private.param`（私有命名空间） |
| 原始点云 | 每帧读取并维护 `key_cloud_vec_` | **不读取**原始点云 |
| 核心步骤 | Extract + Search + Add | 仅 **LoadFrame** + Search + Add |
| TP/FP 分类 | 始终基于 `key_cloud_vec_` 重叠率 | 自动检测平面点云是否可用 |
| 帧率控制 | `ros::Rate(50000)` 无限速 | `rate_hz` 参数可配置 |

**平面点云自适应**：

节点在加载第一帧后自动检测是否存在有效平面点云：

- **有平面点云**（`save_plane_cloud=true` 时提取）：启动时打印 `INFO`，TP 绿色 / FP 红色，行为与原版一致
- **无平面点云**（轻量模式默认）：启动时打印 `WARN`，检测到的 loop 显示**黄色**（已检测但未分类），避免将所有 loop 错误标记为 FP

**颜色映射**：

| 颜色 | 含义 |
|---|---|
| 绿色 | True Positive（有平面点云，重叠率 ≥ 阈值） |
| 红色 | False Positive（有平面点云，重叠率 < 阈值） |
| 黄色 | 检测到 Loop，但无平面点云无法分类 |
| 白色 | 无 Loop，普通路径段 |

**ROS 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `setting_path` | string | `""` | YAML 配置文件路径 |
| `desc_dir` | string | `""` | 描述子目录（extractor 的 `output_dir`） |
| `pose_file` | string | `""` | 位姿文件路径（可选） |
| `cloud_overlap_thr` | double | `0.5` | GT 重叠率判断阈值 |
| `rate_hz` | double | `100.0` | 帧处理速率上限，`0` 表示不限速 |

---

### 3. `src/btc.cpp`（修改）

**修改点一：`SaveFrame()` 新增 `save_plane_cloud` 参数**

```cpp
// 修改前
void BtcDescManager::SaveFrame(const std::string &save_dir, int frame_id,
                               const std::vector<BTC> &btcs_vec);

// 修改后
void BtcDescManager::SaveFrame(const std::string &save_dir, int frame_id,
                               const std::vector<BTC> &btcs_vec,
                               bool save_plane_cloud = true);
```

当 `save_plane_cloud=false` 时，跳过 `pcl::io::savePCDFileBinaryCompressed()` 调用，只写 `.bin` 文件。

**修改点二：修复 `Eigen::Vector3d` 类型转换编译错误**

```cpp
// 修复前（编译错误：invalid cast from Eigen::Vector3d to char*）
ofs.write(reinterpret_cast<const char *>(btc.angle_), 3 * sizeof(double));
ifs.read(reinterpret_cast<char *>(btc.angle_), 3 * sizeof(double));

// 修复后
ofs.write(reinterpret_cast<const char *>(btc.angle_.data()), 3 * sizeof(double));
ifs.read(reinterpret_cast<char *>(btc.angle_.data()), 3 * sizeof(double));
```

---

### 4. `include/btc.h`（修改）

`SaveFrame` 声明同步更新：

```cpp
void SaveFrame(const std::string &save_dir, int frame_id,
               const std::vector<BTC> &btcs_vec,
               bool save_plane_cloud = true);
```

---

## 二、新增/修改的 Launch 文件

### 1. `launch/btc_extractor.launch`（新增）

```xml
roslaunch btc_desc btc_extractor.launch
```

可配置参数（通过命令行覆盖）：

```bash
# 完整模式（保存平面点云，用于后续 TP/FP 分类）
roslaunch btc_desc btc_extractor.launch save_plane_cloud:=true

# 不限速（尽快处理完所有帧）
roslaunch btc_desc btc_extractor.launch rate_hz:=0

# 读取 PCD 格式点云
roslaunch btc_desc btc_extractor.launch read_bin:=false
```

### 2. `launch/btc_recognizer.launch`（新增）

```xml
roslaunch btc_desc btc_recognizer.launch
```

可配置参数：

```bash
# 自定义描述子目录和位姿文件
roslaunch btc_desc btc_recognizer.launch \
    desc_dir:=/your/desc/path \
    pose_file:=/your/pose.txt

# 关闭 RViz
roslaunch btc_desc btc_recognizer.launch rviz:=false
```

---

## 三、CMakeLists.txt 修改

新增两个编译目标：

```cmake
add_executable(btc_extractor example/btc_extractor.cpp)
target_link_libraries(btc_extractor btc_lib utils_lib)

add_executable(btc_recognizer example/btc_recognizer.cpp)
target_link_libraries(btc_recognizer btc_lib utils_lib)
```

原有 `btc_place_recognition` 目标保留，不受影响。

---

## 四、script/ 工具脚本

以下脚本用于数据预处理，均为新增：

### `rename_pcd_files.sh`

将目录下的 PCD/BIN 文件重命名为六位零填充格式（`000000.pcd`、`000001.pcd`…），满足 extractor 的文件命名要求。

```bash
./script/rename_pcd_files.sh /path/to/pcd/dir pcd
./script/rename_pcd_files.sh /path/to/bin/dir bin
```

> **修复说明**：原脚本中 `printf "%06d"` 将前导零字符串当作八进制解析导致报错（如 `08`、`09` 无效），已通过 `"$((10#$num))"` 强制十进制解决。

### `pointcloud2_to_pcd.py`

从 ROS bag 文件中提取 `sensor_msgs/PointCloud2` 消息，批量保存为 PCD 文件。

```bash
python3 script/pointcloud2_to_pcd.py bagfile.bag \
    --topic /velodyne_points \
    --out_dir ./velodyne \
    --binary \
    --keep_intensity
```

| 参数 | 说明 |
|---|---|
| `--topic` | 要提取的话题名 |
| `--out_dir` | PCD 输出目录 |
| `--binary` | 输出二进制 PCD（默认 ASCII） |
| `--keep_intensity` | 保留 intensity 字段 |
| `--start_index` | 起始文件编号（默认 0） |

### `pcd_publisher.py`

将本地 PCD 文件按位姿文件顺序发布为 ROS `PointCloud2` 消息，用于回放调试。

```bash
python3 script/pcd_publisher.py \
    --pcd_dir /path/to/pcds \
    --pose_file /path/to/pose.txt \
    --hz 1.0
```

### `renumber_pose_file.py`

将位姿文件的第一列（帧 ID）重新连续编号，解决合并数据集后 ID 不连续问题。

```bash
python3 script/renumber_pose_file.py input_pose.txt output_pose.txt
```

### `merge_pose_files.sh`

合并两个位姿文件，自动调整第二个文件的帧 ID 使其连续接续第一个。

### `merge_datasets.sh`

合并两个 PCD 数据集目录，将第二个数据集的文件重命名后连续接续第一个，同时合并对应位姿文件。

---

## 五、典型使用流程

### 步骤一：数据准备

```bash
# 从 bag 文件提取点云
python3 script/pointcloud2_to_pcd.py my.bag \
    --topic /velodyne_points --out_dir ./pcds --binary --keep_intensity

# 重命名为六位格式（如有必要）
./script/rename_pcd_files.sh ./pcds pcd
```

### 步骤二：提取描述子

```bash
roslaunch btc_desc btc_extractor.launch \
    pcds_dir:=/path/to/pcds \
    pose_file:=/path/to/pose.txt \
    output_dir:=/path/to/btc_decs
```

### 步骤三：地点识别

```bash
roslaunch btc_desc btc_recognizer.launch \
    desc_dir:=/path/to/btc_decs \
    pose_file:=/path/to/pose.txt
```

---

## 六、文件结构概览

```
btc_descriptor/
├── example/
│   ├── place_recognition.cpp   # 原版单节点（保留，不修改）
│   ├── btc_extractor.cpp       # 新增：离线提取阶段
│   └── btc_recognizer.cpp      # 新增：离线识别阶段
├── include/
│   └── btc.h                   # 修改：SaveFrame 签名增加 save_plane_cloud 参数
├── src/
│   └── btc.cpp                 # 修改：SaveFrame 实现 + Eigen 类型转换修复
├── launch/
│   ├── place_recognition.launch   # 原版（保留）
│   ├── btc_extractor.launch       # 新增
│   └── btc_recognizer.launch      # 新增
├── script/
│   ├── rename_pcd_files.sh        # 新增：文件重命名工具
│   ├── pointcloud2_to_pcd.py      # 新增：bag 转 PCD
│   ├── pcd_publisher.py           # 新增：PCD 回放发布
│   ├── renumber_pose_file.py      # 新增：位姿文件重编号
│   ├── merge_pose_files.sh        # 新增：位姿文件合并
│   └── merge_datasets.sh          # 新增：数据集合并
└── CMakeLists.txt               # 修改：新增 btc_extractor / btc_recognizer 目标
```
