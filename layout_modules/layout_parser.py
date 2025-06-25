import numpy as np
from parse_llm_output import parse_3D_layout


def parse_gpt_response(response, args):
    """解析GPT响应"""
    predicted_object_list = []
    
    if args.gpt_type == 'gpt3.5':
        line_list = response['choices'][0]['text'].split('\n')
    else:
        line_list = response['choices'][0]['message']['content'].split('\n')

    for line in line_list:
        if line == '':
            continue
        try:
            selector_text, bbox = parse_3D_layout(line, args.unit)
            if selector_text == None:
                print(line)
                continue
            predicted_object_list.append([selector_text, bbox])
        except ValueError as e:
            pass
    
    return predicted_object_list


def process_all_iterations(response, args, val_id, val_example, sorted_ids, top_k):
    """处理所有迭代结果"""
    all_predictions = []
    n_lines = []
    n_furnitures = []
    
    # Handle restricted models that don't support multiple iterations
    actual_iterations = min(args.n_iter, len(response['choices']))
    if actual_iterations < args.n_iter:
        print(f"Note: Expected {args.n_iter} iterations, but only got {actual_iterations} from API response")
    
    for i_iter in range(actual_iterations):
        if args.verbose:
            try:
                print(response['choices'][i_iter]['text'])
            except:
                print(response['choices'][i_iter]['message']['content'])

        predicted_object_list = []
        if args.gpt_type == 'gpt3.5':
            line_list = response['choices'][i_iter]['text'].split('\n')
        else:
            line_list = response['choices'][i_iter]['message']['content'].split('\n')

        n_lines.append(len(line_list))
        for line in line_list:
            if line == '':
                continue
            try:
                selector_text, bbox = parse_3D_layout(line, args.unit)
                if selector_text == None:
                    print(line)
                    continue
                predicted_object_list.append([selector_text, bbox])
            except ValueError as e:
                pass
        
        n_furnitures.append(len(predicted_object_list))
        # 为每个iteration创建唯一的query_id
        iteration_query_id = f"{val_id}_iter{i_iter + 1}" if actual_iterations > 1 else val_id
        
        # 获取原始GPT响应用于overlap检测
        if args.gpt_type == 'gpt3.5':
            raw_gpt_response = response['choices'][i_iter]['text']
        else:
            raw_gpt_response = response['choices'][i_iter]['message']['content']
        
        all_predictions.append({
            'query_id': iteration_query_id,
            'iter': i_iter,
            'prompt': val_example[0],
            'object_list': predicted_object_list,
            'sorted_ids': sorted_ids[:top_k],
            'raw_gpt_response': raw_gpt_response,  # 添加原始响应用于overlap检测
        })
    
    return all_predictions, n_lines, n_furnitures 