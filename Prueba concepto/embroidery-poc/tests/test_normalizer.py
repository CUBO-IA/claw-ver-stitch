import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('embroidery_poc', Path(__file__).parents[1] / 'embroidery_poc.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class NormalizerTests(unittest.TestCase):
    def test_mm(self):
        self.assertAlmostEqual(mod.mm_number('6cm'), 60)
        self.assertAlmostEqual(mod.mm_number('96px'), 25.4)

    def test_60mm_limit_and_black(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.svg', Path(tmp) / 'b.svg'
            a.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80"><path d="M0,0 L120,80" style="stroke:red;fill:none"/></svg>')
            result = mod.normalize_svg(a,b, '#000000', 2)
            self.assertEqual(result['page_width_mm'], 56)
            self.assertLess(result['page_height_mm'], 56)
            self.assertIn('stroke:#000000', b.read_text())
            self.assertIn('fill:none', b.read_text())

    def test_reject_gradient(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.svg', Path(tmp) / 'b.svg'
            a.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M0 0Z" fill="url(#g)" /></svg>')
            with self.assertRaises(mod.POCError):
                mod.normalize_svg(a,b,'#000000',2)

if __name__ == '__main__': unittest.main()
