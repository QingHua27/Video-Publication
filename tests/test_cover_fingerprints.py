import unittest,tempfile
from pathlib import Path
from PIL import Image,PngImagePlugin
from utils.local_materials import image_content_hash
class CoverFingerprintTests(unittest.TestCase):
 def test_pixels_equal_despite_metadata_and_compression(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a.png';b=Path(tmp)/'b.png';image=Image.new('RGB',(160,90),'red');image.save(a,compress_level=0)
   meta=PngImagePlugin.PngInfo();meta.add_text('note','different metadata');image.save(b,pnginfo=meta,compress_level=9)
   def fingerprint(p):st=p.stat();return image_content_hash(str(p),st.st_mtime_ns,st.st_size)
   self.assertTrue(fingerprint(a));self.assertEqual(fingerprint(a),fingerprint(b))
   image.putpixel((0,0),(0,0,0));image.save(b);self.assertNotEqual(fingerprint(a),fingerprint(b))
 def test_invalid_image_never_compares_equal(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'bad.png';p.write_bytes(b'bad');st=p.stat();self.assertEqual(image_content_hash(str(p),st.st_mtime_ns,st.st_size),'')
