import math
from typing import Tuple

def calculate_angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """
    Calculates the angle between three points (a, b, c) with b as the vertex.
    
    Uses the dot product of vectors ba and bc to determine the angle in degrees.
    Returns an angle between 0.0 and 180.0 degrees.
    
    Args:
        a (Tuple[float, float]): Coordinates (x, y) of the first point.
        b (Tuple[float, float]): Coordinates (x, y) of the vertex point.
        c (Tuple[float, float]): Coordinates (x, y) of the third point.
        
    Returns:
        float: The calculated angle in degrees.
    """
    # Create vectors ba and bc
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    
    # Calculate dot product
    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    
    # Calculate magnitudes of the vectors
    magnitude_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    magnitude_bc = math.sqrt(bc[0]**2 + bc[1]**2)
    
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
