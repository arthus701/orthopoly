r"""
The spherical_harmonic module provides functions for evaluation of the real, 2D, orthonormal, spherical harmonics and their first two derivatives. A single spherical harmonic is a function in 2D spherical space with a degree and order, :math:`n` and :math:`m`,

.. math::   Y_n^m (\theta, \phi) ,

where :math:`\theta` is the colatitude in :math:`[0,\pi]` and :math:`\phi` is the longitude in :math:`[0,2\pi]`. Each harmonic is the product of an associated Legendre polynomial in the colatitude coordinate and a sine or cosine in the longitude coordinate. Whether the associated Legendre function is accompanied by a sine or a cosine is (for the real harmonics) determined by the sign of the order (:math:`m`). In full, the harmonics are implemented here as

.. math::
    :nowrap:

    \begin{equation}
        Y_n^m(\theta,\phi) =
        \begin{cases}
            \sqrt{2} \cos(m\theta) P_n^{|m|}(\cos\theta) & m < 0 \\
            P_n^{m}(\cos\theta) & m = 0 \\
            \sqrt{2} \sin(m\theta) P_n^{m}(\cos\theta) & m > 0
        \end{cases}
    \end{equation}

where :math:`P_n^m` is an associated Legendre polynomial (:func:`legen_theta`). The harmonics here are orthonormal.

This module contains functions for evaluating the :func:`spherical harmonics <sph_har>`, their :func:`gradients <grad_sph_har>`, and their :func:`laplacians <lap_sph_har>`. It doesn't contain functions to perform transforms from values on the sphere to spherical harmonic expansion coefficients. The module also contains some functions for generating grids in spherical space and for generating random spherical harmonic expansions with specific power density properties (:func:`noise`). The :class:`Expansion` class stores harmonic coefficients, evaluates them, and may be multiplied/divided by scalars. For evaluating only a few expansions at a few sets of points, using the :func:`sph_har` function or :class:`Expansion` class should be fine. For evaluating many expansions (of the same size) at the same set of points, consider using the :func:`sph_har_matrix` function.
"""

import warnings
import numpy as np
from itertools import product
from scipy.spatial import SphericalVoronoi
from numpy import (pi, sqrt, abs, sin, cos, tan, arcsin, arccos, arctan, arctan2,
                   dot, cross, array, zeros, isclose, all, int_, float_)

from .util import *

__all__ = [
    'cart2sph',
    'sph2cart',
    'latlon2sph',
    'sph2latlon',
    'T2nharm',
    'R2nharm',
    'Tnm',
    'Rnm',
    'gegen_hat',
    'legen_norm',
    'legen_hat',
    'legen_theta',
    'dlegen_theta',
    'ddlegen_theta',
    'sph_har_norm',
    'sph_har',
    'sph_har_sum',
    'grad_sph_har',
    'lap_sph_har',
    'sph_har_matrix',
    'sph_har_T_matrix',
    'sph_har_R_matrix',
    'grid_regular',
    'grid_fibonacci',
    'grid_icosahedral',
    'spectrum',
    'noise',
    'Expansion'
]

#-------------------------------------------------------------------------------
# utility functions

#(x, y, z) -> (r, theta, phi)
def cart2sph(x, y, z):
    r"""Converts 3D cartesian coordinates into spherical coordinates

    :param array x: x coordinates
    :param array y: y coordinates
    :param array z: z coordinates

    :return: tuple containing

        - spherical radii
        - polar angles in :math:`[0,\pi]`
        - azimuthal angles in :math:`[0,2\pi]`"""

    r = sqrt(x*x + y*y + z*z)
    theta = arccos(z/r)
    phi = arctan2(y, x) + pi
    return(r, theta, phi)

#(r, theta, phi) -> (x, y, z)
def sph2cart(r, theta, phi):
    r"""Converts spherical coordinates into 3D cartesian coordinates

    :param array r: spherical radii
    :param array theta: polar angles in :math:`[0,\pi]`
    :param array phi: azimuthal angles in :math:`[0,2\pi]`

    :return: tuple containing

        - x coordinates
        - y coordinates
        - z coordinates"""

    x = r*sin(theta)*cos(phi)
    y = r*sin(theta)*sin(phi)
    z = r*cos(theta)
    return(x,y,z)

#(lat, lon) -> (theta, phi)
def latlon2sph(lat, lon):
    r"""Converts from latitude and longitude in degrees to radians

    :param array lat: latitude in [-90,90]
    :param array lon: longitude in [-180,180]

    :return: tuple containing

        - array of polar angles in :math:`[0,\pi]`
        - array of azimuthal angles in :math:`[0,2\pi]`"""

    theta = (-lat/180)*pi + pi/2
    phi = (lon/180)*pi + pi
    return(theta, phi)

