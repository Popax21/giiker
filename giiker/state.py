import typing, enum

class Color(enum.Enum):
    WHITE = 'W'
    YELLOW = 'Y'
    RED = 'R'
    GREEN = 'G'
    BLUE = 'B'
    ORANGE = 'O'

class Face(enum.Enum):
    L = enum.auto()
    R = enum.auto()
    U = enum.auto()
    D = enum.auto()
    F = enum.auto()
    B = enum.auto()

    @property
    def direction(self) -> typing.Tuple[int, int, int]: return {
        Face.L: (-1,  0,  0),
        Face.R: (+1,  0,  0),
        Face.U: ( 0, +1,  0),
        Face.D: ( 0, -1,  0),
        Face.F: ( 0,  0, +1),
        Face.B: ( 0,  0, -1)
    }[self]

    @property
    def color(self) -> Color: return {
        Face.L: Color.RED,
        Face.R: Color.ORANGE,
        Face.U: Color.BLUE,
        Face.D: Color.GREEN,
        Face.F: Color.YELLOW,
        Face.B: Color.WHITE
    }[self]

    @property
    def opposite(self) -> "Face": return {
        Face.L: Face.R,
        Face.R: Face.L,
        Face.U: Face.D,
        Face.D: Face.U,
        Face.F: Face.B,
        Face.B: Face.F
    }[self]

    def is_on_face(self, x: int, y: int, z: int) -> bool:
        dx, dy, dz = self.direction
        return (
            (dx == 0 or x == dx+1) and
            (dy == 0 or y == dy+1) and
            (dz == 0 or z == dz+1)
        )

class Cubelet:
    home_x: int
    home_y: int
    home_z: int

    x_face: Face
    y_face: Face
    z_face: Face

    def __init__(self, home_x, home_y, home_z, x_face = Face.R, y_face = Face.U, z_face = Face.F):
        self.home_x, self.home_y, self.home_z = home_x, home_y, home_z
        self.x_face, self.y_face, self.z_face = x_face, y_face, z_face

    def get_face_color(self, face: Face) -> Color:
        dx, dy, dz = face.direction
        if dx > 0: return self.x_face.color
        if dx < 0: return self.x_face.opposite.color
        if dy > 0: return self.y_face.color
        if dy < 0: return self.y_face.opposite.color
        if dz > 0: return self.z_face.color
        if dz < 0: return self.z_face.opposite.color
        assert False

    @property
    def is_center(self): return (self.home_x == 1 and self.home_y == 1) or (self.home_x == 1 and self.home_z == 1) or (self.home_y == 1 and self.home_z == 1)
    @property
    def is_edge(self): return not self.is_center and (self.home_x == 1 or self.home_y == 1 or self.home_z == 1)
    @property
    def is_corner(self): return not self.is_center and not self.is_edge

