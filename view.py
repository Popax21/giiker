import asyncio, threading, pyglet, math, typing, giiker
from pyglet.math import Vec2, Vec3, Vec4, Mat4

CUBE_VERTS = [
    0, 0, 0,  0, 0, 1,  0, 1, 1,  0, 0, 0,  0, 1, 1,  0, 1, 0, # -x
    1, 0, 0,  1, 1, 0,  1, 1, 1,  1, 0, 0,  1, 1, 1,  1, 0, 1, # +x
    0, 0, 0,  1, 0, 0,  1, 0, 1,  0, 0, 0,  1, 0, 1,  0, 0, 1, # -y
    0, 1, 0,  0, 1, 1,  1, 1, 1,  0, 1, 0,  1, 1, 1,  1, 1, 0, # +y
    0, 0, 0,  0, 1, 0,  1, 1, 0,  0, 0, 0,  1, 1, 0,  1, 0, 0, # -z
    0, 0, 1,  1, 0, 1,  1, 1, 1,  0, 0, 1,  1, 1, 1,  0, 1, 1, # +z
]

CUBE_SHADER = pyglet.graphics.shader.ShaderProgram(pyglet.graphics.shader.Shader("""
#version 150 core

in vec3 pos;
in vec4 color;
out vec3 vertPos;
out vec4 vertCol;

uniform WindowBlock {
    mat4 projection;
    mat4 view;
} window; 

uniform mat4 cubeMat, cubeletMat;

void main() {
    gl_Position = window.projection * window.view * cubeMat * cubeletMat * vec4(pos, 1.0);
    vertPos = pos;
    vertCol = color;
}
    """.strip(), "vertex"),
    pyglet.graphics.shader.Shader("""
#version 150 core

in vec3 vertPos;
in vec4 vertCol;
out vec4 outCol;

void main() {
    float xDst = min(vertPos.x, 1-vertPos.x), yDst = min(vertPos.y, 1-vertPos.y), zDst = min(vertPos.z, 1-vertPos.z);
    float xyDst = max(xDst, yDst), xzDst = max(xDst, zDst), yzDst = max(yDst, zDst);
    float edgeDst = min(xyDst, min(xzDst, yzDst));

    outCol = edgeDst > 0.05 ? vertCol : vec4(0.05, 0.05, 0.05, 1);
}
    """.strip(), "fragment")
)

COLOR_RGBS = {
    giiker.Color.WHITE: (255, 255, 255),
    giiker.Color.YELLOW: (255, 213, 0),
    giiker.Color.RED: (185, 0, 0),
    giiker.Color.GREEN: (0, 155, 72),
    giiker.Color.BLUE: (0, 69, 173),
    giiker.Color.ORANGE: (255, 89, 0)
}

class Cubelet:
    cur_x: int
    cur_y: int
    cur_z: int

    cubelet_mat: Mat4
    cube: pyglet.graphics.vertexdomain.VertexList

    def __init__(self, x, y, z):
        self.update_state(x, y, z, giiker.Cubelet(x, y, z))

        #Create the cube mesh
        colors = []
        for face in [giiker.Face.L, giiker.Face.R, giiker.Face.D, giiker.Face.U, giiker.Face.B, giiker.Face.F]:
            if face.is_on_face(x, y, z):
                col = COLOR_RGBS[face.color]
                colors += [col[0] / 255, col[1] / 255, col[2] / 255, 1] * 6
            else:
                colors += [0,0,0,0] * 6

        self.cube = CUBE_SHADER.vertex_list(len(CUBE_VERTS), pyglet.gl.GL_TRIANGLES, pos=('f', CUBE_VERTS), color=('f', colors))

    def draw(self):
        with CUBE_SHADER:
            CUBE_SHADER["cubeletMat"] = self.cubelet_mat
            self.cube.draw(pyglet.gl.GL_TRIANGLES)

    def update_state(self, x, y, z, cblet: giiker.Cubelet):
        self.cur_x, self.cur_y, self.cur_z = x, y, z

        #Update matrix
        self.cubelet_mat = Mat4.from_translation(Vec3(-0.5, -0.5, -0.5)) @ Mat4([
            *cblet.x_face.direction, 0,
            *cblet.y_face.direction, 0,
            *cblet.z_face.direction, 0,
            0, 0, 0, 1
        ]).transpose() @ Mat4.from_translation(Vec3(x+0.5, y+0.5, z+0.5))