#(theta, phi) -> (lat, lon)
def sph2latlon(theta, phi):
    r"""Converts from radians to latitude and longitude

    :param array theta: polar angle in :math:`[0,\pi]`
    :param array phi: azimuthal angle in :math:`[0,2\pi]`

    :return: tuple containing

        - array of latitudes in [-90,90]
        - array of longitudes in [-180,180]"""

    lat = -(theta - pi/2)*(180/pi)
    lon = (phi - pi)*(180/pi)
    return(lat, lon)

#the number of functions in a triangular truncation
T2nharm = lambda N: (N + 1)**2
T2nharm.__doc__ = 'Computes the number of functions/harmonics in a triangular truncation of degree N'

#the number of functions in a rhomboidal truncation, which must be positive
R2nharm = lambda N,M: (N + 1)**2 - (((abs(N - M + 1) + (N - M + 1))/2).astype('int'))**2
R2nharm.__doc__ = 'Computes the number of functions/harmonics in a rhomboidal truncation of degree N, order width M'

def Tnm(N):
    """Gets arrays representing the degrees and orders of a trianglular truncation of maximum degree N

    :param int N: degree of truncation

    :return: tuple containing

        - the degrees of the functions in the expansion
        - the orders of the functions in the expansion"""

    nharm = T2nharm(N)
    yn = zeros((nharm,), dtype=int_)
    ym = zeros((nharm,), dtype=int_)
    i = 0 #counter
    for n in range(N+1):
        for m in range(-n,n+1):
            yn[i] = n
            ym[i] = m
            i += 1
    return(yn, ym)

def Rnm(N, M):
    """Gets arrays representing the degrees and orders of a rhomboidal truncation of maximum degree N and order width M

    :param int N: highest degree in truncation
    :param int M: highest number of orders in each degree

    :return: tuple containing

        - the degrees of the functions in the expansion
        - the orders of the functions in the expansion"""

    nharm = R2nharm(N, M)
    yn = zeros((nharm,), dtype=int_)
    ym = zeros((nharm,), dtype=int_)
    i = 0 #counter
    for n in range(N+1):
        #left branch
        mf = -n + M - 1
        if mf > 0: mf = 0
        for m in range(-n,mf+1):
            yn[i] = n
            ym[i] = m
            i += 1
        #right branch
        mi = n - M + 1
        if mi < 1: mi = 1
        for m in range(mi,n+1):
            yn[i] = n
            ym[i] = m
            i += 1
    return(yn, ym)

#-------------------------------------------------------------------------------
# functions for evaluating associated Legendre polynomials

def gegen_hat(xhat, n, m):
    r"""Evaluates the degree :math:`n`, order :math:`m` Gegenbauer polynomial using a three term recurrance relationship. As noted in Appendix A of Boyd, this recurrance relationship is mildly unstable for :math:`m` > 0 and the instability worsens for higher :math:`m`. However, it appears that relative error better than :math:`10^{-10}` can be expected if :math:`m` is less than about 50. More info is in
        * Boyd, John P. Chebyshev and Fourier spectral methods. Courier Corporation, 2001.

    :param array/float xhat: evaluation point in :math:`[-1,1]`
    :param int n: degree of polynomial
    :param int m: order of polynomial

    :return: evaluated function, :math:`C_n^m(\hat{x})``"""

    #instability warning
    if m > 45:
        warnings.warn('WARNING: the three term recurrance relation used to evaluate the Gegenbauer polynomials is weakly unstable for high order (m) evaluations.')
    #low n cases
    if n == 0: return(1.0)
    if n == 1: return(2.0*m*xhat)
    #higher n cases using 3 term recurrance relation
    cprev = 1.0 #previous value
    ccurr = 2.0*m*xhat #current value
    i = 1 #counter
    while i < n:
        #compute the next value and swap current with previous at the same time
        cprev, ccurr = ccurr, (2.0*(i + m)*xhat*ccurr - (i + 2.0*m - 1.0)*cprev)/(i + 1.0)
        #increment
        i += 1

    return(ccurr)

def _check_legen_hat_args(xhat, n, m):
    """Checks arguments to Legendre functions are valid"""

    #check points within bounds
    assert all(abs(xhat) <= 1.0), "can't evaluate associated Lege ndre outside [-1,1]"
    #check order isn't negative
    assert m >= 0, "can't have m < 0 in evaluating associated Legendre"
    #warn about order greater than degree
    if m > n:
        warnings.warn("A Legendre function of order greater than degree (m > n) was evaluated. These are zero by the definition and it's unusual to need them.")
        return(0.0*xhat)

def legen_norm(n, m):
    r"""Evaluates the normalization factor for the associated Legendre polynomials with an iteration instead of direct factorials to help avoid overflow:

    .. math::
        :nowrap:

        \begin{equation}
            \sqrt{\frac{(2n + 1) (n - m)!}{4 \pi (n + m)!}}
        \end{equation}

    :param int n: degree of polynomial
    :param int m: order of polynomial (m >= 0)

    :return: normalization factor"""

    f = sqrt((2*n + 1)/(4*pi))
    for i in range(n - m + 1, n + m + 1):
        f /= sqrt(float(i))

    return(f)

