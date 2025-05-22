"""
@Description :   ByteTrack算法实现
                 轻量级多目标跟踪算法
@Author      :   Cao Yingjie
@Time        :   2025/06/20 10:47:48
"""

import numpy as np
from collections import defaultdict, deque
import copy
import torch
from scipy.optimize import linear_sum_assignment


class STrack(object):
    """单个目标跟踪器"""
    _next_id = 0
    track_count = 0

    @staticmethod
    def next_id():
        STrack._next_id += 1
        return STrack._next_id

    def __init__(self, tlwh, score, class_id, temp_feat=None, buffer_size=30):
        """
        初始化单个跟踪器
        
        Args:
            tlwh: 目标框 (top-left x, top-left y, width, height)
            score: 置信度分数
            class_id: 类别ID
            temp_feat: 临时特征
            buffer_size: 状态缓冲区大小
        """
        self.tlwh = np.asarray(tlwh, dtype=np.float64)
        self.score = score
        self.class_id = class_id
        self.tracklet_len = 0
        self.is_activated = False
        self.alpha = 0.9  # 卡尔曼滤波平滑因子

        self.smooth_feat = None
        self.curr_feat = None
        if temp_feat is not None:
            self.update_features(temp_feat)
            
        self.features = deque([], maxlen=buffer_size)
        self.alpha = 0.9
        
        self.state = TrackState.New
        self.kalman_filter = KalmanFilter()
        self.mean, self.covariance = None, None
        
        self.track_id = 0
        self.start_frame = 0
        self.frame_id = 0
        self.time_since_update = 0
        self.end_frame = 0  # 记录最后一次更新的帧

    def predict(self):
        """
        使用卡尔曼滤波预测目标位置
        """
        if self.state != TrackState.Tracked:
            self.mean[7] = 0
        self.mean, self.covariance = self.kalman_filter.predict(self.mean, self.covariance)

    def update(self, new_track, frame_id):
        """
        使用检测结果更新跟踪状态
        
        Args:
            new_track: 新的跟踪对象
            frame_id: 当前帧ID
        """
        self.frame_id = frame_id
        self.time_since_update = 0
        self.tracklet_len += 1

        # 更新特征
        if new_track.curr_feat is not None:
            self.update_features(new_track.curr_feat)
            
        # 更新位置和得分
        new_tlwh = new_track.tlwh
        self.tlwh = new_tlwh
        self.score = new_track.score
        self.class_id = new_track.class_id  # 更新类别信息
        
        # 更新卡尔曼滤波状态
        self.state = TrackState.Tracked
        self.is_activated = True
        
        # 更新卡尔曼滤波器状态
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, self.tlwh_to_xyah(new_tlwh)
        )

    def activate(self, kalman_filter, frame_id):
        """
        激活跟踪器
        
        Args:
            kalman_filter: 卡尔曼滤波器
            frame_id: 当前帧ID
        """
        self.kalman_filter = kalman_filter
        self.track_id = self.next_id()
        
        # 初始化卡尔曼滤波状态
        self.mean, self.covariance = self.kalman_filter.initiate(self.tlwh_to_xyah(self.tlwh))
        
        # 更新状态
        self.tracklet_len = 0
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        self.start_frame = frame_id
        STrack.track_count += 1

    def re_activate(self, new_track, frame_id, new_id=False):
        """
        重新激活跟踪器
        
        Args:
            new_track: 新的跟踪对象
            frame_id: 当前帧ID
            new_id: 是否分配新ID
        """
        # 重新初始化卡尔曼滤波状态
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, self.tlwh_to_xyah(new_track.tlwh)
        )
        
        # 更新特征
        if new_track.curr_feat is not None:
            self.update_features(new_track.curr_feat)
            
        # 更新状态
        self.tracklet_len = 0
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        
        # 如果需要分配新ID
        if new_id:
            self.track_id = self.next_id()
            STrack.track_count += 1
            
        # 更新目标框和得分
        self.tlwh = new_track.tlwh
        self.score = new_track.score
        self.class_id = new_track.class_id  # 更新类别信息

    def mark_lost(self):
        """将跟踪目标标记为丢失状态"""
        self.state = TrackState.Lost
        self.end_frame = self.frame_id
    
    def mark_removed(self):
        """将跟踪目标标记为移除状态"""
        self.state = TrackState.Removed
        self.is_activated = False

    def update_features(self, feat):
        """
        更新特征
        
        Args:
            feat: 新特征
        """
        feat /= np.linalg.norm(feat)
        self.curr_feat = feat
        if self.smooth_feat is None:
            self.smooth_feat = feat
        else:
            self.smooth_feat = self.alpha * self.smooth_feat + (1 - self.alpha) * feat
        self.smooth_feat /= np.linalg.norm(self.smooth_feat)
        self.features.append(feat)

    def tlwh_to_xyah(self, tlwh):
        """
        转换框格式从(top-left x, top-left y, width, height)
        到(center x, center y, aspect ratio, height)
        """
        x, y, w, h = tlwh
        ret = np.asarray([x + w/2, y + h/2, w/h, h], dtype=np.float32)
        return ret

    def to_tlwh(self):
        """获取目标框 (top-left x, top-left y, width, height) 格式"""
        return self.tlwh.copy()

    def to_tlbr(self):
        """获取目标框 (top-left x, top-left y, bottom-right x, bottom-right y) 格式"""
        tlwh = self.tlwh.copy()
        return np.array([tlwh[0], tlwh[1], tlwh[0] + tlwh[2], tlwh[1] + tlwh[3]])

    def to_xyah(self):
        """获取目标框 (center x, center y, aspect ratio, height) 格式"""
        return self.tlwh_to_xyah(self.tlwh)

    @staticmethod
    def tlbr_to_tlwh(tlbr):
        """将(top-left x, top-left y, bottom-right x, bottom-right y)转换为(top-left x, top-left y, width, height)"""
        w = tlbr[2] - tlbr[0]
        h = tlbr[3] - tlbr[1]
        return np.array([tlbr[0], tlbr[1], w, h])


