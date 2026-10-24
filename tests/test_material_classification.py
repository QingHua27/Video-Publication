import unittest
from utils.material_classification import classify_material

class ClassificationTests(unittest.TestCase):
    def test_episode_and_cover_variants_share_one_folder(self):
        for name in ['第一集.mp4','第1集封面横板.png','第01集封面竖版.png','EP01.mp4','第一集_自然淡彩雨润版.mp4']:
            result=classify_material(name)
            self.assertEqual(result['episode_number'],1,name)
            self.assertEqual(result['folder_name'],'第一集',name)

    def test_chinese_episode_numbers_sort_numerically(self):
        for name,n in [('第十集.mp4',10),('第十二集封面横版.png',12),('第二十一集.mp4',21),('第一百零二集.mp4',102)]:
            self.assertEqual(classify_material(name)['episode_number'],n)

    def test_unknown_files_are_not_guessed(self):
        for name in ['合集封面.png','README.md','剧集清单.csv','2026年度视频.mp4','EP01.5.mp4','E1080p封面.png']:
            self.assertEqual(classify_material(name)['folder_name'],'未分类')

    def test_cover_roles_and_video_versions(self):
        self.assertEqual(classify_material('第四集封面横板.png')['material_role'],'landscape_cover')
        self.assertEqual(classify_material('第四集封面竖版.png')['material_role'],'portrait_cover')
        self.assertEqual(classify_material('第四集_手机版预览.mp4')['material_role'],'video')

    def test_chapter_names_and_three_cover_roles(self):
        names=['外婆的道歉信_第一章烟草_1080x1920.mp4','外婆的道歉信片头_第一章烟草_v1.mp4','片头定帧_第一章烟草_v1.png','外婆的道歉信_第1章_封面_16比9.png','外婆的道歉信_第一章烟草_封面_3比4.png','外婆的道歉信_第一章烟草_封面_4比3.png']
        for name in names:
            result=classify_material(name)
            self.assertEqual((result['episode_number'],result['folder_name']),(1,'第一章'),name)
        self.assertEqual(classify_material(names[3])['material_role'],'landscape_cover')
        self.assertEqual(classify_material(names[4])['material_role'],'portrait_cover')
        self.assertEqual(classify_material(names[5])['material_role'],'recommendation_cover')
        self.assertEqual(classify_material('第十二章_猴子.mp4')['folder_name'],'第十二章')

if __name__=='__main__':unittest.main()