class Cube:
    TURN_SPEED = 4*math.pi

    cube_mat: Mat4
    cubelets: typing.List[typing.List[typing.List[Cubelet]]]

    _lock: threading.Lock
    _new_state: giiker.CubeState
    _new_move: giiker.Move

    _cur_move: giiker.Move
    _cur_move_angle: float
    _cur_move_end_state: giiker.CubeState

    def __init__(self, mat):
        self.cube_mat = mat

        self._lock = threading.Lock()
        self._new_state = self._new_move = None

        self._cur_move = self._cur_move_angle = self._cur_move_end_state = None

        #Create cubelets
        self.cubelets = [[[Cubelet(x, y, z) for z in range(3)] for y in range(3)] for x in range(3)]

        pyglet.clock.schedule(self.update)

    def update(self, dt):
        #Check if we have a new cube state
        with self._lock:
            if self._new_state is not None:
                if self._cur_move: self._set_state(self._cur_move_end_state)

                self._cur_move, self._new_move = self._new_move, None
                self._cur_move_angle = 0
                self._cur_move_end_state, self._new_state = self._new_state, None

        #Animate the current move
        if not self._cur_move: return
        self._cur_move_angle += Cube.TURN_SPEED * dt

        if self._cur_move_angle < abs(self._cur_move.angle):
            pass
        else:
            self._set_state(self._cur_move_end_state)
            self._cur_move = self._cur_move_angle = self._cur_move_end_state = None

    def draw(self):
        with CUBE_SHADER:
            CUBE_SHADER["cubeMat"] = self.cube_mat

            #Draw cubelets
            for cblet in self:
                if self._cur_move and self._cur_move.face.is_on_face(cblet.cur_x, cblet.cur_y, cblet.cur_z): continue
                cblet.draw()

            #Draw moving cubelets
            if self._cur_move:
                CUBE_SHADER["cubeMat"] = self.cube_mat @ Mat4.from_rotation((+1 if self._cur_move.is_ccw else -1) * self._cur_move_angle, Vec3(*self._cur_move.face.direction))

                for cblet in self:
                    if not self._cur_move.face.is_on_face(cblet.cur_x, cblet.cur_y, cblet.cur_z): continue
                    cblet.draw()

    def update_state(self, state: giiker.CubeState, move: giiker.Move):
        with self._lock:
            if move: self._new_state, self._new_move = state, move
            else: self._set_state(state)

    def _set_state(self, state: giiker.CubeState):
        for x, y, z, cblet in state:
            self.cubelets[cblet.home_x][cblet.home_y][cblet.home_z].update_state(x, y, z, cblet)

    def __iter__(self) -> typing.Iterable[Cubelet]:
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    yield self.cubelets[x][y][z]

class CubeView(pyglet.window.Window):
    cam_angles: Vec2
    cube: Cube

    _lock: threading.Lock
    _should_close: bool

    def __init__(self):
        super().__init__(1024, 1024, caption="GiiKER Cube View")
        self.set_vsync(True)

        self._lock = threading.Lock()
        self._should_close = False

        #Set up rendering
        pyglet.gl.glClearColor(0.9, 0.9, 0.9, 1)
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glCullFace(pyglet.gl.GL_BACK)
        self.cam_angles = Vec2(math.pi/4, math.pi/4)

        #Create the cube
        self.cube = Cube(Mat4.from_translation(-Vec3(3,3,3) / 2))

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.projection = Mat4.perspective_projection(self.aspect_ratio, 0.1, 1000)

    def on_draw(self, dt):
        self.clear()

        #Update view matrix
        sx, cx = math.sin(self.cam_angles.x), math.cos(self.cam_angles.x)
        sy, cy = math.sin(self.cam_angles.y), math.cos(self.cam_angles.y)
        cam_pos = Vec3(sy * cx, sx, cy * cx) * 10
        self.view = Mat4.look_at(cam_pos, Vec3(), -cam_pos.cross(Vec3(0, 1, 0)).cross(-cam_pos).normalize())

        #Draw the cube
        self.cube.draw()

    def on_key_press(self, symbol, modifiers):
        ud, sd = None, None
        if symbol == pyglet.window.key._1:   ud, sd = Vec3(+1, 0, 0), Vec3(0, +1, 0)
        elif symbol == pyglet.window.key._2: ud, sd = Vec3(-1, 0, 0), Vec3(0, -1, 0)
        elif symbol == pyglet.window.key._3: ud, sd = Vec3(0, +1, 0), Vec3(0, 0, +1)
        elif symbol == pyglet.window.key._4: ud, sd = Vec3(0, -1, 0), Vec3(0, 0, -1)
        elif symbol == pyglet.window.key._5: ud, sd = Vec3(0, 0, +1), Vec3(+1, 0, 0)
        elif symbol == pyglet.window.key._6: ud, sd = Vec3(0, 0, -1), Vec3(-1, 0, 0)
        else: return

        self.cube.cube_mat = Mat4.from_translation(-Vec3(3,3,3) / 2) @ Mat4([
            *sd, 0,
            *ud, 0,
            *sd.cross(ud), 0,
            0, 0, 0, 1
        ]).transpose()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if (buttons & pyglet.window.mouse.LEFT) == 0: return
        self.cam_angles.x -= dy / 512
        self.cam_angles.y -= dx / 512
        self.cam_angles.x = pyglet.math.clamp(self.cam_angles.x, -math.pi/2 * 0.9, +math.pi/2 * 0.9)
        self.cam_angles.y = self.cam_angles.y % (2*math.pi)

    def run(self):
        while not self.has_exit:
            with self._lock:
                if self._should_close: break

            dt = pyglet.clock.tick()
            self.dispatch_events()
            self.dispatch_event('on_draw', dt)
            self.flip()

        self.close()

    @staticmethod
    def run_thread(exit_cb: typing.Union[None, typing.Callable] = None) -> asyncio.Future[typing.Tuple["CubeView", threading.Thread]]:
        fut = asyncio.Future()

        def thread_fnc(loop: asyncio.BaseEventLoop):
            view = CubeView()
            loop.call_soon_threadsafe(lambda: fut.set_result((view, threading.current_thread())))
            view.run()
            if exit_cb and loop.is_running(): loop.call_soon_threadsafe(exit_cb)

        threading.Thread(target=thread_fnc, args=(asyncio.get_event_loop(),)).start()

        return fut

    def close_threadsafe(self):
        with self._lock: self._should_close = True

if __name__ == '__main__': CubeView().run()
    