class TrackState(object):
    """跟踪状态"""
    New = 0  # 新目标，等待确认
    Tracked = 1  # 正在跟踪
    Lost = 2  # 暂时丢失，可能会重新找回
    Removed = 3  # 完全丢失，从跟踪列表中移除


class KalmanFilter(object):
    """
    卡尔曼滤波器 - 用于目标运动预测
    状态变量: [x, y, a, h, vx, vy, va, vh]
    (x, y) 是目标中心点
    a 是宽高比 w/h
    h 是高度
    vx, vy, va, vh 是对应的速度
    """
    def __init__(self):
        ndim = 4
        dt = 1.  # 时间步长
        
        # 定义状态转移矩阵 F
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt
            
        # 定义测量矩阵 H
        self._update_mat = np.eye(ndim, 2 * ndim)
        
        # 定义过程噪声协方差矩阵 Q
        self._std_weight_position = 1. / 20
        self._std_weight_velocity = 1. / 160

    def initiate(self, measurement):
        """
        初始化卡尔曼滤波状态
        
        Args:
            measurement: 初始测量值 [x, y, a, h]
        
        Returns:
            mean: 初始状态均值
            covariance: 初始状态协方差
        """
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]
        
        std = [
            2 * self._std_weight_position * measurement[3],  # 位置标准差与目标高度成比例
            2 * self._std_weight_position * measurement[3],
            1e-2,  # 宽高比标准差
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],  # 速度标准差与目标高度成比例
            10 * self._std_weight_velocity * measurement[3],
            1e-5,  # 宽高比变化速度标准差
            10 * self._std_weight_velocity * measurement[3]
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean, covariance):
        """
        预测状态
        
        Args:
            mean: 当前状态均值
            covariance: 当前状态协方差
        
        Returns:
            mean: 预测状态均值
            covariance: 预测状态协方差
        """
        # 计算预测噪声协方差
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3]
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3]
        ]
        
        # 构建过程噪声协方差矩阵 Q
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))
        
        # 预测状态均值和协方差
        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot([
            self._motion_mat, covariance, self._motion_mat.T
        ]) + motion_cov
        
        return mean, covariance

    def update(self, mean, covariance, measurement):
        """
        使用测量值更新状态
        
        Args:
            mean: 预测状态均值
            covariance: 预测状态协方差
            measurement: 测量值 [x, y, a, h]
        
        Returns:
            new_mean: 更新后的状态均值
            new_covariance: 更新后的状态协方差
        """
        # 计算测量噪声协方差矩阵 R
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3]
        ]
        innovation_cov = np.diag(np.square(std))
        
        # 计算卡尔曼增益
        kalman_gain = np.linalg.multi_dot([
            covariance, self._update_mat.T,
            np.linalg.inv(np.linalg.multi_dot([
                self._update_mat, covariance, self._update_mat.T
            ]) + innovation_cov)
        ])
        
        # 计算创新向量
        innovation = measurement - np.dot(self._update_mat, mean)
        
        # 更新状态均值和协方差
        new_mean = mean + np.dot(kalman_gain, innovation)
        new_covariance = covariance - np.linalg.multi_dot([
            kalman_gain, self._update_mat, covariance
        ])
        
        return new_mean, new_covariance


