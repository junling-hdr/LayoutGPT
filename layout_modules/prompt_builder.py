from transformers import GPT2TokenizerFast
from .data_loader import get_closest_room

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


def create_prompt(sample):
    """创建单个提示"""
    return sample[0] + sample[1] + "\n\n"


def build_prompt_for_val_example(val_example, supporting_examples, args, stats):
    """为验证样本构建提示 - 根据GPT类型选择合适的prompt构建函数"""
    
    # 创建一个临时的args副本，强制使用fixed-random模式
    # 因为supporting_examples已经在外面被选择好了
    temp_args = type('Args', (), {})()
    for attr in dir(args):
        if not attr.startswith('_'):
            setattr(temp_args, attr, getattr(args, attr))
    temp_args.icl_type = 'fixed-random'  # 强制使用fixed-random避免重复处理
    
    if args.gpt_type == 'gpt3.5':
        # GPT-3.5 使用文本提示
        prompt, _ = form_prompt_for_gpt3(
            text_input=val_example,
            top_k=len(supporting_examples),
            stats=stats,
            supporting_examples=supporting_examples,
            args=temp_args,
            train_features=None,
            val_feature=None
        )
        return prompt
    elif args.gpt_type in ['gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini']:
        # ChatGPT/GPT-4 使用消息列表
        messages, _ = form_prompt_for_chatgpt(
            text_input=val_example,
            top_k=len(supporting_examples),
            stats=stats,
            supporting_examples=supporting_examples,
            args=temp_args,
            train_features=None,
            val_feature=None
        )
        return messages
    else:
        raise NotImplementedError(f"Unsupported GPT type: {args.gpt_type}")


def form_prompt_for_gpt3(text_input, top_k, stats, supporting_examples, args,
                        train_features=None, val_feature=None):
    """为GPT-3构建提示"""
    unit_name = 'pixel' if args.unit in ['px', ''] else 'meters'
    class_freq = [f"{obj}: {round(stats['class_frequencies'][obj], 4)}" for obj in stats['object_types']]
    rtn_prompt = 'Instruction: synthesize the 3D layout of an indoor scene. ' \
                'The generated 3D layout should follow the CSS style, where each line starts with the furniture category ' \
                'and is followed by the 3D size, orientation and absolute position. ' \
                "Formally, each line should follow the template: \n" \
                f"FURNITURE {{length: ?{args.unit}: width: ?{args.unit}; height: ?{args.unit}; left: ?{args.unit}; top: ?{args.unit}; depth: ?{args.unit}; orientation: ? degrees;}}\n" \
                f'All values are in {unit_name} but the orientation angle is in degrees.\n\n'
    
    # Add constraints based on args
    if hasattr(args, 'no_overlapping_furniture') and args.no_overlapping_furniture:
        rtn_prompt += "IMPORTANT: Generate CSS for furniture layout. Each item must use absolute positioning and must not overlap with others based on top/left/width/height.\n\n"
    
    rtn_prompt += f"Available furnitures: {', '.join(stats['object_types'])} \n" \
                  f"Overall furniture frequencies: ({'; '.join(class_freq)})\n\n"
    
    if hasattr(args, 'no_additional_furniture') and args.no_additional_furniture:
        rtn_prompt += "CONSTRAINT: - No furniture should significantly overlap with another. Ensure all furniture bounding boxes are non-overlapping in both horizontal and vertical directions.\n" \
                      "- All furniture must be placed entirely within the room boundaries.\n\n"
                
    last_example = f'{text_input[0]}Layout:\n'
    prompting_examples = ''
    total_length = len(tokenizer(rtn_prompt + last_example)['input_ids'])

    # Initialize sorted_ids for all cases
    sorted_ids = []
    
    if args.icl_type == 'k-similar':
        assert train_features is not None
        sorted_ids = get_closest_room(train_features, val_feature)
        supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]

    # loop through the related supporting examples, check if the prompt length exceed limit
    for i, supporting_example in enumerate(supporting_examples[:top_k]):
        current_prompting_example = create_prompt(supporting_example)
        cur_len = len(tokenizer(current_prompting_example)['input_ids'])
        if total_length + cur_len > args.gpt_input_length_limit:  # won't take the input that is too long
            print(f"{i+1}th exemplar exceed max length")
            break
        prompting_examples = current_prompting_example + prompting_examples 
        total_length += cur_len
    
    prompting_examples += last_example
    rtn_prompt += prompting_examples
    
    return rtn_prompt, sorted_ids


