#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC Place Recognition 实验结果绘图脚本
用于毕业设计实验数据可视化
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体支持
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['AR PL UKai CN', 'Noto Sans CJK SC', 'SimHei', 'DejaVu Sans']
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
def plot_timing_per_frame(timing, output_dir, dataset=''):
    fig, ax = plt.subplots(figsize=(12, 5))
    frames = timing['frame_id']
    ax.plot(frames, timing['descriptor_time'], label='描述子提取', linewidth=0.8)
    ax.plot(frames, timing['query_time'], label='回环查询', linewidth=0.8)
    ax.plot(frames, timing['update_time'], label='数据库更新', linewidth=0.8)
    ax.set_xlabel('帧编号')
    ax.set_ylabel('耗时 (ms)')
    ax.set_title(f'逐帧各阶段处理耗时 ({dataset})' if dataset else '逐帧各阶段处理耗时')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_timing_per_frame.png'))
    plt.close(fig)
    print('[Plot] fig_timing_per_frame.png')


# ============================================================
# 图2: 平均耗时柱状图
# ============================================================
def plot_timing_bar(timing, output_dir, dataset=''):
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
    ax.set_title(f'各阶段平均处理耗时 ({dataset})' if dataset else '各阶段平均处理耗时')
    ax.grid(True, axis='y', alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_timing_bar.png'))
    plt.close(fig)
    print('[Plot] fig_timing_bar.png')


# ============================================================
# 图3: 耗时占比饼图
# ============================================================
def plot_timing_pie(timing, output_dir, dataset=''):
    fig, ax = plt.subplots(figsize=(6, 6))
    means = [
        np.mean(timing['descriptor_time']),
        np.mean(timing['query_time']),
        np.mean(timing['update_time']),
    ]
    labels = ['描述子提取', '回环查询', '数据库更新']
    colors = ['#4C72B0', '#55A868', '#C44E52']
    ax.pie(means, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title(f'各阶段耗时占比 ({dataset})' if dataset else '各阶段耗时占比')
    fig.savefig(os.path.join(output_dir, 'fig_timing_pie.png'))
    plt.close(fig)
    print('[Plot] fig_timing_pie.png')


# ============================================================
# 图4: 轨迹图 + 回环连线
# ============================================================
def plot_trajectory_with_loops(traj, loop, output_dir, dataset=''):
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
    ax.set_title(f'轨迹与回环检测结果 ({dataset})' if dataset else '轨迹与回环检测结果')
    ax.legend(loc='best')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_trajectory_loops.png'))
    plt.close(fig)
    print('[Plot] fig_trajectory_loops.png')


# ============================================================
# 图5: 回环检测得分分布直方图
# ============================================================
def plot_score_distribution(loop, output_dir, dataset=''):
    fig, ax = plt.subplots(figsize=(8, 5))
    tp_mask = loop['is_tp'] == 1
    fp_mask = loop['is_tp'] == 0

    if np.any(tp_mask):
        ax.hist(loop['score'][tp_mask], bins=20, alpha=0.7, color='green', label='真阳性', edgecolor='black')
    if np.any(fp_mask):
        ax.hist(loop['score'][fp_mask], bins=20, alpha=0.7, color='red', label='假阳性', edgecolor='black')

    ax.set_xlabel('匹配得分')
    ax.set_ylabel('数量')
    ax.set_title(f'回环检测得分分布 ({dataset})' if dataset else '回环检测得分分布')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_score_distribution.png'))
    plt.close(fig)
    print('[Plot] fig_score_distribution.png')


# ============================================================
# 图6: Overlap 分布直方图
# ============================================================
def plot_overlap_distribution(loop, output_dir, dataset=''):
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
    ax.set_title(f'点云重叠率分布 ({dataset})' if dataset else '点云重叠率分布')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(os.path.join(output_dir, 'fig_overlap_distribution.png'))
    plt.close(fig)
    print('[Plot] fig_overlap_distribution.png')


# ============================================================
# 图7: Precision-Recall 曲线 (按 score 阈值扫描)
# ============================================================
def plot_precision_recall(loop, traj, skip_near_num, output_dir, dataset=''):
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
    ax.set_title(f'精确率-召回率曲线 ({dataset})' if dataset else '精确率-召回率曲线')
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
def plot_descriptor_count(desc_count, output_dir, dataset=''):
    fig, ax1 = plt.subplots(figsize=(12, 5))
    frames = desc_count['frame_id']
    ax1.plot(frames, desc_count['btc_count'], 'b-', linewidth=0.8, label='BTC描述子数量')
    ax1.set_xlabel('帧编号')
    ax1.set_ylabel('BTC数量', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1.set_title(f'逐帧描述子数量变化 ({dataset})' if dataset else '逐帧描述子数量变化')
    fig.savefig(os.path.join(output_dir, 'fig_descriptor_count.png'))
    plt.close(fig)
    print('[Plot] fig_descriptor_count.png')


# ============================================================
# 图9: 回环检测时间帧对矩阵图
# ============================================================
def plot_loop_matrix(loop, total_frames, output_dir, dataset=''):
    fig, ax = plt.subplots(figsize=(8, 8))

    tp_q, tp_m, fp_q, fp_m = [], [], [], []
    for i in range(len(loop['query_id'])):
        qid = loop['query_id'][i]
        mid = loop['matched_id'][i]
        if qid < total_frames and mid < total_frames:
            if loop['is_tp'][i] == 1:
                tp_q.extend([qid, mid])
                tp_m.extend([mid, qid])
            else:
                fp_q.extend([qid, mid])
                fp_m.extend([mid, qid])

    # 先画对角线参考
    ax.plot([0, total_frames], [0, total_frames], 'k--', alpha=0.2, linewidth=0.5)
    if fp_q:
        ax.scatter(fp_q, fp_m, c='red', s=20, marker='x', linewidths=1.0, label='假阳性', zorder=2)
    if tp_q:
        ax.scatter(tp_q, tp_m, c='limegreen', s=20, marker='o', edgecolors='darkgreen',
                   linewidths=0.5, label='真阳性', zorder=3)

    ax.set_xlim(0, total_frames)
    ax.set_ylim(0, total_frames)
    ax.set_aspect('equal')
    ax.set_xlabel('帧编号')
    ax.set_ylabel('帧编号')
    ax.set_title(f'回环检测帧对矩阵 ({dataset})' if dataset else '回环检测帧对矩阵')
    ax.legend(loc='upper left', fontsize=10)
    fig.savefig(os.path.join(output_dir, 'fig_loop_matrix.png'), dpi=150)
    plt.close(fig)
    print('[Plot] fig_loop_matrix.png')


# ============================================================
# 图10: 汇总统计表格图
# ============================================================
def plot_summary_table(summary, timing, output_dir, dataset=''):
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

    ax.set_title(f'实验结果汇总 ({dataset})' if dataset else '实验结果汇总', fontsize=14, fontweight='bold', pad=20)
    fig.savefig(os.path.join(output_dir, 'fig_summary_table.png'))
    plt.close(fig)
    print('[Plot] fig_summary_table.png')


# ============================================================
# Main
# ============================================================
# ============================================================
# 整合图：每类图四个子图，对应 kitti02/05/06/07
# ============================================================

SEQUENCES = ['kitti00', 'kitti02', 'kitti05', 'kitti07']
SEQ_LABELS = ['KITTI-00', 'KITTI-02', 'KITTI-05', 'KITTI-07']


def _load_seq_data(base_dir, seq):
    d = os.path.join(base_dir, seq)
    if not os.path.isdir(d):
        return None
    try:
        timing = load_timing_data(os.path.join(d, 'timing_per_frame.txt'))
        traj = load_trajectory(os.path.join(d, 'trajectory.txt'))
        desc_count = load_descriptor_count(os.path.join(d, 'descriptor_count.txt'))
        summary = load_summary(os.path.join(d, 'summary.txt'))
        loop = None
        lp = os.path.join(d, 'loop_detection.txt')
        if os.path.exists(lp) and os.path.getsize(lp) > 50:
            loop = load_loop_data(lp)
        return dict(timing=timing, traj=traj, desc_count=desc_count,
                    summary=summary, loop=loop)
    except Exception as e:
        print(f'[Warn] Failed to load {seq}: {e}')
        return None


def plot_combined_trajectory(all_data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 16))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None:
            ax.set_title(f'{label} (数据缺失)'); ax.axis('off'); continue
        traj, loop = d['traj'], d['loop']
        ax.plot(traj['x'], traj['y'], 'b-', linewidth=0.5, label='轨迹', zorder=1)
        ax.scatter(traj['x'][0], traj['y'][0], c='green', s=60, marker='^', label='起点', zorder=3)
        ax.scatter(traj['x'][-1], traj['y'][-1], c='red', s=60, marker='v', label='终点', zorder=3)
        if loop is not None and len(loop['query_id']) > 0:
            tp_mask = loop['is_tp'] == 1
            fp_mask = loop['is_tp'] == 0
            for i in np.where(fp_mask)[0]:
                qid, mid = loop['query_id'][i], loop['matched_id'][i]
                if qid < len(traj['x']) and mid < len(traj['x']):
                    ax.plot([traj['x'][qid], traj['x'][mid]], [traj['y'][qid], traj['y'][mid]],
                            'r--', linewidth=0.8, alpha=0.5, zorder=2)
            for i in np.where(tp_mask)[0]:
                qid, mid = loop['query_id'][i], loop['matched_id'][i]
                if qid < len(traj['x']) and mid < len(traj['x']):
                    ax.plot([traj['x'][qid], traj['x'][mid]], [traj['y'][qid], traj['y'][mid]],
                            'g-', linewidth=1.2, alpha=0.6, zorder=2)
            ax.plot([], [], 'g-', linewidth=2, label='真阳性')
            ax.plot([], [], 'r--', linewidth=2, label='假阳性')
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)')
        ax.set_aspect('equal'); ax.legend(loc='best', fontsize=8); ax.grid(True, alpha=0.3)
    fig.suptitle('轨迹与回环检测结果对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_trajectory.png')); plt.close(fig)
    print('[Combined] combined_trajectory.png')