def iou_batch(bbox_a, bbox_b):
    """
    计算两组边界框之间的交并比(IoU)
    
    Args:
        bbox_a: 形状为 (N, 4) 的边界框数组 [x1, y1, x2, y2]
        bbox_b: 形状为 (M, 4) 的边界框数组 [x1, y1, x2, y2]
    
    Returns:
        形状为 (N, M) 的IoU矩阵
    """
    a_tl = bbox_a[:, np.newaxis, :2]
    a_br = bbox_a[:, np.newaxis, 2:]
    b_tl = bbox_b[np.newaxis, :, :2]
    b_br = bbox_b[np.newaxis, :, 2:]
    
    # 计算交集的左上角和右下角
    tl = np.maximum(a_tl, b_tl)
    br = np.minimum(a_br, b_br)
    
    # 计算交集面积
    wh = np.maximum(0.0, br - tl)
    intersection = wh[:, :, 0] * wh[:, :, 1]
    
    # 计算并集面积
    a_area = (a_br[:, :, 0] - a_tl[:, :, 0]) * (a_br[:, :, 1] - a_tl[:, :, 1])
    b_area = (b_br[:, :, 0] - b_tl[:, :, 0]) * (b_br[:, :, 1] - b_tl[:, :, 1])
    union = a_area + b_area - intersection
    
    # 计算IoU
    iou = intersection / np.maximum(union, 1e-10)
    return iou


