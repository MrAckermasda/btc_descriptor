#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC Place Recognition 实验结果绘图脚本
用于毕业设计实验数据可视化
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体支持
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
rcParams['axes.unicode_minus'] = False
rcParams['figure.dpi'] = 150
rcParams['savefig.dpi'] = 300
rcParams['savefig.bbox'] = 'tight'


def load_timing_data(filepath):
    """加载逐帧时间数据"""
    data = np.loadtxt(filepath, comments='#')
    return {
        'frame_id': data[:, 0].astype(int),
        'descriptor_time': data[:, 1],
        'query_time': data[:, 2],
        'update_time': data[:, 3],
        'total_time': data[:, 4],
    }


def load_loop_data(filepath):
    """加载回环检测结果"""
    data = np.loadtxt(filepath, comments='#')
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return {
        'query_id': data[:, 0].astype(int),
        'matched_id': data[:, 1].astype(int),
        'score': data[:, 2],
        'overlap': data[:, 3],
        'is_tp': data[:, 4].astype(int),
    }


def load_trajectory(filepath):
    """加载轨迹数据"""
    data = np.loadtxt(filepath, comments='#')
    return {
        'frame_id': data[:, 0].astype(int),
        'x': data[:, 1],
        'y': data[:, 2],
        'z': data[:, 3],
    }


def load_descriptor_count(filepath):
    """加载描述子数量数据"""
    data = np.loadtxt(filepath, comments='#')
    return {
        'frame_id': data[:, 0].astype(int),
        'btc_count': data[:, 1].astype(int),
        'binary_count': data[:, 2].astype(int),
    }


def load_summary(filepath):
    """加载汇总数据"""
    summary = {}
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                key, val = parts
                try:
                    summary[key] = float(val)
                except ValueError:
                    summary[key] = val
    return summary


# ============================================================
# 图1: 各阶段耗时折线图
# ============================================================
def plot_timing_per_frame(timing, output_dir):
    fig, ax = plt.subplots(figsize=(12, 5))
    frames = timing['frame_id']
    ax.plot(frames, timing['descriptor_time'], label='描述子提取', linewidth=0.8)
    ax.plot(frames, timing['query_time'], label='回环查询', linewidth=0.8)
    ax.plot(frames, timing['update_time'], label='数据库更新', linewidth=0.8)
    ax.set_xlabel('帧编号')
    ax.set_ylabel('耗时 (ms)')
    ax.set_title('逐帧各阶段处理耗时')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_timing_per_frame.png'))
    plt.close(fig)
    print('[Plot] fig_timing_per_frame.png')