def legen_hat(xhat, n, m):
    r"""Evaluates the normalized associated Legendre function of degree n and order m, :math:`P_n^m(x)`, through a three term recurrance relationship. These are **normalized** and the normalization factor is:

    .. math::
        :nowrap:

        \begin{equation}
            \sqrt{\frac{(2n + 1) (n - m)!}{4 \pi (n + m)!}}
        \end{equation}

    as defined in chapter 6 of the reference below, but without the extra factor of :math:`-1^m`
        * Press, William H., et al. Numerical recipes 3rd edition: The art of scientific computing. Cambridge university press, 2007.

    :param array/float xhat: evaluation point in :math:`[-1,1]` (can be an array)
    :param int n: degree of polynomial
    :param int m: order of polynomial (m >= 0)

    :return: evaluated function, :math:`P_n^m(\hat{x})`"""

    #check for issues with input
    _check_legen_hat_args(xhat, n, m)

    #evaluate the initial recursion value, P_m^m, with stable factorials
    pprev = 1.0 #running value for factorials, which becomes P_m^m
    if m > 0: #account for 0! and avoid division by zero
        pprev /= sqrt(2.0*m)
        for i in range(2*m-1, 1, -1):
            if (2*m - 1 - i) % 2 == 0: #double factorial only on every other
                pprev *= i
            pprev /= sqrt(i)
    pprev *= sqrt((2.0*m + 1.0)/(4.0*pi))*((1.0 - xhat**2)**(m/2.0))
    if n == m: return(pprev)
    #evaluate the second value
    pcurr = xhat*sqrt(2.0*m + 3.0)*pprev
    if n == m + 1: return(pcurr)
    #do the recursion
    i = m + 2
    while i <= n:
        #prefactors
        a = sqrt((4.0*i**2 - 1.0)/(i**2 - m**2))
        b = sqrt(((i - 1.0)**2 - m**2)/(4.0*(i - 1.0)**2 - 1.0))
        #evaluate and swap simultaneously
        pprev, pcurr = pcurr, a*(xhat*pcurr - b*pprev)
        #increment
        i += 1

    return(pcurr)

def legen_theta(t, n, m):
    r"""Evaluates the normalized associated Legendre function :math:`P_n^m(cos(\theta))` with a colatitude argument in :math:`[0,\pi]` instead of :math:`[-1,1]`

    :param array/float t: colatitude evaluation point(s) in :math:`[0,\pi]` (can be an array)
    :param int n: degree of polynomial
    :param int m: order of polynomial (m >= 0)

    :return: evaluated function, :math:`P_n^m(\cos(\theta))`"""

    #call the regular Legendre function with xhat=cos(theta)
    return( legen_hat(cos(t), n, m) )

def dlegen_theta(t, n, m):
    r"""Evaluates the first derivative of the normalized associated Legendre function with colatitude argument, :math:`d P_n^m / d \theta`. This can be used in computing the gradient of spherical harmonics. The algorithm is detailed in:
        * Bosch, W. "On the computation of derivatives of Legendre functions." Physics and Chemistry of the Earth, Part A: Solid Earth and Geodesy 25.9-11 (2000): 655-659.

    :param array/float t: colatitude evaluation point(s) in :math:`[0,\pi]` (can be an array)
    :param int n: degree of polynomial
    :param int m: order of polynomial (m >= 0)

    :return: evaluated first derivative, :math:`d P_n^m / d \theta`"""

    if m == 0 and n == 0:
        return( 0.0*t )
    elif m == 0:
        return( -sqrt(n*(n+1.0))*legen_theta(t,n,1) )
    elif m == n:
        return( sqrt(n/2)*legen_theta(t,n,n-1) )
    else:
        return( (sqrt((n+m)*(n-m+1))*legen_theta(t,n,m-1)
               - sqrt((n+m+1)*(n-m))*legen_theta(t,n,m+1))/2 )

def ddlegen_theta(t, n, m):
    r"""Evaluates the second derivative of the normalized associated Legendre function with colatitude argument, :math:`d^2 P_n^m / d \theta^2`. This can be used in computing the Laplacian of spherical harmonics. The algorithm is detailed in:
        * Bosch, W. "On the computation of derivatives of Legendre functions." Physics and Chemistry of the Earth, Part A: Solid Earth and Geodesy 25.9-11 (2000): 655-659.

    :param array/float t: colatitude evaluation point(s) in :math:`[0,\pi]` (can be an array)
    :param int n: degree of polynomial
    :param int m: order of polynomial (m >= 0)

    :return: evaluated second derivative, :math:`d^2 P_n^m / d \theta^2`"""

    if m == 0 and n == 0:
        return( 0.0*t )
    elif m == 0:
        return( -sqrt(n*(n+1))*dlegen_theta(t,n,1) )
    elif m == n:
        return( sqrt(n/2)*dlegen_theta(t,n,n-1) )
    else:
        return( (sqrt((n+m)*(n-m+1))*dlegen_theta(t,n,m-1)
               - sqrt((n+m+1)*(n-m))*dlegen_theta(t,n,m+1))/2 )

