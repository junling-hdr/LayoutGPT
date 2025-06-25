import os
import re
import glob
import webbrowser
from datetime import datetime


def parse_room_size(prompt):
    """Parse room dimensions from prompt"""
    # Match "Room Size: max length XXXpx, max width YYYpx"
    pattern = r"Room Size: max length (\d+)px, max width (\d+)px"
    match = re.search(pattern, prompt)
    
    if match:
        length = int(match.group(1))
        width = int(match.group(2))
        return length, width
    else:
        # Return default values if parsing fails
        print("Warning: Unable to parse room dimensions, using default values")
        return 256, 256


def get_furniture_color(furniture_type):
    """Assign colors for different furniture types"""
    color_map = {
        'double_bed': '#FF6B6B',      # Red
        'single_bed': '#FF8E8E',      # Light red
        'wardrobe': '#4ECDC4',        # Cyan
        'nightstand': '#45B7D1',      # Blue
        'table': '#96CEB4',           # Green
        'chair': '#FFEAA7',           # Yellow
        'pendant_lamp': '#DDA0DD',    # Purple
        'ceiling_lamp': '#FFB6C1',    # Pink
        'bookshelf': '#98D8C8',       # Mint green
        'desk': '#F7DC6F',            # Golden yellow
        'sofa': '#BB8FCE',            # Light purple
        'tv_stand': '#85C1E9',        # Sky blue
        'coffee_table': '#82E0AA',    # Light green
        'armchair': '#F8C471',        # Orange
        'floor_lamp': '#D7BDE2',      # Lavender
    }
    return color_map.get(furniture_type, '#95A5A6')  # Default gray


def find_rendered_image(image_root, id, room_keyword):
    """
    在 image_root 下所有包含 room_keyword 的子文件夹里查找 {id}/rendered_scene_256.png
    """
    pattern = os.path.join(image_root, f"*{room_keyword}*", id, "rendered_scene_256.png")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    return None


def to_file_url(path):
    """Convert local path to file:// URL"""
    return 'file:///' + os.path.abspath(path).replace('\\', '/').replace(' ', '%20')


def get_output_path(base_name, top_n=None, gpt_version=None, output_dir="visualization_output", is_custom=False, add_timestamp=True, timestamp=None):
    """Generate output file path, 支持 top_n 和 gpt_version 子文件夹，以及custom类型，可选择添加时间戳"""
    # Add timestamp to base_name if requested
    if add_timestamp:
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{base_name}_{timestamp}"
    
    if is_custom:
        # Custom results go to custom/html/topn_gptversion/ structure
        if top_n is not None and gpt_version is not None:
            # Sanitize gpt_version for folder names (replace dots and hyphens with underscores)
            safe_gpt_version = gpt_version.replace('.', '_').replace('-', '_')
            folder_name = f"top{top_n}_{safe_gpt_version}"
            return os.path.join(output_dir, "custom", "html", folder_name, f"{base_name}.html")
        elif top_n is not None:
            return os.path.join(output_dir, "custom", "html", f"top{top_n}", f"{base_name}.html")
        else:
            return os.path.join(output_dir, "custom", "html", f"{base_name}.html")
    else:
        # Standard results go to html/topn_gptversion/ structure
        if top_n is not None and gpt_version is not None:
            # Sanitize gpt_version for folder names (replace dots and hyphens with underscores)
            safe_gpt_version = gpt_version.replace('.', '_').replace('-', '_')
            folder_name = f"top{top_n}_{safe_gpt_version}"
            return os.path.join(output_dir, "html", folder_name, f"{base_name}.html")
        elif top_n is not None:
            return os.path.join(output_dir, "html", f"top{top_n}", f"{base_name}.html")
        else:
            return os.path.join(output_dir, "html", f"{base_name}.html")


