# coding=utf-8

import sys
#sys.path.insert(0, '../ebooklib')
import ebooklib
from ebooklib import epub
from ebooklib.utils import parse_string, parse_html_string, guess_type, get_pages_for_items
from lxml import etree
import pickle
import pygame.freetype
import re
import getopt
import os

class EpubFilter:

    font_list=['kindle_build_in/STSongMedium.ttf',#kindle支持的
        'big_font/FZSongS(SIP).ttf',#生僻字第一方案
        'big_font/FZSongS.ttf',#生僻字第二方案
        'big_font/SourceHanSerifSC-Medium.otf']#生僻字第三方案 
    def __init__(self, input_book_name, font_charset_name):
        #字体渲染器
        pygame.freetype.init()
        #key:字体名 value渲染器
        self.fonts_render = {}
        for font in EpubFilter.font_list[1:-1]:
            self.fonts_render[font]=pygame.freetype.Font(font, 50)
            self.fonts_render[font].strong=True
            self.fonts_render[font].strength=1/36#default is 1/36 and the "bold" is 1/12
        font = EpubFilter.font_list[-1]
        self.fonts_render[font]=pygame.freetype.Font(font, 50)
        #所有kindle目前支持的字符集合
        #'kindle内置中文字体/STHeitiMedium'
        self.font_charset_map=pickle.load(open(font_charset_name, 'rb'))
        #kindle支持的字符集
        self.kindle_charset=self.font_charset_map[EpubFilter.font_list[0]]

        #生僻字和它对应的图片名
        self.char_image_map={}
        #当前处理的epub
        self.book=epub.read_epub(input_book_name)
        self.font_image_dir='font_image'
        self.new_css_filename='uncommon_word.css'
        self.temp_dirctory = os.path.join(os.path.dirname(input_book_name),'temp')
        if not os.path.exists(self.temp_dirctory):
            os.makedirs(self.temp_dirctory)
    def filter_book(self):
        #先添加一个新的css用于将图片和文字显示为一行
        new_css_string='''
        .image_as_font {
        vertical-align: -0.1em;
        width: 0.9em;
        height: 0.9em;
        margin: 0.05em;
        }
        '''
        #添加css文件
        new_css_item=epub.EpubItem(file_name=self.new_css_filename, media_type='text/css', content=new_css_string)
        self.book.add_item(new_css_item)

        #找到所有的文本文件（text/html）
        htmls = self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        for html in htmls:
            self.filter_chapter(html,new_css_item)

    def filter_chapter(self, html, new_css_item):
        '''每一章都是一个html
        '''
        #给每一个html文件添加css
        rel_css_dir = os.path.relpath('.', os.path.dirname(html.get_name()))
        rel_css_file_name=os.path.join(rel_css_dir, self.new_css_filename)
        html.add_item(epub.EpubItem(file_name=rel_css_file_name, media_type='text/css'))

        rel_image_dir=os.path.relpath(self.font_image_dir, os.path.dirname(html.get_name()))
        #生成html对应的links
        self.init_links_of_html(html)
        #只处理body里面正文处理       
        html_tree = parse_html_string(html.get_body_content())
        root=html_tree.getroottree()
        build_text_list = etree.XPath("//text()")
        text_list=build_text_list(root)
        for text in text_list:
            #找出一段文字中生僻字的位置
            pos_list = self.find_uncommon_words_in_one_text(text)
            self.add_image_tag_for_uncommon_words_in_one_text(text, pos_list,rel_image_dir)
        #将root更新到html的content中，不然的话，不会保存
        ori_root=parse_html_string(html.content)
        #删除旧的body
        body=ori_root.find('body')
        ori_root.remove(body)
        #新的body
        ori_root.append(root.find('body'))
        html.content = etree.tostring(ori_root, pretty_print=True, encoding='utf-8', xml_declaration=True)
   
    
    def init_links_of_html(self, html_item):
        html_tree = parse_html_string(html_item.content)
        for link in html_tree.getroottree().xpath('//*[local-name()="link"]'):
            item=epub.EpubItem(file_name= link.get('href'), media_type='text/css')
            html_item.add_item(item)


    def find_uncommon_words_in_one_text(self, text):
        #找出一段文字中生僻字的位置
        pos_list=[]
        for idx,char in enumerate(text):
            if re.match(r'\s', char):
                continue
            if char not in self.kindle_charset:
                pos_list.append(idx)
                #没有生成图片时才重新生成
                if char not in self.char_image_map:
                    #查找char所在的字体并渲染，big font还是不够大啊
                    for font, render in self.fonts_render.items():
                        if char in self.font_charset_map[font]:
                            (surface, textpos) = render.render(char, (0, 0, 0))
                            b=char.encode("unicode_escape")
                            name = str(b[2:])[2:-1]
                            name+=".png"
                            pygame.image.save(surface, os.path.join(self.temp_dirctory,name))
                            data=open(os.path.join(self.temp_dirctory,name),'rb').read()
                            self.book.add_item(epub.EpubImage(file_name=os.path.join(self.font_image_dir, name),media_type='image/png', content=data))
                            self.char_image_map[char]=name
                            break
        return pos_list
   
    def add_image_tag_for_uncommon_words_in_one_text(self, text, pos_list, rel_image_dir):
        #插入每个生僻字对应的item
        #text当前处理的文本
        #post_list:已经找出的生僻字的位置
        #image_dir:生成的图片相对于当前html所在的目录
        if len(pos_list):
            parent=text.getparent()
            if not text.is_tail:
                parent.text=text[0:pos_list[0]]
                pos_list.append(len(text))
                for i in range(len(pos_list)-1):
                    item = text.getparent().makeelement("img")
                    the_uncommon_char = text[pos_list[i]]
                    item.set('src', os.path.join(rel_image_dir,self.char_image_map[the_uncommon_char]))
                    item.set('class','image_as_font')
                    #item.text ='|'+text[pos_list[i]]+'|'
                    parent.insert(i, item)
                    item.tail=text[pos_list[i]+1:pos_list[i+1]]
            else:
                pos_list.insert(0,-1)
                for i in range(len(pos_list)-1):
                    item = text.getparent().makeelement("img")
                    the_uncommon_char = text[pos_list[i+1]]
                    item.set('src', os.path.join(rel_image_dir,self.char_image_map[the_uncommon_char]))
                    item.set('class','image_as_font')
                    #item.text ='|'+text[pos_list[i+1]]+'|'
                    parent.addnext(item)
                    #lxml的addnext操作会删除tail，所以需要后设置
                    parent.tail=text[pos_list[i]+1:pos_list[i+1]]
                    parent=item
                parent.tail=text[pos_list[-1]+1:]

    


def main(argv):
    input_book_name = ''
    output_book_name = 'output.epub'
    font_charset_name ='font_char_list'

    try:
        opts, args = getopt.getopt(argv,"hi:o:f:",["ibook=","obook=","font_charset"])
    except getopt.GetoptError:
        print('epub_filter.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('epub_filter.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ibook"):
            input_book_name = arg
        elif opt in ("-o", "--obook"):
            output_book_name = arg
        elif opt in ("-f", "--font_charset"):
            font_charset_name = arg
    if len(input_book_name)==0:
        print('epub_filter.py -i <inputfile> -o <outputfile>')
        sys.exit()

    current_dir = os.path.dirname(__file__)
    input_book_name=os.path.join(current_dir,input_book_name)
    output_book_name=os.path.join(current_dir,output_book_name)
    font_charset_name=os.path.join(current_dir,font_charset_name)

    epub_filer=EpubFilter(input_book_name, font_charset_name)
    epub_filer.filter_book()
    epub.write_epub(output_book_name, epub_filer.book)

if __name__ == '__main__':
    main(sys.argv[1:])