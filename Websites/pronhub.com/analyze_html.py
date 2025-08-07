#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析HTML结构
"""

from bs4 import BeautifulSoup

def analyze_html_structure():
    """分析HTML结构"""
    print("详细分析HTML结构...")
    
    # 基于您提供的HTML示例
    sample_html = '''
    <li class="pcVideoListItem js-pop videoblock videoBox  withKebabMenu" id="v471628125" data-video-id="471628125" data-video-vkey="6870540048f36">
        <div class="wrap flexibleHeight ">
            <div class="phimage">
                <a href="/view_video.php?viewkey=6870540048f36" class="fade videoPreviewBg linkVideoThumb js-linkVideoThumb img fadeUp">
                    <img src="https://pix-cdn77.phncdn.com/c6251/videos/202507/11/15304375/original/0197f910-745a-7af7-b940-7502b735b0ac.png/plain/rs:fit:320:180?hash=DrJWlekHOr1L-5rFP_yKr2DSrN8=&amp;validto=4891363200" alt="I had to take the gag out of her mouth to insert my cock deeper into her throat." data-mediabook="https://ew.phncdn.com/c6251/videos/202507/11/15304375/180P_225K_15304375.webm?validfrom=1754498924&amp;validto=1754506124&amp;rate=56k&amp;burst=150k&amp;ipa=1&amp;hash=zoLEgdiUkfS9akeDnQ2bBNmR3Hs%3D" class="js-pop js-videoThumb thumb js-videoPreview">
                    <div class="marker-overlays js-noFade">
                        <var class="duration">10:12</var>
                    </div>
                </a>
            </div>
            <div class="thumbnail-info-wrapper clearfix">
                <div class="thumbnail-info">
                    <span class="title">
                        <a href="/view_video.php?viewkey=6870540048f36" class="gtm-event-thumb-click">
                            I had to take the gag out of her mouth to insert my cock deeper into her throat.
                        </a>
                    </span>
                    <div class="videoUploaderBlock clearfix">
                        <div class="usernameWrap">
                            <span class="usernameBadgesWrapper">
                                <a rel="" href="/model/body-lyric" title="Body-Lyric" class="">Body-Lyric</a>
                            </span>
                        </div>
                    </div>
                    <div class="videoDetailsBlock">
                        <div>
                            <span class="views"><var>89.7K</var> 次观看</span>
                        </div>
                        <var class="added">55年前</var>
                    </div>
                </div>
            </div>
        </div>
    </li>
    '''
    
    soup = BeautifulSoup(sample_html, 'html.parser')
    li_element = soup.find('li')
    
    print("=== 分析示例HTML结构 ===")
    
    # 1. 基本信息
    video_id = li_element.get('data-video-id', '')
    viewkey = li_element.get('data-video-vkey', '')
    print(f"视频ID: {video_id}")
    print(f"ViewKey: {viewkey}")
    
    # 2. 查找img元素
    img_element = li_element.find('img', class_='js-videoThumb')
    if img_element:
        print("\n=== img元素分析 ===")
        print(f"class: {img_element.get('class', [])}")
        print(f"src: {img_element.get('src', '')[:100]}...")
        print(f"alt: {img_element.get('alt', '')[:100]}...")
        
        # 所有data属性
        data_attrs = {k: v for k, v in img_element.attrs.items() if k.startswith('data-')}
        print("\ndata属性:")
        for attr, value in data_attrs.items():
            print(f"  {attr}: {value[:100]}...")
    
    # 3. 查找上传者信息
    print("\n=== 上传者信息分析 ===")
    uploader_elements = li_element.find_all(['a', 'span'], class_=lambda x: x and ('username' in x.lower() or 'model' in x.lower()))
    for elem in uploader_elements:
        print(f"  {elem.name}.{elem.get('class', [])}: {elem.get_text(strip=True)}")
    
    # 4. 查找观看次数和时间
    print("\n=== 统计信息分析 ===")
    views_element = li_element.find('span', class_='views')
    if views_element:
        print(f"观看次数: {views_element.get_text(strip=True)}")
    
    added_element = li_element.find('var', class_='added')
    if added_element:
        print(f"上传时间: {added_element.get_text(strip=True)}")
    
    duration_element = li_element.find('var', class_='duration')
    if duration_element:
        print(f"时长: {duration_element.get_text(strip=True)}")

if __name__ == "__main__":
    analyze_html_structure() 