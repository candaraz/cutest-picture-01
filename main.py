import math
import os
import struct
import zlib


WIDTH = 1024
HEIGHT = 1024
OUTPUT = os.path.join(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"), "entry.png")
PI = math.pi
TAU = 2.0 * PI


def smoothstep(edge0, edge1, value):
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def blend(canvas, x, y, color, alpha):
    if alpha <= 0.0:
        return
    alpha = min(alpha, 1.0)
    index = (y * WIDTH + x) * 3
    inverse = 1.0 - alpha
    canvas[index] = int(canvas[index] * inverse + color[0] * alpha)
    canvas[index + 1] = int(canvas[index + 1] * inverse + color[1] * alpha)
    canvas[index + 2] = int(canvas[index + 2] * inverse + color[2] * alpha)


def ellipse(canvas, bounds, color, opacity=1.0, softness=1.25):
    x0, y0, x1, y1 = bounds
    rx = (x1 - x0) * 0.5
    ry = (y1 - y0) * 0.5
    cx = x0 + rx
    cy = y0 + ry
    left = max(0, int(x0 - softness - 1))
    right = min(WIDTH, int(x1 + softness + 2))
    top = max(0, int(y0 - softness - 1))
    bottom = min(HEIGHT, int(y1 + softness + 2))
    for y in range(top, bottom):
        ny = (y + 0.5 - cy) / ry
        for x in range(left, right):
            nx = (x + 0.5 - cx) / rx
            distance = (math.sqrt(nx * nx + ny * ny) - 1.0) * min(rx, ry)
            alpha = (1.0 - smoothstep(-softness, softness, distance)) * opacity
            blend(canvas, x, y, color, alpha)


def save_png(path, pixels):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    raw = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        raw.append(0)
        start = y * stride
        raw.extend(pixels[start:start + stride])
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">2I5B", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as image:
        image.write(png)


def polygon(canvas, points, color, softness=1.2, opacity=1.0):
    left = max(0, int(min(point[0] for point in points) - softness - 1))
    right = min(WIDTH, int(max(point[0] for point in points) + softness + 2))
    top = max(0, int(min(point[1] for point in points) - softness - 1))
    bottom = min(HEIGHT, int(max(point[1] for point in points) + softness + 2))
    edges = list(zip(points, points[1:] + points[:1]))
    for y in range(top, bottom):
        py = y + 0.5
        for x in range(left, right):
            px = x + 0.5
            inside = False
            distance2 = 1.0e12
            for (ax, ay), (bx, by) in edges:
                dx = bx - ax
                dy = by - ay
                length2 = dx * dx + dy * dy
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
                ex = px - (ax + t * dx)
                ey = py - (ay + t * dy)
                distance2 = min(distance2, ex * ex + ey * ey)
                if (ay > py) != (by > py) and px < (bx - ax) * (py - ay) / (by - ay) + ax:
                    inside = not inside
            distance = math.sqrt(distance2)
            signed_distance = -distance if inside else distance
            alpha = (1.0 - smoothstep(-softness, softness, signed_distance)) * opacity
            blend(canvas, x, y, color, alpha)


def stroke(canvas, points, color, width, opacity=1.0):
    radius = width * 0.5
    left = max(0, int(min(point[0] for point in points) - radius - 1))
    right = min(WIDTH, int(max(point[0] for point in points) + radius + 2))
    top = max(0, int(min(point[1] for point in points) - radius - 1))
    bottom = min(HEIGHT, int(max(point[1] for point in points) + radius + 2))
    segments = list(zip(points, points[1:]))
    for y in range(top, bottom):
        py = y + 0.5
        for x in range(left, right):
            px = x + 0.5
            distance2 = 1.0e12
            for (ax, ay), (bx, by) in segments:
                dx = bx - ax
                dy = by - ay
                length2 = dx * dx + dy * dy
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
                ex = px - (ax + t * dx)
                ey = py - (ay + t * dy)
                distance2 = min(distance2, ex * ex + ey * ey)
            alpha = (1.0 - smoothstep(radius - 0.8, radius + 0.8, math.sqrt(distance2))) * opacity
            blend(canvas, x, y, color, alpha)


def curve(canvas, start, control, end, color, width, opacity=1.0):
    points = []
    for step in range(13):
        t = step / 12.0
        u = 1.0 - t
        points.append((u * u * start[0] + 2.0 * u * t * control[0] + t * t * end[0],
                       u * u * start[1] + 2.0 * u * t * control[1] + t * t * end[1]))
    stroke(canvas, points, color, width, opacity)


def rotated_ellipse(canvas, cx, cy, rx, ry, angle, color, opacity=1.0, softness=1.25):
    sine = math.sin(angle)
    cosine = math.cos(angle)
    extent_x = math.sqrt((rx * cosine) ** 2 + (ry * sine) ** 2)
    extent_y = math.sqrt((rx * sine) ** 2 + (ry * cosine) ** 2)
    left = max(0, int(cx - extent_x - softness - 1))
    right = min(WIDTH, int(cx + extent_x + softness + 2))
    top = max(0, int(cy - extent_y - softness - 1))
    bottom = min(HEIGHT, int(cy + extent_y + softness + 2))
    for y in range(top, bottom):
        dy = y + 0.5 - cy
        for x in range(left, right):
            dx = x + 0.5 - cx
            local_x = (dx * cosine + dy * sine) / rx
            local_y = (-dx * sine + dy * cosine) / ry
            distance = (math.sqrt(local_x * local_x + local_y * local_y) - 1.0) * min(rx, ry)
            alpha = (1.0 - smoothstep(-softness, softness, distance)) * opacity
            blend(canvas, x, y, color, alpha)


def heart(canvas, cx, cy, size, color, opacity=1.0):
    left = max(0, int(cx - size - 2))
    right = min(WIDTH, int(cx + size + 3))
    top = max(0, int(cy - size - 2))
    bottom = min(HEIGHT, int(cy + size + 3))
    for y in range(top, bottom):
        py = (y + 0.5 - cy) / size
        for x in range(left, right):
            px = (x + 0.5 - cx) / size
            xx = px * px
            yy = py * py
            value = (xx + yy - 1.0) ** 3 - xx * yy * py ** 3
            distance = value * size * 0.32
            alpha = (1.0 - smoothstep(-1.0, 1.0, distance)) * opacity
            blend(canvas, x, y, color, alpha)


def render():
    pixels = bytearray(WIDTH * HEIGHT * 3)
    mint = (223, 245, 238)
    peach = (255, 231, 214)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        base = tuple(int((mint[c] * (1.0 - t) + peach[c] * t) * 0.92)
                     for c in range(3))
        for x in range(WIDTH):
            dx = (x - 515.0) / 650.0
            dy = (y - 488.0) / 650.0
            glow = max(0.0, 1.0 - math.sqrt(dx * dx + dy * dy)) * 0.20
            noise = ((x * 37 + y * 73 + x * y * 19) % 5) - 2
            index = (y * WIDTH + x) * 3
            pixels[index] = max(0, min(255, int(base[0] * (1.0 - glow) + 255 * glow) + noise))
            pixels[index + 1] = max(0, min(255, int(base[1] * (1.0 - glow) + 246 * glow) + noise))
            pixels[index + 2] = max(0, min(255, int(base[2] * (1.0 - glow) + 233 * glow) + noise))

    fur = (255, 246, 233)
    outline = peach
    pink = (255, 158, 181)
    ink = (59, 43, 51)
    white = (255, 255, 255)
    warm = peach

    # A quiet scatter of tiny background wishes.
    for cx, cy, radius in ((154, 268, 13), (862, 205, 11), (925, 524, 12),
                           (140, 708, 10), (881, 882, 12), (300, 904, 9)):
        ellipse(pixels, (cx - radius, cy - radius, cx + radius, cy + radius),
                white, 0.45, 1.0)
        polygon(pixels, ((cx, cy - radius - 5), (cx + 3, cy - 3),
                         (cx + radius + 5, cy), (cx + 3, cy + 3),
                         (cx, cy + radius + 5), (cx - 3, cy + 3),
                         (cx - radius - 5, cy), (cx - 3, cy - 3)),
                white, 1.1)
    heart(pixels, 227, 480, 17, pink, 0.7)
    heart(pixels, 811, 340, 13, pink, 0.72)

    # Ears sit behind the broad, soft head.
    polygon(pixels, ((190, 382), (214, 137), (407, 326), (423, 397)), outline)
    polygon(pixels, ((221, 329), (235, 181), (359, 321), (372, 362)), fur)
    polygon(pixels, ((238, 308), (250, 211), (332, 307), (350, 343)), pink, opacity=0.62)
    polygon(pixels, ((614, 326), (812, 139), (844, 390), (615, 400)), outline)
    polygon(pixels, ((657, 321), (792, 185), (817, 350), (644, 365)), fur)
    polygon(pixels, ((684, 314), (780, 218), (800, 339), (671, 344)), pink, opacity=0.62)
    curve(pixels, (250, 219), (272, 218), (287, 244), white, 3.0, 0.55)
    curve(pixels, (782, 229), (793, 253), (795, 276), white, 3.0, 0.55)

    ellipse(pixels, (126, 179, 898, 931), outline)
    ellipse(pixels, (135, 187, 889, 922), fur)
    ellipse(pixels, (270, 730, 754, 872), warm, 0.22, 28.0)

    # A soft warm rim catches the upper-left edge of the fur.
    curve(pixels, (172, 390), (236, 271), (370, 205), (255, 252, 243), 5.0, 0.62)
    curve(pixels, (370, 205), (438, 179), (512, 179), (255, 252, 243), 5.0, 0.62)

    # Small crown tufts soften the round silhouette.
    ellipse(pixels, (414, 148, 480, 238), outline)
    ellipse(pixels, (424, 158, 470, 228), fur)
    ellipse(pixels, (484, 143, 550, 238), outline)
    ellipse(pixels, (494, 153, 540, 228), fur)
    ellipse(pixels, (546, 160, 608, 249), outline)
    ellipse(pixels, (556, 170, 598, 239), fur)

    # Huge glossy eyes, set a little unevenly for a lively expression.
    ellipse(pixels, (281, 391, 480, 633), outline)
    ellipse(pixels, (287, 396, 474, 627), peach)
    ellipse(pixels, (294, 402, 468, 621), ink)
    ellipse(pixels, (538, 398, 737, 640), outline)
    ellipse(pixels, (544, 403, 731, 634), peach)
    ellipse(pixels, (551, 409, 725, 628), ink)
    ellipse(pixels, (319, 432, 369, 490), white, 0.98)
    ellipse(pixels, (402, 535, 424, 557), white, 0.82)
    ellipse(pixels, (655, 432, 705, 490), white, 0.98)
    ellipse(pixels, (600, 535, 622, 557), white, 0.82)
    curve(pixels, (292, 419), (370, 375), (461, 415), warm, 5.0, 0.75)
    curve(pixels, (550, 426), (628, 383), (729, 422), warm, 5.0, 0.75)

    # Tender cheek blush and tiny freckles.
    ellipse(pixels, (226, 625, 366, 700), pink, 0.55, 2.0)
    ellipse(pixels, (662, 633, 802, 708), pink, 0.55, 2.0)
    for cx, cy in ((271, 656), (305, 667), (696, 664), (731, 653)):
        ellipse(pixels, (cx - 4, cy - 4, cx + 4, cy + 4), white, 0.92, 0.8)

    polygon(pixels, ((493, 633), (512, 618), (533, 633), (513, 651)), pink)
    ellipse(pixels, (506, 626, 514, 634), white, 0.72, 1.0)
    curve(pixels, (512, 654), (494, 675), (478, 661), ink, 4.0)
    curve(pixels, (512, 654), (530, 675), (546, 661), ink, 4.0)
    curve(pixels, (478, 661), (474, 652), (468, 656), ink, 3.5)
    curve(pixels, (546, 661), (551, 652), (557, 656), ink, 3.5)

    # Three fine, gently swept whiskers on either side.
    for start, control, end in (
        ((277, 637), (213, 612), (164, 619)),
        ((272, 656), (204, 652), (151, 671)),
        ((286, 677), (224, 699), (177, 724)),
        ((745, 642), (810, 614), (860, 621)),
        ((750, 661), (818, 657), (873, 675)),
        ((738, 681), (801, 705), (847, 730)),
    ):
        curve(pixels, start, control, end, (185, 167, 160), 2.0, 0.88)

    # A little wave: one paw lifted in greeting.
    ellipse(pixels, (691, 787, 858, 897), (139, 98, 78), 0.2, 24.0)
    rotated_ellipse(pixels, 774, 783, 94, 119, -0.22, outline)
    rotated_ellipse(pixels, 775, 779, 87, 112, -0.22, fur)
    ellipse(pixels, (707, 778, 847, 853), pink, 0.55, 2.0)
    for offset in (-43, 0, 43):
        curve(pixels, (774 + offset, 731), (764 + offset, 754),
              (773 + offset, 772), outline, 4.0, 0.9)
    ellipse(pixels, (752, 798, 762, 808), white, 0.8)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    save_png(OUTPUT, pixels)


if __name__ == "__main__":
    render()
