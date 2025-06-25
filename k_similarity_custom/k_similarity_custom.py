import re
import numpy as np

def extract_enhanced_features_from_input(custom_condition, furniture_list, stats):
    """extract enhanced features from input"""
    
    # 1. room geometry (2D)
    length_match = re.search(r'max length (\d+)', custom_condition)
    width_match = re.search(r'max width (\d+)', custom_condition)
    room_length = float(length_match.group(1)) if length_match else 0
    room_width = float(width_match.group(1)) if width_match else 0
    
    # 2. room derived features (3D)
    room_area = room_length * room_width
    room_ratio = room_length / room_width if room_width > 0 else 1.0
    room_perimeter = 2 * (room_length + room_width)
    
    # 3. furniture type frequency vector (22D - based on the number of furniture types in bedroom)
    furniture_freq_vector = np.zeros(len(stats['object_types']))
    furniture_counts = {}
    
    # parse furniture list (e.g. "double bed, wardrobe, wardrobe, pendant lamp")
    if furniture_list:
        furniture_items = [item.strip().replace(' ', '_') for item in furniture_list.split(',')]
        for item in furniture_items:
            furniture_counts[item] = furniture_counts.get(item, 0) + 1
    
    # build frequency vector
    for i, obj_type in enumerate(stats['object_types']):
        furniture_freq_vector[i] = furniture_counts.get(obj_type, 0)
    
    # 4. furniture statistics (4D)
    total_furniture = sum(furniture_counts.values())
    unique_furniture_types = len(furniture_counts)
    furniture_density = total_furniture / room_area if room_area > 0 else 0
    avg_furniture_per_type = total_furniture / unique_furniture_types if unique_furniture_types > 0 else 0
    
    # 5. semantic features (optional, need text embedding)
    # semantic_features = get_text_embedding(custom_condition)  # using BERT etc.
    
    # combine all features
    feature_vector = np.concatenate([
        [room_length, room_width],                   
        [room_area, room_ratio, room_perimeter],      
        furniture_freq_vector,                        
        [total_furniture, unique_furniture_types, 
         furniture_density, avg_furniture_per_type]   
    ])
    
    return feature_vector  

def get_closest_room_enhanced(train_features, val_feature, weights=None):
    """enhanced similarity matching, support feature weights"""
    
    # default weights: room geometry > furniture type > furniture statistics
    if weights is None:
        weights = {
            'room_geo': 0.4,      # room geometry weight
            'furniture_type': 0.4, # furniture type weight
            'furniture_stats': 0.2 # furniture statistics weight
        }
    
    distances = []
    for train_id, train_feat in train_features.items():
        # calculate distance for each segment
        room_geo_dist = np.mean((train_feat[:5] - val_feature[:5]) ** 2)
        furniture_type_dist = np.mean((train_feat[5:27] - val_feature[5:27]) ** 2)
        furniture_stats_dist = np.mean((train_feat[27:] - val_feature[27:]) ** 2)
        
        # weighted combination
        weighted_dist = (
            weights['room_geo'] * room_geo_dist +
            weights['furniture_type'] * furniture_type_dist +
            weights['furniture_stats'] * furniture_stats_dist
        )
        
        distances.append([train_id, weighted_dist])
    
    distances = sorted(distances, key=lambda x: x[1])
    sorted_ids, _ = zip(*distances)
    return sorted_ids