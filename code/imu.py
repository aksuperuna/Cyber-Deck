#!/usr/bin/env python3

import math
import time
import os

import pygame
from smbus2 import SMBus


# -----------------------------
# MPU6050 configuration
# -----------------------------

I2C_BUS = 1
MPU6050_ADDRESS = 0x68

PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

ACCEL_SCALE = 16384.0   # ±2g
GYRO_SCALE = 131.0      # ±250 degrees/second

ALPHA = 0.98


# -----------------------------
# Upside-down detection
# -----------------------------

UPSIDE_DOWN_THRESHOLD = -0.65
UPRIGHT_THRESHOLD = -0.35
UPSIDE_DOWN_DELAY = 0.25


def signed_int16(high, low):
    value = (high << 8) | low

    if value >= 32768:
        value -= 65536

    return value


class MPU6050:
    def __init__(self, bus_number=1, address=0x68):
        self.bus = SMBus(bus_number)
        self.address = address

        # Wake up the MPU6050
        self.bus.write_byte_data(
            self.address,
            PWR_MGMT_1,
            0
        )

        time.sleep(0.1)

    def read_data(self):
        data = self.bus.read_i2c_block_data(
            self.address,
            ACCEL_XOUT_H,
            14
        )

        accel_x = signed_int16(data[0], data[1])
        accel_y = signed_int16(data[2], data[3])
        accel_z = signed_int16(data[4], data[5])

        gyro_x = signed_int16(data[8], data[9])
        gyro_y = signed_int16(data[10], data[11])
        gyro_z = signed_int16(data[12], data[13])

        return (
            accel_x / ACCEL_SCALE,
            accel_y / ACCEL_SCALE,
            accel_z / ACCEL_SCALE,
            gyro_x / GYRO_SCALE,
            gyro_y / GYRO_SCALE,
            gyro_z / GYRO_SCALE
        )

    def close(self):
        self.bus.close()


def get_accelerometer_angles(ax, ay, az):
    roll = math.degrees(
        math.atan2(ay, az)
    )

    pitch = math.degrees(
        math.atan2(
            -ax,
            math.sqrt(ay * ay + az * az)
        )
    )

    return pitch, roll


def rotate_point(point, pitch, roll, yaw):
    x, y, z = point

    pitch = math.radians(pitch)
    roll = math.radians(roll)
    yaw = math.radians(yaw)

    # Rotate around X axis
    y1 = y * math.cos(pitch) - z * math.sin(pitch)
    z1 = y * math.sin(pitch) + z * math.cos(pitch)
    x1 = x

    # Rotate around Y axis
    x2 = x1 * math.cos(roll) + z1 * math.sin(roll)
    z2 = -x1 * math.sin(roll) + z1 * math.cos(roll)
    y2 = y1

    # Rotate around Z axis
    x3 = x2 * math.cos(yaw) - y2 * math.sin(yaw)
    y3 = x2 * math.sin(yaw) + y2 * math.cos(yaw)
    z3 = z2

    return x3, y3, z3


def project_point(point, screen_width, screen_height):
    x, y, z = point

    camera_distance = 5.0
    scale = 220.0

    denominator = camera_distance - z

    if denominator < 0.2:
        denominator = 0.2

    screen_x = (
        screen_width // 2
        + int(scale * x / denominator)
    )

    screen_y = (
        screen_height // 2
        - int(scale * y / denominator)
    )

    return screen_x, screen_y


def draw_cube(screen, pitch, roll, yaw, color):
    cube_size = 1.0

    vertices = [
        (-cube_size, -cube_size, -cube_size),
        ( cube_size, -cube_size, -cube_size),
        ( cube_size,  cube_size, -cube_size),
        (-cube_size,  cube_size, -cube_size),

        (-cube_size, -cube_size,  cube_size),
        ( cube_size, -cube_size,  cube_size),
        ( cube_size,  cube_size,  cube_size),
        (-cube_size,  cube_size,  cube_size),
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

    projected_points = []

    for vertex in vertices:
        rotated = rotate_point(
            vertex,
            pitch,
            roll,
            yaw
        )

        projected = project_point(
            rotated,
            screen.get_width(),
            screen.get_height()
        )

        projected_points.append(projected)

    for start, end in edges:
        pygame.draw.line(
            screen,
            color,
            projected_points[start],
            projected_points[end],
            4
        )


def main():
    pygame.init()

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("MPU6050 Motion Cube")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 30)

    sensor = MPU6050(
        I2C_BUS,
        MPU6050_ADDRESS
    )

    pitch = 0.0
    roll = 0.0
    yaw = 0.0

    last_time = time.monotonic()

    upside_down = False
    upside_down_time = 0.0

    running = True

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            current_time = time.monotonic()
            dt = current_time - last_time
            last_time = current_time

            # Prevent large angle jumps if the program pauses
            dt = min(dt, 0.1)

            ax, ay, az, gx, gy, gz = sensor.read_data()

            # -----------------------------
            # Detect upside-down orientation
            # -----------------------------

            if not upside_down:
                if az < UPSIDE_DOWN_THRESHOLD:
                    if upside_down_time == 0.0:
                        upside_down_time = current_time

                    elif (
                        current_time - upside_down_time
                        >= UPSIDE_DOWN_DELAY
                    ):
                        upside_down = True

                        # Execute pwrkey once
                        os.system("pwrkey")

                        print("Executed pwrkey")

                else:
                    upside_down_time = 0.0

            else:
                # Leave upside-down mode only when clearly upright
                if az > UPRIGHT_THRESHOLD:
                    upside_down = False
                    upside_down_time = 0.0

            # -----------------------------
            # Calculate orientation
            # -----------------------------

            accel_pitch, accel_roll = get_accelerometer_angles(
                ax,
                ay,
                az
            )

            gyro_pitch = pitch + gx * dt
            gyro_roll = roll + gy * dt

            yaw += gz * dt

            # Complementary filter
            pitch = (
                ALPHA * gyro_pitch
                + (1.0 - ALPHA) * accel_pitch
            )

            roll = (
                ALPHA * gyro_roll
                + (1.0 - ALPHA) * accel_roll
            )

            yaw %= 360.0

            # -----------------------------
            # Draw the window
            # -----------------------------

            if upside_down:
                background_color = (80, 15, 15)
                cube_color = (255, 80, 80)
                status = "UPSIDE DOWN"
                status_color = (255, 100, 100)
            else:
                background_color = (20, 20, 25)
                cube_color = (80, 220, 255)
                status = "UPRIGHT"
                status_color = (100, 255, 100)

            screen.fill(background_color)

            draw_cube(
                screen,
                pitch,
                roll,
                yaw,
                cube_color
            )

            orientation_text = font.render(
                f"Pitch: {pitch:6.1f}   "
                f"Roll: {roll:6.1f}   "
                f"Yaw: {yaw:6.1f}",
                True,
                (240, 240, 240)
            )

            status_text = font.render(
                status,
                True,
                status_color
            )

            acceleration_text = font.render(
                f"Accel Z: {az:+.2f} g",
                True,
                (220, 220, 220)
            )

            screen.blit(orientation_text, (20, 20))
            screen.blit(status_text, (20, 60))
            screen.blit(acceleration_text, (20, 95))

            pygame.display.flip()

            clock.tick(100)

    finally:
        sensor.close()
        pygame.quit()


if __name__ == "__main__":
    main()
