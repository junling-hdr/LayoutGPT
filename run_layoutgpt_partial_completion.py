#!/usr/bin/env python3
"""
LayoutGPT Partial Scene Completion
基于论文中提到的自回归解码机制，实现部分场景补全功能
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from layout_modules.data_loader import load_dataset, get_closest_room
from layout_modules.prompt_builder import build_partial_completion_prompt
from layout_modules.gpt_client import call_gpt_api
from layout_modules.layout_parser import parse_gpt_response
from utils import write_json


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='LayoutGPT Partial Scene Completion')
    
    # 基本参数
    parser.add_argument('--room', type=str, default='bedroom', choices=['bedroom', 'livingroom'],
                       help='房间类型')
    parser.add_argument('--gpt_type', type=str, default='gpt4',
                       choices=['gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini'],
                       help='GPT模型类型')
    parser.add_argument('--dataset_dir', type=str, default='./ATISS/data_output',
                       help='数据集目录')
    parser.add_argument('--base_output_dir', type=str, default='./llm_output/partial_completion/',
                       help='输出基础目录')
    
    # ICL参数  
    parser.add_argument('--icl_type', type=str, default='k-similar',
                       choices=['fixed-random', 'k-similar'], help='上下文学习类型')
    parser.add_argument('--K', type=int, default=4, help='上下文示例数量')
    
    # 部分场景补全特定参数
    parser.add_argument('--partial_layout', type=str, required=True,
                       help='已有的部分家具布局（CSS格式）')
    parser.add_argument('--room_condition', type=str, required=True,
                       help='房间条件描述')
    
    # 生成参数
    parser.add_argument('--temperature', type=float, default=0.8, help='生成温度')
    parser.add_argument('--n_iter', type=int, default=3, help='迭代次数')
    parser.add_argument('--unit', type=str, default='px', choices=['px', 'm', ''],
                       help='单位')
    
    # 约束参数
    parser.add_argument('--no_overlapping_furniture', action='store_true',
                       help='避免家具重叠')
    parser.add_argument('--maintain_symmetry', action='store_true',
                       help='保持视觉对称性')
    parser.add_argument('--enhance_functionality', action='store_true',
                       help='增强功能区域布局')
    
    # 其他参数
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--add_timestamp', action='store_true', help='添加时间戳')
    parser.add_argument('--regular_floor_plan', action='store_true', help='规则平面图')
    parser.add_argument('--normalize', action='store_true', help='归一化')
    parser.add_argument('--gpt_input_length_limit', type=int, default=6000, help='GPT输入长度限制')
    
    return parser.parse_args()


def analyze_partial_layout(partial_layout):
    """分析部分布局，提取现有家具信息"""
    furniture_info = []
    layout_lines = partial_layout.strip().split('\n')
    
    for line in layout_lines:
        line = line.strip()
        if line and '{' in line and '}' in line:
            # 解析家具类型
            furniture_type = line.split('{')[0].strip()
            
            # 解析属性
            properties = {}
            prop_part = line.split('{')[1].split('}')[0]
            for prop in prop_part.split(';'):
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    properties[key.strip()] = value.strip()
            
            furniture_info.append({
                'type': furniture_type,
                'properties': properties,
                'raw_line': line
            })
    
    return furniture_info


def suggest_completion_furniture(existing_furniture, room_type='bedroom'):
    """基于现有家具和房间类型，建议补全的家具"""
    existing_types = [f['type'] for f in existing_furniture]
    
    # 房间类型对应的常见家具配置
    common_configurations = {
        'bedroom': {
            'core_furniture': ['double_bed', 'single_bed'],
            'symmetry_pairs': {
                'nightstand': 2,  # 床头柜通常成对
                'floor_lamp': 2,  # 落地灯可以对称
            },
            'functional_groups': {
                'workspace': ['desk', 'chair'],
                'storage': ['wardrobe', 'cabinet'],
                'lighting': ['ceiling_lamp', 'pendant_lamp'],
                'seating': ['armchair', 'stool']
            }
        },
        'livingroom': {
            'core_furniture': ['sofa'],
            'symmetry_pairs': {
                'armchair': 2,
                'floor_lamp': 2,
            },
            'functional_groups': {
                'entertainment': ['tv_stand', 'coffee_table'],
                'storage': ['bookshelf', 'cabinet'],
                'lighting': ['ceiling_lamp', 'floor_lamp'],
                'additional_seating': ['chair', 'stool']
            }
        }
    }
    
    config = common_configurations.get(room_type, common_configurations['bedroom'])
    suggestions = []
    
    # 检查对称性建议
    for furniture_type, recommended_count in config['symmetry_pairs'].items():
        current_count = existing_types.count(furniture_type)
        if 0 < current_count < recommended_count:
            suggestions.append({
                'type': 'symmetry',
                'furniture': furniture_type,
                'reason': f'建议添加{recommended_count - current_count}个{furniture_type}以保持视觉对称',
                'count': recommended_count - current_count
            })
    
    # 检查功能组建议
    for group_name, group_furniture in config['functional_groups'].items():
        has_any = any(ftype in existing_types for ftype in group_furniture)
        missing = [ftype for ftype in group_furniture if ftype not in existing_types]
        
        if has_any and missing:
            for missing_furniture in missing:
                suggestions.append({
                    'type': 'functional',
                    'furniture': missing_furniture,  
                    'reason': f'完善{group_name}功能区域',
                    'count': 1
                })
    
    return suggestions


def main():
    args = parse_args()
    
    print(f"开始LayoutGPT部分场景补全...")
    print(f"房间类型: {args.room}")
    print(f"GPT模型: {args.gpt_type}")
    print(f"上下文学习: {args.icl_type} (K={args.K})")
    
    # 设置输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if args.add_timestamp else ""
    output_dir = os.path.join(args.base_output_dir, args.room)
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建临时输出目录
    temp_dir = os.path.join(output_dir, 'tmp', args.gpt_type.replace('.', '_').replace('-', '_'))
    os.makedirs(temp_dir, exist_ok=True)
    args.output_dir = output_dir
    
    # 加载数据集
    print("加载数据集...")
    try:
        dataset = load_dataset(args)
        stats = dataset['stats']
        supporting_examples = dataset['train_examples']
        print(f"加载完成: {len(supporting_examples)}个训练示例")
    except Exception as e:
        print(f"数据集加载失败: {e}")
        return
    
    # 分析部分布局
    print("分析部分布局...")
    existing_furniture = analyze_partial_layout(args.partial_layout)
    print(f"发现现有家具: {[f['type'] for f in existing_furniture]}")
    
    # 建议补全家具
    completion_suggestions = suggest_completion_furniture(existing_furniture, args.room)
    if completion_suggestions:
        print("补全建议:")
        for suggestion in completion_suggestions:
            print(f"  - {suggestion['furniture']} ({suggestion['type']}): {suggestion['reason']}")
    
    # 构建提示
    print("构建GPT提示...")
    try:
        prompt, sorted_ids = build_partial_completion_prompt(
            room_condition=args.room_condition,
            partial_layout=args.partial_layout,
            supporting_examples=supporting_examples,
            args=args,
            stats=stats
        )
        
        if args.verbose:
            print("构建的提示预览:")
            if isinstance(prompt, list):
                for i, msg in enumerate(prompt[-2:]):  # 显示最后两条消息
                    print(f"  消息{i}: {msg['role']} - {msg['content'][:200]}...")
            else:
                print(f"  提示内容: {prompt[:500]}...")
                
    except Exception as e:
        print(f"提示构建失败: {e}")
        return
    
    # 调用GPT API
    print("调用GPT API生成补全布局...")
    try:
        val_id = f"partial_completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        response = call_gpt_api(prompt, args, val_id)
        
        if args.verbose:
            print("GPT响应预览:")
            if 'choices' in response and response['choices']:
                choice = response['choices'][0]
                content = choice.get('text', choice.get('message', {}).get('content', ''))
                print(f"  生成内容: {content[:300]}...")
                
    except Exception as e:
        print(f"GPT API调用失败: {e}")
        return
    
    # 解析响应
    print("解析GPT响应...")
    try:
        predicted_objects = parse_gpt_response(response, args)
        print(f"解析得到 {len(predicted_objects)} 个家具对象")
        
        if args.verbose:
            for i, (furniture_type, bbox) in enumerate(predicted_objects):
                print(f"  家具{i+1}: {furniture_type} - {bbox}")
                
    except Exception as e:
        print(f"响应解析失败: {e}")
        return
    
    # 构建完整的结果
    completion_result = {
        'query_id': val_id,
        'room_type': args.room,
        'gpt_model': args.gpt_type,
        'task_type': 'partial_completion',
        'input': {
            'room_condition': args.room_condition,
            'partial_layout': args.partial_layout,
            'existing_furniture': [f['type'] for f in existing_furniture],
        },
        'completion_suggestions': completion_suggestions,
        'generated_furniture': predicted_objects,
        'raw_gpt_response': response['choices'][0].get('text', response['choices'][0].get('message', {}).get('content', '')),
        'sorted_ids': sorted_ids[:args.K] if sorted_ids else [],
        'generation_params': {
            'temperature': args.temperature,
            'n_iter': args.n_iter,
            'icl_type': args.icl_type,
            'K': args.K,
        },
        'timestamp': datetime.now().isoformat(),
    }
    
    # 保存结果
    output_filename = f"partial_completion_{args.gpt_type}_{args.room}"
    if timestamp:
        output_filename += f"_{timestamp}"
    output_filename += ".json"
    
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        write_json(output_path, completion_result)
        print(f"✅ 部分场景补全完成!")
        print(f"结果保存至: {output_path}")
        
        # 输出补全摘要
        print("\n📋 补全摘要:")
        print(f"原有家具: {len(existing_furniture)}件")
        print(f"新增家具: {len(predicted_objects)}件")
        print(f"补全建议采纳: {len([s for s in completion_suggestions if any(s['furniture'] in obj[0] for obj in predicted_objects)])}/{len(completion_suggestions)}")
        
    except Exception as e:
        print(f"结果保存失败: {e}")
        return


if __name__ == "__main__":
    main() 