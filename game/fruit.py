import math

class Fruit:
    def __init__(self, x, y, vx, vy, gravity, radius=28, kind="fruit"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gravity = gravity
        self.radius = radius
        self.kind = kind  # "fruit" or "bomb"
        self.sliced = False

    def update(self):
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy

    def contains_point(self, x, y):
        # Single-point test (kept for compatibility).
        return math.hypot(self.x - x, self.y - y) <= self.radius

    def intersects_segment(self, x1, y1, x2, y2):
        """True if the blade segment (x1,y1)->(x2,y2) touches this fruit's circle.

        Finds the point on the segment closest to the fruit's center and checks
        whether it is within the radius. This catches fast swipes whose two
        endpoints are both outside the circle but whose path crosses it.
        """
        dx = x2 - x1
        dy = y2 - y1
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq == 0:
            # Mouse didn't move: degenerate segment, plain point test.
            return self.contains_point(x1, y1)

        # Project fruit center onto the segment, clamp t to [0, 1].
        t = ((self.x - x1) * dx + (self.y - y1) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return math.hypot(self.x - closest_x, self.y - closest_y) <= self.radius

    def off_screen(self, height):
        return self.y - self.radius > height
