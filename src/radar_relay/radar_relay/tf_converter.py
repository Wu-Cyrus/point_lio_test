#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import rclpy
from rclpy.node import Node

from tf2_msgs.msg import TFMessage
from std_msgs.msg import Float32MultiArray, Int32


class TfConverter(Node):
    """
    Subscribe /tf, extract transform parent->child, publish:
      1) Float32MultiArray [x1,y1,z1,yaw1]
      2) ......(you can add more topics like x11)
    @time 2026-02-01
    """

    def __init__(self):
        super().__init__("tf_converter")

        # ===== 订阅不变 =====
        self.tf_sub = self.create_subscription(TFMessage, "/tf", self.tf_callback, 10)

        # ===== 参数 =====
        self.declare_parameter("target_parent_frame", "camera_init")
        self.declare_parameter("target_child_frame", "aft_mapped")

        # 输出话题
        self.declare_parameter("pose_xyzyaw_topic", "/radar/processed_pose_xyzyaw") # [x, y, z, yaw]


        # 单位：tf 通常是 m/rad；按统一协议，我们发布 mm/rad
        self.declare_parameter("meter_to_mm", 1000.0)




        # ===== 发布者 =====
        self.pose_topic = self.get_parameter("pose_xyzyaw_topic").value

        self.pose_pub = self.create_publisher(Float32MultiArray, self.pose_topic, 10)

        # ===== yaw 连续化状态（新增：仅为避免 ±pi 跳变，并在 ±2pi 回到 0） =====
        self._yaw_prev_raw = None  # 上一帧原始 yaw（(-pi, pi]）
        self._yaw_acc = 0.0        # 连续 yaw（可超过 pi）

        # 节流日志
        self._last_log_ns = 0
        self._log_period_ns = int(2e9)  # 2s

        self.get_logger().info(
            f"Listening /tf for {self.get_parameter('target_parent_frame').value} -> "
            f"{self.get_parameter('target_child_frame').value}"
        )

    # ---------- 工具函数 ----------

    @staticmethod
    def _norm_frame(s: str) -> str:
        # 去掉前导 '/'
        return s.lstrip("/") if s else s

    @staticmethod
    def _yaw_from_quat(x: float, y: float, z: float, w: float) -> float:
        # yaw (Z) from quaternion
        t3 = 2.0 * (w * z + x * y)
        t4 = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)

    @staticmethod
    def _wrap_to_pi(a: float) -> float:
        """把角度包到 (-pi, pi]，用于求最小角差，避免 ±pi 跳变"""
        return (a + math.pi) % (2.0 * math.pi) - math.pi

    @staticmethod
    def _wrap_to_2pi_signed(a: float) -> float:
        """把角度包到 (-2pi, 2pi]，只在 ±360° 时回到 0"""
        two_pi = 2.0 * math.pi
        while a > two_pi:
            a -= two_pi
        while a <= -two_pi:
            a += two_pi
        return a

    # ---------- 回调 ----------

    def tf_callback(self, msg: TFMessage):
        parent = self._norm_frame(self.get_parameter("target_parent_frame").value)
        child  = self._norm_frame(self.get_parameter("target_child_frame").value)



        for tf in msg.transforms:
            if (self._norm_frame(tf.header.frame_id) == parent and
                    self._norm_frame(tf.child_frame_id) == child):

                t = tf.transform.translation
                r = tf.transform.rotation
                # tf 里通常是米(m)
                x_m = float(t.x)
                y_m = float(t.y)
                z_m = float(t.z)

                # ===== yaw 连续化（改动点：替换原本直接 yaw_from_quat 的输出） =====
                yaw_raw = self._yaw_from_quat(float(r.x), float(r.y), float(r.z), float(r.w))

                if self._yaw_prev_raw is None:
                    # 保持启动时的“绝对朝向”初值（不强制归零）
                    self._yaw_acc = yaw_raw
                    self._yaw_prev_raw = yaw_raw
                else:
                    dy = self._wrap_to_pi(yaw_raw - self._yaw_prev_raw)  # 最小角增量
                    self._yaw_acc += dy
                    self._yaw_prev_raw = yaw_raw

                yaw1 = self._wrap_to_2pi_signed(self._yaw_acc)  # 只在 ±360° 回到 0


                # 按你统一协议：发布 mm / rad
                s = float(self.get_parameter("meter_to_mm").value)
                x1 = x_m * s
                y1 = y_m * s
                z1 = z_m * s

                # 1) 发布 [x1_mm, y1_mm, z1_mm, yaw_rad]
                arr = Float32MultiArray()
                arr.data = [float(x1), float(y1), float(z1), float(yaw1)]
                self.pose_pub.publish(arr)


                # 节流日志
                now_ns = self.get_clock().now().nanoseconds
                if now_ns - self._last_log_ns >= self._log_period_ns:
                    self._last_log_ns = now_ns
                    self.get_logger().info(
                        f"x1_mm={x1:.1f}, y1_mm={y1:.1f}, z1_mm={z1:.1f}, yaw1_rad={yaw1:.3f} "
                    )
                break


def main(args=None):
    rclpy.init(args=args)
    node = TfConverter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
