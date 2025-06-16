import os
import re
import glob
import webbrowser


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


def get_output_path(base_name, top_n=None, gpt_version=None, output_dir="visualization_output"):
    """Generate output file path, 支持 top_n 和 gpt_version 子文件夹"""
    if top_n is not None and gpt_version is not None:
        folder_name = f"top{top_n}_{gpt_version}"
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
    with open(output_path, "r", encoding="utf-8") as f:
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