def iou_rotated_boxes(boxes1, boxes2):
    """
    计算旋转边界框之间的IoU
    注意: 这个函数简化处理，不考虑旋转
    
    Args:
        boxes1: 旋转边界框数组 [x, y, w, h, angle]
        boxes2: 旋转边界框数组 [x, y, w, h, angle]
        
    Returns:
        形状为 (N, M) 的IoU矩阵
    """
    # 简化为非旋转版本的IoU计算
    # 将旋转框转换为标准框 (x1, y1, x2, y2)
    boxes1_standard = []
    for box in boxes1:
        # 如果输入是OBB格式（四个角点）
        if hasattr(box, 'pt1x') and hasattr(box, 'pt2x') and hasattr(box, 'pt3x') and hasattr(box, 'pt4x'):
            x_min = min(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
            y_min = min(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
            x_max = max(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
            y_max = max(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
            boxes1_standard.append([x_min, y_min, x_max, y_max])
        else:
            # 标准中心点+宽高+角度格式
            cx, cy, w, h, _ = box
            x1 = cx - w/2
            y1 = cy - h/2
            x2 = cx + w/2
            y2 = cy + h/2
            boxes1_standard.append([x1, y1, x2, y2])
    
    boxes2_standard = []
    for box in boxes2:
        # 如果输入是OBB格式（四个角点）
        if hasattr(box, 'pt1x') and hasattr(box, 'pt2x') and hasattr(box, 'pt3x') and hasattr(box, 'pt4x'):
            x_min = min(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
            y_min = min(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
            x_max = max(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
            y_max = max(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
            boxes2_standard.append([x_min, y_min, x_max, y_max])
        else:
            # 标准中心点+宽高+角度格式
            cx, cy, w, h, _ = box
            x1 = cx - w/2
            y1 = cy - h/2
            x2 = cx + w/2
            y2 = cy + h/2
            boxes2_standard.append([x1, y1, x2, y2])
    
    return iou_batch(np.array(boxes1_standard), np.array(boxes2_standard))


class ByteTracker(object):
    """ByteTrack多目标跟踪器"""
    
    def __init__(self, track_thresh=0.5, track_buffer=30, match_thresh=0.8, fuse_score=True):
        """
        初始化ByteTrack跟踪器
        
        Args:
            track_thresh: 跟踪阈值，低于该阈值的检测框不会被初始化为跟踪器
            track_buffer: 跟踪缓冲区大小，表示多少帧没有匹配后删除跟踪器
            match_thresh: 匹配阈值，用于关联检测框和跟踪器
            fuse_score: 是否融合检测分数
        """
        self.tracked_tracks = []  # 跟踪中的目标
        self.lost_tracks = []     # 丢失的目标
        self.removed_tracks = []  # 移除的目标
        
        self.frame_id = 0
        self.max_time_lost = track_buffer  # 目标丢失后保留的最大帧数
        
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.fuse_score = fuse_score
        
        self.kalman_filter = KalmanFilter()

    def update(self, detection_results):
        """
        使用当前帧的检测结果更新跟踪器
        
        Args:
            detection_results: 当前帧的检测结果，包含目标框和置信度
        
        Returns:
            list: 跟踪结果列表，每个元素包含目标ID、类别ID、置信度和边界框坐标
        """
        self.frame_id += 1
        activated_tracks = []
        refind_tracks = []
        lost_tracks = []
        removed_tracks = []
        
        # 将检测结果转换为STrack对象列表
        detections = []
        for det in detection_results:
            try:
                # 获取边界框坐标 (x1, y1, x2, y2)
                # 使用OBB的四个角点计算外接矩形
                bbox = [
                    min(det.pt1x, det.pt2x, det.pt3x, det.pt4x),
                    min(det.pt1y, det.pt2y, det.pt3y, det.pt4y),
                    max(det.pt1x, det.pt2x, det.pt3x, det.pt4x),
                    max(det.pt1y, det.pt2y, det.pt3y, det.pt4y)
                ]
                
                # 转换为TLWH格式
                tlwh = STrack.tlbr_to_tlwh(bbox)
                
                # 创建STrack对象
                track = STrack(tlwh, det.score, det.classId)
                detections.append(track)
            except Exception as e:
                print(f"处理检测结果时出错: {str(e)}")
                continue
        
        # 将跟踪中的目标和丢失的目标分别存储
        tracked_tracks = []
        for track in self.tracked_tracks:
            if not track.is_activated:
                continue
            tracked_tracks.append(track)
        
        # 合并当前跟踪中的目标和丢失的目标
        unconfirmed_tracks = [t for t in self.tracked_tracks if not t.is_activated]
        lost_tracks = [t for t in self.lost_tracks]
        
        # 预测当前所有跟踪目标的位置
        for track in tracked_tracks:
            track.predict()
        for track in lost_tracks:
            track.predict()
        
        # 第一阶段匹配: 将高置信度检测结果与跟踪中的目标进行匹配
        high_score_detections = [d for d in detections if d.score >= self.track_thresh]
        
        # 计算跟踪目标和检测框之间的IoU
        if len(tracked_tracks) > 0 and len(high_score_detections) > 0:
            track_boxes = np.array([t.to_tlbr() for t in tracked_tracks])
            det_boxes = np.array([d.to_tlbr() for d in high_score_detections])
            iou_matrix = iou_batch(track_boxes, det_boxes)
            
            # 使用匈牙利算法进行匹配
            row_indices, col_indices = linear_sum_assignment(-iou_matrix)
            matched_indices = np.array(list(zip(row_indices, col_indices)))
            
            # 根据IoU阈值筛选匹配结果
            matches = []
            for row, col in matched_indices:
                if iou_matrix[row, col] >= self.match_thresh:
                    matches.append((row, col))
                    
            # 处理未匹配的跟踪目标和检测框
            unmatched_tracks = [i for i in range(len(tracked_tracks)) if i not in [m[0] for m in matches]]
            unmatched_detections = [i for i in range(len(high_score_detections)) if i not in [m[1] for m in matches]]
            
            # 更新匹配的跟踪目标
            for row, col in matches:
                track = tracked_tracks[row]
                det = high_score_detections[col]
                track.update(det, self.frame_id)
                activated_tracks.append(track)
                
            # 处理未匹配的跟踪目标
            for i in unmatched_tracks:
                track = tracked_tracks[i]
                track.mark_lost()
                lost_tracks.append(track)
        else:
            # 没有跟踪目标或检测框，所有都为未匹配
            unmatched_tracks = list(range(len(tracked_tracks)))
            unmatched_detections = list(range(len(high_score_detections)))
            
        # 第二阶段匹配: 将低置信度检测结果与丢失的目标进行匹配
        low_score_detections = [d for d in detections if d.score < self.track_thresh]
        
        if len(unmatched_tracks) > 0 and len(low_score_detections) > 0:
            track_boxes = np.array([tracked_tracks[i].to_tlbr() for i in unmatched_tracks])
            det_boxes = np.array([d.to_tlbr() for d in low_score_detections])
            iou_matrix = iou_batch(track_boxes, det_boxes)
            
            # 使用匈牙利算法进行匹配
            row_indices, col_indices = linear_sum_assignment(-iou_matrix)
            matched_indices = np.array(list(zip(row_indices, col_indices)))
            
            # 根据IoU阈值筛选匹配结果
            matches = []
            for row, col in matched_indices:
                if iou_matrix[row, col] >= self.match_thresh:
                    matches.append((row, col))
                    
            # 处理未匹配的跟踪目标和检测框
            unmatched_tracks_stage2 = [unmatched_tracks[i] for i in range(len(unmatched_tracks)) if i not in [m[0] for m in matches]]
            unmatched_detections_stage2 = [i for i in range(len(low_score_detections)) if i not in [m[1] for m in matches]]
            
            # 更新匹配的跟踪目标
            for row, col in matches:
                track = tracked_tracks[unmatched_tracks[row]]
                det = low_score_detections[col]
                track.update(det, self.frame_id)
                activated_tracks.append(track)
                
            # 处理未匹配的跟踪目标
            for i in unmatched_tracks_stage2:
                track = tracked_tracks[i]
                track.mark_lost()
                lost_tracks.append(track)
        else:
            # 所有未匹配的跟踪目标都标记为丢失
            for i in unmatched_tracks:
                track = tracked_tracks[i]
                track.mark_lost()
                lost_tracks.append(track)
        
        # 处理未确认的跟踪目标
        detections_for_unconfirmed = high_score_detections.copy()
        if len(unconfirmed_tracks) > 0 and len(detections_for_unconfirmed) > 0:
            track_boxes = np.array([t.to_tlbr() for t in unconfirmed_tracks])
            det_boxes = np.array([d.to_tlbr() for d in detections_for_unconfirmed])
            iou_matrix = iou_batch(track_boxes, det_boxes)
            
            # 使用匈牙利算法进行匹配
            row_indices, col_indices = linear_sum_assignment(-iou_matrix)
            matched_indices = np.array(list(zip(row_indices, col_indices)))
            
            # 根据IoU阈值筛选匹配结果
            matches = []
            for row, col in matched_indices:
                if iou_matrix[row, col] >= self.match_thresh:
                    matches.append((row, col))
                    
            # 处理未匹配的未确认跟踪目标
            unmatched_unconfirmed = [i for i in range(len(unconfirmed_tracks)) if i not in [m[0] for m in matches]]
            
            # 激活匹配的未确认跟踪目标
            for row, col in matches:
                track = unconfirmed_tracks[row]
                det = detections_for_unconfirmed[col]
                track.update(det, self.frame_id)
                activated_tracks.append(track)
                
            # 处理未匹配的未确认跟踪目标
            for i in unmatched_unconfirmed:
                track = unconfirmed_tracks[i]
                track.mark_removed()
                removed_tracks.append(track)
        else:
            # 所有未确认的跟踪目标都标记为移除
            for track in unconfirmed_tracks:
                track.mark_removed()
                removed_tracks.append(track)
        
        # 处理丢失的跟踪目标
        for track in self.lost_tracks:
            if self.frame_id - track.end_frame > self.max_time_lost:
                track.mark_removed()
                removed_tracks.append(track)
        
        # 初始化新的跟踪目标
        for i in unmatched_detections:
            det = high_score_detections[i]
            if det.score >= self.track_thresh:
                det.activate(self.kalman_filter, self.frame_id)
                activated_tracks.append(det)
        
        # 更新跟踪器状态
        for track in self.lost_tracks:
            if track not in lost_tracks and track not in removed_tracks:
                lost_tracks.append(track)
                
        self.tracked_tracks = [t for t in self.tracked_tracks if t not in lost_tracks and t not in removed_tracks]
        self.tracked_tracks.extend(activated_tracks)
        self.lost_tracks = lost_tracks
        self.removed_tracks = removed_tracks
        
        # 返回跟踪结果
        outputs = []
        for track in self.tracked_tracks:
            if track.is_activated:
                track_box = track.to_tlwh()
                track_id = track.track_id
                class_id = track.class_id
                score = track.score
                outputs.append({'track_id': track_id, 'class_id': class_id, 'score': score, 'bbox': track_box})
        
        return outputs

    def reset(self):
        """重置跟踪器"""
        self.tracked_tracks = []
        self.lost_tracks = []
        self.removed_tracks = []
        self.frame_id = 0
        STrack._next_id = 0 