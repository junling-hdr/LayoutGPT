import plotly.graph_objects as go
import numpy as np
from .utils import parse_room_size, get_furniture_color, find_rendered_image


def create_room_walls(room_length, room_width, wall_height=250):
    """Create room walls"""
    walls = []
    
    # Floor
    floor_mesh = go.Mesh3d(
        x=[0, room_length, room_length, 0],
        y=[0, 0, room_width, room_width],
        z=[0, 0, 0, 0],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color='#F8F9FA',
        opacity=0.8,
        name='Floor',
        showlegend=True,
        hovertemplate="<b>Room Floor</b><br>Size: %{x} x %{y} px<extra></extra>"
    )
    walls.append(floor_mesh)
    
    # Ceiling
    ceiling_mesh = go.Mesh3d(
        x=[0, room_length, room_length, 0],
        y=[0, 0, room_width, room_width],
        z=[wall_height, wall_height, wall_height, wall_height],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color='#FFFFFF',
        opacity=0.3,
        name='Ceiling',
        showlegend=True,
        hovertemplate="<b>Ceiling</b><extra></extra>"
    )
    walls.append(ceiling_mesh)
    
    # Four walls
    wall_color = '#E9ECEF'
    wall_opacity = 0.4
    
    # Front wall (y=0)
    front_wall = go.Mesh3d(
        x=[0, room_length, room_length, 0],
        y=[0, 0, 0, 0],
        z=[0, 0, wall_height, wall_height],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color=wall_color,
        opacity=wall_opacity,
        name='Front Wall',
        showlegend=False,
        hovertemplate="<b>Front Wall</b><extra></extra>"
    )
    walls.append(front_wall)
    
    # Back wall (y=room_width)
    back_wall = go.Mesh3d(
        x=[0, room_length, room_length, 0],
        y=[room_width, room_width, room_width, room_width],
        z=[0, 0, wall_height, wall_height],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color=wall_color,
        opacity=wall_opacity,
        name='Back Wall',
        showlegend=False,
        hovertemplate="<b>Back Wall</b><extra></extra>"
    )
    walls.append(back_wall)
    
    # Left wall (x=0)
    left_wall = go.Mesh3d(
        x=[0, 0, 0, 0],
        y=[0, room_width, room_width, 0],
        z=[0, 0, wall_height, wall_height],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color=wall_color,
        opacity=wall_opacity,
        name='Left Wall',
        showlegend=False,
        hovertemplate="<b>Left Wall</b><extra></extra>"
    )
    walls.append(left_wall)
    
    # Right wall (x=room_length)
    right_wall = go.Mesh3d(
        x=[room_length, room_length, room_length, room_length],
        y=[0, room_width, room_width, 0],
        z=[0, 0, wall_height, wall_height],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color=wall_color,
        opacity=wall_opacity,
        name='Right Wall',
        showlegend=False,
        hovertemplate="<b>Right Wall</b><extra></extra>"
    )
    walls.append(right_wall)
    
    return walls


def create_3d_furniture_box(obj_data, furniture_type):
    """Create solid 3D furniture box"""
    length = obj_data['length']
    width = obj_data['width'] 
    height = obj_data['height']
    left = obj_data['left']
    top = obj_data['top']
    depth = obj_data['depth']
    
    # Calculate box boundaries
    x_min, x_max = left - length/2, left + length/2
    y_min, y_max = top - width/2, top + width/2
    z_min, z_max = depth - height/2, depth + height/2
    
    # Create 8 vertices of the box
    vertices_x = [x_min, x_max, x_max, x_min, x_min, x_max, x_max, x_min]
    vertices_y = [y_min, y_min, y_max, y_max, y_min, y_min, y_max, y_max]
    vertices_z = [z_min, z_min, z_min, z_min, z_max, z_max, z_max, z_max]
    
    # Define 12 triangular faces of the box (each face composed of 2 triangles)
    faces_i = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 0, 0, 1, 1, 2, 2, 3, 3]
    faces_j = [1, 3, 2, 5, 3, 6, 0, 7, 5, 7, 6, 4, 7, 4, 6, 5, 4, 1, 5, 2, 6, 3, 7, 0]
    faces_k = [3, 2, 5, 6, 6, 7, 7, 4, 7, 6, 4, 5, 4, 6, 5, 4, 1, 5, 2, 6, 3, 7, 0, 4]
    
    color = get_furniture_color(furniture_type)
    
    # Create 3D mesh
    furniture_mesh = go.Mesh3d(
        x=vertices_x,
        y=vertices_y,
        z=vertices_z,
        i=faces_i,
        j=faces_j,
        k=faces_k,
        color=color,
        opacity=0.8,
        name=furniture_type,
        showlegend=True,
        hovertemplate=f"<b>{furniture_type}</b><br>" +
                     f"Position: ({obj_data['left']:.1f}, {obj_data['top']:.1f}, {obj_data['depth']:.1f})<br>" +
                     f"Size: {obj_data['length']:.1f}×{obj_data['width']:.1f}×{obj_data['height']:.1f}<br>" +
                     f"Orientation: {obj_data['orientation']}°<extra></extra>",
        # Add border lines
        contour=dict(show=True, color='rgba(0,0,0,0.3)', width=2)
    )
    
    return furniture_mesh, (left, top, depth)