#-------------------------------------------------------------------------------
# functions for evaluating spherical harmonics

def _check_sph_har_args(t, p, n, m):
    """Makes sure arguments to spherical harmonic functions are valid"""

    assert abs(m) <= n, "can't have abs(m) > n in evaluating spherical harmonics (can't be outside the triangle)"
    assert all(p >= 0) and all(p <= 2*pi), "must evaluate spherical harmonics with 0 <= phi <= 2*pi"
    assert all(t >= 0) and all(t <= pi), "must evaluate spherical harmonics with 0 <= theta <= pi"

def sph_har_norm(n, m):
    r"""Evaluates, with an iteration instead of direct factorials to help avoid overflow, the normalization factor for the spherical harmonics,

    .. math::
        :nowrap:

        \begin{equation}
            \sqrt{ \frac{ (2 - \delta_{m,0})(2n + 1)(n - m)! }{ 4 \pi (n + m)! } } \, ,
        \end{equation}

    where :math:`\delta` is the kronecker delta.

    This can be used to unorthonormalize the spherical harmonics given by :func:`sph_har` or to orthonormalize some unorthonormalized functions. The factorials are evaluated to avoid underflow, but very high orders may still be problematic. Because the orthonormalization is built into the Legendre polynomials used to construct the harmonics in this module, this function is not called to evaluate the harmonics or the legendre polynomials. It's just a convenience function for converting between orthonormalized and unorthonormalized harmonics.

    :param int n: degree of harmonic
    :param int m: order of harmonic

    :return: orthonormalization factor"""

    #only positive m
    m = abs(m)
    #check m value
    assert m <= n, '|m| must be less than or equal to n'
    #start with a prefactor of 2 for zonal harmonics
    if m == 0: f = 1.0
    else:      f = 2.0
    #initialize a running product to avoid overflow/underflow
    K = sqrt(f*(2.0*n + 1)/(4*pi))
    for i in range(n - m + 1, n + m + 1):
        K /= sqrt(float(i))

    return(K)

def sph_har(t, p, n, m):
    r"""Evaluate the **real**, **orthonormal**, spherical harmonic of degree n and
    order m.

    These are associated Legendre polynomials (:func:`legen_hat`) in
    latitude (:math:`\theta`) and sine/cosine in longitude (:math:`\phi`).

    .. math::
        :nowrap:

        \begin{equation}
            Y_n^m(\theta,\phi) =
            \begin{cases}
                \sqrt{2} \cos(m\theta) P_n^{|m|}(\cos\theta) & m < 0 \\
                P_n^{m}(\cos\theta) & m = 0 \\
                \sqrt{2} \sin(m\theta) P_n^{m}(\cos\theta) & m > 0
            \end{cases}
        \end{equation}

    where :math:`P_n^m` is the normalized associated Legendre function implemented in this module as :func:`legen_hat` or :func:`legen_theta`. The normalization ensures that the functions are orthonormal. More info can be found in the references below, among many other places
        * Press, William H., et al. Numerical recipes 3rd edition: The art of scientific computing. Cambridge university press, 2007.
        * Dahlen, F.A. and, and Jeroen Tromp. Theoretical global seismology. Princeton university press, 1998.
        * Fornberg, Bengt. A Practical Guide to Pseudospectral Methods. Cambridge University Press, 1996.

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param int n: degree of harmonic
    :param int m: order of harmonic

    :return: :math:`Y_n^m(\phi,\theta)`"""

    #check arguments
    _check_sph_har_args(t, p, n, m)

    #handle different cases for m
    if     m < 0:  Y = sqrt(2.0)*cos(m*p)
    elif   m == 0: Y = 1.0 + 0.0*p #is one by default, but the same shape as p
    else:          Y = sqrt(2.0)*sin(m*p)
    #apply the associated Legendre function
    Y *= legen_theta(t, n, abs(m))

    return(Y)

def sph_har_sum(t, p, a, yn, ym):
    r"""Evaluates a spherical harmonic expansion at arbitrary points with arbitrary orders and degrees

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param array a: spherical harmonic expansion coefficients
    :param iterable yn: the degrees of the functions in the expansion
    :param iterable ym: the orders of the functions in the expansion

    :return: value of expansion at :math:`\sum_{i} a_i Y_{n_i}^{m_i}(\phi,\theta)`"""

    assert len(a) == len(yn) == len(ym), 'a, yn, and ym must be the same length'

    y = sum( a[i]*sph_har(t, p, yn[i], ym[i]) for i in range(len(a)) )

    return(y)

