from transformers import GPT2TokenizerFast
from .data_loader import get_closest_room

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")


def create_prompt(sample):
    """创建单个提示"""
    return sample[0] + sample[1] + "\n\n"


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
                f'All values are in {unit_name} but the orientation angle is in degrees.\n\n' \
                f"Available furnitures: {', '.join(stats['object_types'])} \n" \
                f"Overall furniture frequencies: ({'; '.join(class_freq)})\n\n"
                
    last_example = f'{text_input[0]}Layout:\n'
    prompting_examples = ''
    total_length = len(tokenizer(rtn_prompt + last_example)['input_ids'])

    if args.icl_type == 'k-similar':
        assert train_features is not None
        sorted_ids = get_closest_room(train_features, val_feature)
        supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]
        if args.test:
            print("retrieved examples:")
            print("\n".join(sorted_ids[:top_k]))

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
                f'All values are in {unit_name} but the orientation angle is in degrees.\n\n' \
                f"Available furnitures: {', '.join(stats['object_types'])} \n" \
                f"Overall furniture frequencies: ({'; '.join(class_freq)})\n\n"

    message_list.append({'role': 'system', 'content': rtn_prompt})
    last_example = f'{text_input[0]}Layout:\n'
    total_length = len(tokenizer(rtn_prompt + last_example)['input_ids'])

    if args.icl_type == 'k-similar':
        assert train_features is not None
        sorted_ids = get_closest_room(train_features, val_feature)
        supporting_examples = [supporting_examples[id] for id in sorted_ids[:top_k]]
        if args.test:
            print("retrieved examples:")
            print("\n".join(sorted_ids[:top_k]))

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