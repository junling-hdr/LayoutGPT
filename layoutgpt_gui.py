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
from PIL import Image, ImageTk

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
        self.root.geometry("1400x900")
        
        # main window
        self.create_widgets()
        
        # default values
        self.set_defaults()
    
    def create_widgets(self):
        # create notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # layout generation
        self.generation_frame = ttk.Frame(notebook)
        notebook.add(self.generation_frame, text="Layout Generation")
        
        # visualization
        self.visualization_frame = ttk.Frame(notebook)
        notebook.add(self.visualization_frame, text="Visualization")
        
        # custom prompt
        self.custom_prompt_frame = ttk.Frame(notebook)
        notebook.add(self.custom_prompt_frame, text="Custom Prompt")
        
        # partial completion
        self.partial_completion_frame = ttk.Frame(notebook)
        notebook.add(self.partial_completion_frame, text="Partial Completion")
        
        # data query
        self.data_query_frame = ttk.Frame(notebook)
        notebook.add(self.data_query_frame, text="Data Query")
        
        # create layout generation ui
        self.create_generation_ui()
        
        # create visualization ui
        self.create_visualization_ui()
        
        # create custom prompt ui
        self.create_custom_prompt_ui()
        
        # create partial completion ui
        self.create_partial_completion_ui()
        
        # create data query ui
        self.create_data_query_ui()
    
    def create_data_query_ui(self):
        # main frame
        main_frame = ttk.Frame(self.data_query_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # query input group
        query_group = ttk.LabelFrame(main_frame, text="Query Input", padding=10)
        query_group.pack(fill=tk.X, pady=(0, 10))
        
        # data id input
        ttk.Label(query_group, text="Data ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.data_id_var = tk.StringVar()
        id_entry = ttk.Entry(query_group, textvariable=self.data_id_var, width=60)
        id_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        # query button
        ttk.Button(query_group, text="Query", command=self.query_data).grid(row=0, column=2)
        
        # example id
        ttk.Label(query_group, text="Example: 8b7f7e8e-0eae-428d-8c0f-9600435db055_Bedroom-3951", 
                 foreground="gray", font=("TkDefaultFont", 8)).grid(row=1, column=0, columnspan=3, 
                 sticky=tk.W, pady=(5, 0))
        
        # dataset parameters group
        dataset_group = ttk.LabelFrame(main_frame, text="Dataset Parameters", padding=10)
        dataset_group.pack(fill=tk.X, pady=(0, 10))
        
        # room type
        ttk.Label(dataset_group, text="Room Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.query_room_var = tk.StringVar(value="bedroom")
        room_combo = ttk.Combobox(dataset_group, textvariable=self.query_room_var, 
                                 values=["bedroom", "livingroom"], state="readonly")
        room_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # dataset directory
        ttk.Label(dataset_group, text="Dataset Directory:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.query_dataset_dir_var = tk.StringVar(value="ATISS/data_output")
        dataset_entry = ttk.Entry(dataset_group, textvariable=self.query_dataset_dir_var, width=25)
        dataset_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        ttk.Button(dataset_group, text="Browse", command=self.browse_query_dataset_dir).grid(row=0, column=4)
        
        # regular floor plan
        self.query_regular_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dataset_group, text="Regular Floor Plan", 
                       variable=self.query_regular_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        # normalize
        self.query_normalize_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dataset_group, text="Normalize", 
                       variable=self.query_normalize_var).grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # unit
        ttk.Label(dataset_group, text="Unit:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.query_unit_var = tk.StringVar(value="px")
        unit_combo = ttk.Combobox(dataset_group, textvariable=self.query_unit_var, 
                                 values=["px", "m", ""], state="readonly")
        unit_combo.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # path hint
        ttk.Label(dataset_group, text="Path should contain bedroom/bedroom022 etc. subdirectories with .npz files", 
                 foreground="gray", font=("TkDefaultFont", 8)).grid(row=2, column=0, columnspan=5, 
                 sticky=tk.W, pady=(5, 0))
        
        # results display group
        results_group = ttk.LabelFrame(main_frame, text="Query Results", padding=10)
        results_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # create treeview for results
        columns = ("Furniture", "Count")
        self.results_tree = ttk.Treeview(results_group, columns=columns, show="headings", height=10)
        
        # define headings
        self.results_tree.heading("Furniture", text="Furniture Type")
        self.results_tree.heading("Count", text="Count")
        
        # configure column widths
        self.results_tree.column("Furniture", width=200)
        self.results_tree.column("Count", width=100)
        
        # add scrollbar
        scrollbar = ttk.Scrollbar(results_group, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # pack treeview and scrollbar
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # create a horizontal frame for info and image
        info_image_frame = ttk.Frame(main_frame)
        info_image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # info display (left side) - 占用50%宽度
        info_group = ttk.LabelFrame(info_image_frame, text="Scene Information", padding=10)
        info_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.scene_info_text = tk.Text(info_group, height=10, wrap=tk.WORD)
        info_scrollbar = ttk.Scrollbar(info_group, orient=tk.VERTICAL, command=self.scene_info_text.yview)
        self.scene_info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.scene_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # image display (right side) - 固定宽度，但更大
        image_group = ttk.LabelFrame(info_image_frame, text="Scene Visualization", padding=10)
        image_group.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # create label for image display
        self.scene_image_label = tk.Label(image_group, text="No image loaded", 
                                         width=60, height=40, bg="lightgray", 
                                         relief="sunken", bd=2, cursor="hand2")
        self.scene_image_label.pack(padx=10, pady=10)
        
        # 绑定双击事件来放大图片
        self.scene_image_label.bind("<Double-Button-1>", self.open_image_viewer)
        
        # 添加提示标签
        image_hint = tk.Label(image_group, text="Double-click image to view full size", 
                             font=("TkDefaultFont", 8), fg="gray")
        image_hint.pack(pady=(0, 5))
        
        # control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Clear Results", command=self.clear_query_results).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Export Results", command=self.export_query_results).pack(side=tk.LEFT)
    
    def create_generation_ui(self):
        # main frame
        main_frame = ttk.Frame(self.generation_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # basic parameters group
        basic_group = ttk.LabelFrame(main_frame, text="Basic Parameters", padding=10)
        basic_group.pack(fill=tk.X, pady=(0, 10))
        
        # room type
        ttk.Label(basic_group, text="Room Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.room_var = tk.StringVar()
        room_combo = ttk.Combobox(basic_group, textvariable=self.room_var, values=["bedroom", "livingroom"], state="readonly")
        room_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # GPT model
        ttk.Label(basic_group, text="GPT Model:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.gpt_type_var = tk.StringVar()
        gpt_combo = ttk.Combobox(basic_group, textvariable=self.gpt_type_var, 
                                values=["gpt3.5-chat", "gpt4", "gpt-4.1", "gpt-4-turbo", "gpt-4.5-preview", "o3", "o4-mini"], state="readonly")
        gpt_combo.grid(row=0, column=3, sticky=tk.W)
        
        # ICL type
        ttk.Label(basic_group, text="ICL Type:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.icl_type_var = tk.StringVar()
        icl_combo = ttk.Combobox(basic_group, textvariable=self.icl_type_var, 
                                values=["fixed-random", "k-similar"], state="readonly")
        icl_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        
        # K value
        ttk.Label(basic_group, text="K Value:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.k_var = tk.StringVar()
        k_entry = ttk.Entry(basic_group, textvariable=self.k_var, width=10)
        k_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # path parameters group
        path_group = ttk.LabelFrame(main_frame, text="path parameters", padding=10)
        path_group.pack(fill=tk.X, pady=(0, 10))
        
        # dataset directory
        ttk.Label(path_group, text="dataset directory:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.dataset_dir_var = tk.StringVar()
        dataset_entry = ttk.Entry(path_group, textvariable=self.dataset_dir_var, width=40)
        dataset_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(path_group, text="browse", command=self.browse_dataset_dir).grid(row=0, column=2)
        
        # output directory
        ttk.Label(path_group, text="output directory:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(path_group, textvariable=self.output_dir_var, width=40)
        output_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Button(path_group, text="browse", command=self.browse_output_dir).grid(row=1, column=2, pady=(10, 0))
        
        # advanced parameters group
        advanced_group = ttk.LabelFrame(main_frame, text="advanced parameters", padding=10)
        advanced_group.pack(fill=tk.X, pady=(0, 10))
        
        # unit
        ttk.Label(advanced_group, text="unit:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.unit_var = tk.StringVar()
        unit_combo = ttk.Combobox(advanced_group, textvariable=self.unit_var, 
                                 values=["px", "m", ""], state="readonly")
        unit_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # temperature
        ttk.Label(advanced_group, text="temperature:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.temperature_var = tk.StringVar()
        temp_entry = ttk.Entry(advanced_group, textvariable=self.temperature_var, width=10)
        temp_entry.grid(row=0, column=3, sticky=tk.W)
        
        # add temperature hint
        ttk.Label(advanced_group, text="(note: o4-mini/o3 have parameter limitations)", 
                 foreground="gray", font=("TkDefaultFont", 8)).grid(row=0, column=4, 
                 sticky=tk.W, padx=(10, 0))
        
        # iteration times
        ttk.Label(advanced_group, text="iteration times:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.n_iter_var = tk.StringVar()
        iter_entry = ttk.Entry(advanced_group, textvariable=self.n_iter_var, width=10)
        iter_entry.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # maximum validation samples
        ttk.Label(advanced_group, text="maximum validation samples:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.max_samples_var = tk.StringVar()
        samples_entry = ttk.Entry(advanced_group, textvariable=self.max_samples_var, width=10)
        samples_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # add hint
        ttk.Label(advanced_group, text="(leave empty to use all validation data)", 
                 foreground="gray", font=("TkDefaultFont", 8)).grid(row=2, column=2, columnspan=2, 
                 sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        # options group
        options_group = ttk.LabelFrame(main_frame, text="options", padding=10)
        options_group.pack(fill=tk.X, pady=(0, 10))
        
        # checkboxes
        self.normalize_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="normalize", variable=self.normalize_var).grid(row=0, column=0, sticky=tk.W)
        
        self.regular_floor_plan_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="regular floor plan", variable=self.regular_floor_plan_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.verbose_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="detailed output (verbose)", variable=self.verbose_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.auto_visualize_regular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="auto visualize after generation", variable=self.auto_visualize_regular_var).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        self.add_timestamp_regular_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="add timestamp to output files", variable=self.add_timestamp_regular_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        self.no_additional_furniture_regular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="no additional furniture", variable=self.no_additional_furniture_regular_var).grid(row=2, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        self.no_overlapping_furniture_regular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_group, text="no overlapping furniture", variable=self.no_overlapping_furniture_regular_var).grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        
        # control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="start generation", command=self.start_generation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="reset parameters", command=self.reset_generation_params).pack(side=tk.LEFT)
        
        # output log
        log_group = ttk.LabelFrame(main_frame, text="output log", padding=10)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.generation_log = scrolledtext.ScrolledText(log_group, height=8)
        self.generation_log.pack(fill=tk.BOTH, expand=True)
    
    def create_visualization_ui(self):
        # main frame
        main_frame = ttk.Frame(self.visualization_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # file selection group
        file_group = ttk.LabelFrame(main_frame, text="file selection", padding=10)
        file_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(file_group, text="JSON file:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.json_file_var = tk.StringVar()
        json_entry = ttk.Entry(file_group, textvariable=self.json_file_var, width=50)
        json_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(file_group, text="browse", command=self.browse_json_file).grid(row=0, column=2)
        
        # visualization options group
        vis_options_group = ttk.LabelFrame(main_frame, text="visualization options", padding=10)
        vis_options_group.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_html_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(vis_options_group, text="generate HTML file", variable=self.generate_html_var).grid(row=0, column=0, sticky=tk.W)
        
        self.generate_matrix_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(vis_options_group, text="generate benchmark matrix", variable=self.generate_matrix_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.auto_open_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(vis_options_group, text="auto open browser", variable=self.auto_open_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.add_timestamp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(vis_options_group, text="add timestamp to filename", variable=self.add_timestamp_var).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        # add info label
        info_label = ttk.Label(vis_options_group, text="hint: now integrated in GUI, no extra script needed", 
                              foreground="green", font=("TkDefaultFont", 8))
        info_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # control buttons
        vis_control_frame = ttk.Frame(main_frame)
        vis_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(vis_control_frame, text="start visualization", command=self.start_visualization).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(vis_control_frame, text="clear log", command=self.clear_vis_log).pack(side=tk.LEFT)
        
        # furniture stats group
        stats_group = ttk.LabelFrame(main_frame, text="furniture stats", padding=10)
        stats_group.pack(fill=tk.X, pady=(10, 0))
        
        # dataset directory selection (for stats)
        ttk.Label(stats_group, text="dataset directory:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.stats_dataset_dir_var = tk.StringVar()
        stats_dataset_entry = ttk.Entry(stats_group, textvariable=self.stats_dataset_dir_var, width=40)
        stats_dataset_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(stats_group, text="browse", command=self.browse_stats_dataset_dir).grid(row=0, column=2)
        
        # room type selection (for stats)
        ttk.Label(stats_group, text="room type:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.stats_room_var = tk.StringVar()
        stats_room_combo = ttk.Combobox(stats_group, textvariable=self.stats_room_var, 
                                       values=["bedroom", "livingroom"], state="readonly")
        stats_room_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # calculate furniture stats button
        ttk.Button(stats_group, text="calculate furniture stats", command=self.calculate_furniture_stats).grid(row=1, column=2, pady=(10, 0))
        
        # output log
        vis_log_group = ttk.LabelFrame(main_frame, text="output log", padding=10)
        vis_log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.visualization_log = scrolledtext.ScrolledText(vis_log_group, height=12)
        self.visualization_log.pack(fill=tk.BOTH, expand=True)
    
    def create_custom_prompt_ui(self):
        """create custom prompt ui"""
        # main frame
        main_frame = ttk.Frame(self.custom_prompt_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # basic parameters group
        basic_group = ttk.LabelFrame(main_frame, text="Basic Parameters", padding=10)
        basic_group.pack(fill=tk.X, pady=(0, 10))
        
        # room type
        ttk.Label(basic_group, text="Room Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.custom_room_var = tk.StringVar()
        custom_room_combo = ttk.Combobox(basic_group, textvariable=self.custom_room_var, 
                                        values=["bedroom", "livingroom"], state="readonly")
        custom_room_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # GPT model
        ttk.Label(basic_group, text="GPT Model:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.custom_gpt_type_var = tk.StringVar()
        custom_gpt_combo = ttk.Combobox(basic_group, textvariable=self.custom_gpt_type_var, 
                                       values=["gpt3.5-chat", "gpt4", "gpt-4.1", "gpt-4-turbo", "gpt-4.5-preview", "o3", "o4-mini"], state="readonly")
        custom_gpt_combo.grid(row=0, column=3, sticky=tk.W)
        
        # unit
        ttk.Label(basic_group, text="Unit:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.custom_unit_var = tk.StringVar()
        custom_unit_combo = ttk.Combobox(basic_group, textvariable=self.custom_unit_var, 
                                        values=["px", "m", ""], state="readonly")
        custom_unit_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # temperature
        ttk.Label(basic_group, text="Temperature:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.custom_temperature_var = tk.StringVar()
        custom_temp_entry = ttk.Entry(basic_group, textvariable=self.custom_temperature_var, width=10)
        custom_temp_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # top_k (in-context learning examples)
        ttk.Label(basic_group, text="Top-K Examples:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.custom_top_k_var = tk.StringVar()
        custom_top_k_entry = ttk.Entry(basic_group, textvariable=self.custom_top_k_var, width=10)
        custom_top_k_entry.grid(row=2, column=1, sticky=tk.W, pady=(10, 0))
        ttk.Label(basic_group, text="(0 = no examples, 8 = default)", foreground="gray", font=("TkDefaultFont", 8)).grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        
        # iteration times
        ttk.Label(basic_group, text="Iteration Times:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.custom_n_iter_var = tk.StringVar()
        custom_n_iter_entry = ttk.Entry(basic_group, textvariable=self.custom_n_iter_var, width=10)
        custom_n_iter_entry.grid(row=3, column=1, sticky=tk.W, pady=(10, 0))
        ttk.Label(basic_group, text="(1 = single result, 3 = default)", foreground="gray", font=("TkDefaultFont", 8)).grid(row=3, column=2, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        
        # room description group
        desc_group = ttk.LabelFrame(main_frame, text="Room Description", padding=10)
        desc_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(desc_group, text="Description:").pack(anchor=tk.W)
        ttk.Label(desc_group, text='(e.g., "A bedroom with a double bed, two wardrobes and a pendant lamp.")', 
                 foreground="gray", font=("TkDefaultFont", 8)).pack(anchor=tk.W)
        
        self.custom_description_var = tk.StringVar()
        desc_entry = ttk.Entry(desc_group, textvariable=self.custom_description_var, width=80)
        desc_entry.pack(fill=tk.X, pady=(5, 0))
        
        # room size group
        size_group = ttk.LabelFrame(main_frame, text="Room Size Settings", padding=10)
        size_group.pack(fill=tk.X, pady=(0, 10))
        
        # length
        ttk.Label(size_group, text="Max Length:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.custom_length_var = tk.StringVar()
        length_entry = ttk.Entry(size_group, textvariable=self.custom_length_var, width=10)
        length_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # width  
        ttk.Label(size_group, text="Max Width:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.custom_width_var = tk.StringVar()
        width_entry = ttk.Entry(size_group, textvariable=self.custom_width_var, width=10)
        width_entry.grid(row=0, column=3, sticky=tk.W)
        
        # available furniture group
        furniture_group = ttk.LabelFrame(main_frame, text="Available Furniture Types", padding=10)
        furniture_group.pack(fill=tk.X, pady=(0, 10))
        
        # furniture list (from stats file)
        furniture_text = scrolledtext.ScrolledText(furniture_group, height=6, wrap=tk.WORD)
        furniture_text.pack(fill=tk.X)
        
        # Load and display furniture types
        try:
            # Load furniture types from the provided stats file
            furniture_types = [
                "armchair", "bookshelf", "cabinet", "ceiling_lamp", "chair", "children_cabinet", 
                "coffee_table", "desk", "double_bed", "dressing_chair", "dressing_table", 
                "floor_lamp", "kids_bed", "nightstand", "pendant_lamp", "shelf", "single_bed", 
                "sofa", "stool", "table", "tv_stand", "wardrobe"
            ]
            furniture_text.insert(tk.END, "Available furniture for bedroom:\n")
            furniture_text.insert(tk.END, ", ".join(furniture_types))
            furniture_text.config(state=tk.DISABLED)
        except Exception:
            furniture_text.insert(tk.END, "Please load dataset to see available furniture types")
            furniture_text.config(state=tk.DISABLED)
        
        # control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Generate Custom Layout", command=self.start_custom_generation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Reset Custom Parameters", command=self.reset_custom_params).pack(side=tk.LEFT)
        
        # custom options group
        custom_options_group = ttk.LabelFrame(main_frame, text="Custom Options", padding=10)
        custom_options_group.pack(fill=tk.X, pady=(10, 0))
        
        self.auto_visualize_custom_var = tk.BooleanVar(value=False  )
        ttk.Checkbutton(custom_options_group, text="auto visualize after generation", variable=self.auto_visualize_custom_var).grid(row=0, column=0, sticky=tk.W)
        
        self.add_timestamp_custom_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(custom_options_group, text="add timestamp to output files", variable=self.add_timestamp_custom_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.no_additional_furniture_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(custom_options_group, text="no additional furniture", variable=self.no_additional_furniture_custom_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.no_overlapping_furniture_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(custom_options_group, text="no overlapping furniture", variable=self.no_overlapping_furniture_custom_var).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        self.verbose_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(custom_options_group, text="detailed output (verbose)", variable=self.verbose_custom_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        # output log
        log_group = ttk.LabelFrame(main_frame, text="Output Log", padding=10)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.custom_log = scrolledtext.ScrolledText(log_group, height=8)
        self.custom_log.pack(fill=tk.BOTH, expand=True)
    
    def set_defaults(self):
        """set default values"""
        self.room_var.set("bedroom")
        self.gpt_type_var.set("gpt4")
        self.icl_type_var.set("k-similar")
        self.k_var.set("8")
        self.dataset_dir_var.set("./ATISS/data_output")
        self.output_dir_var.set("./llm_output/3D/")
        self.unit_var.set("px")
        self.temperature_var.set("0.7")
        self.n_iter_var.set("1")
        self.max_samples_var.set("10")  # default set to 10 validation samples
        self.normalize_var.set(True)
        self.regular_floor_plan_var.set(True)
        self.verbose_var.set(False)
        # 注意：这些变量需要在GUI创建时初始化
        # self.no_additional_furniture_regular_var.set(False)
        # self.no_overlapping_furniture_regular_var.set(False)
        
        # stats default values
        self.stats_dataset_dir_var.set("./ATISS/data_output")
        self.stats_room_var.set("bedroom")
        
        # custom prompt default values
        self.custom_room_var.set("bedroom")
        self.custom_gpt_type_var.set("gpt4")
        self.custom_unit_var.set("px")
        self.custom_temperature_var.set("1.0")  # 增加随机性，避免每次结果相同
        self.custom_top_k_var.set("8")  # default 8 in-context examples
        self.custom_n_iter_var.set("1")  # default 1 iteration
        self.custom_description_var.set("A bedroom with a double bed, two wardrobes and a pendant lamp.")
        self.custom_length_var.set("273")
        self.custom_width_var.set("256")
        self.verbose_custom_var.set(False)
        self.auto_visualize_custom_var.set(True)
        self.add_timestamp_custom_var.set(True)
        self.no_additional_furniture_custom_var.set(True)
        self.no_overlapping_furniture_custom_var.set(True)
        
        # partial completion default values
        self.partial_room_var.set("bedroom")
        self.partial_gpt_type_var.set("gpt4")
        self.partial_icl_type_var.set("k-similar")
        self.partial_k_var.set("4")
        self.partial_room_condition_var.set("Room Type: bedroom\nRoom Size: max length 300px, max width 250px")
        self.partial_temperature_var.set("0.8")
        self.partial_n_iter_var.set("3")
        self.partial_unit_var.set("px")
        self.partial_no_overlapping_var.set(True)
        self.partial_maintain_symmetry_var.set(True)
        self.partial_enhance_functionality_var.set(True)
        self.partial_verbose_var.set(False)
        self.partial_add_timestamp_var.set(True)
    
    def browse_dataset_dir(self):
        """browse dataset directory"""
        directory = filedialog.askdirectory(title="select dataset directory")
        if directory:
            self.dataset_dir_var.set(directory)
    
    def browse_output_dir(self):
        """browse output directory"""
        directory = filedialog.askdirectory(title="select output directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def browse_json_file(self):
        """browse JSON file"""
        file_path = filedialog.askopenfilename(
            title="select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="./llm_output/3D/"
        )
        if file_path:
            self.json_file_var.set(file_path)
    
    def reset_generation_params(self):
        """reset generation parameters"""
        self.set_defaults()
        self.log_generation("parameters reset to default values")
    
    def log_generation(self, message):
        """log generation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.generation_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.generation_log.see(tk.END)
        self.root.update()
    
    def log_visualization(self, message):
        """log visualization"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.visualization_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.visualization_log.see(tk.END)
        self.root.update()
    
    def clear_vis_log(self):
        """clear visualization log"""
        self.visualization_log.delete(1.0, tk.END)
    
    def log_custom(self, message):
        """log custom generation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.custom_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.custom_log.see(tk.END)
        self.root.update()
    
    def reset_custom_params(self):
        """reset custom parameters"""
        self.custom_room_var.set("bedroom")
        self.custom_gpt_type_var.set("gpt4")
        self.custom_unit_var.set("px")
        self.custom_temperature_var.set("1.0")  # 增加随机性
        self.custom_top_k_var.set("8")
        self.custom_n_iter_var.set("1")
        self.custom_description_var.set("A bedroom with a double bed, two wardrobes and a pendant lamp.")
        self.custom_length_var.set("273")
        self.custom_width_var.set("256")
        self.verbose_custom_var.set(False)
        self.no_additional_furniture_custom_var.set(True)
        self.no_overlapping_furniture_custom_var.set(True)
        self.auto_visualize_custom_var.set(True)
        self.add_timestamp_custom_var.set(True)
        self.log_custom("parameters reset to default values")
    
    def browse_stats_dataset_dir(self):
        """browse stats dataset directory"""
        directory = filedialog.askdirectory(title="select dataset directory (for stats)")
        if directory:
            self.stats_dataset_dir_var.set(directory)
    
    def browse_query_dataset_dir(self):
        """browse query dataset directory"""
        directory = filedialog.askdirectory(title="select dataset directory (for query)")
        if directory:
            self.query_dataset_dir_var.set(directory)
    
    def calculate_furniture_stats(self):
        """calculate furniture stats"""
        if not self.stats_dataset_dir_var.get():
            messagebox.showerror("error", "please select dataset directory")
            return
        
        if not self.stats_room_var.get():
            messagebox.showerror("error", "please select room type")
            return
        
        if not os.path.exists(self.stats_dataset_dir_var.get()):
            messagebox.showerror("error", "dataset directory does not exist")
            return
        
        # run stats calculation in a new thread
        thread = threading.Thread(target=self.run_furniture_stats_calculation)
        thread.daemon = True
        thread.start()
    
    def run_furniture_stats_calculation(self):
        """run furniture stats calculation"""
        try:
            dataset_dir = self.stats_dataset_dir_var.get()
            room_type = self.stats_room_var.get()
            
            self.log_visualization(f"start calculating furniture stats: {room_type}")
            
            # build dataset path
            dataset_prefix = f"{dataset_dir}/{room_type}"
            stats_file_path = f"{dataset_prefix}/dataset_stats.txt"
            
            if not os.path.exists(stats_file_path):
                self.log_visualization(f"[ERROR] stats file does not exist: {stats_file_path}")
                messagebox.showerror("error", f"stats file does not exist: {stats_file_path}")
                return
            
            # read stats info
            with open(stats_file_path, "r") as file:
                stats = json.load(file)
            
            # build detailed stats info
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
            
            # add detailed frequency info
            if 'object_types' in stats and 'class_frequencies' in stats:
                for obj_type in stats['object_types']:
                    freq = stats['class_frequencies'].get(obj_type, 0)
                    furniture_stats["detailed_info"]["frequency_details"].append({
                        "furniture_type": obj_type,
                        "frequency": freq,
                        "display_name": obj_type.replace('_', ' ').title()
                    })
                
                # sort by frequency
                furniture_stats["detailed_info"]["frequency_details"].sort(
                    key=lambda x: x['frequency'], reverse=True
                )
            
            # let user select save location
            save_path = filedialog.asksaveasfilename(
                title="save furniture stats",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"furniture_stats_{room_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if save_path:
                # save stats info
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(furniture_stats, f, indent=4, ensure_ascii=False)
                
                self.log_visualization("[SUCCESS] furniture stats calculation completed!")
                self.log_visualization(f"stats info saved to: {save_path}")
                self.log_visualization(f"furniture type count: {furniture_stats['total_furniture_types']}")
                self.log_visualization(f"available furniture: {furniture_stats['detailed_info']['furniture_list']}")
                
                messagebox.showinfo("success", f"furniture stats info saved to:\n{save_path}")
            else:
                self.log_visualization("[WARNING] user cancelled save")
                
        except Exception as e:
            self.log_visualization(f"[ERROR] stats calculation error: {str(e)}")
            messagebox.showerror("error", f"stats calculation error: {str(e)}")
    
    def query_data(self):
        """query data by id"""
        data_id = self.data_id_var.get().strip()
        if not data_id:
            messagebox.showerror("error", "please enter data ID")
            return
        
        # 在新线程中运行查询
        thread = threading.Thread(target=self.run_data_query, args=(data_id,))
        thread.daemon = True
        thread.start()
    
    def run_data_query(self, data_id):
        """run data query in background thread"""
        try:
            # 准备参数
            query_room = self.query_room_var.get()
            query_dataset_dir = self.query_dataset_dir_var.get()
            query_regular = self.query_regular_var.get()
            query_normalize = self.query_normalize_var.get()
            query_unit = self.query_unit_var.get()
            
            class QueryArgs:
                def __init__(self):
                    self.room = query_room
                    self.dataset_dir = query_dataset_dir
                    self.regular_floor_plan = query_regular
                    self.normalize = query_normalize
                    self.unit = query_unit
            
            args = QueryArgs()
            
            # 查找可能的子目录
            base_dir = args.dataset_dir
            room_type = args.room
            possible_subdirs = [room_type, f"{room_type}022", f"{room_type}_new", f"{room_type}_test"]
            
            found_data = None
            found_subdir = None
            
            self.update_scene_info("Searching for data in subdirectories...")
            
            # 逐个检查可能的子目录
            for subdir in possible_subdirs:
                full_path = os.path.join(base_dir, subdir, data_id)
                npz_path = os.path.join(full_path, 'boxes.npz')
                
                if os.path.exists(npz_path):
                    found_subdir = subdir
                    self.update_scene_info(f"Found data in: {os.path.join(base_dir, subdir)}")
                    break
            
            if not found_subdir:
                error_msg = f"Data ID not found in any subdirectory: {data_id}\nChecked: {', '.join(possible_subdirs)}"
                self.update_scene_info(error_msg)
                messagebox.showerror("error", error_msg)
                return
            
            # 直接读取npz文件
            import numpy as np
            
            # 构建npz文件路径
            npz_path = os.path.join(base_dir, found_subdir, data_id, 'boxes.npz')
            
            self.update_scene_info(f"Loading NPZ data: {npz_path}")
            
            # 直接加载npz数据
            data = np.load(npz_path)
            
            # 从npz文件中提取基本信息
            floor_plan_vertices = data['floor_plan_vertices']
            class_labels = data['class_labels']
            sizes = data['sizes']
            angles = data['angles']
            translations = data['translations']
            
            # 计算原始房间尺寸（直接从npz数据，未经任何处理）
            original_room_length = max(floor_plan_vertices[:, 0]) - min(floor_plan_vertices[:, 0])
            original_room_width = max(floor_plan_vertices[:, 2]) - min(floor_plan_vertices[:, 2])
            
            # 如果需要normalize，计算用于显示的房间尺寸
            if query_normalize:
                norm = min(original_room_length, original_room_width)
                display_room_length = original_room_length / norm
                display_room_width = original_room_width / norm
                if query_unit in ['px', '']:
                    scale_factor = 256
                    display_room_length = int(display_room_length * scale_factor)
                    display_room_width = int(display_room_width * scale_factor)
            else:
                display_room_length = original_room_length
                display_room_width = original_room_width
            
            # 构建condition信息（用于显示的版本）
            condition = f"Condition:\nRoom Type: {query_room}\n"
            if query_unit in ['px', '']:
                condition += f"Room Size: max length {display_room_length}{query_unit}, max width {display_room_width}{query_unit}\n"
            else:
                condition += f"Room Size: max length {display_room_length:.2f}{query_unit}, max width {display_room_width:.2f}{query_unit}\n"
            
            # 使用真实的家具类型映射表（基于ATISS数据集）
            furniture_types = [
                "armchair",
                "bookshelf", 
                "cabinet",
                "ceiling_lamp",
                "chair",
                "children_cabinet",
                "coffee_table",
                "desk",
                "double_bed",
                "dressing_chair",
                "dressing_table",
                "floor_lamp",
                "kids_bed",
                "nightstand",
                "pendant_lamp",
                "shelf",
                "single_bed",
                "sofa",
                "stool",
                "table",
                "tv_stand",
                "wardrobe"
            ]
            
            # 构建layout信息
            layout = "Layout:\n"
            furniture_counts = {}
            
            for i, (label, size, angle, loc) in enumerate(zip(class_labels, sizes, angles, translations)):
                # 获取家具类型索引
                label_idx = np.where(label)[0][0] if len(np.where(label)[0]) > 0 else i
                # 从furniture_types列表中获取家具类型名称
                furniture_type = furniture_types[label_idx] if label_idx < len(furniture_types) else f"unknown_furniture_{label_idx}"
                
                length, height, width = size * 2  # 恢复实际尺寸
                orientation = round(angle[0] / 3.1415926 * 180)
                dx, dz, dy = loc
                
                layout += f"{furniture_type} {{length: {length:.2f}; "
                layout += f"width: {width:.2f}; height: {height:.2f}; "
                layout += f"left: {dx:.2f}; top: {dy:.2f}; depth: {dz:.2f}; "
                layout += f"orientation: {orientation} degrees;}}\n"
                
                # 统计家具数量
                furniture_counts[furniture_type] = furniture_counts.get(furniture_type, 0) + 1
            
            # 创建meta_data字典
            meta_data = dict(data)
            
            # 查找对应的图片文件
            image_path = os.path.join(base_dir, found_subdir, data_id, 'rendered_scene_256.png')
            image_data = None
            if os.path.exists(image_path):
                try:
                    # 保存图片路径供查看器使用
                    self.current_image_path = image_path
                    # 加载图片
                    pil_image = Image.open(image_path)
                    # 调整图片大小以适应显示区域（大尺寸）
                    pil_image = pil_image.resize((600, 600), Image.Resampling.LANCZOS)
                    image_data = ImageTk.PhotoImage(pil_image)
                    self.update_scene_info(f"Image loaded: {image_path}")
                except Exception as e:
                    self.update_scene_info(f"Error loading image: {str(e)}")
            else:
                self.current_image_path = None
                self.update_scene_info(f"Image not found: {image_path}")
            
            # 更新结果显示
            self.root.after(0, self.update_query_results, furniture_counts, condition, layout, meta_data, found_subdir, image_data)
            
        except Exception as e:
            error_msg = f"Query error: {str(e)}"
            self.root.after(0, self.update_scene_info, error_msg)
            messagebox.showerror("error", error_msg)
    
    def parse_furniture_from_layout(self, layout):
        """parse furniture information from layout string"""
        furniture_counts = {}
        
        # 按行分割layout
        lines = layout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('Layout:') and '{' in line:
                # 提取家具类型（在{之前的部分）
                furniture_type = line.split('{')[0].strip()
                if furniture_type:
                    furniture_counts[furniture_type] = furniture_counts.get(furniture_type, 0) + 1
        
        return furniture_counts
    
    def update_query_results(self, furniture_counts, condition, layout, meta_data, found_subdir=None, image_data=None):
        """update query results in main thread"""
        # 清空之前的结果
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 添加新结果
        for furniture, count in sorted(furniture_counts.items()):
            self.results_tree.insert("", "end", values=(furniture, count))
        
        # 更新图片显示
        if image_data:
            self.scene_image_label.configure(image=image_data, text="")
            # 保存图片引用，防止被垃圾回收
            self.scene_image_label.image = image_data
        else:
            self.scene_image_label.configure(image="", text="No image available")
            self.scene_image_label.image = None
        
        # 更新场景信息
        info_text = f"Data ID: {self.data_id_var.get()}\n"
        if found_subdir:
            info_text += f"Found in subdirectory: {found_subdir}\n\n"
        
        # 提取原始房间尺寸信息（未normalize）
        room_size_info = ""
        if 'floor_plan_vertices' in meta_data:
            vertices = meta_data['floor_plan_vertices']
            original_room_length = max(vertices[:, 0]) - min(vertices[:, 0])
            original_room_width = max(vertices[:, 2]) - min(vertices[:, 2])
            room_size_info = f"Room Dimensions: {round(original_room_length * 51.2)} x {round(original_room_width * 51.2)} (original units)\n"
        
        info_text += room_size_info
        info_text += f"Total Furniture Items: {sum(furniture_counts.values())}\n"
        info_text += f"Unique Furniture Types: {len(furniture_counts)}\n\n"
        
        # 添加家具列表摘要（自然语言格式）
        furniture_summary = self.generate_furniture_description(furniture_counts, self.data_id_var.get())
        info_text += f"Furniture Summary: {furniture_summary}\n\n"
        
        info_text += f"Condition:\n{condition}\n\nLayout:\n{layout}\n\n"
        
        # 添加元数据信息
        if 'room_layout' in meta_data:
            room_layout_shape = meta_data['room_layout'].shape if hasattr(meta_data['room_layout'], 'shape') else str(meta_data['room_layout'])
            info_text += f"Room Layout Shape: {room_layout_shape}\n"
        
        if 'floor_plan_vertices' in meta_data:
            info_text += f"Floor Plan Vertices: {len(meta_data['floor_plan_vertices'])} points\n"
        
        self.scene_info_text.delete(1.0, tk.END)
        self.scene_info_text.insert(1.0, info_text)
    
    def update_scene_info(self, message):
        """update scene info text (thread-safe)"""
        def _update():
            self.scene_info_text.delete(1.0, tk.END)
            self.scene_info_text.insert(1.0, message)
        
        self.root.after(0, _update)
    
    def clear_query_results(self):
        """clear query results"""
        # 清空结果表格
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 清空场景信息
        self.scene_info_text.delete(1.0, tk.END)
        
        # 清空图片显示
        self.scene_image_label.configure(image="", text="No image loaded")
        self.scene_image_label.image = None
        
        # 清空输入
        self.data_id_var.set("")
    
    def generate_furniture_description(self, furniture_counts, data_id):
        """生成自然语言的家具描述"""
        if not furniture_counts:
            return "No furniture found."
        
        # 确定房间类型
        room_type = "bedroom"  # 默认
        if "bedroom" in data_id.lower():
            room_type = "bedroom"
        elif "living" in data_id.lower():
            room_type = "living room"
        elif "dining" in data_id.lower():
            room_type = "dining room"
        
        # 数字到英文的映射
        number_words = {
            1: "a", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"
        }
        
        # 构建家具描述列表
        furniture_descriptions = []
        
        for furniture, count in sorted(furniture_counts.items()):
            # 处理家具名称（去掉下划线，使其更自然）
            furniture_name = furniture.replace("_", " ")
            
            if count == 1:
                if furniture_name[0].lower() in 'aeiou':
                    furniture_descriptions.append(f"an {furniture_name}")
                else:
                    furniture_descriptions.append(f"a {furniture_name}")
            else:
                # 处理复数形式
                if furniture_name.endswith('y'):
                    plural_name = furniture_name[:-1] + "ies"
                elif furniture_name.endswith(('s', 'sh', 'ch', 'x', 'z')):
                    plural_name = furniture_name + "es"
                else:
                    plural_name = furniture_name + "s"
                
                count_word = number_words.get(count, str(count))
                furniture_descriptions.append(f"{count_word} {plural_name}")
        
        # 组合描述
        if len(furniture_descriptions) == 1:
            description = f"A {room_type} with {furniture_descriptions[0]}."
        elif len(furniture_descriptions) == 2:
            description = f"A {room_type} with {furniture_descriptions[0]} and {furniture_descriptions[1]}."
        else:
            # 多个家具，用逗号分隔，最后用and连接
            all_but_last = ", ".join(furniture_descriptions[:-1])
            description = f"A {room_type} with {all_but_last} and {furniture_descriptions[-1]}."
        
        return description
    
    def open_image_viewer(self, event=None):
        """打开图片查看器窗口"""
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            messagebox.showinfo("Info", "No image to display")
            return
        
        if not os.path.exists(self.current_image_path):
            messagebox.showerror("Error", "Image file not found")
            return
        
        # 创建新窗口
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title("Scene Image Viewer")
        viewer_window.geometry("800x800")
        
        try:
            # 加载原始尺寸的图片
            pil_image = Image.open(self.current_image_path)
            # 调整到合适的查看尺寸
            pil_image = pil_image.resize((750, 750), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_image)
            
            # 创建标签显示图片
            image_label = tk.Label(viewer_window, image=photo)
            image_label.pack(padx=20, pady=20)
            
            # 保存图片引用
            image_label.image = photo
            
            # 添加关闭按钮
            close_btn = tk.Button(viewer_window, text="Close", command=viewer_window.destroy)
            close_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            viewer_window.destroy()
    
    def export_query_results(self):
        """export query results"""
        # 检查是否有结果
        items = self.results_tree.get_children()
        if not items:
            messagebox.showwarning("warning", "No results to export")
            return
        
        # 准备导出数据
        results = []
        for item in items:
            values = self.results_tree.item(item)['values']
            results.append({
                "furniture_type": values[0],
                "count": values[1]
            })
        
        # 选择保存位置
        save_path = filedialog.asksaveasfilename(
            title="Export Query Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"query_results_{self.data_id_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if save_path:
            try:
                if save_path.endswith('.csv'):
                    # 导出为CSV
                    import csv
                    with open(save_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Furniture Type', 'Count'])
                        for result in results:
                            writer.writerow([result['furniture_type'], result['count']])
                else:
                    # 导出为JSON
                    export_data = {
                        "data_id": self.data_id_var.get(),
                        "exported_at": datetime.now().isoformat(),
                        "furniture_counts": results,
                        "total_items": sum(r['count'] for r in results),
                        "unique_types": len(results)
                    }
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=4, ensure_ascii=False)
                
                messagebox.showinfo("success", f"Results exported to:\n{save_path}")
                
            except Exception as e:
                messagebox.showerror("error", f"Export error: {str(e)}")
    
    def validate_generation_params(self):
        """validate generation parameters"""
        if not self.room_var.get():
            messagebox.showerror("error", "please select room type")
            return False
        
        if not self.gpt_type_var.get():
            messagebox.showerror("error", "please select GPT model")
            return False
        
        try:
            k_val = int(self.k_var.get())
            if k_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "K value must be a positive integer")
            return False
        
        if not os.path.exists(self.dataset_dir_var.get()):
            messagebox.showerror("error", "dataset directory does not exist")
            return False
        
        return True
    
    def build_generation_command(self):
        """build generation command"""
        cmd = [sys.executable, "run_layoutgpt_3d_clean.py"]
        
        # basic parameters
        cmd.extend(["--room", self.room_var.get()])
        cmd.extend(["--gpt_type", self.gpt_type_var.get()])
        cmd.extend(["--icl_type", self.icl_type_var.get()])
        cmd.extend(["--K", self.k_var.get()])
        cmd.extend(["--dataset_dir", self.dataset_dir_var.get()])
        cmd.extend(["--base_output_dir", self.output_dir_var.get()])
        cmd.extend(["--unit", self.unit_var.get()])
        cmd.extend(["--temperature", self.temperature_var.get()])
        cmd.extend(["--n_iter", self.n_iter_var.get()])
        
        # optional parameters
        if self.max_samples_var.get():
            cmd.extend(["--max_val_samples", self.max_samples_var.get()])
        
        # boolean options
        if self.normalize_var.get():
            cmd.append("--normalize")
        if self.regular_floor_plan_var.get():
            cmd.append("--regular_floor_plan")
        if self.verbose_var.get():
            cmd.append("--verbose")
        if self.add_timestamp_regular_var.get():
            cmd.append("--add_timestamp")
        if self.no_additional_furniture_regular_var.get():
            cmd.append("--no_additional_furniture")
        if self.no_overlapping_furniture_regular_var.get():
            cmd.append("--no_overlapping_furniture")
        
        return cmd
    
    def start_generation(self):
        """start generation"""
        if not self.validate_generation_params():
            return
        
        # 在新线程中运行生成
        thread = threading.Thread(target=self.run_generation)
        thread.daemon = True
        thread.start()
    
    def run_generation(self):
        """run generation"""
        try:
            cmd = self.build_generation_command()
            self.log_generation(f"start executing command: {' '.join(cmd)}")
            
            # execute command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时输出
            generated_file_path = None
            generated_timestamp = None
            
            for line in process.stdout:
                line = line.strip()
                self.log_generation(line)
                
                # 提取输出文件路径和时间戳
                if "prediction results written to" in line:
                    generated_file_path = line.split("written to ")[-1]
                    # 从文件名中提取时间戳
                    import re
                    timestamp_match = re.search(r'_(\d{8}_\d{6})\.json$', generated_file_path)
                    if timestamp_match:
                        generated_timestamp = timestamp_match.group(1)
            
            process.wait()
            
            if process.returncode == 0:
                self.log_generation("[SUCCESS] generation completed!")
                
                # 自动可视化
                if self.auto_visualize_regular_var.get() and generated_file_path and os.path.exists(generated_file_path):
                    self.log_generation("Starting auto visualization...")
                    self.auto_visualize_file(generated_file_path, generated_timestamp)
                
                messagebox.showinfo("success", "layout generation completed!")
            else:
                self.log_generation(f"[ERROR] generation failed, exit code: {process.returncode}")
                messagebox.showerror("error", "generation failed, please check log")
                
        except Exception as e:
            self.log_generation(f"[ERROR] execution error: {str(e)}")
            messagebox.showerror("error", f"execution error: {str(e)}")
    
    def start_visualization(self):
        """start visualization"""
        if not VISUALIZATION_AVAILABLE:
            messagebox.showerror("error", "visualization module not available, please check visualization_modules")
            return
            
        if not self.json_file_var.get():
            messagebox.showerror("error", "please select JSON file")
            return
        
        if not os.path.exists(self.json_file_var.get()):
            messagebox.showerror("error", "JSON file does not exist")
            return
        
        # run visualization in a new thread
        thread = threading.Thread(target=self.run_visualization)
        thread.daemon = True
        thread.start()
    
    def run_visualization(self):
        """run visualization"""
        try:
            input_file = self.json_file_var.get()
            self.log_visualization(f"start processing file: {input_file}")
            
            # Generate unified timestamp for this visualization session
            unified_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if self.add_timestamp_var.get() else None
            if unified_timestamp:
                self.log_visualization(f"Using unified timestamp: {unified_timestamp}")
            
            # read data first to check if it's custom
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                self.log_visualization("[ERROR] JSON file is empty or invalid!")
                messagebox.showerror("error", "JSON file is empty or invalid!")
                return
            
            # 检测是否为custom生成的结果
            is_custom = False
            first_scene = data[0] if data else {}
            
            # 检测方法：
            # 1. 检查是否有 'is_custom' 标记
            # 2. 检查 query_id 是否以 'custom_' 开头
            # 3. 检查文件路径是否包含 'custom'
            if (first_scene.get('is_custom', False) or 
                (first_scene.get('query_id', '').startswith('custom_')) or
                'custom' in input_file.lower()):
                is_custom = True
                self.log_visualization("[SUCCESS] Detected custom generation results")
            else:
                self.log_visualization("[INFO] Processing standard benchmark results")
            
            # 从文件名解析GPT版本
            filename = os.path.basename(input_file)
            gpt_version = None
            if filename.startswith('gpt') or filename.startswith('custom_gpt'):
                # 智能解析GPT版本名称
                # 对于 gpt3.5-chat.bedroom... 需要取 gpt3.5-chat
                # 对于 gpt4.bedroom... 需要取 gpt4
                # 对于 custom_gpt4_bedroom... 需要取 gpt4
                parts = filename.split('.')
                if filename.startswith('custom_'):
                    # 处理 custom_gpt4_bedroom_20241201_123456.json 格式
                    custom_parts = filename.split('_')
                    if len(custom_parts) >= 2:
                        gpt_version = custom_parts[1]  # 取 gpt4 部分
                elif len(parts) >= 2:
                    # 检查特殊格式的GPT版本
                    if parts[0] == 'gpt3' and len(parts) >= 3 and parts[1] == '5-chat':
                        gpt_version = 'gpt3.5-chat'
                    elif parts[0] == 'gpt-4' and len(parts) >= 3 and parts[1] == '1':
                        gpt_version = 'gpt-4.1'
                    elif parts[0] == 'gpt-4-turbo':
                        gpt_version = 'gpt-4-turbo'
                    elif parts[0] == 'gpt-4' and len(parts) >= 3 and parts[1] == '5-preview':
                        gpt_version = 'gpt-4.5-preview'
                    elif parts[0] == 'o3':
                        gpt_version = 'o3'
                    elif parts[0] == 'o4-mini':
                        gpt_version = 'o4-mini'
                    else:
                        gpt_version = parts[0]  # 普通情况，如 gpt4
            
            self.log_visualization(f"detected GPT version: {gpt_version if gpt_version else 'unknown'}")
            
            # 获取 top_n（从第一个场景推断）
            sorted_imgs = first_scene.get('sorted_ids', [])
            top_n = len(sorted_imgs)
            # 对于custom生成，如果没有sorted_ids，默认使用0
            if is_custom and top_n == 0:
                top_n = 0
                self.log_visualization("Custom generation detected - single result, no in-context examples")
            
            # 为了路径安全，清理GPT版本名称中的特殊字符
            safe_gpt_version = gpt_version.replace('.', '_').replace('-', '_') if gpt_version else None
            if is_custom:
                folder_name = f"custom_top{top_n}_{safe_gpt_version}" if safe_gpt_version else f"custom_top{top_n}"
                output_path_prefix = f"visualization_output/custom/html/"
            else:
                folder_name = f"top{top_n}_{safe_gpt_version}" if safe_gpt_version else f"top{top_n}"
                output_path_prefix = f"visualization_output/html/"
            
            if is_custom:
                self.log_visualization(f"processing custom generation: 1 scene, config: {folder_name}")
            else:
                self.log_visualization(f"processing {len(data)} scenes, config: {folder_name}")
            
            # generate all HTML files
            if self.generate_html_var.get():
                self.log_visualization("generating HTML files...")
                
                # 按场景分组数据，处理多个iteration
                scenes_by_base_id = {}
                for scene_data in data:
                    scene_id = scene_data.get('query_id', f'Scene_{len(scenes_by_base_id)}')
                    
                    # 提取基础scene ID（去掉iteration后缀）
                    if '_iter' in scene_id:
                        base_scene_id = scene_id.split('_iter')[0]
                        iteration_num = scene_data.get('iteration', 1)
                    else:
                        base_scene_id = scene_id
                        iteration_num = 1
                    
                    if base_scene_id not in scenes_by_base_id:
                        scenes_by_base_id[base_scene_id] = []
                    scenes_by_base_id[base_scene_id].append((scene_data, iteration_num))
                
                # 为每个场景的每个iteration生成HTML
                total_files = sum(len(iterations) for iterations in scenes_by_base_id.values())
                file_count = 0
                
                for base_scene_id, iterations in scenes_by_base_id.items():
                    room_name = base_scene_id.split('_')[-1] if '_' in base_scene_id else base_scene_id
                    
                    # 按iteration编号排序
                    iterations.sort(key=lambda x: x[1])
                    
                    for scene_data, iteration_num in iterations:
                        file_count += 1
                        iteration_suffix = f"_iter{iteration_num}" if len(iterations) > 1 else ""
                        
                        self.log_visualization(f"processing HTML {file_count}/{total_files}: {room_name}{iteration_suffix}")
                        
                        try:
                            fig, query_img, sorted_imgs_current = visualize_scene(scene_data, scene_data.get('query_id'))
                            top_n_current = len(sorted_imgs_current) if sorted_imgs_current else 0
                            
                            # 生成文件名，包含iteration后缀
                            if is_custom and top_n_current == 0:
                                base_filename = f"scene_{room_name}_custom{iteration_suffix}"
                                output_path = get_output_path(base_filename, 
                                                            0, safe_gpt_version, is_custom=True, 
                                                            add_timestamp=self.add_timestamp_var.get(), 
                                                            timestamp=unified_timestamp)
                            else:
                                base_filename = f"scene_{room_name}_top{top_n_current}{iteration_suffix}"
                                output_path = get_output_path(base_filename, 
                                                            top_n_current, safe_gpt_version, is_custom=is_custom, 
                                                            add_timestamp=self.add_timestamp_var.get(), 
                                                            timestamp=unified_timestamp)
                            
                            save_and_open_html(fig, output_path, auto_open=self.auto_open_var.get() and file_count==1, 
                                             query_img=query_img, sorted_imgs=sorted_imgs_current)
                            
                        except Exception as e:
                            self.log_visualization(f"    ⚠️ HTML generation failed {room_name}{iteration_suffix}: {str(e)}")
                            continue
            
            # generate benchmark matrix
            if self.generate_matrix_var.get():
                self.log_visualization("generating benchmark matrix image...")
                try:
                    matrix_path = create_benchmark_matrix(data, top_n, safe_gpt_version, is_custom=is_custom, 
                                                        add_timestamp=self.add_timestamp_var.get(), 
                                                        timestamp=unified_timestamp)
                    if matrix_path:
                        self.log_visualization(f"   matrix saved to: {matrix_path}")
                    else:
                        self.log_visualization("  ⚠️ matrix generation failed")
                except Exception as e:
                    self.log_visualization(f"  [ERROR] matrix generation error: {str(e)}")
            
            self.log_visualization("[SUCCESS] visualization completed!")
            self.log_visualization(f"HTML files saved to: {output_path_prefix}{folder_name}/")
            messagebox.showinfo("success", "visualization completed!")
                
        except Exception as e:
            self.log_visualization(f"[ERROR] execution error: {str(e)}")
            messagebox.showerror("error", f"execution error: {str(e)}")
    
    def validate_custom_params(self):
        """validate custom parameters"""
        if not self.custom_room_var.get():
            messagebox.showerror("error", "please select room type")
            return False
        
        if not self.custom_gpt_type_var.get():
            messagebox.showerror("error", "please select GPT model")
            return False
            
        if not self.custom_description_var.get().strip():
            messagebox.showerror("error", "please enter room description")
            return False
        
        try:
            length = int(self.custom_length_var.get())
            width = int(self.custom_width_var.get())
            if length <= 0 or width <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "room size must be positive integers")
            return False
        
        try:
            top_k = int(self.custom_top_k_var.get())
            if top_k < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "top-k examples must be non-negative integers")
            return False
        
        try:
            n_iter = int(self.custom_n_iter_var.get())
            if n_iter < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "iteration times must be positive integers")
            return False
            
        return True
    
    def start_custom_generation(self):
        """start custom generation"""
        if not self.validate_custom_params():
            return
        
        # run custom generation in a new thread
        thread = threading.Thread(target=self.run_custom_generation)
        thread.daemon = True
        thread.start()
    
    def run_custom_generation(self):
        """run custom generation"""
        try:
            self.log_custom("starting custom layout generation...")
            
            # build custom condition
            room_type = self.custom_room_var.get()
            length = self.custom_length_var.get()
            width = self.custom_width_var.get()
            unit = self.custom_unit_var.get()
            description = self.custom_description_var.get().strip()
            
            # create custom condition following the format
            custom_condition = f"Condition:\n"
            custom_condition += f"Room Type: {room_type}\n"
            custom_condition += f"Room Size: max length {length}{unit}, max width {width}{unit}\n"
            custom_condition += f"Description: {description}"
            
            self.log_custom(f"custom condition created:\n{custom_condition}")
            
            # build command for custom generation
            cmd = self.build_custom_generation_command(custom_condition)
            self.log_custom(f"executing command: {' '.join(cmd)}")
            
            # execute command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # real-time output
            generated_file_path = None
            generated_timestamp = None
            
            for line in process.stdout:
                line = line.strip()
                self.log_custom(line)
                
                # 提取输出文件路径和时间戳
                if "Custom generation results written to" in line:
                    generated_file_path = line.split("written to ")[-1]
                    # 从文件名中提取时间戳
                    import re
                    timestamp_match = re.search(r'_(\d{8}_\d{6})\.json$', generated_file_path)
                    if timestamp_match:
                        generated_timestamp = timestamp_match.group(1)
            
            process.wait()
            
            if process.returncode == 0:
                self.log_custom("[SUCCESS] custom generation completed!")
                
                # 自动可视化
                if self.auto_visualize_custom_var.get() and generated_file_path and os.path.exists(generated_file_path):
                    self.log_custom("Starting auto visualization...")
                    self.auto_visualize_file(generated_file_path, generated_timestamp)
                
                messagebox.showinfo("success", "custom layout generation completed!")
            else:
                self.log_custom(f"[ERROR] custom generation failed, exit code: {process.returncode}")
                messagebox.showerror("error", "custom generation failed, please check log")
                
        except Exception as e:
            self.log_custom(f"[ERROR] execution error: {str(e)}")
            messagebox.showerror("error", f"execution error: {str(e)}")
    
    def build_custom_generation_command(self, custom_condition):
        """build custom generation command"""
        cmd = [sys.executable, "run_layoutgpt_custom.py"]
        
        # basic parameters - 使用新的参数名称
        cmd.extend(["--room", self.custom_room_var.get()])
        cmd.extend(["--gpt_type", self.custom_gpt_type_var.get()])
        cmd.extend(["--unit", self.custom_unit_var.get()])
        cmd.extend(["--temperature", self.custom_temperature_var.get()])
        cmd.extend(["--K", self.custom_top_k_var.get()])  # 改为大写K
        cmd.extend(["--n_iter", self.custom_n_iter_var.get()])
        cmd.extend(["--custom_condition", custom_condition])
        if self.add_timestamp_custom_var.get():
            cmd.append("--add_timestamp")
        if self.no_additional_furniture_custom_var.get():
            cmd.append("--no_additional_furniture")
        if self.no_overlapping_furniture_custom_var.get():
            cmd.append("--no_overlapping_furniture")
        if self.verbose_custom_var.get():
            cmd.append("--verbose")
        
        return cmd

    def auto_visualize_file(self, json_file_path, timestamp):
        """自动可视化生成的JSON文件"""
        try:
            self.log_visualization(f"Auto visualizing: {json_file_path}")
            self.log_visualization(f"Using timestamp: {timestamp}")
            
            # 读取数据
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                self.log_visualization("[ERROR] JSON file is empty!")
                return
            
            # 检测是否为custom生成的结果
            is_custom = False
            first_scene = data[0] if data else {}
            
            if (first_scene.get('is_custom', False) or 
                (first_scene.get('query_id', '').startswith('custom_')) or
                'custom' in json_file_path.lower()):
                is_custom = True
                self.log_visualization("[SUCCESS] Auto-visualizing custom generation results")
            else:
                self.log_visualization("[INFO] Auto-visualizing standard benchmark results")
            
            # 从文件名解析GPT版本
            filename = os.path.basename(json_file_path)
            gpt_version = None
            if filename.startswith('gpt') or filename.startswith('custom_gpt'):
                parts = filename.split('.')
                if filename.startswith('custom_'):
                    custom_parts = filename.split('_')
                    if len(custom_parts) >= 2:
                        gpt_version = custom_parts[1]
                elif len(parts) >= 2:
                    if parts[0] == 'gpt3' and len(parts) >= 3 and parts[1] == '5-chat':
                        gpt_version = 'gpt3.5-chat'
                    elif parts[0] == 'gpt-4' and len(parts) >= 3 and parts[1] == '1':
                        gpt_version = 'gpt-4.1'
                    elif parts[0] == 'gpt-4-turbo':
                        gpt_version = 'gpt-4-turbo'
                    elif parts[0] == 'gpt-4' and len(parts) >= 3 and parts[1] == '5-preview':
                        gpt_version = 'gpt-4.5-preview'
                    elif parts[0] == 'o3':
                        gpt_version = 'o3'
                    elif parts[0] == 'o4-mini':
                        gpt_version = 'o4-mini'
                    else:
                        gpt_version = parts[0]
            
            # 获取 top_n
            sorted_imgs = first_scene.get('sorted_ids', [])
            top_n = len(sorted_imgs)
            if is_custom and top_n == 0:
                top_n = 0
            
            safe_gpt_version = gpt_version.replace('.', '_').replace('-', '_') if gpt_version else None
            
            self.log_visualization(f"Processing {len(data)} scenes with timestamp: {timestamp}")
            
            # 生成HTML文件 - 支持多iteration
            # 按场景分组数据，处理多个iteration
            scenes_by_base_id = {}
            for scene_data in data:
                scene_id = scene_data.get('query_id', f'Scene_{len(scenes_by_base_id)}')
                
                # 提取基础scene ID（去掉iteration后缀）
                if '_iter' in scene_id:
                    base_scene_id = scene_id.split('_iter')[0]
                    iteration_num = scene_data.get('iteration', 1)
                else:
                    base_scene_id = scene_id
                    iteration_num = 1
                
                if base_scene_id not in scenes_by_base_id:
                    scenes_by_base_id[base_scene_id] = []
                scenes_by_base_id[base_scene_id].append((scene_data, iteration_num))
            
            # 为每个场景的每个iteration生成HTML
            total_files = sum(len(iterations) for iterations in scenes_by_base_id.values())
            file_count = 0
            
            for base_scene_id, iterations in scenes_by_base_id.items():
                room_name = base_scene_id.split('_')[-1] if '_' in base_scene_id else base_scene_id
                
                # 按iteration编号排序
                iterations.sort(key=lambda x: x[1])
                
                for scene_data, iteration_num in iterations:
                    file_count += 1
                    iteration_suffix = f"_iter{iteration_num}" if len(iterations) > 1 else ""
                    
                    self.log_visualization(f"Processing HTML {file_count}/{total_files}: {room_name}{iteration_suffix}")
                    
                    try:
                        fig, query_img, sorted_imgs_current = visualize_scene(scene_data, scene_data.get('query_id'))
                        top_n_current = len(sorted_imgs_current) if sorted_imgs_current else 0
                        
                        # 生成文件名，包含iteration后缀
                        if is_custom and top_n_current == 0:
                            base_filename = f"scene_{room_name}_custom{iteration_suffix}"
                            output_path = get_output_path(base_filename, 
                                                        0, safe_gpt_version, is_custom=True, 
                                                        add_timestamp=True, timestamp=timestamp)
                        else:
                            base_filename = f"scene_{room_name}_top{top_n_current}{iteration_suffix}"
                            output_path = get_output_path(base_filename, 
                                                        top_n_current, safe_gpt_version, is_custom=is_custom, 
                                                        add_timestamp=True, timestamp=timestamp)
                        
                        save_and_open_html(fig, output_path, auto_open=False, 
                                         query_img=query_img, sorted_imgs=sorted_imgs_current)
                        
                    except Exception as e:
                        self.log_visualization(f"    ⚠️ HTML generation failed {room_name}{iteration_suffix}: {str(e)}")
                        continue
            
            # 生成benchmark matrix
            self.log_visualization("Generating benchmark matrix image...")
            try:
                matrix_path = create_benchmark_matrix(data, top_n, safe_gpt_version, is_custom=is_custom, 
                                                    add_timestamp=True, timestamp=timestamp)
                if matrix_path:
                    self.log_visualization(f"   Matrix saved to: {matrix_path}")
                else:
                    self.log_visualization("  ⚠️ Matrix generation failed")
            except Exception as e:
                self.log_visualization(f"  [ERROR] Matrix generation error: {str(e)}")
            
            self.log_visualization("[SUCCESS] Auto visualization completed!")
            
        except Exception as e:
            self.log_visualization(f"[ERROR] Auto visualization error: {str(e)}")

    def create_partial_completion_ui(self):
        """创建部分场景补全界面"""
        # main frame
        main_frame = ttk.Frame(self.partial_completion_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # basic parameters group
        basic_group = ttk.LabelFrame(main_frame, text="Basic Parameters", padding=10)
        basic_group.pack(fill=tk.X, pady=(0, 10))
        
        # room type
        ttk.Label(basic_group, text="Room Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.partial_room_var = tk.StringVar()
        partial_room_combo = ttk.Combobox(basic_group, textvariable=self.partial_room_var, 
                                        values=["bedroom", "livingroom"], state="readonly")
        partial_room_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # GPT model
        ttk.Label(basic_group, text="GPT Model:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.partial_gpt_type_var = tk.StringVar()
        partial_gpt_combo = ttk.Combobox(basic_group, textvariable=self.partial_gpt_type_var, 
                                       values=["gpt3.5-chat", "gpt4", "gpt-4.1", "gpt-4-turbo", "gpt-4.5-preview", "o3", "o4-mini"], state="readonly")
        partial_gpt_combo.grid(row=0, column=3, sticky=tk.W)
        
        # ICL parameters
        ttk.Label(basic_group, text="ICL Type:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.partial_icl_type_var = tk.StringVar()
        partial_icl_combo = ttk.Combobox(basic_group, textvariable=self.partial_icl_type_var, 
                                       values=["fixed-random", "k-similar"], state="readonly")
        partial_icl_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        
        # K value
        ttk.Label(basic_group, text="K Examples:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.partial_k_var = tk.StringVar()
        partial_k_entry = ttk.Entry(basic_group, textvariable=self.partial_k_var, width=10)
        partial_k_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # room condition group
        condition_group = ttk.LabelFrame(main_frame, text="Room Condition", padding=10)
        condition_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(condition_group, text="Room Condition (e.g., Room Type: bedroom, Room Size: max length 300px, max width 250px):").pack(anchor=tk.W)
        self.partial_room_condition_var = tk.StringVar()
        condition_entry = ttk.Entry(condition_group, textvariable=self.partial_room_condition_var, width=80)
        condition_entry.pack(fill=tk.X, pady=(5, 0))
        
        # partial layout group
        layout_group = ttk.LabelFrame(main_frame, text="Existing Partial Layout", padding=10)
        layout_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(layout_group, text="Existing Furniture Layout (CSS format):").pack(anchor=tk.W)
        ttk.Label(layout_group, text='Example: double_bed {length: 180px; width: 200px; height: 100px; orientation: 0 degrees; left: 100px; top: 50px; depth: 150px;}', 
                 foreground="gray", font=("TkDefaultFont", 8)).pack(anchor=tk.W)
        
        self.partial_layout_text = scrolledtext.ScrolledText(layout_group, height=8, wrap=tk.WORD)
        self.partial_layout_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # generation parameters group
        gen_params_group = ttk.LabelFrame(main_frame, text="Generation Parameters", padding=10)
        gen_params_group.pack(fill=tk.X, pady=(0, 10))
        
        # temperature
        ttk.Label(gen_params_group, text="Temperature:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.partial_temperature_var = tk.StringVar()
        partial_temp_entry = ttk.Entry(gen_params_group, textvariable=self.partial_temperature_var, width=10)
        partial_temp_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # iterations
        ttk.Label(gen_params_group, text="Iterations:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.partial_n_iter_var = tk.StringVar()
        partial_iter_entry = ttk.Entry(gen_params_group, textvariable=self.partial_n_iter_var, width=10)
        partial_iter_entry.grid(row=0, column=3, sticky=tk.W)
        
        # unit
        ttk.Label(gen_params_group, text="Unit:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.partial_unit_var = tk.StringVar()
        partial_unit_combo = ttk.Combobox(gen_params_group, textvariable=self.partial_unit_var, 
                                        values=["px", "m", ""], state="readonly")
        partial_unit_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # completion options group
        options_group = ttk.LabelFrame(main_frame, text="Completion Options", padding=10)
        options_group.pack(fill=tk.X, pady=(0, 10))
        
        self.partial_no_overlapping_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="No Overlapping Furniture", 
                       variable=self.partial_no_overlapping_var).grid(row=0, column=0, sticky=tk.W)
        
        self.partial_maintain_symmetry_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="Maintain Visual Symmetry", 
                       variable=self.partial_maintain_symmetry_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.partial_enhance_functionality_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="Enhance Functionality", 
                       variable=self.partial_enhance_functionality_var).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.partial_verbose_var = tk.BooleanVar()
        ttk.Checkbutton(options_group, text="Verbose Output", 
                       variable=self.partial_verbose_var).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        self.partial_add_timestamp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_group, text="Add Timestamp", 
                       variable=self.partial_add_timestamp_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        # control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Start Partial Completion", command=self.start_partial_completion).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Reset Parameters", command=self.reset_partial_completion_params).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Load Example", command=self.load_partial_completion_example).pack(side=tk.LEFT, padx=(10, 0))
        
        # output log
        log_group = ttk.LabelFrame(main_frame, text="Output Log", padding=10)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.partial_completion_log = scrolledtext.ScrolledText(log_group, height=8)
        self.partial_completion_log.pack(fill=tk.BOTH, expand=True)

    def log_partial_completion(self, message):
        """log partial completion"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.partial_completion_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.partial_completion_log.see(tk.END)
        self.root.update()
    
    def reset_partial_completion_params(self):
        """reset partial completion parameters"""
        self.partial_room_var.set("bedroom")
        self.partial_gpt_type_var.set("gpt4")
        self.partial_icl_type_var.set("k-similar")
        self.partial_k_var.set("4")
        self.partial_room_condition_var.set("Room Type: bedroom\nRoom Size: max length 300px, max width 250px")
        self.partial_temperature_var.set("0.8")
        self.partial_n_iter_var.set("3")
        self.partial_unit_var.set("px")
        self.partial_no_overlapping_var.set(True)
        self.partial_maintain_symmetry_var.set(True)
        self.partial_enhance_functionality_var.set(True)
        self.partial_verbose_var.set(False)
        self.partial_add_timestamp_var.set(True)
        self.partial_layout_text.delete(1.0, tk.END)
        self.log_partial_completion("parameters reset to default values")
    
    def load_partial_completion_example(self):
        """load partial completion example"""
        example_layout = """double_bed {length: 180px; width: 200px; height: 100px; orientation: 0 degrees; left: 100px; top: 50px; depth: 150px;}
nightstand {length: 40px; width: 30px; height: 60px; orientation: 0 degrees; left: 50px; top: 50px; depth: 130px;}"""
        
        self.partial_layout_text.delete(1.0, tk.END)
        self.partial_layout_text.insert(1.0, example_layout)
        self.log_partial_completion("loaded example partial layout: double bed + one nightstand")
    
    def validate_partial_completion_params(self):
        """validate partial completion parameters"""
        if not self.partial_room_var.get():
            messagebox.showerror("error", "please select room type")
            return False
        
        if not self.partial_gpt_type_var.get():
            messagebox.showerror("error", "please select GPT model")
            return False
        
        if not self.partial_room_condition_var.get().strip():
            messagebox.showerror("error", "please enter room condition")
            return False
        
        partial_layout = self.partial_layout_text.get(1.0, tk.END).strip()
        if not partial_layout:
            messagebox.showerror("error", "please enter existing partial layout")
            return False
        
        try:
            k_val = int(self.partial_k_var.get())
            if k_val < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "K examples must be non-negative integer")
            return False
        
        try:
            temp_val = float(self.partial_temperature_var.get())
            if temp_val < 0 or temp_val > 2:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "temperature must be between 0 and 2")
            return False
        
        try:
            iter_val = int(self.partial_n_iter_var.get())
            if iter_val < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("error", "iterations must be positive integer")
            return False
        
        return True
    
    def start_partial_completion(self):
        """start partial completion"""
        if not self.validate_partial_completion_params():
            return
        
        # run partial completion in a new thread
        thread = threading.Thread(target=self.run_partial_completion)
        thread.daemon = True
        thread.start()
    
    def run_partial_completion(self):
        """run partial completion"""
        try:
            self.log_partial_completion("starting partial scene completion...")
            
            # get parameters
            room_type = self.partial_room_var.get()
            gpt_type = self.partial_gpt_type_var.get()
            icl_type = self.partial_icl_type_var.get()
            k_val = self.partial_k_var.get()
            room_condition = self.partial_room_condition_var.get().strip()
            partial_layout = self.partial_layout_text.get(1.0, tk.END).strip()
            temperature = self.partial_temperature_var.get()
            n_iter = self.partial_n_iter_var.get()
            unit = self.partial_unit_var.get()
            
            self.log_partial_completion(f"parameters: {room_type}, {gpt_type}, {icl_type}, K={k_val}")
            
            # build command
            cmd = [sys.executable, "run_layoutgpt_partial_completion.py"]
            cmd.extend(["--room", room_type])
            cmd.extend(["--gpt_type", gpt_type])
            cmd.extend(["--icl_type", icl_type])
            cmd.extend(["--K", k_val])
            cmd.extend(["--room_condition", room_condition])
            cmd.extend(["--partial_layout", partial_layout])
            cmd.extend(["--temperature", temperature])
            cmd.extend(["--n_iter", n_iter])
            cmd.extend(["--unit", unit])
            
            # add optional flags
            if self.partial_no_overlapping_var.get():
                cmd.append("--no_overlapping_furniture")
            if self.partial_maintain_symmetry_var.get():
                cmd.append("--maintain_symmetry")
            if self.partial_enhance_functionality_var.get():
                cmd.append("--enhance_functionality")
            if self.partial_verbose_var.get():
                cmd.append("--verbose")
            if self.partial_add_timestamp_var.get():
                cmd.append("--add_timestamp")
            
            self.log_partial_completion(f"executing command: {' '.join(cmd)}")
            
            # execute command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # real-time output
            generated_file_path = None
            
            for line in process.stdout:
                line = line.strip()
                self.log_partial_completion(line)
                
                # extract output file path
                if "结果保存至:" in line:
                    generated_file_path = line.split("结果保存至: ")[-1]
            
            process.wait()
            
            if process.returncode == 0:
                self.log_partial_completion("[SUCCESS] partial scene completion completed!")
                messagebox.showinfo("success", "partial scene completion completed!")
            else:
                self.log_partial_completion(f"[ERROR] partial completion failed, exit code: {process.returncode}")
                messagebox.showerror("error", "partial completion failed, please check log")
                
        except Exception as e:
            self.log_partial_completion(f"[ERROR] execution error: {str(e)}")
            messagebox.showerror("error", f"execution error: {str(e)}")


def main():
    root = tk.Tk()
    app = LayoutGPTGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 