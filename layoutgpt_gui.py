#!/usr/bin/env python3
"""
LayoutGPT GUI 完整版
包含布局生成和可视化功能的图形界面程序
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import sys
import os
import json
from datetime import datetime

# Import visualization modules
try:
    from visualization_modules.scene_3d import visualize_scene
    from visualization_modules.benchmark_matrix import create_benchmark_matrix
    from visualization_modules.utils import get_output_path, save_and_open_html
    VISUALIZATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Visualization modules not available: {e}")
    VISUALIZATION_AVAILABLE = False


class LayoutGPTGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LayoutGPT - 3D Scene Generation & Visualization")
        self.root.geometry("800x700")
        
        # 创建主框架
        self.create_widgets()
        
        # 默认值
        self.set_defaults()
    
    def create_widgets(self):
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标签页1：布局生成
        self.generation_frame = ttk.Frame(notebook)
        notebook.add(self.generation_frame, text="布局生成 (Layout Generation)")
        
        # 标签页2：可视化
        self.visualization_frame = ttk.Frame(notebook)
        notebook.add(self.visualization_frame, text="可视化 (Visualization)")
        
        # 创建布局生成界面
        self.create_generation_ui()
        
        # 创建可视化界面
        self.create_visualization_ui()
    
    def create_generation_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.generation_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 基本参数组
        basic_group = ttk.LabelFrame(main_frame, text="基本参数", padding=10)
        basic_group.pack(fill=tk.X, pady=(0, 10))
        
        # 房间类型
        ttk.Label(basic_group, text="房间类型:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.room_var = tk.StringVar()
        room_combo = ttk.Combobox(basic_group, textvariable=self.room_var, values=["bedroom", "livingroom"], state="readonly")
        room_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # GPT模型
        ttk.Label(basic_group, text="GPT模型:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.gpt_type_var = tk.StringVar()
        gpt_combo = ttk.Combobox(basic_group, textvariable=self.gpt_type_var, 
                                values=["gpt3.5", "gpt3.5-chat", "gpt4"], state="readonly")
        gpt_combo.grid(row=0, column=3, sticky=tk.W)
        
        # ICL类型
        ttk.Label(basic_group, text="ICL类型:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.icl_type_var = tk.StringVar()
        icl_combo = ttk.Combobox(basic_group, textvariable=self.icl_type_var, 
                                values=["fixed-random", "k-similar"], state="readonly")
        icl_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        
        # K值
        ttk.Label(basic_group, text="K值:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.k_var = tk.StringVar()
        k_entry = ttk.Entry(basic_group, textvariable=self.k_var, width=10)
        k_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # 路径参数组
        path_group = ttk.LabelFrame(main_frame, text="路径参数", padding=10)
        path_group.pack(fill=tk.X, pady=(0, 10))
        
        # 数据集目录
        ttk.Label(path_group, text="数据集目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.dataset_dir_var = tk.StringVar()
        dataset_entry = ttk.Entry(path_group, textvariable=self.dataset_dir_var, width=40)
        dataset_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(path_group, text="浏览", command=self.browse_dataset_dir).grid(row=0, column=2)
        
        # 输出目录
        ttk.Label(path_group, text="输出目录:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(path_group, textvariable=self.output_dir_var, width=40)
        output_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Button(path_group, text="浏览", command=self.browse_output_dir).grid(row=1, column=2, pady=(10, 0))
        
        # 高级参数组
        advanced_group = ttk.LabelFrame(main_frame, text="高级参数", padding=10)
        advanced_group.pack(fill=tk.X, pady=(0, 10))
        
        # 单位
        ttk.Label(advanced_group, text="单位:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.unit_var = tk.StringVar()
        unit_combo = ttk.Combobox(advanced_group, textvariable=self.unit_var, 
                                 values=["px", "m", ""], state="readonly")
        unit_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 温度
        ttk.Label(advanced_group, text="温度:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.temperature_var = tk.StringVar()
        temp_entry = ttk.Entry(advanced_group, textvariable=self.temperature_var, width=10)
        temp_entry.grid(row=0, column=3, sticky=tk.W)
        
        # 迭代次数
        ttk.Label(advanced_group, text="迭代次数:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.n_iter_var = tk.StringVar()
        iter_entry = ttk.Entry(advanced_group, textvariable=self.n_iter_var, width=10)
        iter_entry.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # 最大验证样本数
        ttk.Label(advanced_group, text="最大验证样本数:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.max_samples_var = tk.StringVar()
        samples_entry = ttk.Entry(advanced_group, textvariable=self.max_samples_var, width=10)
        samples_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # 添加提示信息
        ttk.Label(advanced_group, text="(留空表示使用全部验证数据)", 
                 foreground="gray", font=("TkDefaultFont", 8)).grid(row=2, column=2, columnspan=2, 
                 sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        # 选项组
        options_group = ttk.LabelFrame(main_frame, text="选项", padding=10)
        options_group.pack(fill=tk.X, pady=(0, 10))
        
        # 复选框
        self.normalize_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="标准化 (normalize)", variable=self.normalize_var).grid(row=0, column=0, sticky=tk.W)
        
        self.regular_floor_plan_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="规则平面图 (regular_floor_plan)", variable=self.regular_floor_plan_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.test_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="测试模式 (test)", variable=self.test_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.verbose_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="详细输出 (verbose)", variable=self.verbose_var).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="开始生成", command=self.start_generation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="重置参数", command=self.reset_generation_params).pack(side=tk.LEFT)
        
        # 输出日志
        log_group = ttk.LabelFrame(main_frame, text="输出日志", padding=10)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.generation_log = scrolledtext.ScrolledText(log_group, height=8)
        self.generation_log.pack(fill=tk.BOTH, expand=True)
    
    def create_visualization_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.visualization_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 文件选择组
        file_group = ttk.LabelFrame(main_frame, text="文件选择", padding=10)
        file_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(file_group, text="JSON文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.json_file_var = tk.StringVar()
        json_entry = ttk.Entry(file_group, textvariable=self.json_file_var, width=50)
        json_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(file_group, text="浏览", command=self.browse_json_file).grid(row=0, column=2)
        
        # 可视化选项组
        vis_options_group = ttk.LabelFrame(main_frame, text="可视化选项", padding=10)
        vis_options_group.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_html_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(vis_options_group, text="生成HTML文件", variable=self.generate_html_var).grid(row=0, column=0, sticky=tk.W)
        
        self.generate_matrix_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(vis_options_group, text="生成Benchmark矩阵", variable=self.generate_matrix_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.auto_open_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(vis_options_group, text="自动打开浏览器", variable=self.auto_open_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        # 添加说明标签
        info_label = ttk.Label(vis_options_group, text="提示：现在直接集成在GUI中，无需额外脚本", 
                              foreground="green", font=("TkDefaultFont", 8))
        info_label.grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        # 控制按钮
        vis_control_frame = ttk.Frame(main_frame)
        vis_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(vis_control_frame, text="开始可视化", command=self.start_visualization).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(vis_control_frame, text="清空日志", command=self.clear_vis_log).pack(side=tk.LEFT)
        
        # 新增：家具统计按钮组
        stats_group = ttk.LabelFrame(main_frame, text="数据集统计", padding=10)
        stats_group.pack(fill=tk.X, pady=(10, 0))
        
        # 数据集目录选择（用于统计）
        ttk.Label(stats_group, text="数据集目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.stats_dataset_dir_var = tk.StringVar()
        stats_dataset_entry = ttk.Entry(stats_group, textvariable=self.stats_dataset_dir_var, width=40)
        stats_dataset_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(stats_group, text="浏览", command=self.browse_stats_dataset_dir).grid(row=0, column=2)
        
        # 房间类型选择（用于统计）
        ttk.Label(stats_group, text="房间类型:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.stats_room_var = tk.StringVar()
        stats_room_combo = ttk.Combobox(stats_group, textvariable=self.stats_room_var, 
                                       values=["bedroom", "livingroom"], state="readonly")
        stats_room_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # 统计按钮
        ttk.Button(stats_group, text="计算家具统计", command=self.calculate_furniture_stats).grid(row=1, column=2, pady=(10, 0))
        
        # 输出日志
        vis_log_group = ttk.LabelFrame(main_frame, text="输出日志", padding=10)
        vis_log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.visualization_log = scrolledtext.ScrolledText(vis_log_group, height=12)
        self.visualization_log.pack(fill=tk.BOTH, expand=True)
    
    def set_defaults(self):
        """设置默认值"""
        self.room_var.set("bedroom")
        self.gpt_type_var.set("gpt4")
        self.icl_type_var.set("k-similar")
        self.k_var.set("8")
        self.dataset_dir_var.set("./ATISS/data_output")
        self.output_dir_var.set("./llm_output/3D/")
        self.unit_var.set("px")
        self.temperature_var.set("0.7")
        self.n_iter_var.set("1")
        self.max_samples_var.set("10")  # 默认设置为10个验证样本
        self.normalize_var.set(True)
        self.regular_floor_plan_var.set(True)
        self.test_var.set(False)
        self.verbose_var.set(False)
        
        # 统计功能默认值
        self.stats_dataset_dir_var.set("./ATISS/data_output")
        self.stats_room_var.set("bedroom")
    
    def browse_dataset_dir(self):
        """浏览数据集目录"""
        directory = filedialog.askdirectory(title="选择数据集目录")
        if directory:
            self.dataset_dir_var.set(directory)
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)
    
    def browse_json_file(self):
        """浏览JSON文件"""
        file_path = filedialog.askopenfilename(
            title="选择JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="./llm_output/3D/"
        )
        if file_path:
            self.json_file_var.set(file_path)
    
    def reset_generation_params(self):
        """重置生成参数"""
        self.set_defaults()
        self.log_generation("参数已重置为默认值")
    
    def log_generation(self, message):
        """记录生成日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.generation_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.generation_log.see(tk.END)
        self.root.update()
    
    def log_visualization(self, message):
        """记录可视化日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.visualization_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.visualization_log.see(tk.END)
        self.root.update()
    
    def clear_vis_log(self):
        """清空可视化日志"""
        self.visualization_log.delete(1.0, tk.END)
    
    def browse_stats_dataset_dir(self):
        """浏览统计用数据集目录"""
        directory = filedialog.askdirectory(title="选择数据集目录（用于统计）")
        if directory:
            self.stats_dataset_dir_var.set(directory)
    
    def calculate_furniture_stats(self):
        """计算家具统计信息"""
        if not self.stats_dataset_dir_var.get():
            messagebox.showerror("错误", "请选择数据集目录")
            return
        
        if not self.stats_room_var.get():
            messagebox.showerror("错误", "请选择房间类型")
            return
        
        if not os.path.exists(self.stats_dataset_dir_var.get()):
            messagebox.showerror("错误", "数据集目录不存在")
            return
        
        # 在新线程中运行统计计算
        thread = threading.Thread(target=self.run_furniture_stats_calculation)
        thread.daemon = True
        thread.start()
    
    def run_furniture_stats_calculation(self):
        """运行家具统计计算过程"""
        try:
            dataset_dir = self.stats_dataset_dir_var.get()
            room_type = self.stats_room_var.get()
            
            self.log_visualization(f"开始计算家具统计: {room_type}")
            
            # 构建数据集路径
            dataset_prefix = f"{dataset_dir}/{room_type}"
            stats_file_path = f"{dataset_prefix}/dataset_stats.txt"
            
            if not os.path.exists(stats_file_path):
                self.log_visualization(f"❌ 统计文件不存在: {stats_file_path}")
                messagebox.showerror("错误", f"统计文件不存在: {stats_file_path}")
                return
            
            # 读取统计信息
            with open(stats_file_path, "r") as file:
                stats = json.load(file)
            
            # 构建详细统计信息
            furniture_stats = {
                "room_type": room_type,
                "dataset_path": dataset_dir,
                "generated_at": datetime.now().isoformat(),
                "available_furnitures": stats.get('object_types', []),
                "class_frequencies": stats.get('class_frequencies', {}),
                "total_furniture_types": len(stats.get('object_types', [])),
                "detailed_info": {
                    "furniture_list": ', '.join(stats.get('object_types', [])),
                    "frequency_details": []
                }
            }
            
            # 添加详细频率信息
            if 'object_types' in stats and 'class_frequencies' in stats:
                for obj_type in stats['object_types']:
                    freq = stats['class_frequencies'].get(obj_type, 0)
                    furniture_stats["detailed_info"]["frequency_details"].append({
                        "furniture_type": obj_type,
                        "frequency": freq,
                        "display_name": obj_type.replace('_', ' ').title()
                    })
                
                # 按频率排序
                furniture_stats["detailed_info"]["frequency_details"].sort(
                    key=lambda x: x['frequency'], reverse=True
                )
            
            # 让用户选择保存位置
            save_path = filedialog.asksaveasfilename(
                title="保存家具统计信息",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"furniture_stats_{room_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if save_path:
                # 保存统计信息
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(furniture_stats, f, indent=4, ensure_ascii=False)
                
                self.log_visualization("✅ 家具统计计算完成！")
                self.log_visualization(f"统计信息保存到: {save_path}")
                self.log_visualization(f"家具类型数量: {furniture_stats['total_furniture_types']}")
                self.log_visualization(f"可用家具: {furniture_stats['detailed_info']['furniture_list']}")
                
                messagebox.showinfo("成功", f"家具统计信息已保存到:\n{save_path}")
            else:
                self.log_visualization("⚠️ 用户取消保存")
                
        except Exception as e:
            self.log_visualization(f"❌ 统计计算错误: {str(e)}")
            messagebox.showerror("错误", f"统计计算错误: {str(e)}")
    
    def validate_generation_params(self):
        """验证生成参数"""
        if not self.room_var.get():
            messagebox.showerror("错误", "请选择房间类型")
            return False
        
        if not self.gpt_type_var.get():
            messagebox.showerror("错误", "请选择GPT模型")
            return False
        
        try:
            k_val = int(self.k_var.get())
            if k_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "K值必须是正整数")
            return False
        
        if not os.path.exists(self.dataset_dir_var.get()):
            messagebox.showerror("错误", "数据集目录不存在")
            return False
        
        return True
    
    def build_generation_command(self):
        """构建生成命令"""
        cmd = [sys.executable, "run_layoutgpt_3d_adjust.py"]
        
        # 基本参数
        cmd.extend(["--room", self.room_var.get()])
        cmd.extend(["--gpt_type", self.gpt_type_var.get()])
        cmd.extend(["--icl_type", self.icl_type_var.get()])
        cmd.extend(["--K", self.k_var.get()])
        cmd.extend(["--dataset_dir", self.dataset_dir_var.get()])
        cmd.extend(["--base_output_dir", self.output_dir_var.get()])
        cmd.extend(["--unit", self.unit_var.get()])
        cmd.extend(["--temperature", self.temperature_var.get()])
        cmd.extend(["--n_iter", self.n_iter_var.get()])
        
        # 可选参数
        if self.max_samples_var.get():
            cmd.extend(["--max_val_samples", self.max_samples_var.get()])
        
        # 布尔选项
        if self.normalize_var.get():
            cmd.append("--normalize")
        if self.regular_floor_plan_var.get():
            cmd.append("--regular_floor_plan")
        if self.test_var.get():
            cmd.append("--test")
        if self.verbose_var.get():
            cmd.append("--verbose")
        
        return cmd
    
    def start_generation(self):
        """开始生成"""
        if not self.validate_generation_params():
            return
        
        # 在新线程中运行生成
        thread = threading.Thread(target=self.run_generation)
        thread.daemon = True
        thread.start()
    
    def run_generation(self):
        """运行生成过程"""
        try:
            cmd = self.build_generation_command()
            self.log_generation(f"开始执行命令: {' '.join(cmd)}")
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时输出
            for line in process.stdout:
                self.log_generation(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log_generation("✅ 生成完成！")
                messagebox.showinfo("成功", "布局生成完成！")
            else:
                self.log_generation(f"❌ 生成失败，退出码: {process.returncode}")
                messagebox.showerror("错误", "生成过程中出现错误，请查看日志")
                
        except Exception as e:
            self.log_generation(f"❌ 执行错误: {str(e)}")
            messagebox.showerror("错误", f"执行错误: {str(e)}")
    
    def start_visualization(self):
        """开始可视化"""
        if not VISUALIZATION_AVAILABLE:
            messagebox.showerror("错误", "可视化模块不可用，请检查visualization_modules是否存在")
            return
            
        if not self.json_file_var.get():
            messagebox.showerror("错误", "请选择JSON文件")
            return
        
        if not os.path.exists(self.json_file_var.get()):
            messagebox.showerror("错误", "JSON文件不存在")
            return
        
        # 在新线程中运行可视化
        thread = threading.Thread(target=self.run_visualization)
        thread.daemon = True
        thread.start()
    
    def run_visualization(self):
        """运行可视化过程"""
        try:
            input_file = self.json_file_var.get()
            self.log_visualization(f"开始处理文件: {input_file}")
            
            # 从文件名解析GPT版本
            filename = os.path.basename(input_file)
            gpt_version = None
            if filename.startswith('gpt'):
                # 解析如 gpt4.bedroom.k-similar.k_8.px_regular.json
                parts = filename.split('.')
                if parts:
                    gpt_version = parts[0]  # 提取 gpt4, gpt3.5 等
            
            self.log_visualization(f"检测到GPT版本: {gpt_version if gpt_version else '未知'}")
            
            # 读取数据
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                self.log_visualization("❌ JSON文件为空或无效！")
                messagebox.showerror("错误", "JSON文件为空或无效！")
                return
            
            # 获取 top_n（从第一个场景推断）
            first_scene = data[0] if data else {}
            sorted_imgs = first_scene.get('sorted_ids', [])
            top_n = len(sorted_imgs)
            
            folder_name = f"top{top_n}_{gpt_version}" if gpt_version else f"top{top_n}"
            self.log_visualization(f"处理 {len(data)} 个场景，配置: {folder_name}")
            
            # 1. 生成所有 HTML 文件
            if self.generate_html_var.get():
                self.log_visualization("生成HTML文件...")
                for i, scene_data in enumerate(data):
                    scene_id = scene_data.get('query_id', f'Scene_{i}')
                    room_name = scene_id.split('_')[-1] if '_' in scene_id else f'scene_{i}'
                    
                    self.log_visualization(f"  处理HTML {i+1}/{len(data)}: {room_name}")
                    
                    try:
                        fig, query_img, sorted_imgs_current = visualize_scene(scene_data, scene_id)
                        top_n_current = len(sorted_imgs_current) if sorted_imgs_current else 0
                        
                        output_path = get_output_path(f"scene_{room_name}_top{top_n_current}", 
                                                    top_n_current, gpt_version)
                        save_and_open_html(fig, output_path, auto_open=self.auto_open_var.get() and i==0, 
                                         query_img=query_img, sorted_imgs=sorted_imgs_current)
                        
                    except Exception as e:
                        self.log_visualization(f"    ⚠️ HTML生成失败 {room_name}: {str(e)}")
                        continue
            
            # 2. 生成 benchmark 矩阵
            if self.generate_matrix_var.get():
                self.log_visualization("生成benchmark矩阵...")
                try:
                    matrix_path = create_benchmark_matrix(data, top_n, gpt_version)
                    if matrix_path:
                        self.log_visualization(f"  矩阵保存到: {matrix_path}")
                    else:
                        self.log_visualization("  ⚠️ 矩阵生成失败")
                except Exception as e:
                    self.log_visualization(f"  ❌ 矩阵生成错误: {str(e)}")
            
            self.log_visualization("✅ 可视化完成！")
            self.log_visualization(f"HTML文件保存到: visualization_output/html/{folder_name}/")
            messagebox.showinfo("成功", "可视化完成！")
                
        except Exception as e:
            self.log_visualization(f"❌ 执行错误: {str(e)}")
            messagebox.showerror("错误", f"执行错误: {str(e)}")


def main():
    root = tk.Tk()
    app = LayoutGPTGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 