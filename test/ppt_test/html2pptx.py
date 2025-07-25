#!/usr/bin/env python3
"""
HTML转PPT终极转换器
解决文字丢失、背景丢失、版式丢失等问题
确保HTML与PPT的最大一致性
"""

import io
import os
import re
import math
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from bs4 import BeautifulSoup, Tag, NavigableString
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_VERTICAL_ANCHOR, MSO_AUTO_SIZE, PP_PARAGRAPH_ALIGNMENT
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.shapes.shapetree import SlideShapes
import cssutils

# 禁用cssutils的警告
logging.getLogger('cssutils').setLevel(logging.ERROR)


class ConversionConfig:
    """转换配置类"""

    def __init__(self):
        # 基础参数
        self.SLIDE_WIDTH_INCHES = 13.33  # 1280px
        self.SLIDE_HEIGHT_INCHES = 7.5  # 720px
        self.PX_TO_INCHES = 1 / 96

        # 默认样式
        self.DEFAULT_FONT_SIZE = 18
        self.DEFAULT_FONT_FAMILY = 'Microsoft YaHei'
        self.DEFAULT_LINE_HEIGHT = 1.5
        self.DEFAULT_TEXT_COLOR = '#000000'
        self.DEFAULT_BACKGROUND_COLOR = '#ffffff'

        # 布局参数
        self.DEFAULT_PADDING = 60
        self.ELEMENT_SPACING = 15
        self.MIN_ELEMENT_HEIGHT = 0.3

        # 功能开关
        self.PRESERVE_BACKGROUND = True
        self.PRESERVE_COLORS = True
        self.PRESERVE_FONTS = True
        self.PRESERVE_LAYOUT = True
        self.AUTO_FIT_TEXT = True

        # 调试选项
        self.DEBUG_MODE = False
        self.VERBOSE_LOGGING = False


