import os
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from .scene_3d import visualize_scene
from .scene_2d import create_2d_visualization
from .utils import calculate_out_of_boundary_rate


def resize_image_to_height(img_path, target_height):
    """将图片按比例缩放到指定高度"""
    if not os.path.exists(img_path):
        # 创建占位图片
        img = Image.new('RGB', (target_height, target_height), color='lightgray')
        draw = ImageDraw.Draw(img)
        draw.text((target_height//4, target_height//2), "No Image", fill='black')
        return img
    
    img = Image.open(img_path)
    ratio = target_height / img.height
    new_width = int(img.width * ratio)
    return img.resize((new_width, target_height), Image.Resampling.LANCZOS)


def create_image_matrix(matrix_data, cell_height=400):
    """创建图片矩阵，包含 prompt 信息和整体统计"""
    if not matrix_data:
        return None
    
    n_queries = len(matrix_data)
    max_in_context = max(len(data.get('sorted_imgs', [])) for data in matrix_data)
    
    # 矩阵行数：Query + 3D + 2D + In-context images + Prompt
    n_rows = 4 + max_in_context
    
    # 计算每列宽度（取最宽的图片）
    col_widths = []
    for i, data in enumerate(matrix_data):
        max_width = 0
        
        # Query image
        if data['query_img'] and os.path.exists(data['query_img']):
            img = resize_image_to_height(data['query_img'], cell_height)
            max_width = max(max_width, img.width)
        
        # 3D image
        if os.path.exists(data['3d_img']):
            img = resize_image_to_height(data['3d_img'], cell_height)
            max_width = max(max_width, img.width)
        
        # 2D image
        if os.path.exists(data['2d_img']):
            img = resize_image_to_height(data['2d_img'], cell_height)
            max_width = max(max_width, img.width)
        
        # In-context images
        for sorted_img in data.get('sorted_imgs', []):
            if sorted_img and os.path.exists(sorted_img):
                img = resize_image_to_height(sorted_img, cell_height)
                max_width = max(max_width, img.width)
        
        col_widths.append(max(max_width, 500))  # 大幅增加最小宽度
    
    # 创建大图，增加更多空间
    total_width = sum(col_widths) + 400  # 增加左侧标签空间
    total_height = n_rows * cell_height + 300  # 增加顶部标题空间
    
    matrix_img = Image.new('RGB', (total_width, total_height), color='white')
    draw = ImageDraw.Draw(matrix_img)
    
    # 尝试加载字体
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)  # 增大标题字体
        font = ImageFont.truetype("arial.ttf", 20)  # 增大正文字体
        small_font = ImageFont.truetype("arial.ttf", 16)  # 增大小字体
        tiny_font = ImageFont.truetype("arial.ttf", 12)  # 增大微小字体
    except:
        title_font = ImageFont.load_default()
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        tiny_font = ImageFont.load_default()
    
    # 计算整体统计
    total_oob_rate = sum(data['oob_rate'] for data in matrix_data) / len(matrix_data)
    total_scenes = len(matrix_data)
    
    # 绘制标题和统计
    draw.text((10, 10), "Benchmarking Matrix", fill='black', font=title_font)
    draw.text((10, 40), f"Total Scenes: {total_scenes} | Overall OOB Rate: {total_oob_rate:.1%}", 
             fill='darkblue', font=font)
    
    # 绘制行标签
    row_labels = ["Query", "3D View", "2D View", "Prompt"] + [f"In-context {i+1}" for i in range(max_in_context)]
    for i, label in enumerate(row_labels):
        y = 80 + i * cell_height + cell_height // 2
        draw.text((10, y), label, fill='black', font=small_font)
    
    # 填充矩阵
    x_offset = 400
    for col, data in enumerate(matrix_data):
        query_id = data['query_id']
        oob_rate = data['oob_rate']
        
        # 列标题
        col_x = x_offset + sum(col_widths[:col])
        short_id = query_id.split('_')[-1] if '_' in query_id else query_id
        draw.text((col_x, 60), f"{short_id}\nOOB: {oob_rate:.1%}", fill='black', font=small_font)
        
        row_y = 80
        
        # Query image
        if data['query_img'] and os.path.exists(data['query_img']):
            img = resize_image_to_height(data['query_img'], cell_height)
            matrix_img.paste(img, (col_x, row_y))
        row_y += cell_height
        
        # 3D image
        if os.path.exists(data['3d_img']):
            img = resize_image_to_height(data['3d_img'], cell_height)
            matrix_img.paste(img, (col_x, row_y))
        row_y += cell_height
        
        # 2D image
        if os.path.exists(data['2d_img']):
            img = resize_image_to_height(data['2d_img'], cell_height)
            matrix_img.paste(img, (col_x, row_y))
        row_y += cell_height
        
        # 改进的 Prompt 信息显示
        prompt_text = data.get('prompt', 'No prompt')
        object_list = data.get('object_list', [])
        
        # 简化 prompt 显示
        prompt_lines = prompt_text.strip().split('\n')
        room_type = next((line for line in prompt_lines if 'Room Type:' in line), 'Room Type: Unknown')
        room_size = next((line for line in prompt_lines if 'Room Size:' in line), 'Room Size: Unknown')
        
        # 统计家具种类和数量
        furniture_counts = {}
        for furniture_type, obj_data in object_list:
            furniture_counts[furniture_type] = furniture_counts.get(furniture_type, 0) + 1
        
        # 创建 prompt 图片
        prompt_img = Image.new('RGB', (col_widths[col], cell_height), color='lightyellow')
        prompt_draw = ImageDraw.Draw(prompt_img)
        
        # 绘制 prompt 文本
        y_text = 10
        prompt_draw.text((10, y_text), room_type.replace('Room Type: ', ''), fill='black', font=font)
        y_text += 30
        prompt_draw.text((10, y_text), room_size.replace('Room Size: ', ''), fill='black', font=small_font)
        y_text += 25
        prompt_draw.text((10, y_text), f"Total Items: {len(object_list)}", fill='darkblue', font=small_font)
        y_text += 25
        
        # 显示家具种类和数量
        if furniture_counts:
            prompt_draw.text((10, y_text), "Furniture Details:", fill='darkgreen', font=small_font)
            y_text += 20
            
            # 按数量排序显示
            sorted_furniture = sorted(furniture_counts.items(), key=lambda x: x[1], reverse=True)
            items_shown = 0
            max_items = min(len(sorted_furniture), (cell_height - y_text - 30) // 18)
            
            for furn_type, count in sorted_furniture:
                if items_shown >= max_items:
                    remaining = len(sorted_furniture) - items_shown
                    if remaining > 0:
                        prompt_draw.text((15, y_text), f"... +{remaining} more", fill='gray', font=tiny_font)
                    break
                
                display_name = furn_type.replace('_', ' ').title()
                if len(display_name) > 15:
                    display_name = display_name[:15] + '.'
                prompt_draw.text((15, y_text), f"• {display_name}: {count}", fill='black', font=tiny_font)
                y_text += 18
                items_shown += 1
        
        matrix_img.paste(prompt_img, (col_x, row_y))
        row_y += cell_height
        
        # In-context images
        for sorted_img in data.get('sorted_imgs', []):
            if sorted_img and os.path.exists(sorted_img):
                img = resize_image_to_height(sorted_img, cell_height)
                matrix_img.paste(img, (col_x, row_y))
            row_y += cell_height
    
    return matrix_img


def create_benchmark_matrix(data, top_n, gpt_version=None, output_dir="visualization_output"):
    """创建 benchmarking 矩阵图片"""
    print(f"Creating benchmark matrix for {len(data)} scenes...")
    
    matrix_data = []
    temp_files = []
    
    for i, scene_data in enumerate(data):
        query_id = scene_data.get('query_id', f'scene_{i}')
        print(f"Processing {i+1}/{len(data)}: {query_id}")
        
        # 生成 3D 截图 - 添加错误处理
        try:
            fig_3d, query_img, sorted_imgs = visualize_scene(scene_data)
            temp_3d_path = f"temp_3d_{query_id.replace('/', '_').replace('-', '_')}.png"
            
            # 暂时跳过 3D 截图生成，直接创建占位图片
            print(f"  Skipping 3D screenshot generation (avoiding hang)")
            placeholder_img = Image.new('RGB', (800, 600), color='lightblue')
            draw = ImageDraw.Draw(placeholder_img)
            try:
                draw.text((400, 300), f"3D View\n{query_id}\n(Screenshot skipped)", fill='black', anchor="mm")
            except:
                draw.text((350, 280), "3D View (Screenshot skipped)", fill='black')
            placeholder_img.save(temp_3d_path)
            temp_files.append(temp_3d_path)
            print(f"  3D placeholder saved: {temp_3d_path}")
        except Exception as e:
            print(f"  Error in visualize_scene: {e}")
            continue
        
        # 生成 2D 截图
        try:
            print(f"  Generating 2D screenshot...")
            fig_2d = create_2d_visualization(scene_data)
            temp_2d_path = f"temp_2d_{query_id.replace('/', '_').replace('-', '_')}.png"
            fig_2d.savefig(temp_2d_path, dpi=600, bbox_inches='tight')  # 进一步提高DPI到600
            plt.close(fig_2d)
            temp_files.append(temp_2d_path)
            print(f"  2D screenshot saved: {temp_2d_path}")
        except Exception as e:
            print(f"  Warning: Failed to generate 2D screenshot: {e}")
            # 创建占位图片
            temp_2d_path = f"temp_2d_{query_id.replace('/', '_').replace('-', '_')}.png"
            placeholder_img = Image.new('RGB', (800, 600), color='lightgray')
            draw = ImageDraw.Draw(placeholder_img)
            draw.text((400, 300), "2D View\nGeneration Failed", fill='black', anchor="mm")
            placeholder_img.save(temp_2d_path)
            temp_files.append(temp_2d_path)
        
        # 计算 out of boundary 率
        try:
            oob_rate = calculate_out_of_boundary_rate(scene_data)
        except Exception as e:
            print(f"  Warning: Failed to calculate OOB rate: {e}")
            oob_rate = 0.0
        
        matrix_data.append({
            'query_id': query_id,
            'query_img': query_img,
            '3d_img': temp_3d_path,
            '2d_img': temp_2d_path,
            'sorted_imgs': sorted_imgs or [],
            'oob_rate': oob_rate,
            'prompt': scene_data.get('prompt', ''),
            'object_list': scene_data.get('object_list', [])
        })
        print(f"  Completed processing scene {i+1}/{len(data)}")
    
    # 创建矩阵图片
    print("Creating matrix image...")
    try:
        matrix_img = create_image_matrix(matrix_data)
        
        if matrix_img:
            # 保存到 top_n_gpt 文件夹
            if gpt_version:
                folder_name = f"top{top_n}_{gpt_version}"
            else:
                folder_name = f"top{top_n}"
            matrix_output_dir = os.path.join(output_dir, "html", folder_name)
            os.makedirs(matrix_output_dir, exist_ok=True)
            matrix_output_path = os.path.join(matrix_output_dir, "benchmark_matrix.png")
            matrix_img.save(matrix_output_path, dpi=(600, 600))  # 提高到600 DPI
            print(f"Benchmark matrix saved to: {matrix_output_path}")
            
            # 计算总体统计
            if matrix_data:
                total_oob_rate = sum(data['oob_rate'] for data in matrix_data) / len(matrix_data)
                print(f"Overall out-of-boundary rate: {total_oob_rate:.1%}")
        else:
            print("Failed to create matrix image")
            matrix_output_path = None
    except Exception as e:
        print(f"Error creating matrix image: {e}")
        matrix_output_path = None
    
    # 清理临时文件
    print("Cleaning up temporary files...")
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            print(f"Warning: Failed to remove {temp_file}: {e}")
    
    return matrix_output_path 