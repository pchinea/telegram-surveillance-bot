from datetime import datetime
from io import BytesIO
from tempfile import NamedTemporaryFile
from threading import Thread, Lock
from time import time
from typing import IO, Tuple

import cv2
from numpy import ndarray


class CameraDevice:
    def __init__(self, cam_id=0, with_timestamp=True):
        self.with_timestamp = with_timestamp

        self.device = cv2.VideoCapture(cam_id)
        self.frame = self.device.read()[1]

        self.frame_count = 0
        self.start_time = 0.0

        self.running = False
        self.thread = Thread(target=self.update)
        self.lock = Lock()

    def start(self):
        if not self.running:
            self.frame_count = 0
            self.start_time = time()
            self.running = True
            self.thread.start()

    def update(self):
        while self.running:
            frame = self.device.read()[1]
            if self.with_timestamp:
                self.add_timestamp(frame)
            with self.lock:
                self.frame = frame
                self.frame_count += 1

    def read(self) -> Tuple[int, ndarray]:
        with self.lock:
            frame_id = self.frame_count
            frame = self.frame.copy()
        return frame_id, frame

    def stop(self):
        self.running = False
        self.thread.join()

    @property
    def fps(self):
        return self.frame_count / (time() - self.start_time)

    @staticmethod
    def add_timestamp(frame: ndarray):
        dt = str(datetime.now())[:-7]
        org = (1, frame.shape[0] - 3)
        font = cv2.FONT_HERSHEY_PLAIN
        size = 1
        cv2.putText(frame, dt, org, font, size, (0, 0, 0), 2)
        cv2.putText(frame, dt, org, font, size, (255, 255, 255), 1)


class Camera:
    def __init__(self, cam_id=0):
        self.camera = CameraDevice(cam_id)

    def start(self):
        self.camera.start()

    def stop(self):
        self.camera.stop()

    def get_photo(self) -> IO:
        _, im_buf_arr = cv2.imencode(".jpg", self.camera.read()[1])
        return BytesIO(im_buf_arr)

    def get_video(self, seconds=5) -> IO:
        f = NamedTemporaryFile(suffix='.mp4')
        four_cc = cv2.VideoWriter_fourcc(*'avc1')
        fps = self.camera.fps
        out = cv2.VideoWriter(f.name, four_cc, fps, (640, 480))
        n_frames = fps * seconds

        processed = []
        while len(processed) < n_frames:
            frame_id, frame = self.camera.read()
            if frame_id not in processed:
                processed.append(frame_id)
                out.write(frame)

        out.release()
        return f
