import unittest
import numpy as np
from pipeline.terrain.ground_support import interpolate_ground, observed_grid, check_surface_residual


class GroundSupportTests(unittest.TestCase):
    def test_plane_hole_is_order_independent(self):
        points=np.array([[0,0],[0,2],[2,0],[2,2],[1,0],[1,2]],float)
        heights=10+points[:,0]*2-points[:,1]*.5
        query=np.array([[1,1],[.5,.5]])
        a,_=interpolate_ground(points,heights,query)
        b,_=interpolate_ground(points[::-1],heights[::-1],query)
        np.testing.assert_allclose(a,[11.5,10.75])
        np.testing.assert_array_equal(a,b)

    def test_cannot_propagate_across_unobserved_void_or_extrapolate(self):
        points=np.array([[0,0],[0,20],[20,0],[20,20]],float)
        result,qa=interpolate_ground(points,[0,0,20,20],[[10,10],[21,1],[1,1]],max_triangle_edge_m=10)
        self.assertTrue(np.isnan(result).all())
        self.assertFalse(qa['supported'].any())

    def test_bins_preserve_observations_and_missingness(self):
        a=observed_grid([[0,0],[0,0],[2,2]],[5,7,8],(3,3),0,0,1)
        self.assertEqual(a[0,0],6)
        self.assertEqual(a[2,2],8)
        self.assertTrue(np.isnan(a[1,1]))

    def test_unsupported_fin_blocks_promotion(self):
        with self.assertRaisesRegex(ValueError,'residual'):
            check_surface_residual(np.array([56.8,62.6]),np.array([56.8,56.9]),np.array([True,True]))
        with self.assertRaisesRegex(ValueError,'missing'):
            check_surface_residual(np.array([56.8]),np.array([np.nan]),np.array([True]))
        self.assertLess(check_surface_residual(np.array([56.8]),np.array([56.9]),np.array([True]))['max_abs_residual_m'],.2)


if __name__=='__main__':unittest.main()