def plot_combined_timing_per_frame(all_data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(18, 10))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None:
            ax.set_title(f'{label} (数据缺失)'); ax.axis('off'); continue
        t = d['timing']
        ax.plot(t['frame_id'], t['descriptor_time'], linewidth=0.7, label='描述子提取')
        ax.plot(t['frame_id'], t['query_time'], linewidth=0.7, label='回环查询')
        ax.plot(t['frame_id'], t['update_time'], linewidth=0.7, label='数据库更新')
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_xlabel('帧编号'); ax.set_ylabel('耗时 (ms)')
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.suptitle('逐帧各阶段处理耗时对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_timing_per_frame.png')); plt.close(fig)
    print('[Combined] combined_timing_per_frame.png')


def plot_combined_timing_bar(all_data, output_dir):
    colors = ['#4C72B0', '#55A868', '#C44E52']
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None:
            ax.set_title(f'{label} (数据缺失)'); ax.axis('off'); continue
        t = d['timing']
        xlabels = ['描述子\n提取', '回环\n查询', '数据库\n更新']
        means = [np.mean(t['descriptor_time']), np.mean(t['query_time']), np.mean(t['update_time'])]
        stds  = [np.std(t['descriptor_time']),  np.std(t['query_time']),  np.std(t['update_time'])]
        bars = ax.bar(xlabels, means, yerr=stds, color=colors, capsize=4, edgecolor='black', linewidth=0.5)
        for bar, m in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{m:.1f}', ha='center', va='bottom', fontsize=9)
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_ylabel('耗时 (ms)'); ax.grid(True, axis='y', alpha=0.3)
    fig.suptitle('各阶段平均处理耗时对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_timing_bar.png')); plt.close(fig)
    print('[Combined] combined_timing_bar.png')


