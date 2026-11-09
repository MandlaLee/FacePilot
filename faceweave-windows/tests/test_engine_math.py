"""Fast offline geometry and serialization checks (no webcam or neural models)."""
import unittest
from pathlib import Path

import cv2
import numpy as np

from faceweave.engine import REFERENCE, MODELS, _similarity, bgr_chw, scale_frame


class LiveEngineMathTests(unittest.TestCase):
    def test_identity_alignment(self):
        matrix = _similarity(REFERENCE, 112)
        self.assertTrue(np.allclose(matrix[:, :2], np.eye(2), atol=1e-3))
        self.assertTrue(np.allclose(matrix[:, 2], [0, 0], atol=1e-3))

    def test_inswapper_alignment_offset(self):
        matrix = _similarity(REFERENCE, 128)
        self.assertTrue(np.allclose(matrix[:, 2], [8, 0], atol=1e-3))

    def test_alignment_is_invertible(self):
        xy = REFERENCE * 1.8 + np.array([33, 17], dtype=np.float32)
        affine = _similarity(xy, 112)
        forward = cv2.transform(xy.reshape(1, 5, 2), affine).reshape(5, 2)
        self.assertTrue(np.allclose(forward, REFERENCE, atol=.1))

    def test_model_manifest_four_entries(self):
        self.assertEqual(len(MODELS), 4)
        self.assertEqual(len(set(MODELS)), 4)
        for digest in MODELS.values():
            self.assertEqual(len(digest), 64)

    def test_bgr_to_rgb_chw_normalization(self):
        img = np.array([[[0, 128, 255]]], dtype=np.uint8)  # BGR
        result = bgr_chw(img, 0, 255)
        self.assertEqual(result.shape, (1, 3, 1, 1))
        self.assertTrue(np.allclose(result[0, :, 0, 0], [1, 128/255, 0]))

    def test_frame_downsample(self):
        frame = np.zeros((1000, 2000, 3), dtype=np.uint8)
        result = scale_frame(frame, 640)
        self.assertEqual(result.shape[:2], (320, 640))

    def test_no_upscale(self):
        frame = np.zeros((80, 160, 3), dtype=np.uint8)
        self.assertIs(scale_frame(frame, 640), frame)


if __name__ == "__main__":
    unittest.main()
