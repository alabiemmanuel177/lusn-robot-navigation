"""Run the Research 1 landmark provider without starving its TF listener."""
from __future__ import annotations

import rclpy
from rclpy.executors import MultiThreadedExecutor
from research3_landmark_bridge.node import LandmarkObservationNode


def main(args=None) -> None:
    """Spin the unchanged provider node with concurrent TF callback capacity."""
    rclpy.init(args=args)
    node = LandmarkObservationNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.remove_node(node)
        executor.shutdown()
        if node.review_handle is not None:
            node.review_handle.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
