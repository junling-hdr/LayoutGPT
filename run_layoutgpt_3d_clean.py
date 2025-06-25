#!/usr/bin/env python3
"""
LayoutGPT 3D Scene Generation - Clean Version
使用 layout_modules 中的模块化功能
"""

import os
import json
import time
import argparse
import numpy as np
from tqdm import tqdm
from datetime import datetime

from layout_modules import *
from utils import write_json

# 参数解析
parser = argparse.ArgumentParser(prog='LayoutGPT for scene synthesis', 
                               description='Use GPTs to predict 3D layout for indoor scenes.')
parser.add_argument('--room', type=str, default='bedroom', choices=['bedroom','livingroom'])
parser.add_argument('--dataset_dir', type=str)
parser.add_argument('--gpt_type', type=str, default='gpt4', choices=['gpt3.5', 'gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini'])
parser.add_argument('--icl_type', type=str, default='k-similar', choices=['fixed-random', 'k-similar'])
parser.add_argument('--base_output_dir', type=str, default='./llm_output/3D/')
parser.add_argument('--K', type=int, default=8)
parser.add_argument('--gpt_input_length_limit', type=int, default=7000)
parser.add_argument('--unit', type=str, choices=['px', 'm', ''], default='px')
parser.add_argument("--n_iter", type=int, default=1)
parser.add_argument("--test", action='store_true')
parser.add_argument('--verbose', default=False, action='store_true')
parser.add_argument("--suffix", type=str, default="")
parser.add_argument("--normalize", action='store_true')
parser.add_argument("--regular_floor_plan", action='store_true')
parser.add_argument("--temperature", type=float, default=0.7)
parser.add_argument("--max_val_samples", type=int, default=None, 
                   help="Maximum number of validation samples to process")
parser.add_argument("--add_timestamp", action='store_true', default=True,
                   help="Add timestamp to output filenames")
parser.add_argument("--no_additional_furniture", action='store_true', default=False,
                   help="Add constraint to not allow additional furniture")
parser.add_argument("--no_overlapping_furniture", action='store_true', default=False,
                   help="Add constraint to prevent furniture overlapping")
args = parser.parse_args()


def main():
    """主函数"""
    print(f"Starting LayoutGPT 3D generation with {args.gpt_type}")
    
    # 处理后缀
    if args.regular_floor_plan:
        args.suffix += '_regular'

    # 设置输出目录
    args.output_dir = args.base_output_dir
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if args.add_timestamp else ""
    timestamp_suffix = f"_{timestamp}" if timestamp else ""
    
    # 输出文件名
    output_filename = os.path.join(args.output_dir, 
        f'{args.gpt_type}.{args.room}.{args.icl_type}.k_{args.K}.{args.unit}{args.suffix}{timestamp_suffix}.json')
    os.makedirs(os.path.join(args.output_dir, 'raw'), exist_ok=True)
    raw_output_filename = os.path.join(args.output_dir, 'raw', 
        f'raw_{args.gpt_type}.{args.room}.{args.icl_type}.k_{args.K}.{args.unit}{args.suffix}{timestamp_suffix}.json')

    # 加载数据集
    print("Loading dataset...")
    dataset = load_dataset(args)
    train_data = dataset['train_data']
    val_data = dataset['val_data']
    val_features = dataset['val_features']
    stats = dataset['stats']
    
    # 准备支持示例
    if args.icl_type == 'fixed-random':
        all_supporting_examples = list(train_data.values())
        supporting_examples = all_supporting_examples[:args.K]
        train_features = None
    elif args.icl_type == 'k-similar':
        supporting_examples = train_data
        train_features = load_features(dataset['meta_train_data'])
    
    # gpt prediction
    print(f"Starting GPT prediction for {len(val_data)} samples...")
    all_prediction_list = []
    all_responses = []
    top_k = args.K
    
    total_lines = []
    total_furnitures = []
    
    for val_id, val_example in tqdm(val_data.items(), desc="Processing validation samples"):
        # prepare supporting examples
        if args.icl_type == 'fixed-random':
            sorted_ids = []
            selected_supporting_examples = supporting_examples[:top_k]
        elif args.icl_type == 'k-similar':
            val_feature = val_features[val_id]
            sorted_ids = get_closest_room(train_features, val_feature)
            selected_supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]
        
        # build prompt
        prompt = build_prompt_for_val_example(val_example, selected_supporting_examples, args, stats)

        # call gpt api
        try:
            response = call_gpt_api(prompt, args, val_id)
            response['prompt'] = prompt
            all_responses.append(response)
            
            # process response
            predictions, n_lines, n_furnitures = process_all_iterations(
                response, args, val_id, val_example, sorted_ids, top_k
            )
            all_prediction_list.extend(predictions)
            total_lines.extend(n_lines)
            total_furnitures.extend(n_furnitures)
            
            # gpt-4 and o series need to limit speed
            if args.gpt_type in ['gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini']:
                time.sleep(3)
                
        except Exception as e:
            print(f"Error processing {val_id}: {e}")
            continue

    # 保存结果
    print("Saving results...")
    with open(raw_output_filename, 'w') as fout:
        json.dump(all_responses, fout, indent=4, sort_keys=True)

    with open(output_filename, 'w') as fout:
        json.dump(all_prediction_list, fout, indent=4, sort_keys=True)
    
    print(f'GPT-3 ({args.gpt_type}) prediction results written to {output_filename}')
    print(f"Average lines: {np.mean(total_lines):.2f}, Average furniture count: {np.mean(total_furnitures):.2f}")
    print("Generation completed successfully!")
    
    # Return results for GUI integration
    return {
        'output_file': output_filename,
        'timestamp': timestamp,
        'success': True
    }


if __name__ == '__main__':
    main() 