"""Small centroid tracker that supplies persistence and motion features."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

import numpy as np


class CentroidTracker:
    def __init__(self, max_disappeared: int = 15, distance_threshold: float = 80.0):
        self.next_object_id = 0
        self.objects: OrderedDict[int, dict[str, Any]] = OrderedDict()
        self.disappeared: OrderedDict[int, int] = OrderedDict()
        self.max_disappeared = int(max_disappeared)
        self.distance_threshold = float(distance_threshold)

    def register(self, detection: dict[str, Any], centroid: tuple[int, int]) -> None:
        x1, y1, x2, y2 = detection["bbox"]
        area = max(0, (x2 - x1) * (y2 - y1))
        self.objects[self.next_object_id] = {
            "centroid": centroid,
            "bbox": detection["bbox"],
            "detection": dict(detection),
            "frames_seen": 1,
            "history": [centroid],
            "area_history": [area],
            "area_growth": 0.0,
            "velocity": (0.0, 0.0),
            "alert_sent": False,
        }
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id: int) -> None:
        self.objects.pop(object_id, None)
        self.disappeared.pop(object_id, None)

    @staticmethod
    def _centroid(detection: dict[str, Any]) -> tuple[int, int]:
        x1, y1, x2, y2 = detection["bbox"]
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    def update(self, detections: list[dict[str, Any]]) -> OrderedDict[int, dict[str, Any]]:
        if not detections:
            for object_id in list(self.disappeared):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = [self._centroid(detection) for detection in detections]
        if not self.objects:
            for detection, centroid in zip(detections, input_centroids):
                self.register(detection, centroid)
            self._copy_track_ids_to_detections(detections)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = np.asarray(
            [self.objects[object_id]["centroid"] for object_id in object_ids],
            dtype=float,
        )
        new_centroids = np.asarray(input_centroids, dtype=float)
        distances = np.linalg.norm(
            object_centroids[:, np.newaxis, :] - new_centroids[np.newaxis, :, :],
            axis=2,
        )

        rows = distances.min(axis=1).argsort()
        cols = distances.argmin(axis=1)[rows]
        used_rows: set[int] = set()
        used_cols: set[int] = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            if distances[row, col] > self.distance_threshold:
                continue

            object_id = object_ids[row]
            obj = self.objects[object_id]
            previous_centroid = obj["centroid"]
            new_centroid = input_centroids[col]
            x1, y1, x2, y2 = detections[col]["bbox"]
            new_area = max(0, (x2 - x1) * (y2 - y1))
            previous_area = obj["area_history"][-1] if obj["area_history"] else new_area

            obj["centroid"] = new_centroid
            obj["bbox"] = detections[col]["bbox"]
            obj["detection"] = dict(detections[col])
            obj["frames_seen"] += 1
            obj["history"].append(new_centroid)
            obj["history"] = obj["history"][-30:]
            obj["area_history"].append(new_area)
            obj["area_history"] = obj["area_history"][-30:]
            obj["velocity"] = (
                new_centroid[0] - previous_centroid[0],
                new_centroid[1] - previous_centroid[1],
            )
            obj["area_growth"] = (
                (new_area - previous_area) / previous_area if previous_area > 0 else 0.0
            )
            self.disappeared[object_id] = 0
            detections[col]["track_id"] = object_id
            detections[col]["frames_seen"] = obj["frames_seen"]
            detections[col]["velocity"] = obj["velocity"]
            detections[col]["area_growth"] = round(obj["area_growth"], 6)
            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(distances.shape[0])) - used_rows
        unused_cols = set(range(distances.shape[1])) - used_cols
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        for col in unused_cols:
            self.register(detections[col], input_centroids[col])
            new_id = self.next_object_id - 1
            detections[col]["track_id"] = new_id
            detections[col]["frames_seen"] = 1
            detections[col]["velocity"] = (0.0, 0.0)
            detections[col]["area_growth"] = 0.0

        return self.objects

    def _copy_track_ids_to_detections(self, detections: list[dict[str, Any]]) -> None:
        for object_id, detection in zip(self.objects.keys(), detections):
            detection["track_id"] = object_id
            detection["frames_seen"] = self.objects[object_id]["frames_seen"]
            detection["velocity"] = self.objects[object_id]["velocity"]
            detection["area_growth"] = self.objects[object_id]["area_growth"]