# ============================================================
# 图2: 平均耗时柱状图
# ============================================================
def plot_timing_bar(timing, output_dir):
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ['描述子\n提取', '回环\n查询', '数据库\n更新']
    means = [
        np.mean(timing['descriptor_time']),
        np.mean(timing['query_time']),
        np.mean(timing['update_time']),
    ]
    stds = [
        np.std(timing['descriptor_time']),
        np.std(timing['query_time']),
        np.std(timing['update_time']),
    ]
    colors = ['#4C72B0', '#55A868', '#C44E52']
    bars = ax.bar(labels, means, yerr=stds, color=colors, capsize=5, edgecolor='black', linewidth=0.5)
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'{m:.2f}ms', ha='center', va='bottom', fontsize=10)
    ax.set_ylabel('耗时 (ms)')
    ax.set_title('各阶段平均处理耗时')
    ax.grid(True, axis='y', alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_timing_bar.png'))
    plt.close(fig)
    print('[Plot] fig_timing_bar.png')


# ============================================================
# 图3: 耗时占比饼图
# ============================================================
def plot_timing_pie(timing, output_dir):
    fig, ax = plt.subplots(figsize=(6, 6))
    means = [
        np.mean(timing['descriptor_time']),
        np.mean(timing['query_time']),
        np.mean(timing['update_time']),
    ]
    labels = ['描述子提取', '回环查询', '数据库更新']
    colors = ['#4C72B0', '#55A868', '#C44E52']
    ax.pie(means, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title('各阶段耗时占比')
    fig.savefig(os.path.join(output_dir, 'fig_timing_pie.png'))
    plt.close(fig)
    print('[Plot] fig_timing_pie.png')


# ============================================================
# 图4: 轨迹图 + 回环连线
# ============================================================
def plot_trajectory_with_loops(traj, loop, output_dir):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.plot(traj['x'], traj['y'], 'b-', linewidth=0.5, label='运动轨迹', zorder=1)
    ax.scatter(traj['x'][0], traj['y'][0], c='green', s=80, marker='^', label='起点', zorder=3)
    ax.scatter(traj['x'][-1], traj['y'][-1], c='red', s=80, marker='v', label='终点', zorder=3)

    if loop is not None and len(loop['query_id']) > 0:
        tp_mask = loop['is_tp'] == 1
        fp_mask = loop['is_tp'] == 0

        # TP loops
        for i in np.where(tp_mask)[0]:
            qid = loop['query_id'][i]
            mid = loop['matched_id'][i]
            if qid < len(traj['x']) and mid < len(traj['x']):
                ax.plot([traj['x'][qid], traj['x'][mid]],
                        [traj['y'][qid], traj['y'][mid]],
                        'g-', linewidth=1.5, alpha=0.6, zorder=2)

        # FP loops
        for i in np.where(fp_mask)[0]:
            qid = loop['query_id'][i]
            mid = loop['matched_id'][i]
            if qid < len(traj['x']) and mid < len(traj['x']):
                ax.plot([traj['x'][qid], traj['x'][mid]],
                        [traj['y'][qid], traj['y'][mid]],
                        'r--', linewidth=1.0, alpha=0.6, zorder=2)

        # Legend entries
        ax.plot([], [], 'g-', linewidth=2, label='真阳性回环')
        ax.plot([], [], 'r--', linewidth=2, label='假阳性回环')

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('轨迹与回环检测结果')
    ax.legend(loc='best')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_trajectory_loops.png'))
    plt.close(fig)
    print('[Plot] fig_trajectory_loops.png')


# ============================================================
# 图5: 回环检测得分分布直方图
# ============================================================
def plot_score_distribution(loop, output_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    tp_mask = loop['is_tp'] == 1
    fp_mask = loop['is_tp'] == 0

    if np.any(tp_mask):
        ax.hist(loop['score'][tp_mask], bins=20, alpha=0.7, color='green', label='真阳性', edgecolor='black')
    if np.any(fp_mask):
        ax.hist(loop['score'][fp_mask], bins=20, alpha=0.7, color='red', label='假阳性', edgecolor='black')

    ax.set_xlabel('匹配得分')
    ax.set_ylabel('数量')
    ax.set_title('回环检测得分分布')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_score_distribution.png'))
    plt.close(fig)
    print('[Plot] fig_score_distribution.png')


# ============================================================
# 图6: Overlap 分布直方图
# ============================================================
def plot_overlap_distribution(loop, output_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    tp_mask = loop['is_tp'] == 1
    fp_mask = loop['is_tp'] == 0

    if np.any(tp_mask):
        ax.hist(loop['overlap'][tp_mask], bins=20, alpha=0.7, color='green', label='真阳性', edgecolor='black')
    if np.any(fp_mask):
        ax.hist(loop['overlap'][fp_mask], bins=20, alpha=0.7, color='red', label='假阳性', edgecolor='black')

    ax.axvline(x=0.5, color='black', linestyle='--', linewidth=1.5, label='重叠率阈值 (0.5)')
    ax.set_xlabel('点云重叠率')
    ax.set_ylabel('数量')
    ax.set_title('点云重叠率分布')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_overlap_distribution.png'))
    plt.close(fig)
    print('[Plot] fig_overlap_distribution.png')


# ============================================================
# 图7: Precision-Recall 曲线 (按 score 阈值扫描)
# ============================================================
def plot_precision_recall(loop, traj, skip_near_num, output_dir):
    """
    通过扫描不同的 score 阈值来计算 P-R 曲线。
    Ground truth: overlap >= 0.5 的帧对为正样本。
    """
    if loop is None or len(loop['score']) == 0:
        print('[Skip] No loop data for P-R curve')
        return

    scores = loop['score']
    is_tp = loop['is_tp']

    # 计算所有可能的正样本数量 (用于 recall 的分母)
    # 这里用检测到的 TP 数量作为近似 (实际应该用 GT 回环数)
    total_gt_positives = np.sum(is_tp)
    if total_gt_positives == 0:
        print('[Skip] No true positives for P-R curve')
        return

    thresholds = np.linspace(np.min(scores), np.max(scores), 200)
    precisions = []
    recalls = []

    for thr in thresholds:
        detected = scores >= thr
        if np.sum(detected) == 0:
            continue
        tp = np.sum(detected & (is_tp == 1))
        fp = np.sum(detected & (is_tp == 0))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / total_gt_positives
        precisions.append(precision)
        recalls.append(recall)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(recalls, precisions, 'b-', linewidth=2)
    ax.fill_between(recalls, precisions, alpha=0.1, color='blue')
    ax.set_xlabel('召回率')
    ax.set_ylabel('精确率')
    ax.set_title('精确率-召回率曲线')
    ax.set_xlim([0, 1.05])
    ax.set_ylim([0, 1.05])
    ax.grid(True, alpha=0.3)

    # 计算 F1 max
    f1_scores = [2 * p * r / (p + r) if (p + r) > 0 else 0 for p, r in zip(precisions, recalls)]
    if f1_scores:
        max_f1_idx = np.argmax(f1_scores)
        ax.scatter(recalls[max_f1_idx], precisions[max_f1_idx], c='red', s=100, zorder=5,
                   label=f'最大F1={f1_scores[max_f1_idx]:.3f}')
        ax.legend()

    fig.savefig(os.path.join(output_dir, 'fig_precision_recall.png'))
    plt.close(fig)
    print('[Plot] fig_precision_recall.png')


# ============================================================
# 图8: 描述子数量变化
# ============================================================
def plot_descriptor_count(desc_count, output_dir):
    fig, ax1 = plt.subplots(figsize=(12, 5))
    frames = desc_count['frame_id']
    ax1.plot(frames, desc_count['btc_count'], 'b-', linewidth=0.8, label='BTC描述子数量')
    ax1.set_xlabel('帧编号')
    ax1.set_ylabel('BTC数量', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1.set_title('逐帧描述子数量变化')
    fig.savefig(os.path.join(output_dir, 'fig_descriptor_count.png'))
    plt.close(fig)
    print('[Plot] fig_descriptor_count.png')


# ============================================================
# 图9: 回环检测时间帧对矩阵图
# ============================================================
def plot_loop_matrix(loop, total_frames, output_dir):
    fig, ax = plt.subplots(figsize=(8, 8))
    matrix = np.zeros((total_frames, total_frames))

    for i in range(len(loop['query_id'])):
        qid = loop['query_id'][i]
        mid = loop['matched_id'][i]
        if qid < total_frames and mid < total_frames:
            val = 1 if loop['is_tp'][i] == 1 else -1
            matrix[qid, mid] = val
            matrix[mid, qid] = val

    cmap = plt.cm.RdYlGn
    im = ax.imshow(matrix, cmap=cmap, vmin=-1, vmax=1, origin='lower', aspect='equal')
    ax.set_xlabel('帧编号')
    ax.set_ylabel('帧编号')
    ax.set_title('回环检测帧对矩阵')
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_ticks([-1, 0, 1])
    cbar.set_ticklabels(['假阳性', '无回环', '真阳性'])
    fig.savefig(os.path.join(output_dir, 'fig_loop_matrix.png'))
    plt.close(fig)
    print('[Plot] fig_loop_matrix.png')


# ============================================================
# 图10: 汇总统计表格图
# ============================================================
def plot_summary_table(summary, timing, output_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axis('off')

    total_frames = int(summary.get('total_frames', 0))
    triggered = int(summary.get('triggered_loops', 0))
    true_loops = int(summary.get('true_loops', 0))
    false_loops = int(summary.get('false_loops', 0))
    precision = summary.get('precision', 0)

    table_data = [
        ['总帧数', str(total_frames)],
        ['触发回环数', str(triggered)],
        ['真阳性数', str(true_loops)],
        ['假阳性数', str(false_loops)],
        ['精确率', f'{precision:.4f}'],
        ['平均描述子提取耗时', f'{summary.get("mean_descriptor_time_ms", 0):.2f} ms'],
        ['平均回环查询耗时', f'{summary.get("mean_query_time_ms", 0):.2f} ms'],
        ['平均数据库更新耗时', f'{summary.get("mean_update_time_ms", 0):.2f} ms'],
        ['平均总耗时', f'{summary.get("mean_total_time_ms", 0):.2f} ms'],
    ]

    table = ax.table(cellText=table_data, colLabels=['指标', '数值'],
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)

    # Style header
    for j in range(2):
        table[0, j].set_facecolor('#4C72B0')
        table[0, j].set_text_props(color='white', fontweight='bold')

    ax.set_title('实验结果汇总', fontsize=14, fontweight='bold', pad=20)
    fig.savefig(os.path.join(output_dir, 'fig_summary_table.png'))
    plt.close(fig)
    print('[Plot] fig_summary_table.png')


# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) > 1:
        result_dir = sys.argv[1]
    else:
        result_dir = './btc_results'

    if not os.path.isdir(result_dir):
        print(f'Error: directory {result_dir} not found')
        sys.exit(1)

    output_dir = os.path.join(result_dir, 'figures')
    os.makedirs(output_dir, exist_ok=True)

    print(f'Reading data from: {result_dir}')
    print(f'Saving figures to: {output_dir}')
    print('=' * 50)

    # Load data
    timing = load_timing_data(os.path.join(result_dir, 'timing_per_frame.txt'))
    traj = load_trajectory(os.path.join(result_dir, 'trajectory.txt'))
    desc_count = load_descriptor_count(os.path.join(result_dir, 'descriptor_count.txt'))
    summary = load_summary(os.path.join(result_dir, 'summary.txt'))

    loop_path = os.path.join(result_dir, 'loop_detection.txt')
    loop = None
    if os.path.exists(loop_path) and os.path.getsize(loop_path) > 50:
        loop = load_loop_data(loop_path)

    # Generate all plots
    plot_timing_per_frame(timing, output_dir)
    plot_timing_bar(timing, output_dir)
    plot_timing_pie(timing, output_dir)
    plot_trajectory_with_loops(traj, loop, output_dir)
    plot_descriptor_count(desc_count, output_dir)

    if loop is not None and len(loop['query_id']) > 0:
        plot_score_distribution(loop, output_dir)
        plot_overlap_distribution(loop, output_dir)
        plot_precision_recall(loop, traj, skip_near_num=100, output_dir=output_dir)
        plot_loop_matrix(loop, len(traj['frame_id']), output_dir)

    plot_summary_table(summary, timing, output_dir)

    print('=' * 50)
    print(f'Done! {len(os.listdir(output_dir))} figures generated in {output_dir}')


if __name__ == '__main__':
    main()
