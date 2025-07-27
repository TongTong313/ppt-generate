#!/usr/bin/env python3
"""
智能布局分析器
专门处理HTML的复杂布局结构，确保PPT版式与HTML完全一致
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag, NavigableString
from enhanced_html2pptx import TemplateConfig


@dataclass
class ElementPosition:
    """元素位置信息"""
    left: float
    top: float
    width: float
    height: float
    z_index: int = 0
    element_type: str = 'content'
    
    def overlaps_with(self, other: 'ElementPosition') -> bool:
        """检查是否与另一个元素重叠"""
        return (self.left < other.left + other.width and
                self.left + self.width > other.left and
                self.top < other.top + other.height and
                self.top + self.height > other.top)
    
    def get_area(self) -> float:
        """获取元素面积"""
        return self.width * self.height


@dataclass
class LayoutRegion:
    """布局区域"""
    name: str
    left: float
    top: float
    width: float
    height: float
    elements: List[Dict[str, Any]]
    region_type: str = 'content'  # 'header', 'content', 'footer', 'sidebar'
    
    def add_element(self, element: Dict[str, Any]) -> None:
        """添加元素到区域"""
        self.elements.append(element)
    
    def get_element_count(self) -> int:
        """获取区域内元素数量"""
        return len(self.elements)


class AdvancedLayoutAnalyzer:
    """高级布局分析器"""
    
    def __init__(self, config: TemplateConfig):
        self.config = config
        self.px_to_inches = 1 / 96
    
    def analyze_slide_layout(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """分析幻灯片布局"""
        layout_info = {
            'type': 'unknown',
            'regions': [],
            'columns': 1,
            'rows': 1,
            'has_header': False,
            'has_footer': False,
            'has_sidebar': False,
            'layout_complexity': 'simple',
            'grid_structure': None,
            'flex_structure': None
        }
        
        # 获取容器样式
        container_style = self._get_element_style(container, styles)
        
        # 检测布局类型
        layout_info['type'] = self._detect_layout_type(container, styles)
        
        # 分析网格结构
        if self._has_grid_layout(container_style):
            layout_info['grid_structure'] = self._analyze_grid_layout(container, styles)
        
        # 分析弹性布局
        if self._has_flex_layout(container_style):
            layout_info['flex_structure'] = self._analyze_flex_layout(container, styles)
        
        # 检测多栏布局
        layout_info['columns'] = self._detect_column_count(container, styles)
        
        # 分析区域
        layout_info['regions'] = self._analyze_regions(container, styles)
        
        # 计算布局复杂度
        layout_info['layout_complexity'] = self._calculate_complexity(layout_info)
        
        return layout_info
    
    def _detect_layout_type(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> str:
        """检测布局类型"""
        class_names = container.get('class', [])
        container_id = container.get('id', '')
        
        # 基于类名检测
        for class_name in class_names:
            class_lower = class_name.lower()
            if 'title' in class_lower:
                return 'title_slide'
            elif 'two-column' in class_lower or 'dual' in class_lower:
                return 'two_column'
            elif 'three-column' in class_lower or 'triple' in class_lower:
                return 'three_column'
            elif 'data' in class_lower or 'chart' in class_lower:
                return 'data_slide'
            elif 'quote' in class_lower or 'testimonial' in class_lower:
                return 'quote_slide'
            elif 'conclusion' in class_lower or 'summary' in class_lower:
                return 'conclusion_slide'
            elif 'thank' in class_lower:
                return 'thank_you_slide'
        
        # 基于内容结构检测
        children = [child for child in container.children if isinstance(child, Tag)]
        
        # 检测标题页
        h1_count = len(container.find_all('h1'))
        h2_count = len(container.find_all('h2'))
        if h1_count == 1 and h2_count <= 2 and len(children) <= 4:
            return 'title_slide'
        
        # 检测多栏布局
        flex_containers = [child for child in children if self._has_flex_layout(self._get_element_style(child, styles))]
        if len(flex_containers) >= 2:
            return 'multi_column'
        
        # 检测数据展示页
        stat_boxes = container.find_all(class_=re.compile(r'stat|data|metric|number'))
        if len(stat_boxes) >= 3:
            return 'data_slide'
        
        return 'content_slide'
    
    def _has_grid_layout(self, style: Dict[str, str]) -> bool:
        """检测是否使用CSS Grid布局"""
        display = style.get('display', '')
        return 'grid' in display
    
    def _has_flex_layout(self, style: Dict[str, str]) -> bool:
        """检测是否使用Flexbox布局"""
        display = style.get('display', '')
        return 'flex' in display
    
    def _analyze_grid_layout(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """分析CSS Grid布局"""
        container_style = self._get_element_style(container, styles)
        
        grid_info = {
            'template_columns': container_style.get('grid-template-columns', ''),
            'template_rows': container_style.get('grid-template-rows', ''),
            'gap': container_style.get('gap', ''),
            'areas': container_style.get('grid-template-areas', ''),
            'items': []
        }
        
        # 分析网格项目
        for child in container.children:
            if isinstance(child, Tag):
                child_style = self._get_element_style(child, styles)
                item_info = {
                    'element': child,
                    'grid_column': child_style.get('grid-column', ''),
                    'grid_row': child_style.get('grid-row', ''),
                    'grid_area': child_style.get('grid-area', '')
                }
                grid_info['items'].append(item_info)
        
        return grid_info
    
    def _analyze_flex_layout(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """分析Flexbox布局"""
        container_style = self._get_element_style(container, styles)
        
        flex_info = {
            'direction': container_style.get('flex-direction', 'row'),
            'wrap': container_style.get('flex-wrap', 'nowrap'),
            'justify_content': container_style.get('justify-content', 'flex-start'),
            'align_items': container_style.get('align-items', 'stretch'),
            'gap': container_style.get('gap', ''),
            'items': []
        }
        
        # 分析弹性项目
        for child in container.children:
            if isinstance(child, Tag):
                child_style = self._get_element_style(child, styles)
                item_info = {
                    'element': child,
                    'flex_grow': child_style.get('flex-grow', '0'),
                    'flex_shrink': child_style.get('flex-shrink', '1'),
                    'flex_basis': child_style.get('flex-basis', 'auto'),
                    'align_self': child_style.get('align-self', 'auto')
                }
                flex_info['items'].append(item_info)
        
        return flex_info
    
    def _detect_column_count(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> int:
        """检测栏数"""
        # 检测直接子元素中的栏容器
        children = [child for child in container.children if isinstance(child, Tag)]
        
        # 检测flex布局的栏数
        container_style = self._get_element_style(container, styles)
        if self._has_flex_layout(container_style):
            direction = container_style.get('flex-direction', 'row')
            if direction in ['row', 'row-reverse']:
                # 水平排列，计算栏数
                flex_items = [child for child in children if self._is_flex_item(child, styles)]
                return len(flex_items) if flex_items else 1
        
        # 检测基于类名的栏布局
        column_containers = []
        for child in children:
            class_names = child.get('class', [])
            for class_name in class_names:
                if any(keyword in class_name.lower() for keyword in ['column', 'col-', 'grid-']):
                    column_containers.append(child)
                    break
        
        if column_containers:
            return len(column_containers)
        
        # 检测浮动布局
        float_elements = []
        for child in children:
            child_style = self._get_element_style(child, styles)
            if child_style.get('float') in ['left', 'right']:
                float_elements.append(child)
        
        if float_elements:
            return len(float_elements)
        
        return 1
    
    def _is_flex_item(self, element: Tag, styles: Dict[str, Dict[str, str]]) -> bool:
        """检测元素是否为flex项目"""
        style = self._get_element_style(element, styles)
        return any(prop in style for prop in ['flex-grow', 'flex-shrink', 'flex-basis', 'flex'])
    
    def _analyze_regions(self, container: Tag, styles: Dict[str, Dict[str, str]]) -> List[LayoutRegion]:
        """分析布局区域"""
        regions = []
        
        # 检测标准区域
        header_elements = container.find_all(class_=re.compile(r'header|top|title'))
        if header_elements:
            header_region = LayoutRegion(
                name='header',
                left=0, top=0, width=1, height=0.2,
                elements=[{'element': elem, 'type': 'header'} for elem in header_elements],
                region_type='header'
            )
            regions.append(header_region)
        
        footer_elements = container.find_all(class_=re.compile(r'footer|bottom|contact'))
        if footer_elements:
            footer_region = LayoutRegion(
                name='footer',
                left=0, top=0.8, width=1, height=0.2,
                elements=[{'element': elem, 'type': 'footer'} for elem in footer_elements],
                region_type='footer'
            )
            regions.append(footer_region)
        
        # 检测侧边栏
        sidebar_elements = container.find_all(class_=re.compile(r'sidebar|aside|nav'))
        if sidebar_elements:
            sidebar_region = LayoutRegion(
                name='sidebar',
                left=0, top=0.2, width=0.25, height=0.6,
                elements=[{'element': elem, 'type': 'sidebar'} for elem in sidebar_elements],
                region_type='sidebar'
            )
            regions.append(sidebar_region)
        
        # 主内容区域
        content_elements = []
        for child in container.children:
            if isinstance(child, Tag):
                # 排除已分类的元素
                if not any(child in region.elements for region in regions):
                    content_elements.append({'element': child, 'type': 'content'})
        
        if content_elements:
            content_region = LayoutRegion(
                name='content',
                left=0.25 if sidebar_elements else 0,
                top=0.2 if header_elements else 0,
                width=0.75 if sidebar_elements else 1,
                height=0.6 if (header_elements and footer_elements) else 0.8,
                elements=content_elements,
                region_type='content'
            )
            regions.append(content_region)
        
        return regions
    
    def _calculate_complexity(self, layout_info: Dict[str, Any]) -> str:
        """计算布局复杂度"""
        complexity_score = 0
        
        # 基于布局类型评分
        layout_type = layout_info['type']
        type_scores = {
            'title_slide': 1,
            'content_slide': 2,
            'two_column': 3,
            'three_column': 4,
            'multi_column': 4,
            'data_slide': 3,
            'quote_slide': 2,
            'conclusion_slide': 3,
            'thank_you_slide': 1
        }
        complexity_score += type_scores.get(layout_type, 2)
        
        # 基于栏数评分
        columns = layout_info['columns']
        complexity_score += min(columns - 1, 3)
        
        # 基于区域数评分
        regions = layout_info['regions']
        complexity_score += min(len(regions) - 1, 3)
        
        # 基于布局技术评分
        if layout_info['grid_structure']:
            complexity_score += 2
        if layout_info['flex_structure']:
            complexity_score += 1
        
        # 分类复杂度
        if complexity_score <= 3:
            return 'simple'
        elif complexity_score <= 6:
            return 'moderate'
        else:
            return 'complex'
    
    def _get_element_style(self, element: Tag, styles: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """获取元素样式"""
        computed_style = {}
        
        if not element or not element.name:
            return computed_style
        
        # 标签样式
        tag_name = element.name.lower()
        if tag_name in styles:
            computed_style.update(styles[tag_name])
        
        # 类样式
        if element.has_attr('class'):
            for class_name in element['class']:
                selector = f'.{class_name}'
                if selector in styles:
                    computed_style.update(styles[selector])
                
                # 标签+类样式
                tag_class_selector = f'{tag_name}.{class_name}'
                if tag_class_selector in styles:
                    computed_style.update(styles[tag_class_selector])
        
        # ID样式
        if element.has_attr('id'):
            id_selector = f"#{element['id']}"
            if id_selector in styles:
                computed_style.update(styles[id_selector])
        
        # 内联样式
        if element.has_attr('style'):
            inline_styles = self._parse_inline_style(element['style'])
            computed_style.update(inline_styles)
        
        return computed_style
    
    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """解析内联样式"""
        styles = {}
        for rule in style_str.split(';'):
            if ':' in rule:
                prop, value = rule.split(':', 1)
                styles[prop.strip()] = value.strip()
        return styles


class SmartPositionCalculator:
    """智能位置计算器"""
    
    def __init__(self, config: TemplateConfig):
        self.config = config
        self.px_to_inches = 1 / 96
    
    def calculate_positions(self, elements: List[Dict[str, Any]], layout_info: Dict[str, Any]) -> List[ElementPosition]:
        """计算元素位置"""
        positions = []
        
        layout_type = layout_info['type']
        
        if layout_type == 'title_slide':
            positions = self._calculate_title_slide_positions(elements)
        elif layout_type in ['two_column', 'three_column', 'multi_column']:
            positions = self._calculate_multi_column_positions(elements, layout_info)
        elif layout_type == 'data_slide':
            positions = self._calculate_data_slide_positions(elements)
        else:
            positions = self._calculate_standard_positions(elements)
        
        # 解决重叠问题
        positions = self._resolve_overlaps(positions)
        
        return positions
    
    def _calculate_title_slide_positions(self, elements: List[Dict[str, Any]]) -> List[ElementPosition]:
        """计算标题页位置"""
        positions = []
        
        # 可用区域
        available_width = self.config.slide_width_inches - (self.config.padding_left + self.config.padding_right) * self.px_to_inches
        available_height = self.config.slide_height_inches - (self.config.padding_top + self.config.padding_bottom) * self.px_to_inches
        
        start_x = self.config.padding_left * self.px_to_inches
        start_y = self.config.padding_top * self.px_to_inches
        
        current_y = start_y
        
        for i, element in enumerate(elements):
            element_type = element.get('type', 'content')
            
            if element_type == 'heading' and element.get('level', 1) == 1:
                # 主标题
                width = available_width * 0.9
                height = 1.2
                left = start_x + (available_width - width) / 2
                top = current_y
                positions.append(ElementPosition(left, top, width, height, element_type='title'))
                current_y += height + 0.3
            
            elif element_type == 'heading' and element.get('level', 1) == 2:
                # 副标题
                width = available_width * 0.8
                height = 0.8
                left = start_x + (available_width - width) / 2
                top = current_y
                positions.append(ElementPosition(left, top, width, height, element_type='subtitle'))
                current_y += height + 0.2
            
            else:
                # 其他内容
                width = available_width * 0.7
                height = 0.6
                left = start_x + (available_width - width) / 2
                top = current_y
                positions.append(ElementPosition(left, top, width, height, element_type='content'))
                current_y += height + 0.2
        
        return positions
    
    def _calculate_multi_column_positions(self, elements: List[Dict[str, Any]], layout_info: Dict[str, Any]) -> List[ElementPosition]:
        """计算多栏布局位置"""
        positions = []
        columns = layout_info['columns']
        
        # 可用区域
        available_width = self.config.slide_width_inches - (self.config.padding_left + self.config.padding_right) * self.px_to_inches
        available_height = self.config.slide_height_inches - (self.config.padding_top + self.config.padding_bottom) * self.px_to_inches
        
        start_x = self.config.padding_left * self.px_to_inches
        start_y = self.config.padding_top * self.px_to_inches
        
        # 计算栏宽
        column_gap = 0.3  # 栏间距
        column_width = (available_width - (columns - 1) * column_gap) / columns
        
        # 分配元素到栏
        elements_per_column = math.ceil(len(elements) / columns)
        
        for col in range(columns):
            column_x = start_x + col * (column_width + column_gap)
            current_y = start_y
            
            start_idx = col * elements_per_column
            end_idx = min(start_idx + elements_per_column, len(elements))
            
            for i in range(start_idx, end_idx):
                element = elements[i]
                height = self._estimate_element_height(element)
                
                positions.append(ElementPosition(
                    column_x, current_y, column_width, height, element_type='content'
                ))
                
                current_y += height + self.config.element_spacing * self.px_to_inches
        
        return positions
    
    def _calculate_data_slide_positions(self, elements: List[Dict[str, Any]]) -> List[ElementPosition]:
        """计算数据展示页位置"""
        positions = []
        
        # 可用区域
        available_width = self.config.slide_width_inches - (self.config.padding_left + self.config.padding_right) * self.px_to_inches
        available_height = self.config.slide_height_inches - (self.config.padding_top + self.config.padding_bottom) * self.px_to_inches
        
        start_x = self.config.padding_left * self.px_to_inches
        start_y = self.config.padding_top * self.px_to_inches
        
        # 标题区域
        title_elements = [e for e in elements if e.get('type') == 'heading']
        data_elements = [e for e in elements if e.get('type') != 'heading']
        
        current_y = start_y
        
        # 处理标题
        for element in title_elements:
            width = available_width * 0.9
            height = 0.8
            left = start_x + (available_width - width) / 2
            positions.append(ElementPosition(left, current_y, width, height, element_type='title'))
            current_y += height + 0.3
        
        # 处理数据元素 - 水平排列
        if data_elements:
            data_area_height = available_height - (current_y - start_y) - 0.5
            data_width = available_width / len(data_elements)
            
            for i, element in enumerate(data_elements):
                left = start_x + i * data_width
                positions.append(ElementPosition(
                    left, current_y, data_width * 0.9, data_area_height, element_type='data'
                ))
        
        return positions
    
    def _calculate_standard_positions(self, elements: List[Dict[str, Any]]) -> List[ElementPosition]:
        """计算标准布局位置"""
        positions = []
        
        # 可用区域
        available_width = self.config.slide_width_inches - (self.config.padding_left + self.config.padding_right) * self.px_to_inches
        
        start_x = self.config.padding_left * self.px_to_inches
        start_y = self.config.padding_top * self.px_to_inches
        
        current_y = start_y
        
        for element in elements:
            height = self._estimate_element_height(element)
            width = available_width * self.config.max_textbox_width_ratio
            
            positions.append(ElementPosition(
                start_x, current_y, width, height, element_type='content'
            ))
            
            current_y += height + self.config.element_spacing * self.px_to_inches
        
        return positions
    
    def _estimate_element_height(self, element: Dict[str, Any]) -> float:
        """估算元素高度"""
        element_type = element.get('type', 'content')
        content = element.get('content', '')
        
        if element_type == 'heading':
            level = element.get('level', 1)
            if level == 1:
                return 1.0
            elif level == 2:
                return 0.8
            else:
                return 0.6
        elif element_type == 'list':
            if isinstance(content, list):
                return max(0.4, len(content) * 0.3)
            else:
                return 0.6
        else:
            # 基于内容长度估算
            if isinstance(content, str):
                lines = max(1, len(content) // 80)
                return max(0.4, lines * 0.3)
            else:
                return 0.5
    
    def _resolve_overlaps(self, positions: List[ElementPosition]) -> List[ElementPosition]:
        """解决重叠问题"""
        if not self.config.overlap_detection:
            return positions
        
        resolved_positions = positions.copy()
        
        # 检测重叠
        for i in range(len(resolved_positions)):
            for j in range(i + 1, len(resolved_positions)):
                if resolved_positions[i].overlaps_with(resolved_positions[j]):
                    # 解决重叠
                    if self.config.overlap_resolution == 'auto_adjust':
                        # 将第二个元素向下移动
                        new_top = resolved_positions[i].top + resolved_positions[i].height + 0.1
                        resolved_positions[j] = ElementPosition(
                            resolved_positions[j].left,
                            new_top,
                            resolved_positions[j].width,
                            resolved_positions[j].height,
                            resolved_positions[j].z_index,
                            resolved_positions[j].element_type
                        )
        
        return resolved_positions


def main():
    """演示布局分析器的使用"""
    from template_configs import TemplateConfigManager
    
    # 创建配置
    config_manager = TemplateConfigManager()
    config = config_manager.get_config('complex-template')
    
    # 创建分析器
    analyzer = AdvancedLayoutAnalyzer(config)
    calculator = SmartPositionCalculator(config)
    
    print("布局分析器已初始化")
    print(f"配置: {config.default_font_family}, 字体缩放: {config.font_size_scale}")
    
    # 模拟布局分析
    mock_layout = {
        'type': 'two_column',
        'columns': 2,
        'regions': [],
        'layout_complexity': 'moderate'
    }
    
    mock_elements = [
        {'type': 'heading', 'level': 1, 'content': '标题'},
        {'type': 'paragraph', 'content': '段落内容'},
        {'type': 'list', 'content': ['项目1', '项目2', '项目3']}
    ]
    
    positions = calculator.calculate_positions(mock_elements, mock_layout)
    
    print(f"\n计算出 {len(positions)} 个元素位置:")
    for i, pos in enumerate(positions):
        print(f"元素 {i+1}: ({pos.left:.2f}, {pos.top:.2f}) 尺寸: {pos.width:.2f}x{pos.height:.2f}")


if __name__ == '__main__':
    main()