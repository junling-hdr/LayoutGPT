# LayoutGPT 模块化版本

## 文件结构

```
LayoutGPT/
├── layout_modules/           # 布局生成模块
│   ├── __init__.py
│   ├── data_loader.py       # 数据加载和特征提取
│   ├── prompt_builder.py    # GPT提示构建
│   ├── gpt_client.py        # OpenAI API调用
│   └── layout_parser.py     # GPT输出解析
├── visualization_modules/    # 可视化模块
│   ├── __init__.py
│   ├── utils.py            # 通用工具函数
│   ├── scene_3d.py         # 3D场景可视化
│   ├── scene_2d.py         # 2D俯视图可视化
│   └── benchmark_matrix.py # Benchmark矩阵生成
├── run_layoutgpt_simple.py  # 简化的布局生成主程序
├── visualize_simple.py      # 简化的可视化主程序
└── README_modules.md        # 本文档
```

## 核心功能

### 1. 布局生成 (Layout Generation)

**文件**: `run_layoutgpt_simple.py`

**功能**: 使用 GPT 生成 3D 室内场景布局

**使用方法**:

```bash
python run_layoutgpt_simple.py --room bedroom --K 8
```

**主要参数**:

- `--room`: 房间类型 (bedroom/livingroom)
- `--gpt_type`: GPT 模型 (gpt3.5/gpt4)
- `--K`: 上下文示例数量
- `--max_val_samples`: 限制处理的样本数量

### 2. 可视化 (Visualization)

**文件**: `visualize_simple.py`

**功能**:

- 生成所有场景的 HTML 文件（不自动打开浏览器）
- 生成 benchmarking 矩阵图片

**使用方法**:

```bash
# GUI选择文件（推荐）
python visualize_simple.py

# 命令行指定文件
python visualize_simple.py --input llm_output/3D/gpt4.bedroom.k-similar.k_8.px_regular.json
```

## 模块说明

### Layout Modules

#### `data_loader.py`

- `load_dataset()`: 加载完整数据集
- `load_room_boxes()`: 加载单个房间数据
- `get_closest_room()`: 获取最相似的房间

#### `prompt_builder.py`

- `form_prompt_for_gpt3()`: 为 GPT-3 构建提示
- `form_prompt_for_chatgpt()`: 为 ChatGPT 构建提示

#### `gpt_client.py`

- `call_gpt_api()`: 调用 OpenAI API
- 包含错误处理和重试机制

#### `layout_parser.py`

- `parse_gpt_response()`: 解析 GPT 响应
- `process_all_iterations()`: 处理多次迭代结果

### Visualization Modules

#### `utils.py`

- `parse_room_size()`: 解析房间尺寸
- `get_furniture_color()`: 获取家具颜色
- `find_rendered_image()`: 查找渲染图片
- `calculate_out_of_boundary_rate()`: 计算超界率

#### `scene_3d.py`

- `visualize_scene()`: 创建 3D 场景可视化
- `create_room_walls()`: 创建房间墙壁
- `create_3d_furniture_box()`: 创建 3D 家具盒子

#### `scene_2d.py`

- `create_2d_visualization()`: 创建 2D 俯视图
- 显示超出边界的家具（红色边框）

#### `benchmark_matrix.py`

- `create_benchmark_matrix()`: 创建 benchmark 矩阵
- `create_image_matrix()`: 组合图片矩阵
- 包含 Query 图片、3D 视图、2D 视图、Prompt 信息、In-context 图片

## 输出结果

### HTML 文件

- **位置**: `visualization_output/html/top{n}/`
- **文件名**: `scene_{room_name}_top{n}.html`
- **内容**: 3D 可视化 + Query 图片 + In-context 图片

### Benchmark 矩阵

- **位置**: `visualization_output/html/top{n}/benchmark_matrix.png`
- **内容**:
  - 横向：每个 query_id
  - 纵向：Query 图片、3D 占位图、2D 俯视图、Prompt 信息、In-context 图片
  - 标注：每个场景和整体的 out-of-boundary 率
  - 2D 图中红框标识超出边界的家具

## 优势

1. **模块化**: 代码分离，易于维护和扩展
2. **简化**: 只保留核心功能，去除复杂参数
3. **GUI 友好**: 支持文件选择对话框
4. **错误处理**: 完善的异常处理机制
5. **自动化**: 一键生成所有可视化结果

## 注意事项

- 程序会自动处理所有场景，无需额外参数
- HTML 文件不会自动打开浏览器
- 3D 截图暂时使用占位图片（避免程序卡住）
- 2D 图会显示超出房间边界的家具部分
- 矩阵图片包含完整的 benchmarking 信息
