"""
Module for camera related functionality

This file implements both camera management and a top layer for related
operations such as motion detection or output file generation. All
camera and image operations are performed using OpenCV.
"""
from datetime import datetime
from io import BytesIO
from tempfile import NamedTemporaryFile
from threading import Thread, Lock
from time import time
from typing import IO, Tuple, Dict, Any, Optional, List, Iterator

import cv2
import numpy as np


class CameraDevice:
    """
    Class for camera hardware handling.

    This class handles camera hardware using threading to perform reading
    operations on the camera.

    Args:
        cam_id: ID of the video capturing device to open.
    """
    def __init__(self, cam_id=0):
        self._device = cv2.VideoCapture(cam_id)
        self._frame = self._device.read()[1]

        self._frame_count = 0
        self._start_time = 0.0

        self._running = False
        self._thread = Thread(target=self._update)
        self._lock = Lock()

    def start(self):
        """Starts frame grabbing process."""
        if not self._running:
            self._frame_count = 0
            self._start_time = time()
            self._running = True
            self._thread.start()

    def _update(self):
        """
        Updates data with latest frame available.

        This functions is executed in a separated thread because frame
        reading is a blocking operation. Every frame grabbed is stored
        temporarily.
        """
        while self._running:
            frame = self._device.read()[1]
            with self._lock:
                self._frame = frame
                self._frame_count += 1

    def read(self, with_timestamp=True) -> Tuple[int, np.ndarray]:
        """
        Returns the latest stored frame.

        Args:
            with_timestamp: If True a timestamp is printed on the returned
                frame.

        Returns:
            A tuple with the unique identifier of the frame and the frame
            itself.
        """
        with self._lock:
            frame_id = self._frame_count
            frame = self._frame.copy()
        if with_timestamp:
            self._add_timestamp(frame)
        return frame_id, frame

    def stop(self):
        """Stops frame grabbing process."""
        self._running = False
        self._thread.join()

    @property
    def fps(self) -> float:
        """
        Calculates actual frames per seconds value.

        Note:
            This is necessary because FPS value returned by OpenCV could be
            not accurate.

        Returns:
            Current FPS value.
        """
        return self._frame_count / (time() - self._start_time)

    @property
    def frame_size(self) -> Tuple[int, int]:
        """
        Gets the frame resolution based in the last grabbed frame.

        Returns:
            Tuple with frame width and height.
        """
        height, width, _ = self._frame.shape
        return width, height

    @staticmethod
    def _add_timestamp(frame: np.ndarray):
        """Prints timestamp on the given frame."""
        now = str(datetime.now())[:-7]
        org = (1, frame.shape[0] - 3)
        font = cv2.FONT_HERSHEY_PLAIN
        size = 1
        cv2.putText(frame, now, org, font, size, (0, 0, 0), 2)
        cv2.putText(frame, now, org, font, size, (255, 255, 255), 1)


class Camera:
    """
    Top level class for camera operations performing.

    This class provide high level operations returning images and videos in
    a file object.

    Args:
        cam_id: ID of the video capturing device to open.
    """

    STATE_IDLE = 'idle'
    """Awaiting for motion detection."""

    STATE_MOTION_DETECTED = 'motion_detected'
    """After motion have been detected."""

    def __init__(self, cam_id=0):
        self._camera = CameraDevice(cam_id)
        self._surveillance_mode = False

    def start(self):
        """
        Starts camera device.

        Note:
            The camera can only be started once during the instance lifecycle.
        """
        self._camera.start()

    def stop(self):
        """Stops camera devices."""
        self._camera.stop()

    def get_photo(self) -> IO:
        """
        Takes a single shot.

        Returns:
            File object with the photo taken.
        """
        return BytesIO(cv2.imencode(".jpg", self._camera.read()[1])[1])

    def get_video(self, seconds=5) -> IO:
        """Takes a video.

        Args:
            seconds: Video duration.

        Returns:
            File object with the video taken.
        """
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
        """
        Detects motion and find the contours for every motion detected.

        This method receives two consecutive frames and detects changes
        between them.

        Args:
            frame_1: First of the two consecutive frames.
            frame_2: Second of the two consecutive frames.

        Returns:
            A list with the contours found.
        """
        frame_delta = cv2.absdiff(frame_1, frame_2)
        thresh = cv2.threshold(frame_delta, 5, 255, cv2.THRESH_BINARY)[1]

        kernel = np.ones((40, 40), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return cv2.findContours(thresh.copy(),
                                cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)[-2]

    @staticmethod
    def _draw_contours(frame: np.ndarray, contour: np.ndarray):
        """
        Draws a rectangle on the frame that marks a contour.

        This method gets a bounding rectangle for a given contour and
        draws this rectangle on the frame.

        Args:
            frame: Frame on which to draw the rectangles.
            contour: Contour to be marked.
        """
        (x, y, width, height) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 1)

    def motion_detection(self) -> Iterator[Tuple[bool, int, np.ndarray]]:
        """
        Executes motion detection operation during surveillance mode.

        This generator grabs frames continuously and search for motion
        yielding every frame grabbed even motion is detected or not. In
        frames with motion detected the contour is drawn on it.

        Yields:
            A tuple with three values.
                * True if motion is detected or False if not.
                * The unique identifier of the frame.
                * The frame itself.
        """
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
        """
        Starts surveillance mode, waiting for motion detection.

        In this mode it waits until motion is detected, when this happens a
        message is yielded and it starts to record a video, yielding single
        photos during this process until video is yielded. After that it
        goes back to the initial state.

        Args:
            video_seconds: Video duration.
            picture_seconds: Time elapsed between pictures.

        Yields:
            A dict with three possible configurations
                * ``{'detected': True}``
                * ``{'video': <IO>}``
                * ``{'photo': <IO>, 'id': <int>, 'total': <int>}``
        """
        status = Camera.STATE_IDLE
        fps = self._camera.fps
        processed = []
        n_frames = 0
        file: Optional[IO] = None
        video_writer: Optional[cv2.VideoWriter] = None

        for detected, frame_id, frame in self.motion_detection():
            if status == Camera.STATE_IDLE:
                if detected:
                    yield {'detected': True}
                    status = Camera.STATE_MOTION_DETECTED
                    file, video_writer = self._create_video_file('on_motion')
                    n_frames = fps * video_seconds
                    processed = [frame_id]
                    video_writer.write(frame)
            if status == Camera.STATE_MOTION_DETECTED:
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
                    status = Camera.STATE_IDLE

    def surveillance_stop(self):
        """Stops surveillance mode."""
        self._surveillance_mode = False

    def _create_video_file(self,
                           event_type: str) -> Tuple[IO, cv2.VideoWriter]:
        """
        Initializes a temporary video file and a video writer.


        Args:
            event_type: Event type string for filename generation.

        Returns:
            A tuple with the file object and the OpenCV video writer object.
        """
        now_str = str(datetime.now())[:-7]
        table = str.maketrans(': ', '-_')
        prefix = now_str.translate(table) + f'_{event_type}_'

        file = NamedTemporaryFile(prefix=prefix, suffix='.mp4')
        writer = cv2.VideoWriter(file.name,
                                 cv2.VideoWriter_fourcc(*'mp4v'),
                                 self._camera.fps,
                                 self._camera.frame_size)
        return file, writer
