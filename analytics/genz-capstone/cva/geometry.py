"""Craniovertebral angle (CVA) geometry.

CVA = angle between (a) the horizontal line through C7 and (b) the line C7 -> tragus.
Image coordinates: x to the right, y DOWN (pixels). Works for a subject facing
left or right because we use |dx|. Smaller CVA = head further forward.
Assumes the camera is level and the photo is a true side view.
"""
import math

FHP_THRESHOLD_DEG = 50.0   # common research cut-off (<= 50 deg suggests forward head posture)

def angle_from_horizontal(upper, lower):
    """Angle (deg) of the segment lower->upper above the horizontal through `lower`."""
    (ux, uy), (lx, ly) = upper, lower
    dx, dy = abs(ux - lx), (ly - uy)          # y is down, so up = ly - uy
    if dx == 0 and dy == 0:
        raise ValueError("points coincide")
    return math.degrees(math.atan2(dy, dx)) if dx else 90.0

def cva(tragus, c7):
    """True CVA from tragus and C7 (the L0 / L2 measurement)."""
    return angle_from_horizontal(tragus, c7)

def ear_shoulder_proxy(ear, shoulder):
    """Proxy angle from ear and shoulder landmarks (the L1 MediaPipe baseline).
    NOT the same as CVA: the shoulder landmark sits lower and usually more
    anterior than C7, so the proxy is biased — see simulate_proxy_bias.py."""
    return angle_from_horizontal(ear, shoulder)

def level_correction(angle_deg, horizon_tilt_deg):
    """Correct for a camera rolled by `horizon_tilt_deg` (positive = image rotated
    counter-clockwise). Measure the tilt from a known horizontal/vertical in the scene."""
    return angle_deg + horizon_tilt_deg

def classify_fhp(angle_deg, threshold=FHP_THRESHOLD_DEG):
    return angle_deg <= threshold