def calculate_scene_bounds(room_length, room_width, object_list, wall_height=250):
    """Calculate scene boundaries, including all objects (even those outside the room)"""
    min_x, max_x = 0, room_length
    min_y, max_y = 0, room_width
    min_z, max_z = 0, wall_height
    
    # Check boundaries of all furniture
    for furniture_type, obj_data in object_list:
        length = obj_data['length']
        width = obj_data['width']
        height = obj_data['height']
        left = obj_data['left']
        top = obj_data['top']
        depth = obj_data['depth']
        
        x_min, x_max = left - length/2, left + length/2
        y_min, y_max = top - width/2, top + width/2
        z_min, z_max = depth - height/2, depth + height/2
        
        min_x = min(min_x, x_min)
        max_x = max(max_x, x_max)
        min_y = min(min_y, y_min)
        max_y = max(max_y, y_max)
        min_z = min(min_z, z_min)
        max_z = max(max_z, z_max)
    
    # Add some margin
    margin = 50
    return {
        'x_range': [min_x - margin, max_x + margin],
        'y_range': [min_y - margin, max_y + margin],
        'z_range': [min_z - margin, max_z + margin]
    }


def visualize_scene(scene_data, scene_id=None, image_dir="./ATISS/data_output"):
    """Visualize single scene, 并返回图片路径"""
    fig = go.Figure()
    # Get scene information
    if scene_id is None:
        scene_id = scene_data.get('query_id', 'Unknown')
    prompt = scene_data.get('prompt', '')
    object_list = scene_data.get('object_list', [])
    # Parse room dimensions
    room_length, room_width = parse_room_size(prompt)
    wall_height = 250
    print(f"Visualizing scene: {scene_id}")
    print(f"Room info: {prompt.strip()}")
    print(f"Room size: {room_length} x {room_width} px")
    print(f"Furniture count: {len(object_list)}")
    # Calculate scene boundaries (including objects outside the room)
    bounds = calculate_scene_bounds(room_length, room_width, object_list, wall_height)
    # Add room walls
    walls = create_room_walls(room_length, room_width, wall_height)
    for wall in walls:
        fig.add_trace(wall)
    # Create 3D solid boxes for each furniture
    furniture_types_added = set()  # Control legend display
    for i, (furniture_type, obj_data) in enumerate(object_list):
        furniture_mesh, center = create_3d_furniture_box(obj_data, furniture_type)
        # Control legend display (show each furniture type only once)
        show_legend = furniture_type not in furniture_types_added
        if show_legend:
            furniture_types_added.add(furniture_type)
            furniture_mesh.showlegend = True
        else:
            furniture_mesh.showlegend = False
            furniture_mesh.name = ""
        fig.add_trace(furniture_mesh)
        # Add furniture center point labels with better visibility
        fig.add_trace(go.Scatter3d(
            x=[center[0]],
            y=[center[1]], 
            z=[center[2]],
            mode='markers+text',
            marker=dict(size=10, color='black', opacity=1.0, symbol='circle', 
                       line=dict(color='white', width=3)),
            text=[furniture_type.replace('_', ' ').title()],
            textposition="middle center",
            textfont=dict(size=14, color='black', family='Arial Black'),
            showlegend=False,
            hovertemplate=f"<b>{furniture_type}</b><br>" +
                        f"Position: ({obj_data['left']:.1f}, {obj_data['top']:.1f}, {obj_data['depth']:.1f})<br>" +
                        f"Size: {obj_data['length']:.1f}×{obj_data['width']:.1f}×{obj_data['height']:.1f}<br>" +
                        f"Orientation: {obj_data['orientation']}°<extra></extra>"
        ))
    # Process prompt for better display
    prompt_lines = prompt.strip().split('\n')
    formatted_prompt = '<br>'.join([line.strip() for line in prompt_lines if line.strip()])
    # Set layout
    fig.update_layout(
        title=dict(
            text=f"3D Scene Layout: {scene_id}<br><span style='font-size:12px; color:#666;'>Room Size: {room_length} x {room_width} px (Wall Height: {wall_height}px)</span>",
            x=0.5,
            font=dict(size=20)
        ),
        scene=dict(
            xaxis_title="X (left) - px",
            yaxis_title="Y (top) - px", 
            zaxis_title="Z (depth) - px",
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.5),
                up=dict(x=0, y=0, z=1)
            ),
            xaxis=dict(
                range=bounds['x_range'],
                backgroundcolor='rgba(240,240,240,0.8)',
                gridcolor='rgba(255,255,255,0.8)',
                showbackground=True,
                zerolinecolor='rgba(255,255,255,0.8)'
            ),
            yaxis=dict(
                range=bounds['y_range'],
                backgroundcolor='rgba(240,240,240,0.8)',
                gridcolor='rgba(255,255,255,0.8)',
                showbackground=True,
                zerolinecolor='rgba(255,255,255,0.8)'
            ),
            zaxis=dict(
                range=bounds['z_range'],
                backgroundcolor='rgba(240,240,240,0.8)',
                gridcolor='rgba(255,255,255,0.8)',
                showbackground=True,
                zerolinecolor='rgba(255,255,255,0.8)'
            ),
            # Add lighting effects
            bgcolor='rgba(255,255,255,1.0)'
        ),
        width=1200,
        height=900,
        margin=dict(l=20, r=20, b=180, t=120),
        # Improve overall color scheme
        paper_bgcolor='white',
        plot_bgcolor='white',
        # Add prompt information as annotation
        annotations=[
            dict(
                text=f"<b>Scene Prompt:</b><br>{formatted_prompt}",
                xref="paper", yref="paper",
                x=0, y=-0.12,
                xanchor='left', yanchor='top',
                showarrow=False,
                font=dict(size=12, color='#333'),
                bgcolor='rgba(248,249,250,0.9)',
                bordercolor='rgba(200,200,200,0.8)',
                borderwidth=1,
                width=1160
            )
        ]
    )
    # Print information about objects outside room boundaries
    out_of_bounds_objects = []
    for furniture_type, obj_data in object_list:
        length = obj_data['length']
        width = obj_data['width']
        left = obj_data['left']
        top = obj_data['top']
        x_min, x_max = left - length/2, left + length/2
        y_min, y_max = top - width/2, top + width/2
        if x_min < 0 or x_max > room_length or y_min < 0 or y_max > room_width:
            out_of_bounds_objects.append(furniture_type)
    if out_of_bounds_objects:
        print(f"Notice: The following furniture extends beyond room boundaries: {', '.join(out_of_bounds_objects)}")
    # 新增：返回图片路径
    query_id = scene_data.get('query_id', None)
    sorted_ids = scene_data.get('sorted_ids', [])
    # 从 prompt 或 query_id 猜测 room 关键词
    room_keyword = "bedroom" if "bedroom" in prompt.lower() or (query_id and "bedroom" in query_id.lower()) else "livingroom"
    query_img = find_rendered_image(image_dir, query_id, room_keyword) if query_id else None
    sorted_imgs = [find_rendered_image(image_dir, sid, room_keyword) for sid in sorted_ids]
    return fig, query_img, sorted_imgs 