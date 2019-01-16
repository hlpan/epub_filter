#utf-8
#找出字体文件所有支持的字符列表

from lxml import etree
import pickle
import os

font_charset_map={}

#如何kindle不支持的字符，从以下列表[从第2个开始]中选择
#key:字体文件 value:字体在ttx文件对应的cmap_format_
font_list=['kindle_build_in/STSongMedium.ttf',#kindle支持的
'big_font/FZSongS(SIP).ttf',#生僻字第一方案
'big_font/FZSongS.ttf',#生僻字第二方案
'big_font/SourceHanSerifSC-Medium.otf'#生僻字第三方案
]

for font in font_list:
    print(u'正在处理：%s'%(font))
    root=etree.parse(os.path.splitext(font)[0]+'.ttx')
    result=root.xpath('//map[@code]')

    charset=set()
    for elem in result:
        s = elem.get('code')
        if s=='0x29bd3':
            print(s)
        s = s.lstrip('0x')
        if len(s)==0:
            continue
        if len(s)%2==1:
            s='0'+s
        charset.add(chr(int(s, 16)))
        #if len(s)==2:
        #    charset.add(chr(int(s, 16)))
        #else:
        #    b=bytearray(b'\\u0000')
        #    b[2]=ord(s[0])
        #    b[3]=ord(s[1])
        #    b[4]=ord(s[2])
        #    b[5]=ord(s[3])
        #    charset.add(b.decode('unicode_escape'))
    print(len(result))
    print(len(charset))

    font_charset_map[font]=charset
f = open("font_char_list", 'wb')
pickle.dump(font_charset_map, f)