def grad_sph_har(t, p, n, m, R=1):
    r"""Evaluates the gradient of the real, orthonormal, spherical harmonics defined in :func:`sph_har`

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param int n: degree of harmonic
    :param int m: order of harmonic
    :param float R: the radius of the spherical surface, which scales the gradient

    :return: tuple containing

        - gradient component in the :math:`\theta` direction
        - gradient component in the :math:`\phi` direction"""

    #check arguments
    _check_sph_har_args(t, p, n, m)

    #start with the spherical prefactors
    dt = 1.0/R
    dp = 1.0/(R*sin(t))

    #handle different cases for m
    if m < 0:
        dt *= sqrt(2.0)*cos(m*p)
        dp *= -sqrt(2.0)*m*sin(m*p)
    elif m == 0:
        dt *= 1.0 + 0.0*p #forece the same shape as p
        dp *= 0.0*p #force the same shape as p
    else:
        dt *= sqrt(2.0)*sin(m*p)
        dp *= sqrt(2.0)*m*cos(m*p)

    #apply associated Legendre functions
    dt *= dlegen_theta(t, n, abs(m))
    dp *= legen_theta(t, n, abs(m))

    return(dt, dp)

def lap_sph_har(t, p, n, m, R=1):
    r"""Evaluates the Laplacian of the real, orthonormal, spherical harmonics
    defined in :func:`sph_har`

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param int n: degree of harmonic
    :param int m: order of harmonic
    :param float R: the radius of the spherical surface, which scales the gradient

    :return: :math:`\nabla^2 Y_n^m(\theta,\phi)`"""

    #check arguments
    _check_sph_har_args(t, p, n, m)

    #start with spherical prefactors
    ddt = 1.0/((R**2)*sin(t))
    ddp = 1.0/((R**2)*(sin(t)**2))

    #handle different cases for m
    if m < 0:
        ddt *= cos(m*p)*sqrt(2.0)*(sin(t)*ddlegen_theta(t,n,abs(m)) + cos(t)*dlegen_theta(t,n,abs(m)))
        ddp *= -sqrt(2.0)*legen_theta(t,n,abs(m))*(m**2)*cos(m*p)
    elif m == 0:
        ddt *= sin(t)*ddlegen_theta(t,n,m) + cos(t)*dlegen_theta(t,n,m)
        ddp *= 0.0*t #force the same shape as t
    else:
        ddt *= sin(m*p)*sqrt(2.0)*(sin(t)*ddlegen_theta(t,n,m) + cos(t)*dlegen_theta(t,n,m))
        ddp *= -sqrt(2.0)*legen_theta(t,n,m)*(m**2)*sin(m*p)

    #sum the components
    lap = ddt + ddp

    return(lap)

def sph_har_matrix(t, p, yn, ym):
    r"""Assembles the matrix of spherical harmonic function values for an arbitrary subset of harmonics using the latitude coordinates t and the longitude coordinates p

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param array yn: the degrees of the functions in the expansion
    :param array ym: the orders of the functions in the expansion

    :return: matrix with shape (npts,nharm) containing the values of the harmonics at the input points (each row for a point, each column for a harmonic). This matrix is multiplied directly with expansion coefficients to evaluate the expansion at the given points. That is, the returned matrix :math:`Y` sasatisfies :math:`Y a = f`, where a is a vector of nharm expansion coefficients and f is a vector of npts sampled points over the sphere."""

    #number of points
    assert len(t) == len(p), "unequal number of theta and phi coordinates"
    npts = len(t)

    #number of harmonics
    assert len(yn) == len(ym), "yn and ym must be equal length"
    nharm = len(yn)

    #matrix
    Y = zeros((npts,nharm))
    i = 0 #counter
    for i,(n,m) in enumerate(zip(yn,ym)):
        Y[:,i] = sph_har(t, p, n, m)
        i += 1

    return(Y)

def sph_har_T_matrix(t, p, N):
    r"""Assembles the matrix of spherical harmonic function values for a triangular truncation of degree N using the latitude coordinates t and the longitude coordinates p

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param int N: degree of triangular truncation

    :return: tuple containing

        - matrix with shape (npts,nharm) containing the values of the harmonics at the input points (each row for a point, each column for a harmonic). This matrix is multiplied directly with expansion coefficients to evaluate the expansion at the given points. That is, the returned matrix :math:`Y` sasatisfies :math:`Y a = f`, where a is a vector of nharm expansion coefficients and f is a vector of npts sampled points over the sphere.
        - array of the degrees of the functions in the expansion
        - array of the orders of the functions in the expansion"""

    #total number of functions/harmonics
    nharm = T2nharm(N)
    #number of points
    assert len(t) == len(p), "unequal number of theta and phi coordinates"
    npts = len(t)
    #matrix
    Y = zeros((npts,nharm))
    yn, ym = Tnm(N)
    for i,(n,m) in enumerate(zip(yn,ym)):
        Y[:,i] = sph_har(t, p, n, m)

    return(Y, yn, ym)

