import math
import unittest
from pipeline.microblocks.facade_canvas import FacadeCanvas

class FacadeStrokeTests(unittest.TestCase):
    def test_axis_width_is_total_not_radius(self):
        c=FacadeCanvas(64,64)
        c.stroke_uy(0,2,8,20,56,20,2,'frame')
        self.assertEqual({y for d,y,u in c.cells},{19,20})
        self.assertEqual(len(c.cells),48*2*2)

    def test_normal_width_is_angle_independent(self):
        for end in [(54,20),(54,54),(20,54),(54,37)]:
            c=FacadeCanvas(64,64)
            cells=c.stroke_uy(0,1,10,10,*end,2,'frame')
            self.assertTrue(cells)
            du,dy=end[0]-10,end[1]-10
            for d,y,u in cells:
                distance=abs((u+.5-10)*dy-(y+.5-10)*du)/math.hypot(du,dy)
                self.assertLess(distance,1)

    def test_opening_guard_survives_late_trim(self):
        c=FacadeCanvas(64,64)
        cells=c.stroke_uy(0,3,0,0,64,64,2,'frame',exclude=[(20,44,20,44)])
        self.assertTrue(cells)
        self.assertFalse(any(20<=u+.5<44 and 20<=y+.5<44 for d,y,u in cells))

    def test_clip_prevents_panel_escape(self):
        c=FacadeCanvas(64,64)
        cells=c.stroke_uy(0,2,0,32,64,32,2,'frame',clip=(16,48,20,40))
        self.assertEqual({u for d,y,u in cells},set(range(16,48)))

    def test_reversed_endpoints_same_result(self):
        a=FacadeCanvas(64,64); b=FacadeCanvas(64,64)
        a.stroke_uy(0,2,10,13,54,43,2,'frame')
        b.stroke_uy(0,2,54,43,10,13,2,'frame')
        self.assertEqual(a.cells,b.cells)

    def test_reject_bad_width(self):
        for width in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                FacadeCanvas(16,16).stroke_uy(0,1,0,0,15,15,width,'frame')

    def test_no_host_boundary_break(self):
        c=FacadeCanvas(64,64)
        c.stroke_uy(0,2,2,20,62,20,2,'frame')
        for u in (15,16,31,32,47,48):
            self.assertIn((0,19,u),c.cells)

    def test_zero_length_is_empty(self):
        c=FacadeCanvas(32,32)
        self.assertEqual(c.stroke_uy(0,2,10,10,10,10,2,'frame'),set())

if __name__=='__main__': unittest.main()
