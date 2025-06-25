#!/usr/bin/env python3
"""
LayoutGPT Custom Prompt Generation
参考 run_layoutgpt_3d_clean.py 的结构，但使用用户自定义条件而不是验证数据集
"""

import os
import json
import time
import argparse
import numpy as np
from datetime import datetime

from layout_modules import *
from utils import write_json

# 参数解析 - 只保留custom需要的参数
parser = argparse.ArgumentParser(prog='LayoutGPT Custom Generation', 
                               description='Generate 3D layout from custom room description.')
parser.add_argument('--room', type=str, default='bedroom', choices=['bedroom','livingroom'])
parser.add_argument('--dataset_dir', type=str, default='./ATISS/data_output')
parser.add_argument('--gpt_type', type=str, default='gpt4', choices=['gpt3.5', 'gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini'])
parser.add_argument('--icl_type', type=str, default='k-similar', choices=['fixed-random', 'k-similar'])
parser.add_argument('--base_output_dir', type=str, default='./llm_output/custom/')
parser.add_argument('--K', type=int, default=8)
parser.add_argument('--gpt_input_length_limit', type=int, default=7000)
parser.add_argument('--unit', type=str, choices=['px', 'm', ''], default='px')
parser.add_argument("--n_iter", type=int, default=1)
parser.add_argument('--verbose', default=False, action='store_true')
parser.add_argument("--suffix", type=str, default="")
parser.add_argument("--normalize", action='store_true', default=True)
parser.add_argument("--regular_floor_plan", action='store_true', default=True)
parser.add_argument("--temperature", type=float, default=0.7)
parser.add_argument("--add_timestamp", action='store_true', default=True,
                   help="Add timestamp to output filenames")
parser.add_argument("--no_additional_furniture", action='store_true', default=False,
                   help="Add constraint to not allow additional furniture")
parser.add_argument("--no_overlapping_furniture", action='store_true', default=False,
                   help="Add constraint to prevent furniture overlapping")

# Custom特有的参数
parser.add_argument('--custom_condition', type=str, required=True, help='Custom room condition and description')
parser.add_argument('--preset_timestamp', type=str, default=None, 
                   help='Use preset timestamp instead of generating new one (for consistency with regular mode)')

args = parser.parse_args()