def sph_har_R_matrix(t, p, N, M):
    r"""Assembles the matrix of spherical harmonic function values for a rhomboidal truncation of degree N and order width M, using the latitude coordinates t and the longitude coordinates p

    :param array/float t: :math:`\theta`, colatitude coordinate in :math:`[0,\pi]` (can be an array)
    :param array/float p: :math:`\phi`, azimuth/longitude coordinate in :math:`[0,2\pi]` (can be an array)
    :param int N: degree of rhomboidal truncation
    :param int M: order width of rhomboidal truncation

    returns: tuple containing

        - matrix with shape (npts,nharm) containing the values of the harmonics at the input points (each row for a point, each column for a harmonic). This matrix is multiplied directly with expansion coefficients to evaluate the expansion at the given points. That is, the returned matrix :math:`Y` sasatisfies :math:`Y a = f`, where a is a vector of nharm expansion coefficients and f is a vector of npts sampled points over the sphere.
        - array of the degrees of the functions in the expansion
        - array of the orders of the functions in the expansion"""

    #total number of functions/harmonics
    nharm = R2nharm(N, M)
    #number of points
    assert len(t) == len(p), "unequal number of theta and phi coordinates"
    npts = len(t)
    #matrix
    Y = zeros((npts,nharm))
    yn, ym = Rnm(N)
    for i,(n,m) in enumerate(zip(yn,ym)):
        Y[:,i] = sph_har(t, p, n, m)

    return(Y, yn, ym)

#-------------------------------------------------------------------------------
# functions for grid generation

def grid_regular(nth, nph=None, poles=True):
    r"""Creates a grid of points regularly spaced in each direction. It can include points right at the poles or can be a nice 2D array by starting and stopping off the boundaries

    :param int nth: number of theta points
    :param int nph: number of phi points (will be 2*nth if unused)
    :param bool poles: include two points exactly at the poles or not

    :return: tuple containing

        - :math:`\theta`, array of colatitude coordinates in :math:`[0,\pi]`
        - :math:`\phi`, array of azimuth/longitude coordinates in :math:`[0,2\pi]`"""

    if nph is None: nph = nth*2

    if poles:
        t = np.linspace(0, pi, nth)[1:-1]
        p = np.linspace(0, 2*pi - 2*pi/nph, nph)
        p, t = np.meshgrid(p, t)
        p, t = p.flatten(), t.flatten()
        p = np.append(p, [0, 0])
        t = np.append(t, [0, pi])
    else:
        t = np.linspace(pi/(2*nth), pi - pi/(2*nth), nth)
        p = np.linspace(pi/nph, 2*pi - pi/nph, nph)
        p, t = np.meshgrid(p, t)
        p, t = p.flatten(), t.flatten()

    return(t, p)

def grid_fibonacci(n):
    r"""Arranges :math:`n` or :math:`n+1` points (must be an odd number) in a Fibonacci lattice/grid over the surface of a sphere. The grid achieves nearly uniform spacing over the sphere and is remarkably easy to calculate, making it an attractive option. For details and explanation, see
        * Gonzalez, Alvaro. "Measurement of areas on a sphere using Fibonacci and latitude-longitude lattices." Mathematical Geosciences 42.1 (2010): 49.

    :param int n: desired number of points (output might have one extra point)

    :return: tuple containing

        - :math:`\theta`, array of colatitude coordinates in :math:`[0,\pi]`
        - :math:`\phi`, array of azimuth/longitude coordinates in :math:`[0,2\pi]`"""

    if n % 2 == 0:
        warnings.warn('Fibonacci grids can only have an odd number of points. An extra point was added.')

    #convert the number of points to the order(?) N
    N = int(np.ceil((n - 1)/2))
    n = 2*N + 1
    #indices
    i = np.arange(-N, N+1)
    #golden ratio
    r = (1 + sqrt(5))/2
    #latitude coords
    t = arcsin(2*i/(2*N + 1)) + pi/2
    #longitude coords
    p = np.mod(2*pi*i/r, 2*pi)

    return(t, p)

def _find_el(x, y, z):
    """From the cartesian coordinates of vertices on a spherical surface,
    use a Delaunay triangulation to group vertices into elements
    args:
        x, y, z - cartesian coords of vertices
    returns:
        el - list of length 3 index arrays indicating vertices of each el"""

    try:
        tri = SphericalVoronoi(np.stack((x, y, z)).T)._tri
    except MemoryError:
        raise MemoryError('There are too many vertices to perform Delaunay triangulation with available memory. You may need to use a bigger computer.')
    else:
        el = tri.simplices.astype(np.uint32)
        return(el)

