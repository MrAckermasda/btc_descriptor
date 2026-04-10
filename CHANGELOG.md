# BTC Place Recognition 版本更新记录

---

## v0.1.0 — 项目初始化 (2026-02-11)

基于 BTC (Binary Triangle Combined) 描述子的 3D 激光雷达地点识别框架初始搭建。

### 初始内容

- 项目骨架搭建，包含 `include/`、`src/`、`example/` 基本目录结构
- 初始 README 文档
- 论文补充材料 `supply/Supplementary_Material_for_BTC.pdf`

---

## v0.2.0 — 核心算法发布 (2026-02-18)

发布 BTC 核心功能代码与地点识别示例程序。

### 新增

- `include/btc.h` — BTC 描述子、BinaryDescriptor、BtcDescManager 等核心数据结构与类定义
- `include/utils.h` / `src/utils.cpp` — 工具函数（位姿加载、点云转换、overlap 计算、时间统计等）
- `include/CustomMsg.h` / `include/CustomPoint.h` — Livox 自定义消息与点云格式
- `src/btc.cpp` — BTC 描述子提取、回环搜索、数据库管理的完整实现（~1900 行）
- `example/place_recognition.cpp` — 单节点在线地点识别示例（读取点云 → 提取描述子 → 搜索回环 → RViz 可视化）
- `config/config_outdoor.yaml` / `config/config_indoor.yaml` — 室内外场景配置参数
- `launch/place_recognition.launch` — ROS launch 文件
- `rviz_cfg/loop.rviz` — RViz 可视化配置
- `poses/` — KITTI 数据集位姿文件（00/02/05/06/07/08 序列）
- `CMakeLists.txt` / `package.xml` — ROS 包构建配置

---

## v0.3.0 — 离线两阶段拆分 (2026-02-25)

将原始单节点流程拆分为两个独立的离线阶段，提取阶段只需运行一次，识别阶段可多次运行调参。

```
原有流程（单节点）：
  读取点云 → GenerateBtcDescs() → SearchLoop() → AddBtcDescs() → 可视化

新流程（两节点）：
  [阶段一] btc_extractor：读取点云 → GenerateBtcDescs() → SaveFrame()
  [阶段二] btc_recognizer：LoadFrame() → SearchLoop() → AddBtcDescs() → 可视化
```

### 新增

- `example/btc_extractor.cpp` — 离线描述子提取节点，支持私有命名空间参数、可选位姿文件、可配置帧率
- `example/btc_recognizer.cpp` — 离线地点识别节点，自动检测平面点云可用性，TP/FP/未分类三色显示
- `launch/btc_extractor.launch` / `launch/btc_recognizer.launch`
- `CHANGES.md` — 项目改动说明文档
- `.gitignore`

### 修改

- `src/btc.cpp` — `SaveFrame()` 新增 `save_plane_cloud` 参数，支持轻量模式只保存 `.bin`
- `include/btc.h` — `SaveFrame` 声明同步更新
- `CMakeLists.txt` — 新增 `btc_extractor` / `btc_recognizer` 编译目标

---

## v0.4.0 — 数据工具链 (2026-03-04)

新增一系列数据预处理与格式转换工具脚本。

### 新增

- `script/pointcloud2_to_pcd.py` — 从 ROS bag 提取 PointCloud2 消息批量保存为 PCD 文件
- `script/pcd_publisher.py` — 本地 PCD 文件按位姿顺序发布为 ROS 消息，用于回放调试
- `script/rename_pcd_files.sh` — PCD/BIN 文件重命名为六位零填充格式，修复八进制解析 bug
- `script/renumber_pose_file.py` — 位姿文件帧 ID 重新连续编号
- `script/merge_pose_files.sh` — 合并两个位姿文件，自动调整帧 ID
- `script/merge_datasets.sh` — 合并两个 PCD 数据集目录及对应位姿文件

---

## v0.5.0 — 离线识别优化 (2026-03-11)