class CubeState:
    cubelets: typing.List[typing.List[typing.List[Cubelet]]]

    def __init__(self): self.cubelets = [[[Cubelet(x,y,z) for z in range(3)] for y in range(3)] for x in range(3)]

    def apply_move(self, move: "Move"):
        rot_mat: typing.List[typing.List[int]] = move.rot_matrix

        new_cubelets = [[[None for x in range(3)] for y in range(3)] for z in range(3)]
        for x, y, z, c in self:
            if move.face.is_on_face(x, y, z):
                p = (x-1,y-1,z-1)
                np = tuple(sum(rot_mat[oi][ni] * p[oi] for oi in range(3)) for ni in range(3))
                nx, ny, nz = np[0]+1, np[1]+1, np[2]+1

                assert new_cubelets[nx][ny][nz] == None
                new_cubelets[nx][ny][nz] = c

                for d, f in [((1, 0, 0), c.x_face), ((0, 1, 0), c.y_face), ((0, 0, 1), c.z_face)]:
                    ndx, ndy, ndz = tuple(sum(rot_mat[oi][ni] * d[oi] for oi in range(3)) for ni in range(3))
                    if ndx != 0:    c.x_face = f if ndx > 0 else f.opposite
                    elif ndy != 0:  c.y_face = f if ndy > 0 else f.opposite
                    elif ndz != 0:  c.z_face = f if ndz > 0 else f.opposite
                    else: assert False
            else:
                assert new_cubelets[x][y][z] == None
                new_cubelets[x][y][z] = c

        self.cubelets = new_cubelets

    @property
    def is_solved(self) -> bool: 
        return all(
            (c.home_x, c.home_y, c.home_z) == (x,y,z) and
            (c.x_face, c.y_face, c.z_face) == (Face.R, Face.U, Face.F)
        for x,y,z,c in self)

    def __getitem__(self, idx): return self.cubelets[idx[0]][idx[1]][idx[2]]
    def __setitem__(self, idx, val): self.cubelets[idx[0]][idx[1]][idx[2]] = val

    def __iter__(self) -> typing.Iterator[typing.Tuple[int, int, int, Cubelet]]:
        for x in range(3):
            for y in range(3):
                for z in range(3):
                    yield x, y, z, self.cubelets[x][y][z] 

    def __str__(self):
        s = ""
        for f in Face:
            if len(s) > 0: s += " "
            for x, y, z, c in self:
                if f.is_on_face(x, y, z):
                    s += c.get_face_color(f).value

        return s

    @staticmethod
    def decode_state(bts: bytes) -> "CubeState":
        def get_nibble(i) -> int: return (bts[i//2] >> (4 - 4 * (i%2))) & 0xf

        state = CubeState()

        #nibbles 0-7: index of cubelet at corner position | 1 nibble [1;8]
        #nibbles 8-15: rotation of cubelet at corner position | 1 nibble [1;3]
        CORNER_POSITIONS = [(x,y,z) for y in [0, 2] for x, z in [(0, 2), (0, 0), (2, 0), (2, 2)]]
        for pi in range(len(CORNER_POSITIONS)):
            x, y, z = CORNER_POSITIONS[pi]
            hx, hy, hz = CORNER_POSITIONS[get_nibble(pi) - 1]
    
            hof = [f if c > 0 else f.opposite for c, f in [(hx, Face.R), (hy, Face.U), (hz, Face.F)]]           #determine outwards facing colors per axis at home position
            of = hof if (x == hx) ^ (z == hz) ^ (y == hy) else hof[::-1]                                        #determine outwards facing colors per axis at current position
            rof = [of[(i + 3-get_nibble(8 + pi)) % 3] for i in range(3)]                                        #determine rotated outwards facing colors
            raf = [rof[i] if (x,y,z)[i] > 0 else rof[i].opposite for i in range(3)]                             #determine rotated axis vector colors (inverted if facing inside)

            state[x,y,z] = Cubelet(hx, hy, hz, *raf)

        #nibbles 16-27: index of cubelet at edge position | 1 nibble [1;12]
        #nibbles 28-30: rotation of cublet at edge position | 1 bit
        EDGE_POSITIONS = [(x,0,z) for x, z in [(1, 2), (0, 1), (1, 0), (2, 1)]] + [(x,1,z) for x, z in [(0, 2), (0, 0), (2, 0), (2, 2)]] + [(x,2,z) for x, z in [(1, 2), (0, 1), (1, 0), (2, 1)]]
        for pi in range(len(EDGE_POSITIONS)):
            x, y, z = EDGE_POSITIONS[pi]
            hx, hy, hz = EDGE_POSITIONS[get_nibble(16 + pi) - 1]

            hof = [f if c > 0 else f.opposite for c, f in [(hx, Face.R), (hy, Face.U), (hz, Face.F)] if c != 1] #determine outwards facing colors at home position
            of = hof if (hx != 1) ^ (x == 1) else hof[::-1]                                                     #determine outwards facing colors at current position

            rofa, rofb = of[::-1] if (bts[14 + pi//8] >> (7 - (pi%8))) & 1 else of                              #determine rotated outwards facing colors per axis
            rof = [None, rofa, rofb] if x == 1 else [rofa, None, rofb] if y == 1 else [rofa, rofb, None]
            raf = [rof[i] if (x,y,z)[i] > 0 else rof[i].opposite for i in range(3)]                             #determine rotated axis vector colors (inverted if facing inside)

            for i in range(3):                                                                                  #fill in missing rotated axis vector colors using cross products
                if raf[i]: continue
                dax, day, daz = raf[(i+1) % 3].direction
                dbx, dby, dbz = raf[(i+2) % 3].direction
                dr = (day*dbz - daz*dby, daz*dbx - dax*dbz, dax*dby - day*dbx)
                raf[i] = next(f for f in Face if f.direction == dr)

            state[x, y, z] = Cubelet(hx, hy, hz, *raf)

        assert (bts[15] & 0xf) == 0

        return state