def form_prompt_for_chatgpt(text_input, top_k, stats, supporting_examples, args,
                           train_features=None, val_feature=None):
    """为ChatGPT构建提示"""
    message_list = []
    unit_name = 'pixel' if args.unit in ['px', ''] else 'meters'
    class_freq = [f"{obj}: {round(stats['class_frequencies'][obj], 4)}" for obj in stats['object_types']]
    rtn_prompt = 'You are a 3D indoor scene designer. \nInstruction: synthesize the 3D layout of an indoor scene. ' \
                'The generated 3D layout should follow the CSS style, where each line starts with the furniture category ' \
                'and is followed by the 3D size, orientation and absolute position. ' \
                "Formally, each line should follow the template: \n" \
                f"FURNITURE {{length: ?{args.unit}: width: ?{args.unit}; height: ?{args.unit}; orientation: ? degrees; left: ?{args.unit}; top: ?{args.unit}; depth: ?{args.unit};}}\n" \
                f'All values are in {unit_name} but the orientation angle is in degrees.\n\n'
    
    # Add constraints based on args
    if hasattr(args, 'no_overlapping_furniture') and args.no_overlapping_furniture:
        rtn_prompt += "IMPORTANT: Generate CSS for furniture layout. Each item must use absolute positioning and must not overlap with others based on top/left/width/height.\n\n"
    
    rtn_prompt += f"Available furnitures: {', '.join(stats['object_types'])} \n" \
                  f"Overall furniture frequencies: ({'; '.join(class_freq)})\n\n"
    
    if hasattr(args, 'no_additional_furniture') and args.no_additional_furniture:
        rtn_prompt += "CONSTRAINT: No additional furniture beyond what is specified in the room description.\n\n"

    message_list.append({'role': 'system', 'content': rtn_prompt})
    last_example = f'{text_input[0]}Layout:\n'
    total_length = len(tokenizer(rtn_prompt + last_example)['input_ids'])

    # Initialize sorted_ids for all cases
    sorted_ids = []
    
    if args.icl_type == 'k-similar':
        assert train_features is not None
        sorted_ids = get_closest_room(train_features, val_feature)
        supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]

    # loop through the related supporting examples, check if the prompt length exceed limit
    for i, supporting_example in enumerate(supporting_examples[:top_k]):
        cur_len = len(tokenizer(supporting_example[0]+supporting_example[1])['input_ids'])
        if total_length + cur_len > args.gpt_input_length_limit:  # won't take the input that is too long
            print(f"{i+1}th exemplar exceed max length")
            break
        total_length += cur_len

        current_messages = [
            {'role': 'user', 'content': supporting_example[0]+"Layout:\n"},
            {'role': 'assistant', 'content': supporting_example[1].lstrip("Layout:\n")},
        ]
        message_list = message_list + current_messages
    
    # concatename prompts for gpt4
    message_list.append({'role': 'user', 'content': last_example})

    return message_list, sorted_ids 


