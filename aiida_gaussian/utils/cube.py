"""
Routines regarding gaussian cube files
"""

import numpy as np
import ase

ANG_TO_BOHR = 1.8897259886


class Cube:
    """
    Gaussian cube format
    """

    def __init__(
        self,
        title=None,
        comment=None,
        ase_atoms=None,
        origin=np.array([0.0, 0.0, 0.0]),
        cell=None,
        cell_n=None,
        data=None
    ):
        # pylint: disable=too-many-arguments
        """
        cell in [au] and (3x3)
        origin in [au]
        """
        self.title = title
        self.comment = comment
        self.ase_atoms = ase_atoms
        self.origin = origin
        self.cell = cell
        self.data = data
        if data is not None:
            self.cell_n = data.shape
        else:
            self.cell_n = cell_n

    @classmethod
    def from_file_handle(cls, filehandle, read_data=True):
        # pylint: disable=too-many-locals
        f = filehandle
        c = cls()
        c.title = f.readline().rstrip()
        c.comment = f.readline().rstrip()

        line = f.readline().split()
        natoms = int(line[0])

        section_headers = False
        if natoms < 0:
            # A negative number of atoms usually indicates that there
            # are multiple data sections and each of those have a header
            natoms = -natoms
            section_headers = True

        c.origin = np.array(line[1:], dtype=float)

        c.cell_n = np.empty(3, dtype=int)
        c.cell = np.empty((3, 3))
        for i in range(3):
            n, x, y, z = [float(s) for s in f.readline().split()]
            c.cell_n[i] = int(n)
            c.cell[i] = n * np.array([x, y, z])

        numbers = np.empty(natoms, int)
        positions = np.empty((natoms, 3))
        for i in range(natoms):
            line = f.readline().split()
            numbers[i] = int(line[0])
            positions[i] = [float(s) for s in line[2:]]

        positions /= ANG_TO_BOHR  # convert from bohr to ang

        c.ase_atoms = ase.Atoms(numbers=numbers, positions=positions)

        if read_data:
            # Option 1: less memory usage but might be slower
            c.data = np.empty(c.cell_n[0] * c.cell_n[1] * c.cell_n[2], dtype=float)
            cursor = 0
            if section_headers:
                f.readline()

            for i, line in enumerate(f):
                ls = line.split()
                c.data[cursor:cursor + len(ls)] = ls
                cursor += len(ls)

            # Option 2: Takes much more memory (but may be faster)
            #data = np.array(f.read().split(), dtype=float)

            c.data = c.data.reshape(c.cell_n)

        return c

    @classmethod
    def from_file(cls, filepath, read_data=True):
        with open(filepath, 'r') as f:
            c = cls.from_file_handle(f, read_data=read_data)
        return c

    def write_cube_file(self, filename):

        natoms = len(self.ase_atoms)

        f = open(filename, 'w')

        if self.title is None:
            f.write(filename + '\n')
        else:
            f.write(self.title + '\n')

        if self.comment is None:
            f.write('cube\n')
        else:
            f.write(self.comment + '\n')

        dv_br = self.cell / self.data.shape

        f.write(
            "%5d %12.6f %12.6f %12.6f\n" % (natoms, self.origin[0], self.origin[1], self.origin[2])
        )

        for i in range(3):
            f.write(
                "%5d %12.6f %12.6f %12.6f\n" %
                (self.data.shape[i], dv_br[i][0], dv_br[i][1], dv_br[i][2])
            )

        if natoms > 0:

            positions = self.ase_atoms.positions * ANG_TO_BOHR
            numbers = self.ase_atoms.get_atomic_numbers()
            for i in range(natoms):
                at_x, at_y, at_z = positions[i]
                f.write("%5d %12.6f %12.6f %12.6f %12.6f\n" % (numbers[i], 0.0, at_x, at_y, at_z))

        self.data.tofile(f, sep='\n', format='%12.6e')

        f.close()

    def swapaxes(self, ax1, ax2):

        p = self.ase_atoms.positions
        p[:, ax1], p[:, ax2] = p[:, ax2], p[:, ax1].copy()

        self.origin[ax1], self.origin[ax2] = (self.origin[ax2], self.origin[ax1].copy())

        self.cell[:, ax1], self.cell[:, ax2] = (self.cell[:, ax2], self.cell[:, ax1].copy())
        self.cell[ax1, :], self.cell[ax2, :] = (self.cell[ax2, :], self.cell[ax1, :].copy())

        self.data = np.swapaxes(self.data, ax1, ax2)

        self.cell_n = self.data.shape

    def get_plane_above_topmost_atom(self, height, axis=2):
        """
        Returns the 2d plane above topmost atom in direction (default: z)
        height in [angstrom]
        """
        topmost_atom_z = np.max(self.ase_atoms.positions[:, axis])  # Angstrom
        plane_z = (height + topmost_atom_z) * ANG_TO_BOHR - self.origin[axis]

        plane_index = int(
            np.round(plane_z / self.cell[axis, axis] * np.shape(self.data)[axis] - 0.499)
        )

        if axis == 0:
            return self.data[plane_index, :, :]
        if axis == 1:
            return self.data[:, plane_index, :]
        return self.data[:, :, plane_index]

    def get_x_index(self, x_ang):
        # returns the index value for a given x coordinate in angstrom
        return int(
            np.round(
                (x_ang * ANG_TO_BOHR - self.origin[0]) / self.cell[0, 0] * np.shape(self.data)[0]
            )
        )

    def get_y_index(self, y_ang):
        # returns the index value for a given y coordinate in angstrom
        return int(
            np.round(
                (y_ang * ANG_TO_BOHR - self.origin[1]) / self.cell[1, 1] * np.shape(self.data)[1]
            )
        )

    def get_z_index(self, z_ang):
        # returns the index value for a given z coordinate in angstrom
        return int(
            np.round(
                (z_ang * ANG_TO_BOHR - self.origin[2]) / self.cell[2, 2] * np.shape(self.data)[2]
            )
        )

    @property
    def dv(self):
        """ in [ang] """
        return self.cell / self.cell_n / ANG_TO_BOHR

    @property
    def dv_ang(self):
        """ in [ang] """
        return self.cell / self.cell_n / ANG_TO_BOHR

    @property
    def dv_au(self):
        """ in [au] """
        return self.cell / self.cell_n

    @property
    def x_arr_au(self):
        """ in [au] """
        return np.arange(
            self.origin[0], self.origin[0] + (self.cell_n[0] - 0.5) * self.dv_au[0, 0],
            self.dv_au[0, 0]
        )

    @property
    def y_arr_au(self):
        """ in [au] """
        return np.arange(
            self.origin[1], self.origin[1] + (self.cell_n[1] - 0.5) * self.dv_au[1, 1],
            self.dv_au[1, 1]
        )

    @property
    def z_arr_au(self):
        """ in [au] """
        return np.arange(
            self.origin[2], self.origin[2] + (self.cell_n[2] - 0.5) * self.dv_au[2, 2],
            self.dv_au[2, 2]
        )

    @property
    def x_arr_ang(self):
        """ in [ang] """
        return self.x_arr_au / ANG_TO_BOHR

    @property
    def y_arr_ang(self):
        """ in [ang] """
        return self.y_arr_au / ANG_TO_BOHR

    @property
    def z_arr_ang(self):
        """ in [ang] """
        return self.z_arr_au / ANG_TO_BOHR