class CSSProcessor:
    """CSS处理器"""

    def __init__(self, config: ConversionConfig):
        self.config = config

    def parse_css_file(self, css_content: str) -> Dict[str, Dict[str, str]]:
        """解析CSS内容"""
        try:
            # 预处理CSS
            css_content = self._preprocess_css(css_content)

            # 解析CSS
            sheet = cssutils.parseString(css_content)
            styles = {}

            for rule in sheet:
                if rule.type == rule.STYLE_RULE:
                    selector = rule.selectorText
                    properties = {}

                    for prop in rule.style:
                        properties[prop.name] = prop.value

                    if properties:
                        styles[selector] = properties

            return styles
        except Exception as e:
            if self.config.DEBUG_MODE:
                print(f"CSS解析错误: {e}")
            return {}

    def _preprocess_css(self, css_content: str) -> str:
        """预处理CSS，移除不支持的内容"""
        # 移除@规则
        css_content = re.sub(r'@[^{]+{[^}]*}', '', css_content)
        css_content = re.sub(r'@media[^{]*{[^{}]*(?:{[^}]*}[^{}]*)*}', '',
                             css_content)

        # 移除伪元素和伪类
        css_content = re.sub(r'::(before|after)[^}]*}', '', css_content)
        css_content = re.sub(r':hover[^}]*}', '', css_content)
        css_content = re.sub(r':focus[^}]*}', '', css_content)

        # 简化复杂属性
        css_content = re.sub(r'linear-gradient\([^)]+\)', '#f0f0f0',
                             css_content)
        css_content = re.sub(r'radial-gradient\([^)]+\)', '#f0f0f0',
                             css_content)

        # 移除不支持的属性
        unsupported_props = [
            'box-shadow', 'text-shadow', 'transform', 'transition',
            'animation', 'filter', 'backdrop-filter', 'clip-path'
        ]
        for prop in unsupported_props:
            css_content = re.sub(rf'{prop}[^;]*;', '', css_content)

        return css_content

    def compute_element_style(
            self, element: Tag,
            all_styles: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """计算元素的最终样式"""
        computed = {}

        # 1. 通用标签样式
        tag_name = element.name.lower()
        for selector, style in all_styles.items():
            if selector == tag_name:
                computed.update(style)

        # 2. 类样式
        if element.has_attr('class'):
            for class_name in element['class']:
                for selector, style in all_styles.items():
                    if selector == f'.{class_name}':
                        computed.update(style)
                    elif selector == f'{tag_name}.{class_name}':
                        computed.update(style)

        # 3. ID样式
        if element.has_attr('id'):
            id_name = element['id']
            for selector, style in all_styles.items():
                if selector == f'#{id_name}':
                    computed.update(style)

        # 4. 内联样式
        if element.has_attr('style'):
            inline_styles = self._parse_inline_style(element['style'])
            computed.update(inline_styles)

        return computed

    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """解析内联样式"""
        styles = {}
        for rule in style_str.split(';'):
            if ':' in rule:
                prop, value = rule.split(':', 1)
                styles[prop.strip()] = value.strip()
        return styles


class LayoutAnalyzer:
    """布局分析器"""

    def __init__(self, config: ConversionConfig):
        self.config = config

    def analyze_slide_layout(
            self, container: Tag,
            styles: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """分析幻灯片布局"""
        layout_info = {
            'type': 'standard',
            'elements': [],
            'columns': 1,
            'has_title': False,
            'has_subtitle': False,
            'background': None
        }

        # 检测布局类型
        children = [
            child for child in container.children if isinstance(child, Tag)
        ]

        # 检测标题
        for child in children:
            if child.name.lower() in ['h1', 'h2'
                                      ] and not layout_info['has_title']:
                layout_info['has_title'] = True
                if child.name.lower() == 'h2':
                    layout_info['has_subtitle'] = True

        # 检测多栏布局
        flex_containers = [
            child for child in children
            if self._has_flex_display(child, styles)
        ]
        if flex_containers:
            layout_info['type'] = 'multi_column'
            layout_info['columns'] = len(flex_containers)

        # 检测特殊布局
        class_names = container.get('class', [])
        for class_name in class_names:
            if 'title' in class_name.lower():
                layout_info['type'] = 'title_slide'
            elif 'two-column' in class_name.lower():
                layout_info['type'] = 'two_column'
                layout_info['columns'] = 2
            elif 'data' in class_name.lower():
                layout_info['type'] = 'data_slide'

        return layout_info

    def _has_flex_display(self, element: Tag,
                          styles: Dict[str, Dict[str, str]]) -> bool:
        """检测元素是否使用flex布局"""
        element_style = styles.get(f".{' '.join(element.get('class', []))}",
                                   {})
        return element_style.get('display') == 'flex'


class TextProcessor:
    """文本处理器"""

    def __init__(self, config: ConversionConfig):
        self.config = config

    def extract_all_text_elements(
            self, container: Tag,
            styles: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """提取所有可视化文本元素，按HTML结构创建独立文本框"""
        text_elements = []

        def _extract_structured(element: Tag,
                                parent_style: Dict[str, str] = None) -> None:
            """按结构化方式提取元素"""
            tag_name = element.name.lower()
            element_style = self._get_element_style(element, styles)

            # 合并父级样式
            if parent_style:
                merged_style = parent_style.copy()
                merged_style.update(element_style)
                element_style = merged_style

            # 处理块级元素
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                full_text = element.get_text().strip()
                if full_text:
                    text_elements.append({
                        'type': 'heading',
                        'content': full_text,
                        'style': element_style,
                        'tag': tag_name,
                        'element_id': id(element)
                    })

            elif tag_name == 'p':
                full_text = element.get_text().strip()
                if full_text:
                    text_elements.append({
                        'type': 'paragraph',
                        'content': full_text,
                        'style': element_style,
                        'tag': tag_name,
                        'element_id': id(element)
                    })

            elif tag_name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li', recursive=False):
                    li_text = li.get_text().strip()
                    if li_text:
                        li_style = self._get_element_style(li, styles)
                        merged_li_style = element_style.copy()
                        merged_li_style.update(li_style)
                        list_items.append({
                            'content': li_text,
                            'style': merged_li_style
                        })

                if list_items:
                    text_elements.append({
                        'type': 'list',
                        'content': list_items,
                        'style': element_style,
                        'tag': tag_name,
                        'list_type': tag_name,
                        'element_id': id(element)
                    })

            elif tag_name == 'blockquote':
                quote_text = element.get_text().strip()
                if quote_text:
                    text_elements.append({
                        'type': 'quote',
                        'content': quote_text,
                        'style': element_style,
                        'tag': tag_name,
                        'element_id': id(element)
                    })

            elif tag_name == 'pre':
                code_text = element.get_text().strip()
                if code_text:
                    text_elements.append({
                        'type': 'code',
                        'content': code_text,
                        'style': element_style,
                        'tag': tag_name,
                        'element_id': id(element)
                    })

            elif tag_name in ['div', 'section', 'article']:
                # 检查div是否有特殊的类或ID来确定布局角色
                class_list = element.get('class', [])
                element_id = element.get('id', '')

                # 检查是否包含有意义的直接文本内容
                direct_text = self._get_direct_text_content(element)
                has_block_children = any(child.name in [
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol',
                    'blockquote', 'pre', 'div'
                ] for child in element.find_all(recursive=False)
                                         if isinstance(child, Tag))

                if direct_text and not has_block_children:
                    # 如果有直接文本且没有块级子元素，作为文本块处理
                    text_elements.append({
                        'type': 'text_block',
                        'content': direct_text,
                        'style': element_style,
                        'tag': tag_name,
                        'element_id': id(element),
                        'classes': class_list,
                        'id_attr': element_id
                    })
                else:
                    # 递归处理子元素
                    for child in element.children:
                        if isinstance(child, Tag):
                            _extract_structured(child, element_style)

            elif tag_name in ['span', 'strong', 'em', 'b', 'i']:
                # 内联元素通常不单独成框，除非没有父级块元素
                parent_tag = element.parent.name.lower(
                ) if element.parent else ''
                if parent_tag not in [
                        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li',
                        'blockquote'
                ]:
                    full_text = element.get_text().strip()
                    if full_text:
                        text_elements.append({
                            'type': 'inline_text',
                            'content': full_text,
                            'style': element_style,
                            'tag': tag_name,
                            'element_id': id(element)
                        })
            else:
                # 其他元素递归处理
                for child in element.children:
                    if isinstance(child, Tag):
                        _extract_structured(child, element_style)

        # 开始提取
        _extract_structured(container)

        # 按DOM顺序排序（保持HTML中的原始顺序）
        return text_elements

    def _get_direct_text_content(self, element: Tag) -> str:
        """获取元素的直接文本内容（不包括子元素的文本）"""
        texts = []
        for content in element.contents:
            if isinstance(content, NavigableString):
                text = str(content).strip()
                if text:
                    texts.append(text)
        return ' '.join(texts)

    def _set_textbox_background(self, textbox, style: Dict[str, str]) -> None:
        """设置文本框背景色"""
        bg_color = style.get('background-color') or style.get('background')
        if bg_color:
            # 清理复杂背景值
            if 'linear-gradient' in bg_color or 'radial-gradient' in bg_color:
                import re
                hex_colors = re.findall(r'#[0-9a-fA-F]{6}', bg_color)
                if hex_colors:
                    bg_color = hex_colors[0]
                else:
                    bg_color = '#f8f9fa'
            elif 'url(' in bg_color:
                bg_color = '#ffffff'
            elif ' ' in bg_color:
                parts = bg_color.split()
                for part in parts:
                    if part.startswith('#') or part.startswith('rgb'):
                        bg_color = part
                        break
                else:
                    bg_color = None

            color = self._parse_color(bg_color)
            if color:
                fill = textbox.fill
                fill.solid()
                fill.fore_color.rgb = color
                if self.config.DEBUG_MODE:
                    print(f"        设置文本框背景: {bg_color} -> {color}")

    def _set_textbox_border(self, textbox, style: Dict[str, str]) -> None:
        """设置文本框边框"""
        border = style.get('border', '')
        border_color = style.get('border-color', '')
        border_width = style.get('border-width', '0')
        border_style = style.get('border-style', 'solid')

        # 解析复合border属性
        if border and not border_color and not border_width:
            parts = border.split()
            for part in parts:
                if part.endswith('px') or part.endswith('pt'):
                    border_width = part
                elif part in ['solid', 'dashed', 'dotted', 'none']:
                    border_style = part
                elif part.startswith('#') or part.startswith('rgb'):
                    border_color = part

        width_pt = self._parse_length(border_width) if border_width else 0
        if width_pt > 0 and border_style != 'none':
            line = textbox.line
            line.color.rgb = self._parse_color(border_color) or RGBColor(
                200, 200, 200)
            line.width = Pt(width_pt)
            if self.config.DEBUG_MODE:
                print(
                    f"        设置边框: {border_width} {border_style} {border_color}"
                )
        else:
            # 设置为无边框
            textbox.line.fill.background()

    def _set_shape_background(self, shape, style: Dict[str, str]) -> None:
        """设置形状背景色"""
        if not self.config.PRESERVE_BACKGROUND:
            return

        # 获取背景色
        bg_color = style.get('background-color') or style.get('background')

        if bg_color:
            # 清理背景值
            if 'linear-gradient' in bg_color or 'radial-gradient' in bg_color:
                # 从渐变中提取主色调
                if '#' in bg_color:
                    hex_colors = re.findall(r'#[0-9a-fA-F]{6}', bg_color)
                    if hex_colors:
                        bg_color = hex_colors[0]
                    else:
                        bg_color = '#f8f9fa'
                else:
                    bg_color = '#f8f9fa'

            elif 'url(' in bg_color:
                bg_color = '#ffffff'  # 图片背景用白色代替

            # 如果background属性包含多个值，提取颜色部分
            if bg_color and ' ' in bg_color:
                parts = bg_color.split()
                for part in parts:
                    if (part.startswith('#') or part.startswith('rgb')
                            or part in [
                                'white', 'black', 'red', 'green', 'blue',
                                'gray', 'grey'
                            ]):
                        bg_color = part
                        break
                else:
                    bg_color = None

            color = self._parse_color(bg_color)
            if color:
                fill = shape.fill
                fill.solid()
                fill.fore_color.rgb = color

                if self.config.DEBUG_MODE:
                    print(f"        设置文本框背景色: {bg_color} -> {color}")
        else:
            # 没有背景色时设为透明
            shape.fill.background()

    def _set_shape_border(self, shape, style: Dict[str, str]) -> None:
        """设置形状边框"""
        border_style = style.get('border') or style.get('border-style', '')
        border_color = style.get('border-color', '')
        border_width = style.get('border-width', '0')

        # 解析复合border属性 (如: "1px solid #ccc")
        if border_style and not border_color and not border_width:
            parts = border_style.split()
            for part in parts:
                if part.endswith('px') or part.endswith('pt'):
                    border_width = part
                elif part in ['solid', 'dashed', 'dotted', 'none']:
                    border_style = part
                elif part.startswith('#') or part.startswith('rgb'):
                    border_color = part

        # 解析边框宽度
        width_pt = self._parse_length(border_width) if border_width else 0

        if width_pt > 0 and border_style not in ['none', 'hidden']:
            line = shape.line
            line.color.rgb = self._parse_color(border_color) or RGBColor(
                200, 200, 200)
            line.width = Pt(width_pt)

            # 设置边框样式
            if border_style == 'dashed':
                line.dash_style = MSO_LINE_DASH_STYLE.DASH
            elif border_style == 'dotted':
                line.dash_style = MSO_LINE_DASH_STYLE.DOT
            else:
                line.dash_style = MSO_LINE_DASH_STYLE.SOLID

            if self.config.DEBUG_MODE:
                print(
                    f"        设置边框: {border_width} {border_style} {border_color}"
                )
        else:
            # 无边框
            shape.line.fill.background()

    def _get_element_style(
            self, element: Tag,
            styles: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """获取元素样式"""
        computed = {}
        tag_name = element.name.lower()

        # 标签样式
        if tag_name in styles:
            computed.update(styles[tag_name])

        # 类样式
        if element.has_attr('class'):
            for class_name in element['class']:
                selector = f'.{class_name}'
                if selector in styles:
                    computed.update(styles[selector])

                combined_selector = f'{tag_name}.{class_name}'
                if combined_selector in styles:
                    computed.update(styles[combined_selector])

        # ID样式
        if element.has_attr('id'):
            id_selector = f"#{element['id']}"
            if id_selector in styles:
                computed.update(styles[id_selector])

        # 内联样式
        if element.has_attr('style'):
            inline_styles = {}
            for rule in element['style'].split(';'):
                if ':' in rule:
                    prop, value = rule.split(':', 1)
                    inline_styles[prop.strip()] = value.strip()
            computed.update(inline_styles)

        return computed

    def _get_direct_text(self, element: Tag) -> str:
        """获取元素的直接文本内容"""
        texts = []
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    texts.append(text)
        return ' '.join(texts)


class PPTGenerator:
    """PPT生成器"""

    def __init__(self, config: ConversionConfig):
        self.config = config
        self.css_processor = CSSProcessor(config)
        self.layout_analyzer = LayoutAnalyzer(config)
        self.text_processor = TextProcessor(config)

    def px_to_inches(self, px: Union[str, int, float]) -> float:
        """像素转英寸"""
        if isinstance(px, str):
            px = self._parse_length(px)
        return float(px) * self.config.PX_TO_INCHES

    def _parse_length(self, value: str, base_size: float = 16) -> float:
        """解析长度值"""
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return 0

        value = value.strip().lower()
        try:
            if value.endswith('px'):
                return float(value[:-2])
            elif value.endswith('pt'):
                return float(value[:-2]) * 4 / 3
            elif value.endswith('rem'):
                return float(value[:-3]) * base_size
            elif value.endswith('em'):
                return float(value[:-2]) * base_size
            elif value.endswith('%'):
                return float(value[:-1]) / 100 * base_size
            else:
                return float(value)
        except:
            return 0

    def _parse_color(self, color_str: str) -> Optional[RGBColor]:
        """解析颜色"""
        if not color_str:
            return None

        color_str = color_str.strip().lower()

        # 十六进制
        if color_str.startswith('#'):
            hex_color = color_str.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c * 2 for c in hex_color])
            if len(hex_color) == 6:
                try:
                    r, g, b = tuple(
                        int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
                    return RGBColor(r, g, b)
                except:
                    return None

        # RGB
        elif color_str.startswith('rgb'):
            nums = re.findall(r'\d+', color_str)
            if len(nums) >= 3:
                try:
                    return RGBColor(int(nums[0]), int(nums[1]), int(nums[2]))
                except:
                    return None

        # 颜色名扩展映射
        color_map = {
            'black': RGBColor(0, 0, 0),
            'white': RGBColor(255, 255, 255),
            'red': RGBColor(255, 0, 0),
            'green': RGBColor(0, 128, 0),
            'blue': RGBColor(0, 0, 255),
            'gray': RGBColor(128, 128, 128),
            'grey': RGBColor(128, 128, 128),
            'silver': RGBColor(192, 192, 192),
            'maroon': RGBColor(128, 0, 0),
            'yellow': RGBColor(255, 255, 0),
            'lime': RGBColor(0, 255, 0),
            'aqua': RGBColor(0, 255, 255),
            'teal': RGBColor(0, 128, 128),
            'navy': RGBColor(0, 0, 128),
            'fuchsia': RGBColor(255, 0, 255),
            'purple': RGBColor(128, 0, 128),
            'orange': RGBColor(255, 165, 0),
            'pink': RGBColor(255, 192, 203),
            'transparent': None,
            # 常见CSS预设颜色
            '#2c3e50': RGBColor(44, 62, 80),
            '#7f8c8d': RGBColor(127, 140, 141),
            '#34495e': RGBColor(52, 73, 94),
            '#f8f9fa': RGBColor(248, 249, 250),
            '#667eea': RGBColor(102, 126, 234),
            '#764ba2': RGBColor(118, 75, 162),
        }
        return color_map.get(color_str)

    def create_text_shape(self,
                          slide,
                          text: str,
                          style: Dict[str, str],
                          bounds: Tuple[float, float, float, float],
                          tag: str = 'p') -> Any:
        """创建具有完整样式的文本形状"""
        left, top, width, height = bounds

        # 创建文本框
        textbox = slide.shapes.add_textbox(Inches(left), Inches(top),
                                           Inches(width), Inches(height))

        # 设置文本框背景色
        bg_color = style.get('background-color') or style.get('background')
        if bg_color and self.config.PRESERVE_BACKGROUND:
            # 清理复杂背景值
            if 'linear-gradient' in bg_color or 'radial-gradient' in bg_color:
                import re
                hex_colors = re.findall(r'#[0-9a-fA-F]{6}', bg_color)
                if hex_colors:
                    bg_color = hex_colors[0]
                else:
                    bg_color = '#f8f9fa'
            elif 'url(' in bg_color:
                bg_color = '#ffffff'
            elif ' ' in bg_color:
                parts = bg_color.split()
                for part in parts:
                    if part.startswith('#') or part.startswith('rgb'):
                        bg_color = part
                        break
                else:
                    bg_color = None

            if bg_color:
                color = self._parse_color(bg_color)
                if color:
                    fill = textbox.fill
                    fill.solid()
                    fill.fore_color.rgb = color
                    if self.config.DEBUG_MODE:
                        print(f"        设置文本框背景: {bg_color} -> {color}")

        # 设置文本框边框
        border = style.get('border', '')
        if border and self.config.PRESERVE_BACKGROUND:
            # 解析border属性 (如: "1px solid #ccc")
            parts = border.split()
            border_width = '0'
            border_style = 'solid'
            border_color = '#cccccc'

            for part in parts:
                if part.endswith('px') or part.endswith('pt'):
                    border_width = part
                elif part in ['solid', 'dashed', 'dotted', 'none']:
                    border_style = part
                elif part.startswith('#') or part.startswith('rgb'):
                    border_color = part

            width_pt = self._parse_length(border_width) if border_width else 0
            if width_pt > 0 and border_style != 'none':
                line = textbox.line
                line.color.rgb = self._parse_color(border_color) or RGBColor(
                    200, 200, 200)
                line.width = Pt(width_pt)
                if self.config.DEBUG_MODE:
                    print(
                        f"        设置边框: {border_width} {border_style} {border_color}"
                    )
            else:
                # 设置为无边框
                textbox.line.fill.background()

        text_frame = textbox.text_frame
        text_frame.clear()
        text_frame.word_wrap = True
        text_frame.auto_size = MSO_AUTO_SIZE.NONE if not self.config.AUTO_FIT_TEXT else MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT

        # 设置内边距
        margin = self._parse_length(style.get('padding', '4'))
        text_frame.margin_left = Inches(margin / 72)  # 转换为英寸
        text_frame.margin_right = Inches(margin / 72)
        text_frame.margin_top = Inches(margin / 72)
        text_frame.margin_bottom = Inches(margin / 72)

        # 设置垂直对齐
        vertical_align = style.get('vertical-align', 'middle')
        if vertical_align == 'top':
            text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
        elif vertical_align == 'bottom':
            text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.BOTTOM
        else:
            text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

        # 设置段落
        paragraph = text_frame.paragraphs[0]
        paragraph.text = text

        # 文本对齐
        text_align = style.get('text-align', 'left')
        align_map = {
            'left': PP_PARAGRAPH_ALIGNMENT.LEFT,
            'center': PP_PARAGRAPH_ALIGNMENT.CENTER,
            'right': PP_PARAGRAPH_ALIGNMENT.RIGHT,
            'justify': PP_PARAGRAPH_ALIGNMENT.JUSTIFY
        }
        paragraph.alignment = align_map.get(text_align,
                                            PP_PARAGRAPH_ALIGNMENT.LEFT)

        # 字体设置
        run = paragraph.runs[0]

        # 字体大小
        font_size = self._parse_length(
            style.get('font-size', str(self.config.DEFAULT_FONT_SIZE)))
        run.font.size = Pt(font_size)

        # 字体族
        font_family = style.get('font-family', self.config.DEFAULT_FONT_FAMILY)
        if ',' in font_family:
            font_family = font_family.split(',')[0]
        font_family = font_family.strip('\'"')
        run.font.name = font_family

        # 字体颜色
        color = self._parse_color(
            style.get('color', self.config.DEFAULT_TEXT_COLOR))
        if color:
            run.font.color.rgb = color

        # 字体样式
        font_weight = style.get('font-weight', 'normal')
        run.font.bold = font_weight in ['bold', 'bolder', '700', '800', '900']

        font_style = style.get('font-style', 'normal')
        run.font.italic = font_style == 'italic'

        # 行间距
        line_height = style.get('line-height',
                                str(self.config.DEFAULT_LINE_HEIGHT))
        try:
            if line_height.replace('.', '').isdigit():
                paragraph.line_spacing = float(line_height)
        except:
            pass

        return textbox

    def create_list_shape(self,
                          slide,
                          items: List[Dict[str, Any]],
                          style: Dict[str, str],
                          bounds: Tuple[float, float, float, float],
                          list_type: str = 'ul') -> Any:
        """创建列表形状"""
        left, top, width, height = bounds

        textbox = slide.shapes.add_textbox(Inches(left), Inches(top),
                                           Inches(width), Inches(height))

        text_frame = textbox.text_frame
        text_frame.clear()
        text_frame.word_wrap = True
        text_frame.auto_size = MSO_AUTO_SIZE.NONE
        text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP

        for i, item in enumerate(items):
            paragraph = text_frame.add_paragraph(
            ) if i > 0 else text_frame.paragraphs[0]

            # 列表符号
            if list_type == 'ul':
                bullet = '• '
            else:
                bullet = f'{i+1}. '

            paragraph.text = bullet + item['content']

            # 设置样式
            run = paragraph.runs[0]
            item_style = item.get('style', style)

            font_size = self._parse_length(
                item_style.get('font-size',
                               str(self.config.DEFAULT_FONT_SIZE)))
            run.font.size = Pt(font_size)

            font_family = item_style.get('font-family',
                                         self.config.DEFAULT_FONT_FAMILY)
            if ',' in font_family:
                font_family = font_family.split(',')[0]
            run.font.name = font_family.strip('\'"')

            color = self._parse_color(
                item_style.get('color', self.config.DEFAULT_TEXT_COLOR))
            if color:
                run.font.color.rgb = color

            paragraph.space_after = Pt(6)

        return textbox

    def set_slide_background(self, slide, style: Dict[str, str]) -> None:
        """设置幻灯片背景"""
        if not self.config.PRESERVE_BACKGROUND:
            return

        # 优先使用background-color，然后是background
        bg_color = style.get('background-color') or style.get('background')

        if not bg_color:
            bg_color = self.config.DEFAULT_BACKGROUND_COLOR

        # 智能处理复杂背景值
        if 'linear-gradient' in bg_color or 'radial-gradient' in bg_color:
            # 从渐变中提取主色调
            import re
            hex_colors = re.findall(r'#[0-9a-fA-F]{6}', bg_color)
            if hex_colors:
                bg_color = hex_colors[0]  # 使用第一个颜色
            else:
                # 尝试提取rgb颜色
                rgb_match = re.search(
                    r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', bg_color)
                if rgb_match:
                    r, g, b = rgb_match.groups()
                    bg_color = f'rgb({r}, {g}, {b})'
                else:
                    bg_color = '#f8f9fa'  # 默认浅灰色

        elif 'url(' in bg_color:
            bg_color = '#ffffff'  # 图片背景用白色代替

        # 如果background属性包含多个值，智能提取颜色部分
        if bg_color and ' ' in bg_color:
            parts = bg_color.split()
            for part in parts:
                if (part.startswith('#') or part.startswith('rgb') or part in [
                        'white', 'black', 'red', 'green', 'blue', 'gray',
                        'grey', 'lightblue', 'lightgray', 'darkgray',
                        'lightgreen', 'yellow', 'orange', 'purple', 'pink',
                        'brown', 'navy', 'teal'
                ]):
                    bg_color = part
                    break
            else:
                bg_color = '#ffffff'  # 默认白色

        # 解析并应用颜色
        color = self._parse_color(bg_color)
        if color:
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = color
            if self.config.DEBUG_MODE:
                print(f"      设置幻灯片背景色: {bg_color} -> {color}")
        else:
            # 如果无法解析颜色，使用默认白色
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(255, 255, 255)
            if self.config.DEBUG_MODE:
                print(f"      使用默认白色背景")

    def calculate_layout_bounds(
            self, slide_style: Dict[str, str],
            layout_info: Dict[str, Any]) -> Tuple[float, float, float, float]:
        """计算布局边界"""
        # 解析padding
        padding = slide_style.get('padding', str(self.config.DEFAULT_PADDING))
        padding_parts = padding.split()

        if len(padding_parts) == 1:
            p_top = p_right = p_bottom = p_left = self.px_to_inches(
                self._parse_length(padding_parts[0]))
        elif len(padding_parts) == 2:
            p_top = p_bottom = self.px_to_inches(
                self._parse_length(padding_parts[0]))
            p_left = p_right = self.px_to_inches(
                self._parse_length(padding_parts[1]))
        elif len(padding_parts) == 4:
            p_top = self.px_to_inches(self._parse_length(padding_parts[0]))
            p_right = self.px_to_inches(self._parse_length(padding_parts[1]))
            p_bottom = self.px_to_inches(self._parse_length(padding_parts[2]))
            p_left = self.px_to_inches(self._parse_length(padding_parts[3]))
        else:
            p_top = p_right = p_bottom = p_left = self.px_to_inches(
                self.config.DEFAULT_PADDING)

        left = p_left
        top = p_top
        width = self.config.SLIDE_WIDTH_INCHES - p_left - p_right
        height = self.config.SLIDE_HEIGHT_INCHES - p_top - p_bottom

        return (left, top, width, height)

    def convert(self, html_content: str, output_file: str) -> str:
        """主转换方法"""
        if self.config.DEBUG_MODE:
            print("开始HTML转PPT转换...")

        # 解析HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # 解析CSS
        all_styles = {}

        # 内联样式
        for style_tag in soup.find_all('style'):
            css_content = style_tag.string or style_tag.get_text()
            if css_content:
                styles = self.css_processor.parse_css_file(css_content)
                all_styles.update(styles)

        # 外部CSS文件
        for link_tag in soup.find_all('link', rel='stylesheet'):
            href = link_tag.get('href')
            if href and os.path.exists(href):
                try:
                    with open(href, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                        styles = self.css_processor.parse_css_file(css_content)
                        all_styles.update(styles)
                except Exception as e:
                    if self.config.DEBUG_MODE:
                        print(f"加载CSS文件失败 {href}: {e}")

        if self.config.DEBUG_MODE:
            print(f"解析到 {len(all_styles)} 个CSS规则")

        # 找到幻灯片容器
        slide_containers = soup.select('.slide-container')
        if not slide_containers:
            raise ValueError("未找到 .slide-container 元素")

        print(f"找到 {len(slide_containers)} 个幻灯片")

        # 创建PPT
        prs = Presentation()
        prs.slide_width = Inches(self.config.SLIDE_WIDTH_INCHES)
        prs.slide_height = Inches(self.config.SLIDE_HEIGHT_INCHES)

        # 处理每个幻灯片
        for i, container in enumerate(slide_containers):
            if self.config.DEBUG_MODE:
                print(f"\n处理幻灯片 {i+1}/{len(slide_containers)}")

            self._process_slide(prs, container, all_styles, i + 1)

        # 保存PPT
        prs.save(output_file)
        print(f"PPT已保存: {output_file}")

        return output_file

    def _process_slide(self, prs: Presentation, container: Tag,
                       all_styles: Dict[str, Dict[str, str]], slide_num: int):
        """处理单个幻灯片"""
        # 创建幻灯片
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)

        # 获取容器样式
        container_style = self.css_processor.compute_element_style(
            container, all_styles)

        # 设置背景
        self.set_slide_background(slide, container_style)

        # 分析布局
        layout_info = self.layout_analyzer.analyze_slide_layout(
            container, all_styles)

        # 计算内容区域
        content_bounds = self.calculate_layout_bounds(container_style,
                                                      layout_info)

        # 提取所有文本元素
        text_elements = self.text_processor.extract_all_text_elements(
            container, all_styles)

        if self.config.DEBUG_MODE:
            print(f"  - 提取到 {len(text_elements)} 个文本元素")
            print(f"  - 布局类型: {layout_info['type']}")

        # 布局元素
        self._layout_elements(slide, text_elements, content_bounds,
                              layout_info)

    def _layout_elements(self, slide, text_elements: List[Dict[str, Any]],
                         content_bounds: Tuple[float, float, float, float],
                         layout_info: Dict[str, Any]):
        """智能布局元素 - 为每个元素创建独立文本框"""
        content_left, content_top, content_width, content_height = content_bounds

        # 根据布局类型采用不同策略
        layout_type = layout_info.get('type', 'standard')

        if layout_type == 'title_slide':
            self._layout_title_slide(slide, text_elements, content_bounds)
        elif layout_type == 'two_column':
            self._layout_two_column(slide, text_elements, content_bounds)
        elif layout_type == 'multi_column':
            self._layout_multi_column(slide, text_elements, content_bounds)
        else:
            self._layout_standard(slide, text_elements, content_bounds)

    def _layout_standard(self, slide, text_elements: List[Dict[str, Any]],
                         content_bounds: Tuple[float, float, float, float]):
        """标准布局 - 垂直排列，确保元素间距合理"""
        content_left, content_top, content_width, content_height = content_bounds
        current_y = content_top

        for i, element in enumerate(text_elements):
            if self.config.DEBUG_MODE:
                content_preview = str(element['content'])[:50] + "..." if len(
                    str(element['content'])) > 50 else str(element['content'])
                print(
                    f"    [{i+1}] {element['type']}({element.get('tag', 'unknown')}): {content_preview}"
                )

            # 计算元素的精确位置和尺寸
            element_layout = self._calculate_element_layout(
                element, content_bounds, current_y)

            # 确保不超出边界
            if element_layout['top'] + element_layout[
                    'height'] > content_top + content_height:
                remaining_height = content_top + content_height - element_layout[
                    'top']
                if remaining_height < self.config.MIN_ELEMENT_HEIGHT:
                    if self.config.DEBUG_MODE:
                        print(f"      跳过：超出边界")
                    break
                element_layout['height'] = remaining_height

            # 创建独立文本框
            bounds = (element_layout['left'], element_layout['top'],
                      element_layout['width'], element_layout['height'])

            try:
                self._create_element_textbox(slide, element, bounds, i + 1)

                # 更新Y坐标，增加更大的间距避免堆叠
                element_spacing = self._get_enhanced_element_spacing(
                    element['type'], element.get('tag', ''))
                current_y = element_layout['top'] + element_layout[
                    'height'] + element_layout[
                        'margin_bottom'] + element_spacing

            except Exception as e:
                if self.config.DEBUG_MODE:
                    print(f"      错误: {e}")
                    import traceback
                    traceback.print_exc()
                continue

    def _get_enhanced_element_spacing(self, element_type: str,
                                      tag: str) -> float:
        """获取增强的元素间距，避免堆叠"""
        base_spacing = self.px_to_inches(12)  # 基础间距

        # 根据元素类型调整间距
        if element_type == 'heading' or tag in [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]:
            if tag == 'h1':
                return self.px_to_inches(24)  # 大标题后更大间距
            elif tag == 'h2':
                return self.px_to_inches(20)
            else:
                return self.px_to_inches(16)
        elif element_type == 'list':
            return self.px_to_inches(18)  # 列表后稍大间距
        elif element_type == 'code':
            return self.px_to_inches(20)  # 代码块后较大间距
        elif element_type == 'quote':
            return self.px_to_inches(16)  # 引用后中等间距
        elif element_type in ['paragraph', 'text_block']:
            return self.px_to_inches(14)  # 段落间中等间距
        else:
            return base_spacing

    def _calculate_element_layout(self, element: Dict[str, Any],
                                  content_bounds: Tuple[float, float, float,
                                                        float],
                                  current_y: float) -> Dict[str, float]:
        """精确计算元素布局"""
        content_left, content_top, content_width, content_height = content_bounds
        style = element.get('style', {})
        element_type = element.get('type', 'text')
        tag = element.get('tag', 'div')

        # 解析margin - 更精确的处理
        margin_top = self._parse_css_spacing(style.get('margin-top', '0'))
        margin_bottom = self._parse_css_spacing(style.get(
            'margin-bottom', '0'))
        margin_left = self._parse_css_spacing(style.get('margin-left', '0'))
        margin_right = self._parse_css_spacing(style.get('margin-right', '0'))

        # 如果有margin属性，解析它
        if 'margin' in style and not any(
            [margin_top, margin_bottom, margin_left, margin_right]):
            margin_values = self._parse_margin_shorthand(style['margin'])
            margin_top = margin_values['top']
            margin_bottom = margin_values['bottom']
            margin_left = margin_values['left']
            margin_right = margin_values['right']

        # 解析padding
        padding = self._parse_css_spacing(style.get('padding', '4'))

        # 计算基础高度
        base_height = self._calculate_element_height(element)

        # 根据元素类型和样式精确计算宽度和位置
        available_width = content_width - margin_left - margin_right
        element_left = content_left + margin_left

        # 根据元素类型进行特殊调整
        if element_type == 'heading' or tag in [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]:
            # 标题元素占全宽
            element_width = available_width

        elif element_type == 'list':
            # 列表元素增加缩进
            list_indent = self.px_to_inches(24)
            element_width = available_width - list_indent
            element_left += list_indent

        elif element_type == 'code':
            # 代码块通常有背景，需要一些边距
            code_margin = self.px_to_inches(8)
            element_width = available_width - code_margin * 2
            element_left += code_margin

        elif element_type == 'quote':
            # 引用通常有左右缩进
            quote_indent = self.px_to_inches(32)
            element_width = available_width - quote_indent * 2
            element_left += quote_indent

        elif element_type in ['paragraph', 'text_block']:
            # 段落和文本块
            element_width = available_width

            # 根据text-align调整
            text_align = style.get('text-align', 'left')
            if text_align == 'center':
                # 居中文本可以稍微缩进
                center_margin = self.px_to_inches(16)
                element_width = available_width - center_margin * 2
                element_left += center_margin
            elif text_align == 'right':
                # 右对齐文本
                right_margin = self.px_to_inches(16)
                element_width = available_width - right_margin

        else:
            # 其他元素
            element_width = available_width

        # 确保最小宽度
        min_width = self.px_to_inches(100)
        element_width = max(element_width, min_width)

        # 确保不超出边界
        if element_left + element_width > content_left + content_width:
            element_width = content_left + content_width - element_left

        return {
            'left': element_left,
            'top': current_y + margin_top,
            'width': element_width,
            'height': base_height,
            'margin_bottom': margin_bottom,
            'padding': padding
        }

    def _parse_css_spacing(self, value: str) -> float:
        """解析CSS间距值（margin, padding等）"""
        if not value or value == '0':
            return 0.0

        # 处理多个值的情况 (如: "10px 20px")
        parts = value.split()
        if parts:
            first_value = parts[0]
            return self.px_to_inches(self._parse_length(first_value))
        return 0.0

    def _parse_margin_shorthand(self, margin: str) -> Dict[str, float]:
        """解析margin简写属性"""
        parts = margin.split()
        if len(parts) == 1:
            # margin: 10px
            value = self._parse_css_spacing(parts[0])
            return {
                'top': value,
                'right': value,
                'bottom': value,
                'left': value
            }
        elif len(parts) == 2:
            # margin: 10px 20px
            vertical = self._parse_css_spacing(parts[0])
            horizontal = self._parse_css_spacing(parts[1])
            return {
                'top': vertical,
                'right': horizontal,
                'bottom': vertical,
                'left': horizontal
            }
        elif len(parts) == 4:
            # margin: 10px 20px 30px 40px
            return {
                'top': self._parse_css_spacing(parts[0]),
                'right': self._parse_css_spacing(parts[1]),
                'bottom': self._parse_css_spacing(parts[2]),
                'left': self._parse_css_spacing(parts[3])
            }
        else:
            return {'top': 0.0, 'right': 0.0, 'bottom': 0.0, 'left': 0.0}

    def _layout_title_slide(self, slide, text_elements: List[Dict[str, Any]],
                            content_bounds: Tuple[float, float, float, float]):
        """标题页布局 - 居中对齐，大标题突出"""
        content_left, content_top, content_width, content_height = content_bounds

        # 计算总内容高度
        total_height = sum(
            self._calculate_element_height(elem) for elem in text_elements)
        total_spacing = len(text_elements) * self.px_to_inches(20)  # 标题页间距更大

        # 垂直居中
        start_y = content_top + (content_height - total_height -
                                 total_spacing) / 2
        current_y = max(start_y, content_top)

        for i, element in enumerate(text_elements):
            # 标题页元素都居中
            element_width = content_width * 0.9
            element_left = content_left + (content_width - element_width) / 2
            element_height = self._calculate_element_height(element)

            bounds = (element_left, current_y, element_width, element_height)

            try:
                self._create_element_textbox(slide, element, bounds, i + 1)
                current_y += element_height + self.px_to_inches(20)

            except Exception as e:
                if self.config.DEBUG_MODE:
                    print(f"      标题页元素错误: {e}")
                continue

    def _layout_two_column(self, slide, text_elements: List[Dict[str, Any]],
                           content_bounds: Tuple[float, float, float, float]):
        """两栏布局，增加间距避免堆叠"""
        content_left, content_top, content_width, content_height = content_bounds

        # 分割为两栏，增加栏间距
        col_gap = self.px_to_inches(30)  # 增加栏间距
        col_width = (content_width - col_gap) / 2
        left_col_left = content_left
        right_col_left = content_left + col_width + col_gap

        left_y = content_top
        right_y = content_top

        # 标题通常占全宽
        for i, element in enumerate(text_elements):
            tag = element.get('tag', '')
            element_type = element.get('type', '')

            if tag in ['h1', 'h2'] and i == 0:  # 第一个标题占全宽
                bounds = (content_left, left_y, content_width,
                          self._calculate_element_height(element))
                self._create_element_textbox(slide, element, bounds, i + 1)
                # 增加标题后的间距
                title_spacing = self._get_enhanced_element_spacing(
                    element_type, tag)
                left_y += bounds[3] + title_spacing
                right_y = left_y
            else:
                # 交替放置在两栏
                if i % 2 == 1:  # 左栏
                    bounds = (left_col_left, left_y, col_width,
                              self._calculate_element_height(element))
                    self._create_element_textbox(slide, element, bounds, i + 1)
                    # 增加元素间距
                    element_spacing = self._get_enhanced_element_spacing(
                        element_type, tag)
                    left_y += bounds[3] + element_spacing
                else:  # 右栏
                    bounds = (right_col_left, right_y, col_width,
                              self._calculate_element_height(element))
                    self._create_element_textbox(slide, element, bounds, i + 1)
                    # 增加元素间距
                    element_spacing = self._get_enhanced_element_spacing(
                        element_type, tag)
                    right_y += bounds[3] + element_spacing

    def _layout_multi_column(self, slide, text_elements: List[Dict[str, Any]],
                             content_bounds: Tuple[float, float, float,
                                                   float]):
        """多栏布局，增加间距避免堆叠"""
        content_left, content_top, content_width, content_height = content_bounds

        # 根据元素数量决定栏数
        num_elements = len(text_elements)
        if num_elements <= 3:
            num_cols = 2
        elif num_elements <= 6:
            num_cols = 3
        else:
            num_cols = 4

        # 增加栏间距
        col_gap = self.px_to_inches(24)
        col_width = (content_width - col_gap * (num_cols - 1)) / num_cols
        col_positions = []
        col_y_positions = []

        for i in range(num_cols):
            col_x = content_left + i * (col_width + col_gap)
            col_positions.append(col_x)
            col_y_positions.append(content_top)

        # 标题通常占全宽
        element_index = 0
        for i, element in enumerate(text_elements):
            tag = element.get('tag', '')
            element_type = element.get('type', '')

            if tag in ['h1', 'h2'] and i == 0:  # 第一个标题占全宽
                bounds = (content_left, content_top, content_width,
                          self._calculate_element_height(element))
                self._create_element_textbox(slide, element, bounds, i + 1)
                # 更新所有栏的Y位置，增加标题后间距
                title_spacing = self._get_enhanced_element_spacing(
                    element_type, tag)
                new_y = content_top + bounds[3] + title_spacing
                col_y_positions = [new_y] * num_cols
            else:
                # 选择最短的栏
                col_index = col_y_positions.index(min(col_y_positions))

                bounds = (col_positions[col_index], col_y_positions[col_index],
                          col_width, self._calculate_element_height(element))
                self._create_element_textbox(slide, element, bounds, i + 1)
                # 增加元素间距
                element_spacing = self._get_enhanced_element_spacing(
                    element_type, tag)
                col_y_positions[col_index] += bounds[3] + element_spacing

    def _create_element_textbox(self, slide, element: Dict[str, Any],
                                bounds: Tuple[float, float, float,
                                              float], element_num: int):
        """为单个元素创建独立文本框"""
        left, top, width, height = bounds
        element_type = element['type']
        tag = element.get('tag', 'div')

        if self.config.DEBUG_MODE:
            print(
                f"      创建文本框[{element_num}]: {element_type}({tag}) at ({left:.2f}, {top:.2f}, {width:.2f}, {height:.2f})"
            )

        try:
            # 根据元素类型创建不同的文本框
            if element_type == 'list':
                self.create_list_shape(slide, element['content'],
                                       element['style'], bounds,
                                       element['list_type'])

            elif element_type == 'quote':
                content = f'"{element["content"]}"'
                self.create_text_shape(slide, content, element['style'],
                                       bounds, tag)

            elif element_type == 'code':
                self.create_text_shape(slide, element['content'],
                                       element['style'], bounds, tag)

            elif element_type == 'heading':
                # 标题元素 - 应用标题样式
                self.create_text_shape(slide, element['content'],
                                       element['style'], bounds, tag)

            elif element_type == 'paragraph':
                # 段落元素 - 应用段落样式
                self.create_text_shape(slide, element['content'],
                                       element['style'], bounds, tag)

            elif element_type == 'text_block':
                # 文本块（通常是div中的内容）
                self.create_text_shape(slide, element['content'],
                                       element['style'], bounds, tag)

            elif element_type == 'inline_text':
                # 内联文本元素
                self.create_text_shape(slide, element['content'],
                                       element['style'], bounds, tag)
            else:
                # 默认处理
                self.create_text_shape(slide, str(element['content']),
                                       element['style'], bounds, tag)

            if self.config.DEBUG_MODE:
                print(f"        ✓ 成功创建 {element_type} 文本框")

        except Exception as e:
            if self.config.DEBUG_MODE:
                print(f"        ✗ 创建文本框失败: {e}")
                import traceback
                traceback.print_exc()
            # 不抛出异常，继续处理其他元素
            pass

    def _calculate_element_height(self, element: Dict[str, Any]) -> float:
        """智能计算元素高度，确保有足够空间避免堆叠"""
        element_type = element.get('type', 'text')
        tag = element.get('tag', 'p')
        content = str(element.get('content', ''))

        # 根据元素类型和标签计算基础高度，增加更多空间
        if element_type == 'heading' or tag in [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]:
            if tag == 'h1':
                base_height = self.px_to_inches(85)  # 增加大标题高度
            elif tag == 'h2':
                base_height = self.px_to_inches(70)  # 增加高度
            elif tag == 'h3':
                base_height = self.px_to_inches(55)  # 增加高度
            elif tag == 'h4':
                base_height = self.px_to_inches(45)
            else:
                base_height = self.px_to_inches(40)

        elif element_type == 'list':
            # 列表高度根据项目数量，增加每项空间
            item_count = len(element.get('content', []))
            base_height = self.px_to_inches(45 + item_count * 32)  # 增加每项高度

        elif element_type == 'code':
            # 代码块根据行数，增加行高
            line_count = len(content.split('\n'))
            base_height = self.px_to_inches(55 + line_count * 25)  # 增加代码行高

        elif element_type == 'quote':
            # 引用文本，增加高度
            line_count = max(1, len(content) // 50 + 1)  # 减少每行字符数
            base_height = self.px_to_inches(50 + line_count * 28)  # 增加引用高度

        elif element_type in ['paragraph', 'text_block']:
            # 段落和文本块根据内容长度，增加高度
            char_count = len(content)
            if char_count <= 50:
                base_height = self.px_to_inches(45)  # 增加短文本高度
            elif char_count <= 150:
                base_height = self.px_to_inches(60)  # 增加中等文本高度
            elif char_count <= 300:
                base_height = self.px_to_inches(80)  # 增加长文本高度
            else:
                line_count = max(2, char_count // 60 + 1)  # 减少每行字符数，增加行数
                base_height = self.px_to_inches(35 + line_count * 25)  # 增加行高

        elif element_type == 'inline_text':
            # 内联文本增加高度
            base_height = self.px_to_inches(35)  # 增加内联文本高度

        else:
            # 默认文本高度，增加空间
            line_count = max(2, len(content) // 70 + 1)
            base_height = self.px_to_inches(35 + line_count * 22)  # 增加默认高度

        # 应用最小和最大高度限制
        min_height = self.px_to_inches(35)  # 增加最小高度
        max_height = self.px_to_inches(250)  # 增加最大高度限制

        return max(min_height, min(base_height, max_height))

    def _get_element_spacing(self, element: Dict[str, Any]) -> float:
        """获取元素间距"""
        element_type = element.get('type', 'text')
        tag = element.get('tag', 'p')

        # 根据元素类型确定间距
        if element_type == 'heading' or tag in [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]:
            if tag == 'h1':
                return self.px_to_inches(30)  # 大标题后更大间距
            elif tag == 'h2':
                return self.px_to_inches(25)
            elif tag in ['h3', 'h4']:
                return self.px_to_inches(20)
            else:
                return self.px_to_inches(15)

        elif element_type == 'list':
            return self.px_to_inches(18)  # 列表后适中间距

        elif element_type == 'code':
            return self.px_to_inches(20)  # 代码块后较大间距

        elif element_type == 'quote':
            return self.px_to_inches(18)  # 引用后适中间距

        elif element_type in ['paragraph', 'text_block']:
            return self.px_to_inches(15)  # 段落间标准间距

        elif element_type == 'inline_text':
            return self.px_to_inches(8)  # 内联文本间距较小

        else:
            return self.px_to_inches(12)  # 默认间距


def convert_html_to_ppt(html_file: str,
                        output_file: str,
                        config: ConversionConfig = None) -> str:
    """便捷转换函数"""
    config = config or ConversionConfig()
    generator = PPTGenerator(config)

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    return generator.convert(html_content, output_file)


if __name__ == "__main__":
    import sys

    # 创建配置
    config = ConversionConfig()
    config.DEBUG_MODE = True
    config.VERBOSE_LOGGING = True

    if len(sys.argv) < 3:
        print("用法: python html2pptx.py <HTML文件> <输出PPT文件>")
        print("示例:")
        print("  python html2pptx.py ppt-demo.html output.pptx")
        print("  python html2pptx.py complex-demo.html complex-output.pptx")
        sys.exit(1)

    html_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        result = convert_html_to_ppt(html_file, output_file, config)
        print(f"\n✅ 转换完成: {result}")
    except Exception as e:
        print(f"\n❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