def form_prompt_for_partial_completion_chatgpt(partial_layout, room_condition, top_k, stats, 
                                              supporting_examples, args, train_features=None, val_feature=None):
    """为部分场景补全构建ChatGPT提示"""
    message_list = []
    unit_name = 'pixel' if args.unit in ['px', ''] else 'meters'
    class_freq = [f"{obj}: {round(stats['class_frequencies'][obj], 4)}" for obj in stats['object_types']]
    
    # 系统提示：强调补全任务的特殊性
    system_prompt = 'You are a 3D indoor scene designer specializing in PARTIAL SCENE COMPLETION. \n' \
                   'CRITICAL: Your task is to ONLY OUTPUT THE NEW FURNITURE needed to complete the scene. ' \
                   'DO NOT repeat or output the existing furniture that is already provided.\n\n' \
                   'Instruction: Complete a 3D layout by adding missing furniture to an existing partial layout. ' \
                   'The NEW furniture should be coherent with existing ones and follow common interior design principles:\n' \
                   '- Visual symmetry (e.g., matching nightstands on both sides of bed)\n' \
                   '- Positional relations (e.g., chairs near desks, stools at bed end)\n' \
                   '- Room functionality (e.g., workspace areas, relaxation zones)\n\n' \
                   'The generated 3D layout should follow the CSS style format:\n' \
                   f"FURNITURE {{length: ?{args.unit}; width: ?{args.unit}; height: ?{args.unit}; orientation: ? degrees; left: ?{args.unit}; top: ?{args.unit}; depth: ?{args.unit};}}\n" \
                   f'All values are in {unit_name} but the orientation angle is in degrees.\n\n'
    
    system_prompt += f"Available furnitures: {', '.join(stats['object_types'])} \n" \
                    f"Overall furniture frequencies: ({'; '.join(class_freq)})\n\n"
    
    # 添加补全约束
    system_prompt += "COMPLETION CONSTRAINTS:\n" \
                    "1. DO NOT modify or move existing furniture - only ADD new furniture\n" \
                    "2. Ensure visual balance and symmetry where appropriate\n" \
                    "3. Maintain functional relationships between furniture pieces\n" \
                    "4. Avoid overlapping with existing furniture\n" \
                    "5. Consider traffic flow and accessibility\n\n"
    
    message_list.append({'role': 'system', 'content': system_prompt})
    
    # 计算总长度限制
    condition_and_partial = f'{room_condition}\n\nExisting Layout:\n{partial_layout}\n\nComplete Layout:\n'
    total_length = len(tokenizer(system_prompt + condition_and_partial)['input_ids'])
    
    # 选择相似示例用于上下文学习
    sorted_ids = []
    if args.icl_type == 'k-similar' and train_features is not None:
        sorted_ids = get_closest_room(train_features, val_feature)
        supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]
    
    # 添加支持示例（展示补全过程）
    for i, supporting_example in enumerate(supporting_examples[:top_k]):
        # 模拟部分场景和完整场景的对比
        full_layout = supporting_example[1].replace("Layout:\n", "")
        # 简化：取前一半家具作为"部分场景"
        furniture_lines = [line for line in full_layout.split('\n') if line.strip() and '{' in line]
        partial_count = max(1, len(furniture_lines) // 2)
        partial_furniture = '\n'.join(furniture_lines[:partial_count])
        
        # 计算需要补全的家具（剩余的家具）
        remaining_furniture = '\n'.join(furniture_lines[partial_count:])
        
        cur_len = len(tokenizer(supporting_example[0] + partial_furniture + remaining_furniture)['input_ids'])
        if total_length + cur_len > args.gpt_input_length_limit:
            print(f"{i+1}th completion exemplar exceed max length")
            break
        total_length += cur_len
        
        # 构建补全示例对话 - 只输出新增家具，不重复已有家具
        completion_messages = [
            {
                'role': 'user', 
                'content': f"{supporting_example[0]}\nExisting Layout:\n{partial_furniture}\n\nAdd the following furniture to complete the layout:"
            },
            {
                'role': 'assistant', 
                'content': remaining_furniture  # ✅ 只输出需要补全的家具
            },
        ]
        message_list.extend(completion_messages)
    
    # 添加当前任务 - 改为补全任务的提示
    current_task_content = f'{room_condition}\n\nExisting Layout:\n{partial_layout}\n\nAdd the following furniture to complete the layout:'
    message_list.append({
        'role': 'user', 
        'content': current_task_content
    })
    
    return message_list, sorted_ids


def build_partial_completion_prompt(room_condition, partial_layout, supporting_examples, args, stats):
    """构建部分场景补全的提示 - 主入口函数"""
    
    if args.gpt_type in ['gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini']:
        messages, sorted_ids = form_prompt_for_partial_completion_chatgpt(
            partial_layout=partial_layout,
            room_condition=room_condition,
            top_k=len(supporting_examples),
            stats=stats,
            supporting_examples=supporting_examples,
            args=args,
            train_features=None,
            val_feature=None
        )
        return messages, sorted_ids
    else:
        raise NotImplementedError(f"Partial completion not supported for GPT type: {args.gpt_type}") 