def main():
    """主函数 - 参考clean版本的结构"""
    print(f"Starting LayoutGPT Custom Generation with {args.gpt_type}")
    print(f"Custom condition: {args.custom_condition}")
    print(f"In-context learning: {args.icl_type}, K={args.K}")
    
    # 处理后缀
    if args.regular_floor_plan:
        args.suffix += '_regular'

    # 设置输出目录
    args.output_dir = args.base_output_dir
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 使用预设时间戳或生成新的时间戳
    if args.preset_timestamp:
        timestamp = args.preset_timestamp
        print(f"Using preset timestamp: {timestamp}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if args.add_timestamp else ""
    
    timestamp_suffix = f"_{timestamp}" if timestamp else ""
    
    # 生成输出文件名
    output_filename = os.path.join(args.output_dir, 
        f'custom_{args.gpt_type}.{args.room}.{args.icl_type}.k_{args.K}.{args.unit}{args.suffix}{timestamp_suffix}.json')
    os.makedirs(os.path.join(args.output_dir, 'raw'), exist_ok=True)
    raw_output_filename = os.path.join(args.output_dir, 'raw', 
        f'raw_custom_{args.gpt_type}.{args.room}.{args.icl_type}.k_{args.K}.{args.unit}{args.suffix}{timestamp_suffix}.json')

    # 加载数据集 - 但只用训练数据，不用验证数据
    print("Loading dataset...")
    dataset = load_dataset(args)
    train_data = dataset['train_data']
    stats = dataset['stats']
    
    print(f"Loaded {len(train_data)} training examples for in-context learning")
    
    # 准备支持示例 - 完全复用clean版本的逻辑
    if args.icl_type == 'fixed-random':
        all_supporting_examples = list(train_data.values())
        supporting_examples = all_supporting_examples[:args.K]
        train_features = None
    elif args.icl_type == 'k-similar':
        supporting_examples = train_data
        # 对于custom模式，使用基于尺寸的特征而不是图像特征
        train_features = load_features(dataset['meta_train_data'], floor_plan=False)
    
    # 构建自定义验证样本 - 替代原来的val_data
    custom_val_id = f'custom_{timestamp}'
    custom_val_example = [args.custom_condition]  # 只有条件，没有layout
    
    # 为k-similar从用户条件中提取特征
    val_feature = None
    if args.icl_type == 'k-similar' and train_features:
        # 从用户自定义条件中提取房间尺寸作为特征
        import re
        # 解析房间尺寸，例如 "max length 273px, max width 256px"
        length_match = re.search(r'max length (\d+)', args.custom_condition)
        width_match = re.search(r'max width (\d+)', args.custom_condition)
        
        if length_match and width_match:
            room_length = float(length_match.group(1))
            room_width = float(width_match.group(1))
            # 创建用户房间特征向量 [length, width]
            val_feature = np.array([room_length, room_width])
            print(f"Extracted room feature from user input: length={room_length}, width={room_width}")
            
            sorted_ids = get_closest_room(train_features, val_feature)
            selected_supporting_examples = [supporting_examples[id] for id in sorted_ids[:args.K]]
            top_k = args.K
        else:
            print("Warning: Could not extract room dimensions from custom condition, falling back to fixed-random")
            sorted_ids = []
            selected_supporting_examples = list(supporting_examples.values())[:args.K]
            top_k = args.K
    else:
        sorted_ids = []
        selected_supporting_examples = list(supporting_examples.values())[:args.K]
        top_k = args.K
    
    # 构建prompt - 复用clean版本的逻辑
    if args.verbose:
        print(f"\nDEBUG: About to build prompt with constraints:")
        print(f"  args.no_additional_furniture = {getattr(args, 'no_additional_furniture', 'NOT SET')}")
        print(f"  args.no_overlapping_furniture = {getattr(args, 'no_overlapping_furniture', 'NOT SET')}")
    
    prompt = build_prompt_for_val_example(custom_val_example, selected_supporting_examples, args, stats)
    
    if args.verbose:
        print(f"\n{'='*60}")
        print(f"VERBOSE OUTPUT")
        print(f"{'='*60}")
        print(f"Custom Query ID: {custom_val_id}")
        print(f"ICL Type: {args.icl_type}")
        print(f"K Value: {args.K}")
        print(f"Top-K Examples Used: {top_k}")
        
        # 显示约束设置
        print(f"\nCONSTRAINT SETTINGS:")
        print(f"  No Additional Furniture: {getattr(args, 'no_additional_furniture', False)}")
        print(f"  No Overlapping Furniture: {getattr(args, 'no_overlapping_furniture', False)}")
        
        if args.icl_type == 'k-similar' and val_feature is not None:
            print(f"\nUser Room Feature: {val_feature}")
            print(f"Selected Similar Training IDs: {sorted_ids[:top_k]}")
        
        print(f"\nSelected Supporting Examples Count: {len(selected_supporting_examples)}")
        
        # 显示选中的示例信息
        for i, example in enumerate(selected_supporting_examples):
            print(f"\n--- Supporting Example {i+1} ---")
            condition_lines = example[0].split('\n')
            for line in condition_lines[:3]:  # 只显示前3行条件
                if line.strip():
                    print(f"  {line}")
            layout_lines = example[1].split('\n')
            furniture_count = len([line for line in layout_lines if line.strip() and not line.startswith('Layout:')])
            print(f"  Furniture items: {furniture_count}")
        
        print(f"\n{'='*60}")
        print(f"GENERATED PROMPT:")
        print(f"{'='*60}")
        
        # 检查约束是否被添加
        constraints_found = []
        if hasattr(args, 'no_additional_furniture') and args.no_additional_furniture:
            constraints_found.append("[+] No additional furniture constraint")
        if hasattr(args, 'no_overlapping_furniture') and args.no_overlapping_furniture:
            constraints_found.append("[+] No overlapping furniture constraint")
        
        if constraints_found:
            print("ACTIVE CONSTRAINTS:")
            for constraint in constraints_found:
                print(f"  {constraint}")
            print()
        
        if isinstance(prompt, list):
            # ChatGPT format (messages)
            for i, msg in enumerate(prompt):
                print(f"Message {i+1} ({msg['role']}):")
                content = msg['content']
                
                # 对于系统消息，显示更多内容以包含约束
                if msg['role'] == 'system':
                    # 检查并高亮约束文本
                    if "CONSTRAINT:" in content or "IMPORTANT:" in content:
                        print("*** CONSTRAINT DETECTED IN SYSTEM MESSAGE ***")
                    if len(content) > 1500:
                        print(f"{content[:1500]}...")
                    else:
                        print(content)
                else:
                    if len(content) > 500:
                        print(f"{content[:500]}...")
                    else:
                        print(content)
                print("-" * 40)
        else:
            # GPT-3 format (string)
            # 检查并高亮约束文本
            if "CONSTRAINT:" in prompt or "IMPORTANT:" in prompt:
                print("*** CONSTRAINT DETECTED IN PROMPT ***")
            # 显示更多内容以包含约束
            if len(prompt) > 2000:
                print(f"{prompt[:2000]}...")
            else:
                print(prompt)
        print(f"{'='*60}\n")
    
    # GPT预测 - 优化版本，一次性调用获取所有迭代结果
    print("Calling GPT API...")
    all_prediction_list = []
    all_responses = []

    print(f"Generating {args.n_iter} iterations in single API call...")
    
    try:
        # 一次性调用GPT API获取所有迭代结果
        response = call_gpt_api(prompt, args, custom_val_id)
        response['prompt'] = prompt
        all_responses.append(response)
        
        if args.verbose:
            print(f"{'='*60}")
            print(f"GPT API RESPONSE ({args.n_iter} iterations):")
            print(f"{'='*60}")
            for i, choice in enumerate(response.get('choices', [])[:args.n_iter]):
                raw_response = choice.get('message', {}).get('content', '') or choice.get('text', '')
                print(f"Iteration {i+1} Response:")
                if len(raw_response) > 400:
                    print(f"{raw_response[:400]}...")
                else:
                    print(raw_response)
                print("-" * 40)
            print(f"{'='*60}\n")
        
        # 处理所有迭代的响应
        predictions, n_lines, n_furnitures = process_all_iterations(
            response, args, custom_val_id, custom_val_example, sorted_ids, top_k
        )
        
        # 为每个预测添加迭代信息
        for i, prediction in enumerate(predictions):
            prediction['iteration'] = i + 1
            prediction['iteration_id'] = f"{custom_val_id}_iter{i + 1}"
        
        all_prediction_list.extend(predictions)
        
    except Exception as e:
        print(f"Error in API call: {e}")
        return {'success': False}
    
    # 为所有预测添加额外信息
    for prediction in all_prediction_list:
        prediction['custom_condition'] = args.custom_condition
        prediction['gpt_type'] = args.gpt_type
        prediction['temperature'] = args.temperature
        prediction['unit'] = args.unit
        prediction['top_k'] = args.K
        prediction['icl_type'] = args.icl_type
        prediction['generated_at'] = datetime.now().isoformat()
        prediction['is_custom'] = True
        prediction['timestamp'] = timestamp
    
    # 处理所有迭代的结果
    if args.verbose and all_prediction_list:
        print(f"{'='*60}")
        print(f"FINAL RESULTS SUMMARY:")
        print(f"{'='*60}")
        print(f"Total iterations: {args.n_iter}")
        print(f"Total predictions: {len(all_prediction_list)}")
        
        # 显示每个迭代的统计
        for i in range(args.n_iter):
            iteration_predictions = [p for p in all_prediction_list if p.get('iteration', 1) == i + 1]
            if iteration_predictions:
                pred = iteration_predictions[0]
                print(f"\nIteration {i + 1}:")
                print(f"  Query ID: {pred.get('query_id', 'N/A')}")
                print(f"  Object count: {len(pred.get('object_list', []))}")
                print(f"  Room dimensions: {pred.get('room_length', 'N/A')} x {pred.get('room_width', 'N/A')}")
        print(f"{'='*60}\n")

    # 保存结果 - 复用clean版本的逻辑
    print("Saving results...")
    with open(raw_output_filename, 'w') as fout:
        json.dump(all_responses, fout, indent=4, sort_keys=True)

    with open(output_filename, 'w') as fout:
        json.dump(all_prediction_list, fout, indent=4, sort_keys=True)
    
    print(f'Custom generation results written to {output_filename}')
    if all_prediction_list:
        print(f"Generated {len(all_prediction_list[0]['object_list'])} furniture items")
        print(f"Used {len(sorted_ids[:top_k])} in-context examples")
    print("Custom generation completed successfully!")
    
    # Return results for GUI integration
    return {
        'output_file': output_filename,
        'timestamp': timestamp,
        'success': True
    }


if __name__ == '__main__':
    result = main()
    if not result.get('success', False):
        exit(1) 