def _subdivide_elements(t, p, el):
    """Subdivide each triangular element in the mesh into four new triangles
    args:
        t - polar coordinates of vertices in :math:`[0,\pi]`
        p - azimuthal coordinates of vertices in :math:`[0,2\pi]`
        el - list of element index arrays
    returns:
        t - polar coordinates of vertices in :math:`[0,\pi]`
        p - azimuthal coordinates of vertices in :math:`[0,2\pi]`
        el - list of element index arrays"""

    #convert to cartesian points
    pts = [array(p) for p in zip(*sph2cart(1.0, t, p))]
    #compute midpoints
    ma = set([tuple((pts[e[0]] + pts[e[1]])/2.0) for e in el])
    mb = set([tuple((pts[e[1]] + pts[e[2]])/2.0) for e in el])
    mc = set([tuple((pts[e[2]] + pts[e[0]])/2.0) for e in el])
    #take only uniques
    m = ma | mb | mc
    #add to original list
    pts += list(m)
    #convert back to spherical to set all radii to 1
    x, y, z = zip(*pts)
    _, t, p = cart2sph(array(x), array(y), array(z))
    #compute new element and neighbor lists
    el = _find_el(*sph2cart(1.0, t, p))

    return(t, p, el)

def _icosahedron_base(R=1):
    """Generate the triangles forming an icosahedron, returned in cartesian
    or spherical coordinates
    optional args:
        R - radius of sphere to put vertices on
    returns:
        x - x coordinates of icosahedron vertices
        y - y coordinates of icosahedron vertices
        z - z coordinates of icosahedron vertices
        el - list of triangular element indices"""

    #golden ratio
    PHI = (1.0 + sqrt(5.0))/2.0

    #icosahedron vertices (12 of them)
    i, j, k = zip(*product([-1, 1], [-PHI, PHI], [0]))
    pts = list(zip(i,j,k)) + list(zip(j,k,i)) + list(zip(k,i,j))
    x, y, z = zip(*pts)
    x, y, z = array(x), array(y), array(z)

    #assemble edges (30 of them)
    D = zeros((12,12))
    for i in range(12):
        for j in range(i+1,12):
            D[i,j] = sqrt((x[i] - x[j])**2 + (y[i] - y[j])**2 + (z[i] - z[j])**2)
    edg = [array(i, dtype=int_) for i in zip(*np.nonzero(isclose(D,2)))]

    #assemble elements (20 of them)
    el = set()
    for i in range(30):
        for j in range(i+1,30):
            for k in range(j+1,30):
                s = set(edg[i]) | set(edg[j]) | set(edg[k])
                if len(s) == 3:
                    el.add(tuple(s))
    el = [array(e, dtype=int_) for e in el]

    #normalize vertices for the proper radius
    x *= R/sqrt(1 + PHI**2)
    y *= R/sqrt(1 + PHI**2)
    z *= R/sqrt(1 + PHI**2)

    return(x, y, z, el)

def grid_icosahedral(nsub):
    r"""Generates an icosahedral grid with a given number of subdivisions

    :param int nsub: number of times to subdivide the initial 20 faces of the icosahedron. The number of cells increases rapidly with more subdivisions and is :math:`20(4^{\textrm{nsub}})`
    :return: tuple containing

        - :math:`\theta`, array of colatitude coordinates in :math:`[0,\pi]`
        - :math:`\phi`, array of azimuth/longitude coordinates in :math:`[0,2\pi]`"""

    #check input
    assert type(nsub) is int, "nsub must be an integer"
    assert nsub >= 0, "nsub must be >= 0"

    #string version of the number of subdivisions
    n = str(nsub)

    print('creating icosahedral mesh')
    #generate the initial 12 icosahedron vertices and element index arrays
    x, y, z, el = _icosahedron_base()
    #convert the points to spherical coordinates
    _, t, p = cart2sph(x, y, z)
    #subdivide the elements as many times as called for
    for i in range(nsub):
        t, p, el = _subdivide_elements(t, p, el)
        print('  subdivision %d finished, %d elements' % (i+1, len(el)))
    print('icosahedral mesh finished')

    return(t, p)

#-------------------------------------------------------------------------------
# functions for spectra

def spectrum(a, yn, ym):
    """Computes the power spectrum of a spherical harmonic expansion, the total power per degree. Because the harmonics are orthonormal, each function's coefficient is simply squared to compute its power. The squared coefficients of all orders within a degree are averaged.

    :param array a: spherical harmonic expansion coefficients
    :param array yn: the degrees of the functions in the expansion
    :param array ym: the orders of the functions in the expansion

    :return: tuple containing

        - array of sorted array of degrees for each power
        - array of power for each degree represented in yn"""

    assert len(a) == len(yn) == len(ym), 'a, yn, and ym must be the same length'

    #sorted array of degrees present in expansion
    ns = array(list(set(yn)))
    ns.sort()
    l = len(ns)
    #power for each degree
    ps = zeros((l,))
    for i,n in enumerate(ns):
        #get all the coefficients of degree n
        sl = a[yn == n]
        #average their squared values
        if len(sl) > 0:
            ps[i] = (sl**2).sum()/len(sl)

    return(ns, ps)

