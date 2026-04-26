import math
from typing import Sequence


def calculate_angle(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    """
    Calculates the angle between three points (a, b, c) with b as the vertex.
    
    Uses the dot product of vectors ba and bc to determine the angle in degrees.
    Returns an angle between 0.0 and 180.0 degrees.
    
    Args:
        a: Coordinates of the first point.
        b: Coordinates of the vertex point.
        c: Coordinates of the third point.
        
    Returns:
        float: The calculated angle in degrees.
    """
    if len(a) != len(b) or len(b) != len(c):
        raise ValueError("Angle points must share the same dimensionality.")

    # Create vectors ba and bc in arbitrary dimensional space.
    ba = [a_i - b_i for a_i, b_i in zip(a, b)]
    bc = [c_i - b_i for c_i, b_i in zip(c, b)]

    # Calculate dot product and magnitudes.
    dot_product = sum(ba_i * bc_i for ba_i, bc_i in zip(ba, bc))
    magnitude_ba = math.sqrt(sum(component ** 2 for component in ba))
    magnitude_bc = math.sqrt(sum(component ** 2 for component in bc))
    
    # Avoid division by zero if points are identical
    if magnitude_ba == 0 or magnitude_bc == 0:
        return 0.0
        
    # Calculate cosine of the angle
    cos_angle = dot_product / (magnitude_ba * magnitude_bc)
    
    # Handle potential floating point errors where cos_angle is slightly outside [-1.0, 1.0]
    cos_angle = max(min(cos_angle, 1.0), -1.0)
    
    # Calculate the angle in radians and convert to degrees
    angle_radians = math.acos(cos_angle)
    angle_degrees = math.degrees(angle_radians)
    
    return angle_degrees
