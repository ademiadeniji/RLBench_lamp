from typing import List
import numpy as np
from pyrep.objects.shape import Shape
from pyrep.objects.proximity_sensor import ProximitySensor
from rlbench.const import colors
from rlbench.backend.task import Task
from rlbench.backend.conditions import (
    DetectedCondition,
    NothingGrasped,
    GraspedCondition,
)
from rlbench.backend.spawn_boundary import SpawnBoundary


class PickUpCup(Task):
    def init_task(self) -> None:
        self.cup1 = Shape("cup1")
        self.cup2 = Shape("cup2")
        self.cup1_visual = Shape("cup1_visual")
        self.cup2_visual = Shape("cup2_visual")
        self.boundary = SpawnBoundary([Shape("boundary")])
        self.success_sensor = ProximitySensor("success")
        self.register_graspable_objects([self.cup1, self.cup2])

        self._grasped_cond = GraspedCondition(self.robot.gripper, self.cup1)
        self._detected_cond = DetectedCondition(self.cup1, self.success_sensor, negated=True)

        self.register_success_conditions(
            [
                self._detected_cond, self._grasped_cond
            ]
        )

    def init_episode(self, index: int) -> List[str]:
        self.variation_index = index
        target_color_name, target_rgb = colors[index]

        random_idx = np.random.choice(len(colors))
        while random_idx == index:
            random_idx = np.random.choice(len(colors))
        _, other1_rgb = colors[random_idx]

        self.cup1_visual.set_color(target_rgb)
        self.cup2_visual.set_color(other1_rgb)

        self.boundary.clear()
        self.boundary.sample(self.cup2, min_distance=0.1)
        self.boundary.sample(self.success_sensor, min_distance=0.1)

        return [
            "pick up the %s cup" % target_color_name,
            "grasp the %s cup and lift it" % target_color_name,
            "lift the %s cup" % target_color_name,
        ]

    def variation_count(self) -> int:
        return len(colors)

    def change_reward(self, task) -> None:
        self.reward_lang = task

    def reward(self) -> float:
        grasped = self._grasped_cond.condition_met()[0]

        if not grasped:
            grasp_cup1_reward = np.exp(
                -np.linalg.norm(
                    self.cup1.get_position() - self.robot.arm.get_tip().get_position()
                )
            )
            reward = grasp_cup1_reward
        else:
            lift_cup1_reward = np.exp(
                -np.linalg.norm(
                    self.cup1.get_position() - self.success_sensor.get_position()
                )
            )
            reward = 1.0 + lift_cup1_reward
        
        # # Vertical gripper reward
        # curr_quat = self.robot.gripper.get_quaternion()
        # goal_quat = [1, 0, 0, 0]
        # euler = Rotation.from_quat(curr_quat).as_euler("xyz", degrees=True) + 180
        # goal_euler = Rotation.from_quat(goal_quat).as_euler("xyz", degrees=True) + 180
        # euler_dist = [
        #     min(abs(e - ge), 360 - abs(e - ge)) / 360.0
        #     for e, ge in zip(euler, goal_euler)
        # ]
        # gripper_reward = np.exp(-np.linalg.norm(euler_dist))

        # reward += gripper_reward
        return reward

    def get_low_dim_state(self) -> np.ndarray:
        # For ad-hoc reward computation, attach reward
        reward = self.reward()
        state = super().get_low_dim_state()
        return np.hstack([reward, state])
