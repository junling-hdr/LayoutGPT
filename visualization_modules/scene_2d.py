import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from .utils import parse_room_size, get_furniture_color


def create_2d_visualization(scene_data):
    """创建 2D 俯视图可视化，显示超出边界的家具，包含颜色标签"""
    prompt = scene_data.get('prompt', '')
    object_list = scene_data.get('object_list', [])
    room_length, room_width = parse_room_size(prompt)
    
    # 计算所有家具的边界，确保图片能显示超出房间的部分
    all_x_coords = [0, room_length]
    all_y_coords = [0, room_width]
    
    for furniture_type, obj_data in object_list:
        length = obj_data['length']
        width = obj_data['width']
        left = obj_data['left']
        top = obj_data['top']
        
        x_min, x_max = left - length/2, left + length/2
        y_min, y_max = top - width/2, top + width/2
        
        all_x_coords.extend([x_min, x_max])
        all_y_coords.extend([y_min, y_max])
    
    # 设置图片范围，包含所有家具
    margin = 30
    x_min, x_max = min(all_x_coords) - margin, max(all_x_coords) + margin
    y_min, y_max = min(all_y_coords) - margin, max(all_y_coords) + margin
    
    # 增加图片大小和DPI以提高清晰度
    fig, (ax, legend_ax) = plt.subplots(1, 2, figsize=(20, 12), gridspec_kw={'width_ratios': [4, 1]})
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')
    
    # 绘制房间边界（实线）
    room_rect = patches.Rectangle((0, 0), room_length, room_width, 
                                 linewidth=4, edgecolor='black', facecolor='lightgray', alpha=0.3)
    ax.add_patch(room_rect)
    
    # 添加房间边界标注
    ax.text(room_length/2, -margin/3, f'Room: {room_length}×{room_width}px', 
           ha='center', va='top', fontsize=16, weight='bold')
    
    # 统计家具类型和颜色
    furniture_colors = {}
    furniture_counts = {}
    oob_count = 0
    
    # 绘制家具
    for furniture_type, obj_data in object_list:
        length = obj_data['length']
        width = obj_data['width']
        left = obj_data['left']
        top = obj_data['top']
        
        x = left - length/2
        y = top - width/2
        
        # 检查是否超出边界
        x_min_furn, x_max_furn = left - length/2, left + length/2
        y_min_furn, y_max_furn = top - width/2, top + width/2
        is_oob = (x_min_furn < 0 or x_max_furn > room_length or 
                 y_min_furn < 0 or y_max_furn > room_width)
        
        if is_oob:
            oob_count += 1
        
        color = get_furniture_color(furniture_type)
        furniture_colors[furniture_type] = color
        furniture_counts[furniture_type] = furniture_counts.get(furniture_type, 0) + 1
        
        # 超出边界的家具用红色边框
        edge_color = 'red' if is_oob else 'darkgray'
        edge_width = 4 if is_oob else 3  # 增加边框宽度
        
        furniture_rect = patches.Rectangle((x, y), length, width,
                                         linewidth=edge_width, edgecolor=edge_color, 
                                         facecolor=color, alpha=0.8)
        ax.add_patch(furniture_rect)
        
        # 添加家具标签，使用更清晰的字体
        display_name = furniture_type.replace('_', '\n')
        ax.text(left, top, display_name, 
               ha='center', va='center', fontsize=12, weight='bold',  # 增大字体
               bbox=dict(boxstyle="round,pad=0.4", facecolor='white', alpha=0.9))  # 增加padding和不透明度
    
    # 计算并显示 OOB 率
    oob_rate = oob_count / len(object_list) if object_list else 0
    
    ax.set_title(f"2D Layout: {scene_data.get('query_id', 'Unknown')}\nOOB Rate: {oob_rate:.1%} ({oob_count}/{len(object_list)})", 
                fontsize=18, weight='bold')
    ax.set_xlabel("X (px)", fontsize=14)
    ax.set_ylabel("Y (px)", fontsize=14)
    ax.grid(True, alpha=0.3)
    
    # 在右侧创建颜色标签图例
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)
    legend_ax.set_title("Furniture Colors & Counts", fontsize=14, weight='bold', pad=20)
    legend_ax.axis('off')
    
    # 按数量排序显示图例
    sorted_furniture = sorted(furniture_counts.items(), key=lambda x: x[1], reverse=True)
    
    y_pos = 0.95
    y_step = 0.06
    
    for furniture_type, count in sorted_furniture:
        if y_pos < 0.05:  # 如果空间不够，停止显示
            legend_ax.text(0.1, y_pos, f"... +{len(sorted_furniture) - sorted_furniture.index((furniture_type, count))} more", 
                          fontsize=10, color='gray')
            break
            
        color = furniture_colors[furniture_type]
        display_name = furniture_type.replace('_', ' ').title()
        
        # 绘制颜色方块
        color_rect = patches.Rectangle((0.05, y_pos-0.02), 0.08, 0.04, 
                                     facecolor=color, edgecolor='black', linewidth=1)
        legend_ax.add_patch(color_rect)
        
        # 添加文字标签
        legend_ax.text(0.18, y_pos, f"{display_name} ({count})", 
                      fontsize=12, va='center', weight='bold')
        
        y_pos -= y_step
    
    # 添加总体统计
    legend_ax.text(0.05, 0.02, f"Total: {len(object_list)} items\nOOB: {oob_count} items ({oob_rate:.1%})", 
                  fontsize=13, weight='bold',
                  bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.8))
    
    # 在主图中添加传统图例
    legend_elements = [
        Line2D([0], [0], color='darkgray', lw=2, label='In Boundary'),
        Line2D([0], [0], color='red', lw=3, label='Out of Boundary'),
        patches.Rectangle((0, 0), 1, 1, facecolor='lightgray', alpha=0.3, label='Room Area')
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
    
    plt.tight_layout()
    return fig 