优化离线识别阶段的稳定性与平面点云处理逻辑。

### 修改

- `src/btc.cpp` — 修复 `Eigen::Vector3d` 二进制读写类型转换编译错误（补充 `.data()` 调用）；优化 `SaveFrame` / `LoadFrame` 的平面点云处理逻辑
- `include/btc.h` — 完善 `SaveFrame` / `LoadFrame` 接口声明
- `example/btc_recognizer.cpp` — 改进平面点云自适应检测逻辑，优化 TP/FP 分类显示
- `launch/btc_extractor.launch` — 参数调整

---

## v1.0.0 — 实验数据导出与可视化 (2026-03-18)

面向毕业设计，新增实验数据自动导出与 Python 绘图功能。

### 新增功能

#### C++ 数据导出 (`example/place_recognition.cpp`)

- 新增 ROS 参数 `output_dir`，指定实验结果输出目录（默认 `./btc_results`）
- 程序运行时自动生成以下 txt 文件：

| 文件 | 格式 | 说明 |
|------|------|------|
| `timing_per_frame.txt` | frame_id descriptor_time query_time update_time total_time | 逐帧各阶段耗时(ms) |
| `loop_detection.txt` | query_id matched_id score overlap is_tp | 回环检测结果及TP/FP标注 |
| `trajectory.txt` | frame_id x y z | 每帧位姿轨迹 |
| `descriptor_count.txt` | frame_id btc_count binary_count | 每帧描述子数量 |
| `summary.txt` | key value | 汇总统计(帧数/回环数/精确率/平均耗时) |

#### Python 绘图脚本 (`scripts/plot_results.py`)

读取上述 txt 文件，生成 10 张 300DPI 实验图表：

- `fig_timing_per_frame.png` — 逐帧各阶段耗时折线图
- `fig_timing_bar.png` — 平均耗时柱状图(含标准差)
- `fig_timing_pie.png` — 耗时占比饼图
- `fig_trajectory_loops.png` — 轨迹图 + TP/FP 回环连线
- `fig_descriptor_count.png` — 描述子数量变化曲线
- `fig_score_distribution.png` — 回环检测得分分布(TP vs FP)
- `fig_overlap_distribution.png` — 点云重叠率分布
- `fig_precision_recall.png` — Precision-Recall 曲线(含 Max F1)
- `fig_loop_matrix.png` — 回环检测帧对矩阵图
- `fig_summary_table.png` — 汇总统计表格

### 修改文件

- `example/place_recognition.cpp` — 新增数据导出逻辑
- `launch/place_recognition.launch` — 新增 `output_dir` 参数
- `scripts/plot_results.py` — 新增绘图脚本

### 使用方法

```bash
# 1. 编译运行
cd ~/lcd_ws && catkin_make
roslaunch btc_desc place_recognition.launch

# 2. 绘图（通过 --dataset 指定数据集名称，显示在图表标题中）
python3 src/btc_descriptor/scripts/plot_results.py src/btc_descriptor/btc_results --dataset KITTI-05
# 图表输出至 btc_results/figures/
```

---

## v1.0.1 — 绘图脚本中文化与数据集标注 (2026-03-19)

绘图脚本全面中文化，并支持在图表标题中标注数据集名称。

### 修改

- `scripts/plot_results.py`：
  - 所有图表标题、坐标轴标签、图例、表格内容改为中文
  - 修复中文字体缺失问题，使用系统自带 `AR PL UKai CN` 字体
  - 新增 `--dataset` / `-d` 命令行参数，指定数据集名称（如 `KITTI-05`），自动拼接到所有图表标题中
  - 改用 `argparse` 解析命令行参数

### 使用方法

```bash
# 指定数据集名称
python3 scripts/plot_results.py ./btc_results --dataset KITTI-05

# 未来其他数据集
python3 scripts/plot_results.py ./btc_results -d BUAA-Campus
```