def save_and_open_html(fig, output_path, auto_open=True, query_img=None, sorted_imgs=None):
    """Save HTML file and automatically open it, embed query and sorted images with absolute file URLs"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_html(output_path)

    top_n = len(sorted_imgs) if sorted_imgs else 0
    # read html content
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if utf-8 fails
        with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
    # construct image html
    img_html = ""
    if query_img and os.path.exists(query_img):
        img_html += f'<div><b>Query Image:</b><br><img src="{to_file_url(query_img)}" width="256" style="border:2px solid #333;margin-bottom:8px;"></div>'
    if sorted_imgs:
        img_html += f'<div><b>In-context Images (Learn from top {top_n} similar):</b><br>'
        for img in sorted_imgs:
            if img and os.path.exists(img):
                img_html += f'<img src="{to_file_url(img)}" width="128" style="margin:2px;border:1px solid #aaa;">'
        img_html += '</div>'
    # insert into <body>
    html = html.replace("<body>", f"<body>{img_html}", 1)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML file saved to: {output_path}")
    if auto_open:
        try:
            webbrowser.open(f'file://{os.path.abspath(output_path)}')
            print(f"Opened in browser: {output_path}")
        except Exception as e:
            print(f"Cannot automatically open browser: {e}")


def calculate_out_of_boundary_rate(scene_data):
    """计算超出房间边界的家具比例"""
    prompt = scene_data.get('prompt', '')
    object_list = scene_data.get('object_list', [])
    room_length, room_width = parse_room_size(prompt)
    
    total_furniture = len(object_list)
    out_of_bounds_count = 0
    
    for furniture_type, obj_data in object_list:
        length = obj_data['length']
        width = obj_data['width']
        left = obj_data['left']
        top = obj_data['top']
        
        x_min, x_max = left - length/2, left + length/2
        y_min, y_max = top - width/2, top + width/2
        
        if x_min < 0 or x_max > room_length or y_min < 0 or y_max > room_width:
            out_of_bounds_count += 1
    
    return out_of_bounds_count / total_furniture if total_furniture > 0 else 0


def parse_css_layout(raw_gpt_response):
    """解析GPT生成的CSS格式布局"""
    furniture_layouts = []
    
    if not raw_gpt_response:
        return furniture_layouts
    
    lines = raw_gpt_response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or 'Layout:' in line or 'Condition:' in line:
            continue
            
        # 匹配格式: furniture_name {length: 150px; width: 175px; height: 72px; left: 185px; top: 116px; depth: 36px;orientation: -90 degrees;}
        match = re.match(r'(\w+)\s*\{([^}]+)\}', line)
        if match:
            furniture_name = match.group(1)
            properties_str = match.group(2)
            
            # 提取CSS属性
            properties = extract_css_properties(properties_str)
            if properties:
                furniture_layouts.append((furniture_name, properties))
    
    return furniture_layouts


def extract_css_properties(properties_str):
    """从CSS属性字符串中提取家具位置和尺寸信息"""
    properties = {}
    
    # 解析CSS属性
    for prop in properties_str.split(';'):
        prop = prop.strip()
        if ':' in prop:
            key, value = prop.split(':', 1)
            key = key.strip()
            value = value.strip().replace('px', '').replace('degrees', '').strip()
            
            try:
                if key in ['length', 'width', 'height', 'left', 'top', 'depth']:
                    properties[key] = float(value)
                elif key == 'orientation':
                    properties[key] = float(value)
            except ValueError:
                continue
    
    # 检查必要的属性
    required_props = ['length', 'width', 'left', 'top']
    if all(prop in properties for prop in required_props):
        # 注意：GPT的CSS格式中：
        # - length: 家具的长度（对应我们的width）
        # - width: 家具的宽度（对应我们的height）
        # - left: X坐标位置
        # - top: Y坐标位置
        return {
            'width': properties['length'],   # GPT的length -> 我们的width (X方向尺寸)
            'height': properties['width'],   # GPT的width -> 我们的height (Y方向尺寸)
            'left': properties['left'],      # X坐标中心点
            'top': properties['top'],        # Y坐标中心点
            'depth': properties.get('depth', 0),
            'orientation': properties.get('orientation', 0)
        }
    
    return None


def check_furniture_overlap(furniture1, furniture2):
    """检查两个家具是否重叠 - 考虑完整的2D矩形，而不是中心点"""
    # 获取家具1的2D边界矩形 (left, top是中心点)
    x1_min = furniture1['left'] - furniture1['width'] / 2
    x1_max = furniture1['left'] + furniture1['width'] / 2
    y1_min = furniture1['top'] - furniture1['height'] / 2
    y1_max = furniture1['top'] + furniture1['height'] / 2
    
    # 获取家具2的2D边界矩形
    x2_min = furniture2['left'] - furniture2['width'] / 2
    x2_max = furniture2['left'] + furniture2['width'] / 2
    y2_min = furniture2['top'] - furniture2['height'] / 2
    y2_max = furniture2['top'] + furniture2['height'] / 2
    
    # 检查两个矩形是否重叠 (AABB碰撞检测)
    # 如果两个矩形不重叠，则它们在某个轴上完全分离
    no_overlap_x = (x1_max <= x2_min) or (x2_max <= x1_min)
    no_overlap_y = (y1_max <= y2_min) or (y2_max <= y1_min)
    
    # 如果在任何轴上没有重叠，则整体没有重叠
    return not (no_overlap_x or no_overlap_y)


def calculate_overlap_area(furniture1, furniture2):
    """计算两个家具的重叠面积 - 精确计算2D矩形重叠区域"""
    # 获取家具1的2D边界矩形
    x1_min = furniture1['left'] - furniture1['width'] / 2
    x1_max = furniture1['left'] + furniture1['width'] / 2
    y1_min = furniture1['top'] - furniture1['height'] / 2
    y1_max = furniture1['top'] + furniture1['height'] / 2
    
    # 获取家具2的2D边界矩形
    x2_min = furniture2['left'] - furniture2['width'] / 2
    x2_max = furniture2['left'] + furniture2['width'] / 2
    y2_min = furniture2['top'] - furniture2['height'] / 2
    y2_max = furniture2['top'] + furniture2['height'] / 2
    
    # 计算重叠区域的边界
    overlap_x_min = max(x1_min, x2_min)
    overlap_x_max = min(x1_max, x2_max)
    overlap_y_min = max(y1_min, y2_min)
    overlap_y_max = min(y1_max, y2_max)
    
    # 计算重叠区域的宽度和高度
    overlap_width = max(0, overlap_x_max - overlap_x_min)
    overlap_height = max(0, overlap_y_max - overlap_y_min)
    
    return overlap_width * overlap_height


def calculate_overlapping_statistics(scene_data):
    """计算家具重叠统计信息"""
    raw_gpt_response = scene_data.get('raw_gpt_response', '')
    
    # 如果没有原始GPT响应，尝试从object_list构建
    if not raw_gpt_response:
        object_list = scene_data.get('object_list', [])
        if not object_list:
            return {
                'overlapping_rate': 0.0,
                'average_overlapping_number': 0.0,
                'total_overlaps': 0,
                'total_furniture': 0,
                'furniture_with_overlaps': 0
            }
        
        # 从object_list构建furniture_layouts
        furniture_layouts = []
        for furniture_type, obj_data in object_list:
            if isinstance(obj_data, dict):
                furniture_layouts.append((furniture_type, obj_data))
            elif isinstance(obj_data, list) and len(obj_data) >= 4:
                # [length, width, height, left, top, depth, orientation]
                properties = {
                    'width': obj_data[0],   # length -> width
                    'height': obj_data[1],  # width -> height
                    'left': obj_data[3],
                    'top': obj_data[4],
                    'depth': obj_data[5] if len(obj_data) > 5 else 0,
                    'orientation': obj_data[6] if len(obj_data) > 6 else 0
                }
                furniture_layouts.append((furniture_type, properties))
    else:
        # 解析GPT的原始响应
        furniture_layouts = parse_css_layout(raw_gpt_response)
    
    if not furniture_layouts:
        return {
            'overlapping_rate': 0.0,
            'average_overlapping_number': 0.0,
            'total_overlaps': 0,
            'total_furniture': 0,
            'furniture_with_overlaps': 0
        }
    
    total_furniture = len(furniture_layouts)
    furniture_with_overlaps = set()
    total_overlaps = 0
    
    # 检查每对家具之间的重叠
    for i in range(len(furniture_layouts)):
        for j in range(i + 1, len(furniture_layouts)):
            furniture1_name, furniture1_props = furniture_layouts[i]
            furniture2_name, furniture2_props = furniture_layouts[j]
            
            if check_furniture_overlap(furniture1_props, furniture2_props):
                furniture_with_overlaps.add(i)
                furniture_with_overlaps.add(j)
                total_overlaps += 1
    
    # 计算统计信息
    overlapping_rate = len(furniture_with_overlaps) / total_furniture if total_furniture > 0 else 0.0
    average_overlapping_number = total_overlaps / total_furniture if total_furniture > 0 else 0.0
    
    return {
        'overlapping_rate': overlapping_rate,
        'average_overlapping_number': average_overlapping_number,
        'total_overlaps': total_overlaps,
        'total_furniture': total_furniture,
        'furniture_with_overlaps': len(furniture_with_overlaps)
    } 