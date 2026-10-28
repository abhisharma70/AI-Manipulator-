#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, PointStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
import tf2_ros
import tf2_geometry_msgs

class ObjectDetector(Node):
    def __init__(self):
        super().__init__('object_detector')

        self.bridge = CvBridge()
        self.camera_info = None
        self.depth_image = None

        # TF Buffer and Listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Subscriptions
        self.create_subscription(
            CameraInfo,
            '/camera/camera_info',
            self.camera_info_callback,
            10
        )
        self.create_subscription(
            Image,
            '/camera/depth_image',
            self.depth_callback,
            10
        )
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        # Publisher for target pose
        self.pose_pub = self.create_publisher(PoseStamped, '/target_object_pose', 10)
        self.get_logger().info('Object Detector Node Initialized. Waiting for image stream...')

    def camera_info_callback(self, msg: CameraInfo):
        if self.camera_info is None:
            self.camera_info = msg
            self.get_logger().info('Camera intrinsic parameters received.')

    def depth_callback(self, msg: Image):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        except Exception as e:
            self.get_logger().error(f'Failed to convert depth image: {e}')

    def image_callback(self, msg: Image):
        if self.camera_info is None or self.depth_image is None:
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert RGB image: {e}')
            return

        # Convert to HSV color space for robust color segmentation
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        # Red color range mask (handles wrap-around in HSV)
        lower_red_1 = np.array([0, 100, 100])
        upper_red_1 = np.array([10, 255, 255])
        lower_red_2 = np.array([170, 100, 100])
        upper_red_2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Morphological filtering to eliminate noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return

        # Get largest contour corresponding to the target pick object
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        if area < 100:  # Noise threshold
            return

        M = cv2.moments(largest_contour)
        if M["m00"] == 0:
            return

        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        # Sample depth value at centroid (handling single-channel float32 or uint16)
        try:
            depth_val = float(self.depth_image[v, u])
        except IndexError:
            return

        # Check if depth is valid (non-zero and finite)
        if np.isnan(depth_val) or np.isinf(depth_val) or depth_val <= 0.05:
            # Fallback search in small neighbourhood
            roi = self.depth_image[max(0, v-3):min(self.depth_image.shape[0], v+4),
                                   max(0, u-3):min(self.depth_image.shape[1], u+4)]
            valid = roi[np.isfinite(roi) & (roi > 0.05)]
            if len(valid) == 0:
                return
            depth_val = float(np.median(valid))

        # Project 2D pixel (u, v) and depth Z to 3D camera coordinates
        # K matrix: [fx, 0, cx, 0, fy, cy, 0, 0, 1]
        fx = self.camera_info.k[0]
        cx = self.camera_info.k[2]
        fy = self.camera_info.k[4]
        cy = self.camera_info.k[5]

        cam_z = depth_val
        cam_x = (u - cx) * cam_z / fx
        cam_y = (v - cy) * cam_z / fy

        # Create PointStamped in camera frame
        point_cam = PointStamped()
        point_cam.header.stamp = msg.header.stamp
        point_cam.header.frame_id = self.camera_info.header.frame_id or 'camera_link_optical'
        point_cam.point.x = cam_x
        point_cam.point.y = cam_y
        point_cam.point.z = cam_z

        # Transform point into base_link coordinate frame
        try:
            transform = self.tf_buffer.lookup_transform(
                'base_link',
                point_cam.header.frame_id,
                rclpy.time.Time()
            )
            point_base = tf2_geometry_msgs.do_transform_point(point_cam, transform)

            # Publish Target PoseStamped
            target_pose = PoseStamped()
            target_pose.header.stamp = self.get_clock().now().to_msg()
            target_pose.header.frame_id = 'base_link'
            target_pose.pose.position.x = point_base.point.x
            target_pose.pose.position.y = point_base.point.y
            target_pose.pose.position.z = point_base.point.z
            # Downward orientation for gripper (grasping from above)
            target_pose.pose.orientation.x = 0.7071
            target_pose.pose.orientation.y = 0.0
            target_pose.pose.orientation.z = 0.7071
            target_pose.pose.orientation.w = 0.0

            self.pose_pub.publish(target_pose)
            self.get_logger().info(
                f'Target Detected at base_link: X={point_base.point.x:.3f}, Y={point_base.point.y:.3f}, Z={point_base.point.z:.3f}'
            )
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            self.get_logger().warn(f'TF transformation to base_link failed: {e}', throttle_duration_sec=2.0)

def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