def plot_combined_score_distribution(all_data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None or d['loop'] is None:
            ax.set_title(f'{label} (无回环数据)'); ax.axis('off'); continue
        loop = d['loop']
        tp = loop['is_tp'] == 1; fp = loop['is_tp'] == 0
        if np.any(tp):
            ax.hist(loop['score'][tp], bins=20, alpha=0.7, color='green', label='真阳性', edgecolor='black')
        if np.any(fp):
            ax.hist(loop['score'][fp], bins=20, alpha=0.7, color='red', label='假阳性', edgecolor='black')
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_xlabel('匹配得分'); ax.set_ylabel('数量')
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.suptitle('回环检测得分分布对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_score_distribution.png')); plt.close(fig)
    print('[Combined] combined_score_distribution.png')


def plot_combined_precision_recall(all_data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None or d['loop'] is None:
            ax.set_title(f'{label} (无回环数据)'); ax.axis('off'); continue
        loop = d['loop']
        scores = loop['score']; is_tp = loop['is_tp']
        total_gt = np.sum(is_tp)
        if total_gt == 0:
            ax.set_title(f'{label} (无真阳性)'); ax.axis('off'); continue
        thresholds = np.linspace(np.min(scores), np.max(scores), 200)
        precisions, recalls = [], []
        for thr in thresholds:
            detected = scores >= thr
            if np.sum(detected) == 0: continue
            tp_n = np.sum(detected & (is_tp == 1))
            fp_n = np.sum(detected & (is_tp == 0))
            precisions.append(tp_n / (tp_n + fp_n))
            recalls.append(tp_n / total_gt)
        ax.plot(recalls, precisions, 'b-', linewidth=2)
        ax.fill_between(recalls, precisions, alpha=0.1, color='blue')
        f1s = [2*p*r/(p+r) if (p+r) > 0 else 0 for p, r in zip(precisions, recalls)]
        if f1s:
            idx = int(np.argmax(f1s))
            ax.scatter(recalls[idx], precisions[idx], c='red', s=80, zorder=5,
                       label=f'F1={f1s[idx]:.3f}')
            ax.legend(fontsize=9)
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_xlabel('召回率'); ax.set_ylabel('精确率')
        ax.set_xlim([0, 1.05]); ax.set_ylim([0, 1.05]); ax.grid(True, alpha=0.3)
    fig.suptitle('精确率-召回率曲线对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_precision_recall.png')); plt.close(fig)
    print('[Combined] combined_precision_recall.png')


