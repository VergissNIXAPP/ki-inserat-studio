import unittest
from app_utils import normalize_analysis, question_list, is_access_block
class Tests(unittest.TestCase):
 def test_questions(self):
  self.assertEqual(question_list(None),[])
  self.assertEqual(question_list('Test?'),['Test?'])
  self.assertEqual(question_list(['A','B']),['A','B'])
  self.assertEqual(question_list({'frage':'A'}),['{"frage": "A"}'])
 def test_price(self):
  base={'title':'Titel','description':'Text'}
  self.assertEqual(normalize_analysis({**base,'price_eur':'12,50'})['price_eur'],12.5)
  for p in (float('nan'),float('inf'),True,-10,'keine Angabe'):
   self.assertIsNone(normalize_analysis({**base,'price_eur':p})['price_eur'])
 def test_shape(self):
  for value in ([],{}, {'title':[], 'description':'x'}):
   with self.assertRaises(ValueError):normalize_analysis(value)
 def test_blocks(self):
  self.assertTrue(is_access_block('IP-Bereich vorübergehend gesperrt.'))
  self.assertTrue(is_access_block('Verify you are human'))
  self.assertFalse(is_access_block('Willkommen bei Kleinanzeigen'))
if __name__=='__main__':unittest.main()
