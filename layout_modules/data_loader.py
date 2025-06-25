import os
import os.path as op
import json
import numpy as np
from tqdm import tqdm
from PIL import Image


def load_room_boxes(prefix, id, stats, unit, args):
    """加载房间盒子数据"""
    data = np.load(op.join(prefix, id, 'boxes.npz'))
    x_c, y_c = data['floor_plan_centroid'][0], data['floor_plan_centroid'][2]
    x_offset = min(data['floor_plan_vertices'][:, 0])
    y_offset = min(data['floor_plan_vertices'][:, 2])
    room_length = max(data['floor_plan_vertices'][:, 0]) - min(data['floor_plan_vertices'][:, 0])
    room_width = max(data['floor_plan_vertices'][:, 2]) - min(data['floor_plan_vertices'][:, 2])
    vertices = np.stack((data['floor_plan_vertices'][:, 0] - x_offset, data['floor_plan_vertices'][:, 2] - y_offset), axis=1)
    vertices = np.asarray([list(nxy) for nxy in set(tuple(xy) for xy in vertices)])
    
    # normalize
    if args.normalize:
        norm = min(room_length, room_width)
        room_length, room_width = room_length / norm, room_width / norm
        vertices /= norm
        if unit in ['px', '']:
            scale_factor = 256
            room_length, room_width = int(room_length * scale_factor), int(room_width * scale_factor)

    vertices = [f'({v[0]:.2f}, {v[1]:.2f})' for v in vertices]

    if unit in ['px', '']:
        condition = f"Condition:\n"
        if args.room == 'livingroom':
            if 'dining' in id.lower():
                condition += f"Room Type: living room & dining room\n"
            else:
                condition += f"Room Type: living room\n"
        else:
            condition += f"Room Type: {args.room}\n"
        condition += f"Room Size: max length {room_length}{unit}, max width {room_width}{unit}\n"
    else:
        condition = f"Condition:\n" \
                    f"Room Type: {args.room}\n" \
                    f"Room Size: max length {room_length:.2f}{unit}, max width {room_width:.2f}{unit}\n"

    layout = 'Layout:\n'
    for label, size, angle, loc in zip(data['class_labels'], data['sizes'], data['angles'], data['translations']):
        label_idx = np.where(label)[0][0]
        if label_idx >= len(stats['object_types']):  # NOTE:
            continue
        cat = stats['object_types'][label_idx]
        
        length, height, width = size  # NOTE: half the actual size
        length, height, width = length * 2, height * 2, width * 2
        orientation = round(angle[0] / 3.1415926 * 180)
        dx, dz, dy = loc  # NOTE: center point
        dx = dx + x_c - x_offset
        dy = dy + y_c - y_offset

        # normalize
        if args.normalize:
            length, width, height = length / norm, width / norm, height / norm
            dx, dy, dz = dx / norm, dy / norm, dz / norm
            if unit in ['px', '']:
                length, width, height = int(length * scale_factor), int(width * scale_factor), int(height * scale_factor)
                dx, dy, dz = int(dx * scale_factor), int(dy * scale_factor), int(dz * scale_factor)

        if unit in ['px', '']:
            layout += f"{cat} {{length: {length}{unit}; " \
                      f"width: {width}{unit}; " \
                      f"height: {height}{unit}; " \
                      f"left: {dx}{unit}; " \
                      f"top: {dy}{unit}; " \
                      f"depth: {dz}{unit};" \
                      f"orientation: {orientation} degrees;}}\n"
        else:
            layout += f"{cat} {{length: {length:.2f}{unit}; " \
                      f"height: {height:.2f}{unit}; " \
                      f"width: {width:.2f}{unit}; " \
                      f"orientation: {orientation} degrees; " \
                      f"left: {dx:.2f}{unit}; " \
                      f"top: {dy:.2f}{unit}; " \
                      f"depth: {dz:.2f}{unit};}}\n"

    return condition, layout, dict(data)


def load_set(prefix, ids, stats, unit, args):
    """加载数据集"""
    id2prompt = {}
    meta_data = {}
    for id in tqdm(ids):
        condition, layout, data = load_room_boxes(prefix, id, stats, unit, args)
        id2prompt[id] = [condition, layout]
        meta_data[id] = data
    return id2prompt, meta_data


def load_features(meta_data, floor_plan=True):
    """加载特征"""
    features = {}
    for id, data in meta_data.items():
        if floor_plan:
            features[id] = np.asarray(Image.fromarray(data['room_layout'].squeeze()).resize((64, 64)))
        else:
            room_length = max(data['floor_plan_vertices'][:, 0]) - min(data['floor_plan_vertices'][:, 0])
            room_width = max(data['floor_plan_vertices'][:, 2]) - min(data['floor_plan_vertices'][:, 2])
            features[id] = np.asarray([room_length, room_width])
    return features


def get_closest_room(train_features, val_feature):
    """get the closest room"""
    distances = [[id, ((feat - val_feature) ** 2).mean()] for id, feat in train_features.items()]
    distances = sorted(distances, key=lambda x: x[1])
    sorted_ids, _ = zip(*distances)
    return sorted_ids


def load_dataset(args):
    """加载完整数据集"""
    dataset_prefix = f"{args.dataset_dir}/{args.room}"
    
    with open(f"dataset/3D/{args.room}_splits.json", "r") as file:
        splits = json.load(file)
        
    with open(f"{dataset_prefix}/dataset_stats.txt", "r") as file:
        stats = json.load(file)

    # load train examples
    train_ids = splits['rect_train'] if args.regular_floor_plan else splits['train']
    train_data, meta_train_data = load_set(dataset_prefix, train_ids, stats, args.unit, args)

    # load val examples
    val_ids = splits['rect_test'] if args.regular_floor_plan else splits['test']
    val_data, meta_val_data = load_set(dataset_prefix, val_ids, stats, args.unit, args)
    val_features = load_features(meta_val_data)
    
    print(f"Loaded {len(train_data)} train samples and {len(val_data)} validation samples")

    # 只在标准模式下限制验证样本数量（如果指定了max_val_samples）
    if hasattr(args, 'max_val_samples') and getattr(args, 'max_val_samples', None) is not None:
        val_data = {k: v for k, v in list(val_data.items())[:args.max_val_samples]}
        print(f"Limited validation samples to {len(val_data)} samples")

    return {
        'train_data': train_data,
        'val_data': val_data,
        'meta_train_data': meta_train_data,
        'meta_val_data': meta_val_data,
        'val_features': val_features,
        'stats': stats
    } 