def plot_combined_loop_matrix(all_data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 16))
    axes = axes.flatten()
    for ax, seq, label in zip(axes, SEQUENCES, SEQ_LABELS):
        d = all_data.get(seq)
        if d is None or d['loop'] is None:
            ax.set_title(f'{label} (无回环数据)'); ax.axis('off'); continue
        loop = d['loop']
        n = len(d['traj']['frame_id'])
        tp_q, tp_m, fp_q, fp_m = [], [], [], []
        for i in range(len(loop['query_id'])):
            qid, mid = loop['query_id'][i], loop['matched_id'][i]
            if qid < n and mid < n:
                if loop['is_tp'][i] == 1:
                    tp_q.extend([qid, mid]); tp_m.extend([mid, qid])
                else:
                    fp_q.extend([qid, mid]); fp_m.extend([mid, qid])
        ax.plot([0, n], [0, n], 'k--', alpha=0.2, linewidth=0.5)
        if fp_q:
            ax.scatter(fp_q, fp_m, c='red', s=8, marker='x', linewidths=0.8, label='假阳性', zorder=2)
        if tp_q:
            ax.scatter(tp_q, tp_m, c='limegreen', s=8, marker='o', edgecolors='darkgreen',
                       linewidths=0.3, label='真阳性', zorder=3)
        ax.set_xlim(0, n); ax.set_ylim(0, n); ax.set_aspect('equal')
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_xlabel('帧编号'); ax.set_ylabel('帧编号')
        ax.legend(loc='upper left', fontsize=8, markerscale=2)
    fig.suptitle('回环检测帧对矩阵对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_loop_matrix.png'), dpi=150); plt.close(fig)
    print('[Combined] combined_loop_matrix.png')


def plot_combined_summary(all_data, output_dir):
    seqs_ok = [s for s in SEQUENCES if all_data.get(s) is not None]
    labels_ok = [SEQ_LABELS[SEQUENCES.index(s)] for s in seqs_ok]
    precisions  = [all_data[s]['summary'].get('precision', 0) for s in seqs_ok]
    desc_times  = [all_data[s]['summary'].get('mean_descriptor_time_ms', 0) for s in seqs_ok]
    query_times = [all_data[s]['summary'].get('mean_query_time_ms', 0) for s in seqs_ok]
    true_loops  = [int(all_data[s]['summary'].get('true_loops', 0)) for s in seqs_ok]
    false_loops = [int(all_data[s]['summary'].get('false_loops', 0)) for s in seqs_ok]
    x = np.arange(len(seqs_ok)); w = 0.35

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    ax = axes[0, 0]
    bars = ax.bar(x, precisions, color='#4C72B0', edgecolor='black', linewidth=0.5)
    for bar, v in zip(bars, precisions):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{v:.3f}', ha='center', va='bottom', fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(labels_ok)
    ax.set_ylabel('精确率'); ax.set_ylim(0, 1.15)
    ax.set_title('回环检测精确率', fontweight='bold'); ax.grid(True, axis='y', alpha=0.3)

    ax = axes[0, 1]
    ax.bar(x - w/2, desc_times,  w, label='描述子提取', color='#4C72B0', edgecolor='black', linewidth=0.5)
    ax.bar(x + w/2, query_times, w, label='回环查询',   color='#55A868', edgecolor='black', linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(labels_ok)
    ax.set_ylabel('平均耗时 (ms)')
    ax.set_title('各阶段平均耗时对比', fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, axis='y', alpha=0.3)

    ax = axes[1, 0]
    b1 = ax.bar(x - w/2, true_loops,  w, label='真阳性', color='#55A868', edgecolor='black', linewidth=0.5)
    b2 = ax.bar(x + w/2, false_loops, w, label='假阳性', color='#C44E52', edgecolor='black', linewidth=0.5)
    for bar, v in zip(b1, true_loops):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(v), ha='center', va='bottom', fontsize=9)
    for bar, v in zip(b2, false_loops):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(v), ha='center', va='bottom', fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels_ok)
    ax.set_ylabel('回环数量')
    ax.set_title('真阳性 vs 假阳性数量', fontweight='bold')
    ax.legend(fontsize=9); ax.grid(True, axis='y', alpha=0.3)

    ax = axes[1, 1]; ax.axis('off')
    col_labels = ['序列', '总帧数', '精确率', '均值总耗时(ms)']
    table_data = []
    for s, lab in zip(seqs_ok, labels_ok):
        sm = all_data[s]['summary']
        table_data.append([lab, str(int(sm.get('total_frames', 0))),
                           f"{sm.get('precision', 0):.4f}",
                           f"{sm.get('mean_total_time_ms', 0):.2f}"])
    tbl = ax.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1.2, 2.0)
    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor('#4C72B0')
        tbl[0, j].set_text_props(color='white', fontweight='bold')
    ax.set_title('汇总参数表', fontweight='bold', pad=60)

    fig.suptitle('KITTI 序列实验结果对比', fontsize=16, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(output_dir, 'combined_summary.png')); plt.close(fig)
    print('[Combined] combined_summary.png')


