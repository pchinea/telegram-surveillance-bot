from datetime import datetime
from io import BytesIO
from tempfile import NamedTemporaryFile
from threading import Thread, Lock
from time import time
from typing import IO, Tuple, Dict, Any, Optional, List, Iterator

import cv2
import numpy as np


class CameraDevice:
    def __init__(self, cam_id=0):
        self._device = cv2.VideoCapture(cam_id)
        self._frame = self._device.read()[1]
        self._height, self._width, _ = self._frame.shape

        self._frame_count = 0
        self._start_time = 0.0

        self._running = False
        self._thread = Thread(target=self.update)
        self._lock = Lock()

    def start(self):
        if not self._running:
            self._frame_count = 0
            self._start_time = time()
            self._running = True
            self._thread.start()

    def update(self):
        while self._running:
            frame = self._device.read()[1]
            with self._lock:
                self._frame = frame
                self._frame_count += 1

    def read(self, with_timestamp=True) -> Tuple[int, np.ndarray]:
        with self._lock:
            frame_id = self._frame_count
            frame = self._frame.copy()
        if with_timestamp:
            self._add_timestamp(frame)
        return frame_id, frame

    def stop(self):
        self._running = False
        self._thread.join()

    @property
    def fps(self):
        return self._frame_count / (time() - self._start_time)

    @property
    def frame_size(self):
        return self._width, self._height

    @staticmethod
    def _add_timestamp(frame: np.ndarray):
        now = str(datetime.now())[:-7]
        org = (1, frame.shape[0] - 3)
        font = cv2.FONT_HERSHEY_PLAIN
        size = 1
        cv2.putText(frame, now, org, font, size, (0, 0, 0), 2)
        cv2.putText(frame, now, org, font, size, (255, 255, 255), 1)


class Camera:
    STATUS_IDLE = 'idle'
    STATUS_MOTION_DETECTED = 'motion_detected'

    def __init__(self, cam_id=0):
        self._camera = CameraDevice(cam_id)
        self._surveillance_mode = False

    def start(self):
        self._camera.start()

    def stop(self):
        self._camera.stop()

    def get_photo(self) -> IO:
        return BytesIO(cv2.imencode(".jpg", self._camera.read()[1])[1])

    def get_video(self, seconds=5) -> IO:
        file, video_writer = self._create_video_file('on_demand')
        n_frames = self._camera.fps * seconds

        processed = []
        while len(processed) < n_frames:
            frame_id, frame = self._camera.read()
            if frame_id not in processed:
                processed.append(frame_id)
                video_writer.write(frame)

        video_writer.release()
        return file

    @staticmethod
    def _get_motion_contours(frame_1: np.ndarray,
                             frame_2: np.ndarray) -> List[np.ndarray]:
        frame_delta = cv2.absdiff(frame_1, frame_2)
        thresh = cv2.threshold(frame_delta, 5, 255, cv2.THRESH_BINARY)[1]

        kernel = np.ones((40, 40), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return cv2.findContours(thresh.copy(),
                                cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)[-2]

    @staticmethod
    def _draw_contours(frame: np.ndarray, contour: np.ndarray):
        (x, y, width, height) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 1)

    def motion_detection(self) -> Iterator[Tuple[bool, int, np.ndarray]]:
        self._surveillance_mode = True
        previous_frame = None
        last_frame_id = 0

        while self._surveillance_mode:
            frame_id, frame = self._camera.read()
            if frame_id == last_frame_id:
                continue
            last_frame_id = frame_id

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if previous_frame is None:
                previous_frame = gray
                continue

            contours = self._get_motion_contours(previous_frame, gray)

            detected = False
            for contour in contours:
                if cv2.contourArea(contour) < 2000:
                    continue
                self._draw_contours(frame, contour)
                detected = True

            previous_frame = gray
            yield detected, frame_id, frame

    def surveillance_start(self,
                           video_seconds=30,
                           picture_seconds=5) -> Iterator[Dict[str, Any]]:
        status = Camera.STATUS_IDLE
        fps = self._camera.fps
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
        self._surveillance_mode = False

    def _create_video_file(self,
                           event_type: str) -> Tuple[IO, cv2.VideoWriter]:
        now_str = str(datetime.now())[:-7]
        table = str.maketrans(': ', '-_')
        prefix = now_str.translate(table) + f'_{event_type}_'

        file = NamedTemporaryFile(prefix=prefix, suffix='.mp4')
        writer = cv2.VideoWriter(file.name,
                                 cv2.VideoWriter_fourcc(*'mp4v'),
                                 self._camera.fps,
                                 self._camera.frame_size)
        return file, writer
