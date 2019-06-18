# -*- coding: utf-8 -*-
"""Some matrix specialization."""

import time

import numpy as np

from . import _pygimli_ as pgcore
from . import (CMatrix, CSparseMapMatrix, CSparseMatrix, ElementMatrix,
               IVector, MatrixBase, R3Vector, RVector, )

from .logger import warn

# make core matrices (now in pgcore, later pgcore.core) known here for tab-completion
BlockMatrix = pgcore.RBlockMatrix
IdentityMatrix = pgcore.IdentityMatrix

BlockMatrix = pgcore.RBlockMatrix
SparseMapMatrix = pgcore.RSparseMapMatrix
SparseMatrix = pgcore.RSparseMatrix
Vector = pgcore.RVector
Matrix = pgcore.RMatrix

class MultMatrix(pgcore.MatrixBase):
    def __init__(self, A, verbose=False):
        self._A = A
        super(MultMatrix, self).__init__(verbose)  # only in Python 3

    @property
    def A(self):
        return self._A
    @A.setter
    def A(self, A):
        self._A = A

    def rows(self):
        """Return number of rows (using underlying matrix)."""
        return self.A.rows()

    def cols(self):
        """Return number of columns (using underlying matrix)."""
        return self.A.cols()

    def save(self, filename):
        """So it can be used in inversion with dosave flag"""
        pass


class MultLeftMatrix(MultMatrix):
    """Matrix consisting of actual RMatrix and lef-side vector."""

    def __init__(self, A, left, verbose=False):
        """Constructor saving matrix and vector."""
        if A.rows() != len(left):
            raise Exception("Matrix columns do not fit vector length!")
        super(MultLeftMatrix, self).__init__(A, verbose)  # only in Python 3

        self._l = left

    @property
    def l(self):
        return self._l
    @l.setter
    def r(self, l):
        self._l = l

    def mult(self, x):
        """Multiplication from right-hand-side (dot product A*x)."""
        return self.A.mult(x) * self.l

    def transMult(self, x):
        """Multiplication from right-hand-side (dot product A.T * x)"""
        return self.A.transMult(x * self.l)

LMultRMatrix = MultLeftMatrix  # alias for backward compatibility


class MultRightMatrix(MultMatrix):
    """Some Matrix, multiplied with a right hand side vector r."""

    def __init__(self, A, r=None, verbose=False):
        super(MultRightMatrix, self).__init__(A, verbose)

        if r is None:
            self._r = pgcore.RVector(self.cols(), 1.0)
        else:
            self._r = r


    @property
    def r(self):
        return self._r
    @r.setter
    def r(self, r):
        self._r = r

    def mult(self, x):
        """Return M*x = A*(r*x)"""
        if len(x) != len(self.r):
            # assuming A was complex
            # warn('need to double x')
            # print('mult:', self.A.rows(), " x " , self.A.cols(), 
            #        'x:', len(x), 'r:', len(self.r))
            # print(self.perm)
            return self.A.mult(x[self.perm] * self.r)
            #return self.A.mult(pgcore.cat(x, x) * self.r)
        return self.A.mult(x * self.r)

    def transMult(self, x):
        """Return M.T*x=(A.T*x)*r"""
        # print('transmult', self.A.rows(), " x " , self.A.cols(), x, self.r, )
        return self.A.transMult(x) * self.r

RMultRMatrix = MultRightMatrix  # alias for backward compatibility


class MultLeftRightMatrix(MultMatrix):
    """Matrix consisting of actual RMatrix and left-hand-side vector."""

    def __init__(self, A, left, right, verbose=False):
        """Constructor saving matrix and vector."""
        if A.cols() != len(right):
            raise Exception("Matrix columns do not fit right vector length!")
        if A.rows() != len(left):
            raise Exception("Matrix rows do not fit left vector length!")

        super(MultLeftRightMatrix, self).__init__(A, verbose)
        self._r = right
        self._l = left

    @property
    def l(self):
        return self._l
    @l.setter
    def r(self, l):
        self._l = l
    @property
    def r(self):
        return self._r
    @r.setter
    def r(self, r):
        self._r = r

    def mult(self, x):
        """Multiplication from right-hand-side (dot product A*x)."""
        return self.A.mult(x * self._r) * self._l

    def transMult(self, x):
        """Multiplication from right-hand-side (dot product A.T*x)."""
        return self.A.transMult(x * self._l) * self._r

LRMultRMatrix = MultLeftRightMatrix  # alias for backward compatibility


