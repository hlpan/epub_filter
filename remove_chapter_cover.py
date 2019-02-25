import os
from lxml import etree
path='jpm/EPUB/text'
#os.makedirs(os.path.join(path, "new"))
files= os.listdir(path) #得到文件夹下的所有文件名称
names = []
#章节封面：章节
cover_chapter={}
for file in files: #遍历文件夹
    if os.path.splitext(file)[1]=='.html': #判断是否是文件夹，不是文件夹才打开
        #build_text_list = etree.XPath("//text()")
        names.append(file)
       
print(names)

for i in range(len(names)):
    #只处理带有“split”的文件和它的下一个文件
    if 'split' in names[i]:
        cover_chapter[names[i]]=names[i+1]

for cover, chapter in cover_chapter.items():
    #解析文件
    cover_root=etree.parse(os.path.join(path, cover))
    chapter_root=etree.parse(os.path.join(path, chapter))

    chapter_tile=cover_root.xpath('//*[local-name()="h2"]')[0]  
    chapter_body=chapter_root.xpath('//*[local-name()="body"]')[0] 
    
    chapter_body.insert(0, chapter_tile)
    os.remove(os.path.join(path,cover)) 
    with open(os.path.join(path,chapter),'wb+') as new_chapter_file:
            new_chapter_file.write(etree.tostring(chapter_root, encoding='utf-8'))