def main_combined(base_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f'Loading data from: {base_dir}')
    print(f'Saving combined figures to: {output_dir}')
    print('=' * 50)
    all_data = {}
    for seq in SEQUENCES:
        d = _load_seq_data(base_dir, seq)
        if d is not None:
            all_data[seq] = d; print(f'  [OK] {seq}')
        else:
            print(f'  [Miss] {seq}')
    plot_combined_trajectory(all_data, output_dir)
    plot_combined_timing_per_frame(all_data, output_dir)
    plot_combined_timing_bar(all_data, output_dir)
    plot_combined_score_distribution(all_data, output_dir)
    plot_combined_precision_recall(all_data, output_dir)
    plot_combined_loop_matrix(all_data, output_dir)
    plot_combined_summary(all_data, output_dir)
    print('=' * 50)
    print(f'Done! {len(os.listdir(output_dir))} figures in {output_dir}')


def main():
    parser = argparse.ArgumentParser(description='BTC 实验结果绘图')
    parser.add_argument('result_dir', nargs='?', default='./btc_results', help='实验结果目录')
    parser.add_argument('--dataset', '-d', default='', help='数据集名称，显示在图表标题中 (如 KITTI-05)')
    parser.add_argument('--combined', '-c', action='store_true',
                        help='生成整合对比图（kitti02/05/06/07 各一子图），result_dir 为包含各序列子目录的父目录')
    args = parser.parse_args()

    result_dir = args.result_dir
    ds = args.dataset

    if not os.path.isdir(result_dir):
        print(f'Error: directory {result_dir} not found')
        sys.exit(1)

    if args.combined:
        output_dir = os.path.join(result_dir, 'figures')
        main_combined(result_dir, output_dir)
        return

    output_dir = os.path.join(result_dir, 'figures')
    os.makedirs(output_dir, exist_ok=True)

    print(f'Reading data from: {result_dir}')
    print(f'Saving figures to: {output_dir}')
    if ds:
        print(f'Dataset label: {ds}')
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
    plot_timing_per_frame(timing, output_dir, ds)
    plot_timing_bar(timing, output_dir, ds)
    plot_timing_pie(timing, output_dir, ds)
    plot_trajectory_with_loops(traj, loop, output_dir, ds)
    plot_descriptor_count(desc_count, output_dir, ds)

    if loop is not None and len(loop['query_id']) > 0:
        plot_score_distribution(loop, output_dir, ds)
        plot_overlap_distribution(loop, output_dir, ds)
        plot_precision_recall(loop, traj, skip_near_num=100, output_dir=output_dir, dataset=ds)
        plot_loop_matrix(loop, len(traj['frame_id']), output_dir, ds)

    plot_summary_table(summary, timing, output_dir, ds)

    print('=' * 50)
    print(f'Done! {len(os.listdir(output_dir))} figures generated in {output_dir}')


if __name__ == '__main__':
    main()
