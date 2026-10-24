import unittest
from utils.publish_collections import validate_collection, bilibili_collection_fields, CollectionSelectionError

class CollectionTests(unittest.TestCase):
    def test_empty_collection_keeps_platform_default(self):
        for platform in range(1, 7):
            self.assertEqual(validate_collection(platform, ''), '')

    def test_bilibili_requires_numeric_season_id(self):
        self.assertEqual(bilibili_collection_fields('123'), {'season_id': 123})
        for value in ('合集名称', '0', '-1', True):
            with self.assertRaises(CollectionSelectionError):
                validate_collection(6, value)

    def test_other_installed_platforms_accept_exact_collection_name(self):
        for platform in (1, 2, 3, 4, 5):
            self.assertEqual(validate_collection(platform, ' 我的合集 '), '我的合集')
        with self.assertRaises(CollectionSelectionError):
            validate_collection(9, '合集')

if __name__ == '__main__':
    unittest.main()
