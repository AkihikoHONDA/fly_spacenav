import numpy as np
from flyrendezvous.viewer import colors, lattice_xy

def test_color_scale_is_fixed_and_signed():
    x=np.array([-1.,0.,1.])
    c=colors(x,1)
    np.testing.assert_array_equal(c,[[40,95,210],[230,230,230],[210,45,45]])
    np.testing.assert_array_equal(colors(np.array([0.,100.]),1)[0],c[1])
    np.testing.assert_array_equal(colors(np.array([-2.,2.]),1),c[[0,2]])

def test_lattice_coordinates_are_not_image_pixels():
    np.testing.assert_allclose(lattice_xy(np.array([0,1]),np.array([0,0])),[[0,0],[0,np.sqrt(3)]])