__BlockMatrix_addMatrix__ = pgcore.RBlockMatrix.addMatrix
def __BlockMatrix_addMatrix_happy_GC__(self, M):
    """Add an existing matrix to this block matrix and return a unique index.

    The Matrix will not be used until the matrix index has been assigned to a
    row and column number by adding a matrix entry.

    Monkeypatched to increases the reference counter of M to keep the gc happy.
    """
    if not hasattr(self, '__mats__'):
        self.__mats__ = []
    self.__mats__.append(M)
    return __BlockMatrix_addMatrix__(self, M)

pgcore.RBlockMatrix.addMatrix = __BlockMatrix_addMatrix_happy_GC__




class Add2Matrix(pgcore.MatrixBase):
    """Matrix by adding two matrices."""

    def __init__(self, A, B):
        super().__init__()
        self.A = A
        self.B = B
        assert A.rows() == B.rows()
        assert A.cols() == B.cols()

    def mult(self, x):
        """Return M*x = A*(r*x)"""
        return self.A.mult(x) + self.B.mult(x)

    def transMult(self, x):
        """Return M.T*x=(A.T*x)*r"""
        return self.A.transMult(x) + self.B.transMult(x)

    def cols(self):
        """Number of columns."""
        return self.A.cols()

    def rows(self):
        """Number of rows."""
        return self.A.rows()


class Mult2Matrix(pgcore.MatrixBase):
    """Matrix  by multiplying two matrices."""

    def __init__(self, A, B):
        super().__init__()
        self.A = A
        self.B = B
        assert A.cols() == B.rows()

    def mult(self, x):
        """Return M*x = A*(r*x)"""
        return self.A.mult(self.B.mult(x))

    def transMult(self, x):
        """Return M.T*x=(A.T*x)*r"""
        return self.B.transMult(self.A.transMult(x))

    def cols(self):
        """Number of columns."""
        return self.B.cols()

    def rows(self):
        """Number of rows."""
        return self.A.rows()


class DiagonalMatrix(pgcore.MatrixBase):
    """Square matrix with a vector on the main diagonal."""

    def __init__(self, d):
        super().__init__()
        self.d = d

    def mult(self, x):
        """Return M*x = r*x (element-wise)"""
        return x * self.d

    def transMult(self, x):
        """Return M.T*x=(A.T*x)*r"""
        return x * self.d

    def cols(self):
        """Number of columns (length of diagonal)."""
        return len(self.d)

    def rows(self):
        """Number of rows (length of diagonal)."""
        return len(self.d)


class Cm05Matrix(pgcore.MatrixBase):
    """Matrix implicitly representing the inverse square-root."""

    def __init__(self, A, verbose=False):
        """Constructor saving matrix and vector.

        Parameters
        ----------
        A : ndarray
            numpy type (full) matrix
        """
        from scipy.linalg import eigh  # , get_blas_funcs

        if A.shape[0] != A.shape[1]:  # rows/cols for pgcore matrix
            raise Exception("Matrix must by square (and symmetric)!")

        self.size = A.shape[0]
        t = time.time()
        self.ew, self.EV = eigh(A)
        self.mul = np.sqrt(1./self.ew)
        if verbose:
            pgcore.info('(C) Time for eigenvalue decomposition:{:.1f} s'.format(
                time.time() - t))

        self.A = A
        super().__init__(verbose)  # only in Python 3

    def rows(self):
        """Return number of rows (using underlying matrix)."""
        return self.size

    def cols(self):
        """Return number of columns (using underlying matrix)."""
        return self.size

    def mult(self, x):
        """Multiplication from right-hand side (dot product)."""
        part1 = (np.dot(np.transpose(x), self.EV).T*self.mul).reshape(-1, 1)
        return self.EV.dot(part1).reshape(-1,)
#        return self.EV.dot((x.T.dot(self.EV)*self.mul).T)

    def transMult(self, x):
        """Multiplication from right-hand side (dot product)."""
        return self.mult(x)  # matrix is symmetric by definition

class NDMatrix(BlockMatrix):
    """Diagonal block (block-Jacobi) matrix derived from pg.matrix.BlockMatrix.

    (to be moved to a better place at a later stage)
    """

    def __init__(self, num, nrows, ncols):
        super(NDMatrix, self).__init__()  # call inherited init function
        self.Ji = []  # list of individual block matrices
        for i in range(num):
            self.Ji.append(pg.Matrix())
            self.Ji[-1].resize(nrows, ncols)
            n = self.addMatrix(self.Ji[-1])
            self.addMatrixEntry(n, nrows * i, ncols * i)

        self.recalcMatrixSize()
        print(self.rows(), self.cols())
