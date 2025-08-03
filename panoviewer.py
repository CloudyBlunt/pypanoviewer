import pygame
from pygame.locals import * 
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import numpy as np
import math

WIDTH, HEIGHT = 800, 600
FOV_Y = 75.0
Z_NEAR = 0.1
Z_FAR = 100.0

yaw = 0.0
pitch = 0.0
zoom = 1.0

panorama_texture_id = None

#-------------------------------

def create_sphere(radius, slices, stacks):
    vertices = []
    normals = []
    tex_coords = []
    indices = []

    for i in range(stacks + 1):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0 = radius * math.sin(lat0)
        zr0 = radius * math.cos(lat0)

        for j in range(slices + 1):
            lng = 2 * math.pi * float(j) / slices
            x = zr0 * math.cos(lng)
            y = zr0 * math.sin(lng)

            vertices.append([x, y, z0])
            normals.append([x/radius, y/radius, z0/radius]) 
            tex_coords.append([float(j) / slices, float(i) / stacks]) 

    for i in range(stacks):
        for j in range(slices):
            p1 = i * (slices + 1) + j
            p2 = p1 + (slices + 1)
            p3 = p1 + 1
            p4 = p2 + 1

            indices.append([p1, p2, p3])
            indices.append([p3, p2, p4])

    return np.array(vertices, dtype=np.float32), \
           np.array(normals, dtype=np.float32), \
           np.array(tex_coords, dtype=np.float32), \
           np.array(indices, dtype=np.uint32)

def init_gl(width, height):
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y * zoom, (width / float(height)), Z_NEAR, Z_FAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def resize_gl_scene(width, height):
    if height == 0:
        height = 1
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y * zoom, (width / float(height)), Z_NEAR, Z_FAR)
    glMatrixMode(GL_MODELVIEW)

def load_texture(image_path=None):
    global panorama_texture_id

    if panorama_texture_id is not None:
        glDeleteTextures(1, [panorama_texture_id])
        panorama_texture_id = None 
    img = None

    if image_path:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
    if img is None:
        img = Image.fromarray(generate_gradient(2048, 1024))

    img_data = np.array(list(img.getdata()), np.uint8)

    panorama_texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, panorama_texture_id) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) 
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE) 
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    glEnable(GL_TEXTURE_2D) 

def generate_gradient(width, height):
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            r = int(255 * (x / (width - 1)))
            g = int(255 * (y / (height - 1)))
            b = int(255 * (1 - (x / (width - 1))))
            pixels[x, y] = (r, g, b)
    return np.array(img)

# ------------------------------------

def draw_scene(sphere_data):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    glRotatef(yaw, 0.0, 1.0, 0.0)
    glRotatef(pitch, 1.0, 0.0, 0.0)
    glTranslatef(0.0, 0.0, -0.01)
    
    glBindTexture(GL_TEXTURE_2D, panorama_texture_id)
    vertices, normals, tex_coords, indices = sphere_data
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)

    glVertexPointer(3, GL_FLOAT, 0, vertices)
    glNormalPointer(GL_FLOAT, 0, normals)
    glTexCoordPointer(2, GL_FLOAT, 0, tex_coords)
    glDrawElements(GL_TRIANGLES, len(indices.flatten()), GL_UNSIGNED_INT, indices)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_NORMAL_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)


def main():
    global yaw, pitch, zoom
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    init_gl(WIDTH, HEIGHT)
    load_texture()
    sphere_data = create_sphere(1.0, 60, 60)
    
    running = True
    dragging = False
    last_mouse_pos = (0, 0)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                resize_gl_scene(event.w, event.h)
                pygame.display.set_mode((event.w, event.h), DOUBLEBUF | OPENGL | RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    last_mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    current_mouse_pos = event.pos
                    
                    dx = current_mouse_pos[0] - last_mouse_pos[0]
                    dy = current_mouse_pos[1] - last_mouse_pos[1]

                    sensitivity = 0.1

                    pitch += dy * sensitivity
                    yaw += dx * sensitivity

                    yaw %= 360

                    last_mouse_pos = current_mouse_pos
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    zoom *= 0.95
                elif event.y < 0:
                    zoom *= 1.05
                zoom = max(0.1, min(2.0, zoom))
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(FOV_Y * zoom, (WIDTH / float(HEIGHT)), Z_NEAR, Z_FAR)
                glMatrixMode(GL_MODELVIEW)
            elif event.type == pygame.DROPFILE:
                image_path = event.file
                load_texture(image_path)
        draw_scene(sphere_data)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()