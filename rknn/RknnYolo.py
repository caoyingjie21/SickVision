"""
@Description :   Define the model loading class, to export rknn model and using.
                 the file must run on linux and install rknn-toolkit2 with python.
                 more information refer to https://github.com/airockchip/rknn-toolkit2/tree/master
@Author      :   Cao Yingjie
@Time        :   2025/04/23 08:47:48
"""

import os
import sys
import urllib
import urllib.request
import time
import numpy as np
import argparse
import cv2,math
from math import ceil
from itertools import product as product
from shapely.geometry import Polygon

# 导入ByteTrack跟踪器
from ByteTracker import ByteTracker

# from rknn.api import RKNN
from rknn.api import RKNN

class RKNN_YOLO:
    """
    RKNN YOLO模型封装类
    用于加载和运行RKNN模型进行目标检测
    """
    
    def __init__(self, model_path, target='rk3588', device_id=None, conf_threshold=0.45, nms_threshold=0.45):
        """
        初始化RKNN YOLO模型
        
        Args:
            model_path (str): RKNN模型路径
            target (str, optional): 目标RKNPU平台. 默认为 'rk3588'
            device_id (str, optional): 设备ID. 默认为 None
            conf_threshold (float, optional): 置信度阈值. 默认为 0.45
            nms_threshold (float, optional): NMS阈值. 默认为 0.45
        """
        self.CLASSES = ['seasoning']
        self.meshgrid = []
        self.class_num = len(self.CLASSES)
        self.head_num = 3
        self.strides = [8, 16, 32]
        self.map_size = [[80, 80], [40, 40], [20, 20]]
        self.reg_num = 16
        self.input_height = 640
        self.input_width = 640
        self.nms_thresh = nms_threshold
        self.object_thresh = conf_threshold
        self.conf_threshold = conf_threshold  # 添加置信度阈值属性
        self.nms_threshold = nms_threshold    # 添加NMS阈值属性
        self.rknn = None
        
        # 初始化ByteTrack跟踪器
        self.tracker = ByteTracker(track_thresh=0.5, track_buffer=30, match_thresh=0.8)
        self.with_tracking = True  # 跟踪器开关
        
        try:
            # 初始化RKNN
            self.rknn = RKNN(verbose=True)
            
            # 加载模型
            ret = self.rknn.load_rknn(model_path)
            if ret != 0:
                raise RuntimeError(f'Load RKNN model "{model_path}" failed!')
                
            # 初始化运行时环境，使用所有三个NPU核心
            ret = self.rknn.init_runtime(
                target=target,
                device_id=device_id,
                core_mask=RKNN.NPU_CORE_0 | RKNN.NPU_CORE_1 | RKNN.NPU_CORE_2  # 使用所有三个NPU核心
            )
            if ret != 0:
                raise RuntimeError('Init runtime environment failed!')
            
            # 生成网格
            self._generate_meshgrid()
        except Exception as e:
            # 确保在初始化失败时释放资源
            if self.rknn is not None:
                try:
                    self.rknn.release()
                except:
                    pass
                self.rknn = None
            raise RuntimeError(f"初始化RKNN_YOLO时出错: {str(e)}")
        
    def _generate_meshgrid(self):
        """生成网格坐标"""
        for index in range(self.head_num):
            for i in range(self.map_size[index][0]):
                for j in range(self.map_size[index][1]):
                    self.meshgrid.append(j + 0.5)
                    self.meshgrid.append(i + 0.5)
                    
    def _get_covariance_matrix(self, boxes):
        """计算协方差矩阵"""
        a, b, c = boxes.w, boxes.h, boxes.angle
        cos = math.cos(c)
        sin = math.sin(c)
        cos2 = math.pow(cos, 2)
        sin2 = math.pow(sin, 2)
        return a * cos2 + b * sin2, a * sin2 + b * cos2, (a - b) * cos * sin
        
    def _probiou(self, obb1, obb2, eps=1e-7):
        """计算旋转框IOU"""
        x1, y1 = obb1.x, obb1.y
        x2, y2 = obb2.x, obb2.y
        a1, b1, c1 = self._get_covariance_matrix(obb1)
        a2, b2, c2 = self._get_covariance_matrix(obb2)

        t1 = (((a1 + a2) * math.pow((y1 - y2), 2) + (b1 + b2) * math.pow((x1 - x2), 2)) / ((a1 + a2) * (b1 + b2) - math.pow((c1 + c2), 2) + eps)) * 0.25
        t2 = (((c1 + c2) * (x2 - x1) * (y1 - y2)) / ((a1 + a2) * (b1 + b2) - math.pow((c1 + c2), 2) + eps)) * 0.5

        temp1 = (a1 * b1 - math.pow(c1, 2)) if (a1 * b1 - math.pow(c1, 2)) > 0 else 0
        temp2 = (a2 * b2 - math.pow(c2, 2)) if (a2 * b2 - math.pow(c2, 2)) > 0 else 0
        t3 = math.log((((a1 + a2) * (b1 + b2) - math.pow((c1 + c2), 2)) / (4 * math.sqrt((temp1 * temp2)) + eps)+ eps)) * 0.5

        if (t1 + t2 + t3) > 100:
            bd = 100
        elif (t1 + t2 + t3) < eps:
            bd = eps
        else:
            bd = t1 + t2 + t3
        hd = math.sqrt((1.0 - math.exp(-bd) + eps))
        return 1 - hd
        
    def _nms_rotated(self, boxes, nms_thresh):
        """旋转框NMS"""
        pred_boxes = []
        sort_boxes = sorted(boxes, key=lambda x: x.score, reverse=True)
        for i in range(len(sort_boxes)):
            if sort_boxes[i].classId != -1:
                pred_boxes.append(sort_boxes[i])
                for j in range(i + 1, len(sort_boxes), 1):
                    ious = self._probiou(sort_boxes[i], sort_boxes[j])
                    if ious > nms_thresh:
                        sort_boxes[j].classId = -1
        return pred_boxes
        
    def _sigmoid(self, x):
        """Sigmoid函数"""
        return 1 / (1 + math.exp(-x))
        
    def _xywhr2xyxyxyxy(self, x, y, w, h, angle):
        """
        转换中心点格式 (x, y, w, h, angle) 到四点格式 (x1, y1, x2, y2, x3, y3, x4, y4)
        
        Args:
            x, y: 中心点坐标
            w, h: 宽度和高度
            angle: 旋转角度（弧度）
            
        Returns:
            四个角点的坐标
        """
        try:
            # 计算旋转角度的正弦和余弦
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            
            # 计算未旋转状态下的四个角点偏移量
            w2, h2 = w / 2.0, h / 2.0
            
            # 生成四个角点（顺时针方向）
            pt1x = x - w2 * cos_a + h2 * sin_a
            pt1y = y - w2 * sin_a - h2 * cos_a
            
            pt2x = x + w2 * cos_a + h2 * sin_a
            pt2y = y + w2 * sin_a - h2 * cos_a
            
            pt3x = x + w2 * cos_a - h2 * sin_a
            pt3y = y + w2 * sin_a + h2 * cos_a
            
            pt4x = x - w2 * cos_a - h2 * sin_a
            pt4y = y - w2 * sin_a + h2 * cos_a
            
            # 确保返回的坐标是有效的
            if (np.isnan(pt1x) or np.isnan(pt1y) or np.isnan(pt2x) or np.isnan(pt2y) or 
                np.isnan(pt3x) or np.isnan(pt3y) or np.isnan(pt4x) or np.isnan(pt4y)):
                # 如果有NaN值，退回到非旋转框
                pt1x, pt1y = x - w2, y - h2
                pt2x, pt2y = x + w2, y - h2
                pt3x, pt3y = x + w2, y + h2
                pt4x, pt4y = x - w2, y + h2
                print(f"警告: 检测到NaN坐标，退回到非旋转框。输入: x={x}, y={y}, w={w}, h={h}, angle={angle}")
            
            return pt1x, pt1y, pt2x, pt2y, pt3x, pt3y, pt4x, pt4y
        
        except Exception as e:
            # 出现异常时，退回到非旋转框
            w2, h2 = w / 2.0, h / 2.0
            pt1x, pt1y = x - w2, y - h2
            pt2x, pt2y = x + w2, y - h2
            pt3x, pt3y = x + w2, y + h2
            pt4x, pt4y = x - w2, y + h2
            print(f"旋转边界框计算异常，退回到非旋转框: {str(e)}")
            return pt1x, pt1y, pt2x, pt2y, pt3x, pt3y, pt4x, pt4y
        
    def _postprocess(self, out):
        """后处理函数"""
        detect_result = []
        output = []
        for i in range(len(out)):
            output.append(out[i].reshape((-1)))

        gridIndex = -2
        cls_index = 0
        cls_max = 0

        for index in range(self.head_num):
            reg = output[index * 2 + 0]
            cls = output[index * 2 + 1]
            ang = output[self.head_num * 2 + index]

            for h in range(self.map_size[index][0]):
                for w in range(self.map_size[index][1]):
                    gridIndex += 2

                    if 1 == self.class_num:
                        cls_max = self._sigmoid(cls[0 * self.map_size[index][0] * self.map_size[index][1] + h * self.map_size[index][1] + w])
                        cls_index = 0
                    else:
                        for cl in range(self.class_num):
                            cls_val = cls[cl * self.map_size[index][0] * self.map_size[index][1] + h * self.map_size[index][1] + w]
                            if 0 == cl:
                                cls_max = cls_val
                                cls_index = cl
                            else:
                                if cls_val > cls_max:
                                    cls_max = cls_val
                                    cls_index = cl
                        cls_max = self._sigmoid(cls_max)

                    if cls_max > self.object_thresh:
                        regdfl = []
                        for lc in range(4):
                            sfsum = 0
                            locval = 0
                            for df in range(self.reg_num):
                                temp = math.exp(reg[((lc * self.reg_num) + df) * self.map_size[index][0] * self.map_size[index][1] + h * self.map_size[index][1] + w])
                                reg[((lc * self.reg_num) + df) * self.map_size[index][0] * self.map_size[index][1] + h * self.map_size[index][1] + w] = temp
                                sfsum += temp

                            for df in range(self.reg_num):
                                sfval = reg[((lc * self.reg_num) + df) * self.map_size[index][0] * self.map_size[index][1] + h * self.map_size[index][1] + w] / sfsum
                                locval += sfval * df
                            regdfl.append(locval)

                        angle = (self._sigmoid(ang[h * self.map_size[index][1] + w]) - 0.25) * math.pi

                        left, top, right, bottom = regdfl[0], regdfl[1], regdfl[2], regdfl[3]
                        cos, sin = math.cos(angle), math.sin(angle)
                        fx = (right - left) / 2
                        fy = (bottom - top) / 2

                        cx = ((fx * cos - fy * sin) + self.meshgrid[gridIndex + 0]) * self.strides[index]
                        cy = ((fx * sin + fy * cos) + self.meshgrid[gridIndex + 1])* self.strides[index]
                        cw = (left + right) * self.strides[index]
                        ch = (top + bottom) * self.strides[index]

                        box = CSXYWHR(cls_index, cls_max, cx, cy, cw, ch, angle)
                        detect_result.append(box)

        pred_boxes = self._nms_rotated(detect_result, self.nms_thresh)
        result = []
        
        for i in range(len(pred_boxes)):
            classid = pred_boxes[i].classId
            score = pred_boxes[i].score
            cx = pred_boxes[i].x
            cy = pred_boxes[i].y
            cw = pred_boxes[i].w
            ch = pred_boxes[i].h
            angle = pred_boxes[i].angle

            bw_ = cw if cw > ch else ch
            bh_ = ch if cw > ch else cw
            bt = angle % math.pi if cw > ch else (angle + math.pi / 2) % math.pi

            pt1x, pt1y, pt2x, pt2y, pt3x, pt3y, pt4x, pt4y = self._xywhr2xyxyxyxy(cx, cy, bw_, bh_, bt)
            bbox = DetectBox(classid, score, pt1x, pt1y, pt2x, pt2y, pt3x, pt3y, pt4x, pt4y, angle)
            result.append(bbox)
            
        return result
        
    def detect(self, image):
        """
        对输入图像进行目标检测
        
        Args:
            image (numpy.ndarray): 输入图像，BGR格式
            
        Returns:
            list: 检测结果列表，每个元素为DetectBox对象
        """
        # 预处理
        image_h, image_w = image.shape[:2]
        image = cv2.resize(image, (self.input_width, self.input_height), interpolation=cv2.INTER_LINEAR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = np.expand_dims(image, 0)
        
        # 推理
        results = self.rknn.inference(inputs=[image], data_format='nhwc')
        
        # 后处理
        pred_boxes = self._postprocess(results)
        
        # 转换回原始图像尺寸
        for box in pred_boxes:
            box.pt1x = int(box.pt1x / self.input_width * image_w)
            box.pt1y = int(box.pt1y / self.input_height * image_h)
            box.pt2x = int(box.pt2x / self.input_width * image_w)
            box.pt2y = int(box.pt2y / self.input_height * image_h)
            box.pt3x = int(box.pt3x / self.input_width * image_w)
            box.pt3y = int(box.pt3y / self.input_height * image_h)
            box.pt4x = int(box.pt4x / self.input_width * image_w)
            box.pt4y = int(box.pt4y / self.input_height * image_h)
            
        return pred_boxes
    
    def detect_and_track(self, image):
        """
        对输入图像进行目标检测和跟踪
        
        Args:
            image (numpy.ndarray): 输入图像，BGR格式
            
        Returns:
            list: 跟踪结果列表，每个元素为TrackBox对象
        """
        # 目标检测
        detection_boxes = self.detect(image)
        
        # 如果没有启用跟踪，直接返回检测结果
        if not self.with_tracking:
            return [{'detect_box': box, 'track_id': -1, 'class_id': box.classId, 'score': box.score} for box in detection_boxes]
        
        # 如果没有检测到目标，返回空列表
        if len(detection_boxes) == 0:
            return []
            
        # 使用ByteTrack进行跟踪
        tracking_results = self.tracker.update(detection_boxes)
        
        # 构建跟踪结果列表
        tracked_boxes = []
        
        # 将跟踪结果与检测框对应起来
        for track_result in tracking_results:
            track_id = track_result['track_id']
            # 跟踪器返回的是TLWH格式
            track_bbox = track_result['bbox']  # (x, y, w, h)格式
            class_id = track_result['class_id']
            score = track_result['score']
            
            # 找到对应的检测框
            matched_box = None
            best_iou = 0
            
            for box in detection_boxes:
                if box.classId == class_id:
                    # 计算检测框的中心点和跟踪结果的中心点
                    det_center_x = (box.pt1x + box.pt2x + box.pt3x + box.pt4x) / 4
                    det_center_y = (box.pt1y + box.pt2y + box.pt3y + box.pt4y) / 4
                    
                    # 跟踪结果的中心点
                    track_center_x = track_bbox[0] + track_bbox[2] / 2
                    track_center_y = track_bbox[1] + track_bbox[3] / 2
                    
                    # 计算两个中心点之间的欧氏距离
                    distance = np.sqrt((det_center_x - track_center_x)**2 + (det_center_y - track_center_y)**2)
                    
                    # 获取检测框和跟踪框的面积，用于计算IoU
                    det_min_x = min(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
                    det_min_y = min(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
                    det_max_x = max(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
                    det_max_y = max(box.pt1y, box.pt2y, box.pt3y, box.pt4y)
                    
                    det_area = (det_max_x - det_min_x) * (det_max_y - det_min_y)
                    
                    track_area = track_bbox[2] * track_bbox[3]
                    
                    # 计算交集区域
                    x_overlap = max(0, min(det_max_x, track_bbox[0] + track_bbox[2]) - max(det_min_x, track_bbox[0]))
                    y_overlap = max(0, min(det_max_y, track_bbox[1] + track_bbox[3]) - max(det_min_y, track_bbox[1]))
                    intersection = x_overlap * y_overlap
                    
                    # 计算IoU
                    union = det_area + track_area - intersection
                    iou = intersection / (union + 1e-6)
                    
                    # 优先匹配IoU大的，其次考虑中心点距离
                    match_score = iou - 0.01 * distance
                    
                    if match_score > best_iou:
                        best_iou = match_score
                        matched_box = box
            
            # 如果找到匹配的检测框，将其添加到跟踪结果中
            if matched_box:
                tracked_boxes.append({
                    'detect_box': matched_box,
                    'track_id': track_id,
                    'class_id': class_id,
                    'score': score
                })
            else:
                # 如果没有找到匹配的检测框，创建一个基于跟踪结果的检测框
                x, y, w, h = track_bbox
                # 为了避免创建新的DetectBox，我们可以在不同的角点重复使用相同的坐标
                # 这样跟踪ID会被保留，但不会在图像上绘制旋转的框
                temp_box = DetectBox(
                    class_id, score, 
                    x, y, x+w, y, x+w, y+h, x, y+h, 0.0
                )
                tracked_boxes.append({
                    'detect_box': temp_box,
                    'track_id': track_id,
                    'class_id': class_id,
                    'score': score
                })
                
        return tracked_boxes
    
    def enable_tracking(self, enable=True):
        """
        启用或禁用目标跟踪
        
        Args:
            enable (bool): 是否启用跟踪
        """
        self.with_tracking = enable
        if enable:
            # 重置跟踪器
            self.tracker.reset()
    
    def draw_result(self, image, detection_results, draw_track_id=True):
        """
        在图像上绘制检测和跟踪结果
        
        Args:
            image (numpy.ndarray): 输入图像，BGR格式
            detection_results: 检测结果列表或跟踪结果列表
            draw_track_id (bool): 是否绘制跟踪ID
            
        Returns:
            numpy.ndarray: 绘制了检测和跟踪结果的图像
        """
        result_image = image.copy()
        colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (0, 255, 255), (255, 255, 0)]
        
        for i, result in enumerate(detection_results):
            # 确定是跟踪结果还是检测结果
            if isinstance(result, dict) and 'detect_box' in result:
                # 跟踪结果
                box = result['detect_box']
                track_id = result['track_id']
                color = colors[track_id % len(colors)]  # 使用跟踪ID来确定颜色
            else:
                # 检测结果
                box = result
                track_id = -1
                color = colors[0]  # 默认颜色
            
            # 绘制检测框
            pts = np.array([[box.pt1x, box.pt1y], [box.pt2x, box.pt2y], 
                            [box.pt3x, box.pt3y], [box.pt4x, box.pt4y]], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(result_image, [pts], True, color, 2)
            
            # 绘制类别和置信度
            class_name = self.CLASSES[box.classId] if box.classId < len(self.CLASSES) else f"Class {box.classId}"
            label = f"{class_name}: {box.score:.2f}"
            
            # 如果有跟踪ID，添加到标签中
            if track_id != -1 and draw_track_id:
                label += f" ID:{track_id}"
                
            # 计算标签位置
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            text_x = min(box.pt1x, box.pt2x, box.pt3x, box.pt4x)
            text_y = min(box.pt1y, box.pt2y, box.pt3y, box.pt4y) - 5
            
            # 确保文本在图像范围内
            if text_y < 0:
                text_y = max(box.pt1y, box.pt2y, box.pt3y, box.pt4y) + 20
                
            # 绘制标签背景
            cv2.rectangle(result_image, (text_x, text_y - label_size[1] - 5),
                         (text_x + label_size[0], text_y + 5), color, -1)
            
            # 绘制标签文本
            cv2.putText(result_image, label, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return result_image
        
    def release(self):
        """
        释放RKNN资源
        在不再使用检测器时调用此方法
        """
        if hasattr(self, 'rknn') and self.rknn is not None:
            try:
                self.rknn.release()
            except Exception as e:
                print(f"释放RKNN资源时出错: {str(e)}")
            finally:
                self.rknn = None

    def __del__(self):
        """析构函数，确保资源被释放"""
        try:
            self.release()
        except AttributeError:
            # 如果self.rknn已经是None，忽略AttributeError错误
            pass

# 辅助类定义
class CSXYWHR:
    def __init__(self, classId, score, x, y, w, h, angle):
        self.classId = classId
        self.score = score
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.angle = angle

class DetectBox:
    def __init__(self, classId, score, pt1x, pt1y, pt2x, pt2y, pt3x, pt3y, pt4x, pt4y, angle):
        self.classId = classId
        self.score = score
        self.pt1x = pt1x
        self.pt1y = pt1y
        self.pt2x = pt2x
        self.pt2y = pt2y
        self.pt3x = pt3x
        self.pt3y = pt3y
        self.pt4x = pt4x
        self.pt4y = pt4y
        self.angle = angle