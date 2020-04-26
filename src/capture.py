from datetime import datetime
from io import BytesIO
from tempfile import NamedTemporaryFile
from threading import Thread, Lock
from time import time
from typing import IO, Tuple, Generator, Dict, Any, Optional

import cv2
import numpy as np


class CameraDevice:
    def __init__(self, cam_id=0):
        self.device = cv2.VideoCapture(cam_id)
        self.frame = self.device.read()[1]
        self.height, self.width, _ = self.frame.shape

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
            with self.lock:
                self.frame = frame
                self.frame_count += 1

    def read(self, with_timestamp=True) -> Tuple[int, np.ndarray]:
        with self.lock:
            frame_id = self.frame_count
            frame = self.frame.copy()
        if with_timestamp:
            self.add_timestamp(frame)
        return frame_id, frame

    def stop(self):
        self.running = False
        self.thread.join()

    @property
    def fps(self):
        return self.frame_count / (time() - self.start_time)

    @property
    def frame_size(self):
        return self.width, self.height

    @staticmethod
    def add_timestamp(frame: np.ndarray):
        dt = str(datetime.now())[:-7]
        org = (1, frame.shape[0] - 3)
        font = cv2.FONT_HERSHEY_PLAIN
        size = 1
        cv2.putText(frame, dt, org, font, size, (0, 0, 0), 2)
        cv2.putText(frame, dt, org, font, size, (255, 255, 255), 1)


class Camera:
    STATUS_IDLE = 'idle'
    STATUS_MOTION_DETECTED = 'motion_detected'

    def __init__(self, cam_id=0):
        self.camera = CameraDevice(cam_id)
        self.surveillance_mode = False

    def start(self):
        self.camera.start()

    def stop(self):
        self.camera.stop()

    def get_photo(self) -> IO:
        _, im_buf_arr = cv2.imencode(".jpg", self.camera.read()[1])
        return BytesIO(im_buf_arr)

    def get_video(self, seconds=5) -> IO:
        f = NamedTemporaryFile(suffix='.mp4')
        four_cc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = self.camera.fps
        out = cv2.VideoWriter(f.name, four_cc, fps, self.camera.frame_size)
        n_frames = fps * seconds

        processed = []
        while len(processed) < n_frames:
            frame_id, frame = self.camera.read()
            if frame_id not in processed:
                processed.append(frame_id)
                out.write(frame)

        out.release()
        return f

    def motion_detection(self):
        self.surveillance_mode = True
        previous_frame = None
        last_frame_id = 0

        while self.surveillance_mode:
            frame_id, frame = self.camera.read()
            if frame_id == last_frame_id:
                continue
            last_frame_id = frame_id

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if previous_frame is None:
                previous_frame = gray
                continue

            frame_delta = cv2.absdiff(previous_frame, gray)
            thresh = cv2.threshold(frame_delta, 5, 255, cv2.THRESH_BINARY)[1]

            kernel = np.ones((40, 40), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            # thresh = cv2.dilate(thresh, None, iterations=2)
            contours = cv2.findContours(
                thresh.copy(),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )[-2]

            previous_frame = gray

            detected = False
            for c in contours:
                if cv2.contourArea(c) < 2000:
                    continue

                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                detected = True

            yield detected, frame_id, frame

    def surveillance_start(
            self,
            video_seconds=30,
            picture_seconds=5
    ) -> Generator[Dict[str, Any], None, None]:
        status = Camera.STATUS_IDLE
        fps = self.camera.fps
        processed = []
        n_frames = 0
        file: Optional[IO] = None
        video_writer: Optional[cv2.VideoWriter] = None

        for detected, frame_id, frame in self.motion_detection():
            if status == Camera.STATUS_IDLE:
                if detected:
                    yield {'detected': True}
                    status = Camera.STATUS_MOTION_DETECTED
                    file, video_writer = self._create_video_file('on_motion')
                    n_frames = fps * video_seconds
                    processed = [frame_id]
                    video_writer.write(frame)
            if status == Camera.STATUS_MOTION_DETECTED:
                if not len(processed) % int(fps * picture_seconds):
                    yield {
                        'photo': BytesIO(cv2.imencode(".jpg", frame)[1]),
                        'id': (len(processed) // int(fps * picture_seconds)),
                        'total': video_seconds // picture_seconds
                    }
                if len(processed) < n_frames:
                    if frame_id not in processed:
                        processed.append(frame_id)
                        video_writer.write(frame)
                else:
                    video_writer.release()
                    yield {'video': file}
                    status = Camera.STATUS_IDLE

    def surveillance_stop(self):
        self.surveillance_mode = False

    def _create_video_file(self, event_type: str) -> Tuple[IO, cv2.VideoWriter]:
        now_str = str(datetime.now())[:-7]
        table = str.maketrans(': ', '-_')
        prefix = now_str.translate(table) + f'_{event_type}_'

        file = NamedTemporaryFile(prefix=prefix, suffix='.mp4')
        writer = cv2.VideoWriter(
            file.name,
            cv2.VideoWriter_fourcc(*'mp4v'),
            self.camera.fps,
            self.camera.frame_size
        )
        return file, writer
