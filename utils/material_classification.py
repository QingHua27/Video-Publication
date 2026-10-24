"""Non-destructive episode folders inferred from material display filenames."""
import re
import unicodedata
from pathlib import PurePath

DIGITS = dict(zip('零〇一二两三四五六七八九', (0,0,1,2,2,3,4,5,6,7,8,9)))
UNITS = {'十':10,'百':100,'千':1000,'万':10000}

def episode_number(text):
    if text.isdecimal():
        return int(text)
    if all(char in DIGITS for char in text):
        return int(''.join(str(DIGITS[char]) for char in text))
    total=section=number=0
    for char in text:
        if char in DIGITS:
            number=DIGITS[char]
        elif char=='万':
            total+=(section+number)*10000;section=number=0
        elif char in UNITS:
            section+=(number or 1)*UNITS[char];number=0
        else:
            return None
    return total+section+number

def episode_label(number,suffix='集'):
    if number>=10000:
        return f'第{number}{suffix}'
    result='';zero=False
    for divisor,unit in [(1000,'千'),(100,'百'),(10,'十'),(1,'')]:
        digit=number//divisor%10
        if digit:
            if zero:result+='零'
            result+='零一二三四五六七八九'[digit]+unit;zero=False
        elif result:zero=True
    if result.startswith('一十'):result=result[1:]
    return f'第{result}{suffix}'

def classify_material(filename):
    name=unicodedata.normalize('NFKC',str(filename or ''))
    match=re.search(r'第\s*([0-9零〇一二两三四五六七八九十百千万]+)\s*([集话期章])',name)
    unit='章' if match and match.group(2)=='章' else '集'
    if not match:
        match=re.search(r'(?:^|[\s_.\-])EP?\s*0*([0-9]+)(?![0-9A-Za-z]|\.[0-9])',name,re.I)
    number=episode_number(match.group(1)) if match else None
    if number is not None and not 1<=number<=99999:number=None
    ext=PurePath(name).suffix.lower()
    role='other'
    if ext in ('.mp4','.mov','.avi','.mkv','.webm','.m4v','.flv','.wmv'):
        role='video'
    elif ext in ('.png','.jpg','.jpeg','.webp','.bmp','.gif'):
        role='image'
        if re.search(r'4\s*[:：xX×比_\-]\s*3|推荐页',name,re.I):role='recommendation_cover'
        elif re.search(r'横[版板]|landscape|16\s*[:：xX×比_\-]\s*9',name,re.I):role='landscape_cover'
        elif re.search(r'竖[版板]|portrait|3\s*[:：xX×比_\-]\s*4',name,re.I):role='portrait_cover'
    return {'episode_number':number,'episode_unit':unit,'folder_name':episode_label(number,unit) if number else '未分类','material_role':role}
