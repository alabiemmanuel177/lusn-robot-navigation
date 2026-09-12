#!/usr/bin/env python3
"""Rendering camera model for stationary captures, with depth-image verification.

The Gazebo RGB-D sensor is composed from the robot description: camera_link at
(0.069, -0.047, 0.107) in the model frame, the sensor at (0.064, -0.047, 0.107)
in the link, and the model spawned 0.010 m above the floor. The localization
transform published for `camera_depth_frame` comes from the URDF used by the
state publisher and sits about 0.06 m behind, 0.05 m left of and 0.11 m below
the sensor that actually renders pixels. Assets placed with that transform miss
their intended image region; `verify_against_depth` measures the real camera
from retained depth samples so the model is evidence, not an assumption.
"""
from __future__ import annotations

import math

import numpy as np

SENSOR_OFFSET_MODEL = (0.069 + 0.064, -0.047 - 0.047, 0.107 + 0.107)
SPAWN_HEIGHT = 0.010
CAMERA_OFFSET_BASE = (SENSOR_OFFSET_MODEL[0], SENSOR_OFFSET_MODEL[1], SENSOR_OFFSET_MODEL[2] + SPAWN_HEIGHT)
MODEL_ID = 'research3-rendering-camera-model/v1'


def rendering_camera(pose):
    """Optical centre and optical rotation (columns: right, down, forward) in the map frame."""
    x, y, yaw = float(pose['x']), float(pose['y']), float(pose['yaw'])
    fx, fy, fz = CAMERA_OFFSET_BASE
    cos, sin = math.cos(yaw), math.sin(yaw)
    centre = np.array([x + fx * cos - fy * sin, y + fx * sin + fy * cos, fz])
    forward = np.array([cos, sin, 0.])
    right = np.array([sin, -cos, 0.])
    down = np.array([0., 0., -1.])
    return centre, np.column_stack([right, down, forward])


def sdf_rpy(rotation):
    pitch = math.asin(max(-1., min(1., -float(rotation[2, 0]))))
    roll = math.atan2(rotation[2, 1], rotation[2, 2])
    yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    return roll, pitch, yaw


def rotation_from_rpy(roll, pitch, yaw):
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def back_project(depth, camera_info):
    k = camera_info['k']
    fx, fy, cx, cy = k[0], k[4], k[2], k[5]
    height, width = depth.shape
    v, u = np.mgrid[0:height, 0:width]
    z = depth
    return np.stack([(u - cx) / fx * z, (v - cy) / fy * z, z], -1)


def verify_against_depth(pose, depth, camera_info, rgb, walls, *, floor_rgb=None):
    """Estimate the camera from floor and wall depth samples; compare with the model.

    Returns per-plane estimates and residuals in metres. Floor pixels are the
    dominant light-grey colour of the bottom rows; wall pixels are the dark-grey
    wall material. Assignment to a wall face uses the model as an initial guess,
    then the face constraint re-solves the camera coordinate independently.
    """
    centre, rotation = rendering_camera(pose)
    points = back_project(depth, camera_info)
    valid = np.isfinite(depth) & (depth > .05) & (depth < 12.)
    floor_rgb = np.asarray(floor_rgb if floor_rgb is not None else rgb[-8:, :, :].reshape(-1, 3).mean(0).round())
    floor = valid & np.all(np.abs(rgb.astype(np.int16) - floor_rgb.astype(np.int16)) <= 6, axis=2)
    result = dict(model_id=MODEL_ID, model_centre=centre.tolist(), floor_pixels=int(floor.sum()))
    if floor.sum() >= 500:
        y_opt = points[..., 1][floor]
        z_opt = points[..., 2][floor]
        slope, intercept = np.polyfit(z_opt, y_opt, 1)
        result.update(depth_floor_height=float(np.median(y_opt)), depth_floor_height_std=float(np.std(y_opt)),
                      depth_pitch_slope=float(slope), height_residual=float(np.median(y_opt) - centre[2]))
    wall = valid & np.all(np.abs(rgb.astype(np.int16) - np.array([82, 84, 86], dtype=np.int16)) <= 25, axis=2)
    if wall.sum() >= 500:
        vectors = points[wall] @ rotation.T
        guess = centre + vectors
        faces = []
        for row in walls:
            for axis, size, other in (('x', 'sx', 'sy'), ('y', 'sy', 'sx')):
                index = 0 if axis == 'x' else 1
                for sign in (-1, 1):
                    faces.append((index, row[axis] + sign * row[size] / 2))
        residuals = np.stack([np.abs(guess[:, index] - value) for index, value in faces], 1)
        assignment = residuals.argmin(1)
        near = residuals.min(1) < .06
        estimates = {0: [], 1: []}
        for face_index, (index, value) in enumerate(faces):
            selected = (assignment == face_index) & near
            if selected.sum() >= 300:
                estimates[index].append((value - np.median(vectors[selected][:, index]), int(selected.sum())))
        for index, key in ((0, 'x'), (1, 'y')):
            if estimates[index]:
                weights = np.array([count for _, count in estimates[index]], dtype=float)
                values = np.array([value for value, _ in estimates[index]])
                estimate = float(np.sum(values * weights) / weights.sum())
                result[f'depth_{key}'] = estimate
                result[f'{key}_residual'] = estimate - float(centre[index])
                result[f'{key}_faces_used'] = len(estimates[index])
    residuals = [abs(result[k]) for k in ('height_residual', 'x_residual', 'y_residual') if k in result]
    result['max_abs_residual_m'] = max(residuals) if residuals else None
    result['verified'] = bool(residuals) and result['max_abs_residual_m'] <= .03 and 'height_residual' in result
    return result