def noise(N, p, tol=1e-12):
    """Generates the coefficients for a random triangular spherical harmonic expansion with a specific relationship between the degree and the power spectral density (noise)

    :param int N: maximum degree in expansion
    :param p: exponent of power spectral density relationship with degree, so that the power in each degree :math:`n` is proportional to :math:`n^p`. The following colors, input as strings, will work

        * 'red':    p = -2
        * 'pink':   p = -1
        * 'white':  p = 0
        * 'blue':   p = 1
        * 'violet': p = 2
    :param float tol: bisection method relative tolerance when normalizing across a single degree's coefficients for the total power

    :return: :class:`Expansion` object with expansion coefficients for noise"""

    #convert noise keywords into exponents if needed
    if   p == 'red':    p = -2
    elif p == 'pink':   p = -1
    elif p == 'white':  p =  0
    elif p == 'blue':   p =  1
    elif p == 'violet': p =  2
    else:
        assert isnum(p), 'p must be a number or a keyword'
    #get triangular degree and order arrays
    yn, ym = Tnm(N)
    #find expansion coefficients
    a = zeros((len(yn),))
    for n in set(yn[yn != 0]): #must ignore the zeroth degree (DC component)
        #power density
        d = float(n)**float(p)
        #terms/functions of degree n
        sl = (yn == n)
        L = sum(sl)
        #random uniform distribution across the terms of degree n
        r = 2.0*np.random.rand(L) - 1.0
        #find a factor f where sum(f*r**2) = d, using the bisection method
        flo = 0.0
        dlo = 0.0
        fhi = 1.0
        dhi = (fhi*r*r).sum()/L
        while dhi <= d:
            fhi *= 2
            dhi = (fhi*r*r).sum()/L
        fmi = fhi/2.0
        dmi = (fmi*r*r).sum()/L
        while abs(dmi - d)/abs(d) > tol:
            if dmi > d:
                fhi = fmi
            else:
                flo = fmi
            fmi = fhi/2 + flo/2
            dmi = (fmi*r*r).sum()/L
        #set the expansion coefficients
        a[sl] = sqrt(fmi)*r
    #create an expansion object
    ex = Expansion(a, yn, ym)

    return(ex)

#-------------------------------------------------------------------------------
# functions for spherical harmonic transforms...?


#-------------------------------------------------------------------------------
# classes

class Expansion:
    """Stores the expansion coefficients and degree-order pairs of a spherical harmonic expansion and provides a convenient way to evaluate the expansion and its properties. To evaluate the expansion, simply call the object on arrays of spherical coordinates.

    :param array a: coefficients of spherical harmonic expansion
    :param array yn: degrees of functions in expansion
    :param array ym: orders of functions in expansion"""

    def __init__(self, a, yn, ym):

        #check input
        assert len(a) == len(yn) == len(ym)
        #store the expansion
        self._a = array(a, dtype=float_)
        self._yn = array(yn, dtype=int_)
        self._ym = array(ym, dtype=int_)
        #check for duplicates
        assert len(set(list(zip(self._yn, self._ym)))) == len(self._yn), 'cannot have multiple coefficients for the same degree-order pair'
        #check m <= n
        assert all(abs(ym) <= yn), 'no ym value can be greater than its corresponding yn value'

    @property
    def a(self):
        'Coefficients of expansion'
        return(self._a)

    @property
    def yn(self):
        'Degrees of functions in expansion'
        return(self._yn)

    @property
    def ym(self):
        'Orders of functions in expansion'
        return(self._ym)

    @property
    def spectrum(self):
        'Power density of expansion'
        return( spectrum(*self.unpack) )

    @property
    def unpack(self):
        'Return tuple with `a`, `yn`, `ym`'
        return(self.a, self.yn, self.ym)

    def __call__(self, theta, phi):
        """Evaluates the expansion at (theta,phi) point(s)
        args:
            theta - colatitude in :math:`[0,\pi]`
            phi - longitude in :math:`[0,2\pi]`"""

        return( sph_har_sum(theta, phi, *self.unpack) )

    def __mul__(self, val):
        #create a copy
        r = Expansion(*self.unpack)
        #modify the coefficients
        r._a *= val
        return(r)

    def __truediv__(self, val):
        #create a copy
        r = Expansion(*self.unpack)
        #modify the coefficients
        r._a /= val
        return(r)
