import os
import sys
import time
import traceback
from pathlib import Path
from typing import List, Tuple, Dict, Union, Optional
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.font import Font

class FileConverter:
    """文件转换核心类"""
    
    def __init__(self, source_path: str, target_format: str, 
                 custom_output: str = None, merge_to_pdf: bool = False,
                 merge_filename: str = None, file_list: List[str] = None,
                 separate_folder: bool = False):
        # 基本参数初始化
        self.source_path = Path(source_path).resolve()
        self.target_format = target_format.lower().strip('.')
        self.merge_to_pdf = merge_to_pdf
        self.merge_filename = merge_filename
        self.file_list = file_list
        self.separate_folder = separate_folder
        
        # ==================== 路径逻辑判断区域（核心修改）====================
        # 使用统一的逻辑判断链条确定所有输出路径
        paths = self._determine_output_paths()
        self.base_dir = paths['base_dir']  # 基准工作目录
        self.output_folder = paths['converted_output_dir']  # 转换后文件输出目录
        
        # 如果是自定义输出路径，则覆盖转换后文件的输出目录
        if custom_output:
            self.output_folder = Path(custom_output).resolve()
        # ==================== 路径逻辑判断区域结束 ====================
        
        # 初始化统计信息
        self.converted_files: List[Path] = []
        self.total_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.failed_files: List[Tuple[str, str]] = []
    
    def _determine_output_paths(self):
        """确定输出路径和PDF命名（核心逻辑）"""
        
        # 步骤1: 确定输入目录（文件的实际所在目录）
        if self.file_list:
            # 多文件模式：使用第一个文件的父目录
            # 示例: D:\...\店员小姐2_1026828\WEBP\image1.webp → input_dir = WEBP文件夹
            input_dir = Path(self.file_list[0]).parent
        elif self.source_path.is_file():
            # 单文件模式：使用文件的父目录
            # 示例: D:\...\店员小姐2_1026828\image.png → input_dir = 店员小姐2_1026828文件夹
            input_dir = self.source_path.parent
        else:
            # 文件夹模式：直接使用选中的目录
            # 示例: D:\...\店员小姐2_1026828 → input_dir = 店员小姐2_1026828文件夹
            input_dir = self.source_path
        
        # 步骤2: 根据separate_folder选项确定基础目录(base_dir)
        # 这是整个逻辑的核心分叉点，决定了输出结构的两种不同模式
        if self.separate_folder:
            # 场景A: "文件已存放至单独文件夹"被勾选
            # 说明文件已经在专用子文件夹中（如WEBP），需要"跳出"一层到父目录
            # base_dir = input_dir的父目录
            # 示例: input_dir=D:\...\店员小姐2_1026828\WEBP → base_dir=D:\...\店员小姐2_1026828
            base_dir = input_dir.parent
        else:
            # 场景B: "文件已存放至单独文件夹"未勾选（默认）
            # 说明文件直接存放在目标文件夹中，不需要调整层级
            # base_dir = input_dir本身
            # 示例: input_dir=D:\...\店员小姐2_1026828 → base_dir=D:\...\店员小姐2_1026828
            base_dir = input_dir
        
        # 步骤3: 确定转换后文件的输出目录
        # 无论哪种场景，转换后的图片都输出在base_dir下的"目标格式"子文件夹中
        # 示例: D:\...\店员小姐2_1026828\PNG
        converted_output_dir = base_dir / self.target_format.upper()
        
        # 步骤4: 确定PDF输出路径（仅默认情况，不使用self.merge_filename）
        pdf_name = f"{base_dir.name}.pdf"
        pdf_output_path = base_dir / pdf_name
        
        return {
            'base_dir': base_dir,
            'converted_output_dir': converted_output_dir,
            'pdf_output_path': pdf_output_path,
            'pdf_name': pdf_name
        }
    
    def detect_source_format(self) -> str:
        """自动检测源文件格式"""
        try:
            if self.file_list:
                files = [Path(f) for f in self.file_list]
            elif self.source_path.is_file():
                files = [self.source_path]
            else:
                files = [f for f in self.source_path.iterdir() if f.is_file()]
            
            if not files:
                raise ValueError("源文件夹为空")
            
            for file in files:
                try:
                    with Image.open(file) as img:
                        return img.format.lower()
                except:
                    continue
            
            return files[0].suffix[1:].lower()
        except Exception as e:
            raise ValueError(f"无法检测源文件格式: {str(e)}")
    
    def converter(self, file_path: Path, retry_count: int = 0) -> bool:
        """转换单个文件，带重试机制"""
        max_retries = 3
        try:
            with Image.open(file_path) as img:
                # 转换模式
                if img.mode in ('RGBA', 'LA') and self.target_format in ['jpg', 'jpeg']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode not in ['RGB', 'RGBA']:
                    img = img.convert('RGB')
                
                # 构建输出路径
                output_path = self.output_folder / f"{file_path.stem}.{self.target_format}"
                
                # 保存图片
                save_kwargs = {}
                if self.target_format in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = 95
                    save_kwargs['optimize'] = True
                elif self.target_format == 'png':
                    save_kwargs['optimize'] = True
                
                img.save(output_path, **save_kwargs)
                
                # 记录转换成功的文件
                if self.merge_to_pdf and self.target_format != 'pdf':
                    self.converted_files.append(output_path)
                
                return True
                
        except Exception as e:
            error_msg = str(e)
            
            # 分析错误原因
            if "cannot identify image file" in error_msg.lower():
                reason = "文件损坏或不是有效的图片格式"
            elif "permission denied" in error_msg.lower():
                reason = "权限不足，无法读取或写入文件"
            elif "file not found" in error_msg.lower():
                reason = "文件不存在（可能被其他程序占用）"
            elif "memory" in error_msg.lower():
                reason = "内存不足，图片可能过大"
            elif "decompression bomb" in error_msg.lower():
                reason = "图片尺寸过大，超过安全限制"
            else:
                reason = f"未知错误: {error_msg}"
            
            self.failed_files.append((file_path.name, reason))
            
            # 重试逻辑
            if retry_count < max_retries:
                time.sleep(retry_count + 1)
                return self.converter(file_path, retry_count + 1)
            
            return False
    
    def merge_pdf(self):
        """合并文件为PDF"""
        if not self.converted_files:
            return None
        
        try:
            # 确定PDF输出路径
            if self.merge_filename:
                # 用户自定义了文件名，使用base_dir作为输出目录
                pdf_path = self.base_dir / f"{self.merge_filename}.pdf"
            else:
                # 使用默认文件名（base_dir的名称）
                pdf_path = self.base_dir / f"{self.base_dir.name}.pdf"
            
            # 收集所有图片并转换为RGB
            images = []
            for img_path in sorted(self.converted_files):
                try:
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    print(f"无法加载 {img_path} 用于PDF合并: {e}")
                    continue
            
            if not images:
                return None
            
            # 保存为PDF
            images[0].save(
                pdf_path,
                "PDF",
                resolution=100.0,
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                quality=95,
                optimize=True
            )
            
            return str(pdf_path)
            
        except Exception as e:
            self.failed_files.append(("PDF合并", f"合并失败: {str(e)}"))
            return None
    
    def convert_all(self, progress_callback=None):
        """转换所有文件"""
        # 创建输出文件夹
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # 获取文件列表
        if self.file_list:
            files = [Path(f) for f in self.file_list if Path(f).exists()]
        elif self.source_path.is_file():
            files = [self.source_path]
        else:
            files = [f for f in self.source_path.iterdir() if f.is_file()]
        
        self.total_files = len(files)
        
        # 遍历转换
        for i, file_path in enumerate(files):
            try:
                if self.converter(file_path):
                    self.success_count += 1
                else:
                    self.fail_count += 1
            except Exception:
                self.fail_count += 1
                self.failed_files.append((file_path.name, f"致命错误: {traceback.format_exc()}"))
            
            # 更新进度
            if progress_callback:
                progress = (i + 1) / self.total_files * 100
                progress_callback(progress, f"正在转换: {file_path.name}")
        
        # 合并PDF
        pdf_path = None
        if self.merge_to_pdf and self.target_format != 'pdf':
            if progress_callback:
                progress_callback(100, "正在合并PDF...")
            pdf_path = self.merge_pdf()
        
        return {
            'total': self.total_files,
            'success': self.success_count,
            'failed': self.fail_count,
            'failed_files': self.failed_files,
            'output_folder': str(self.output_folder),
            'pdf_merged': pdf_path is not None,
            'pdf_path': pdf_path
        }

class ConversionGUI:
    """图形用户界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("文件格式转换工具")
        
        # 窗口可拉伸且内部组件自适应
        self.root.geometry("650x550")  # 增加高度以适应新控件
        self.root.minsize(600, 500)    # 增加最小高度
        self.root.resizable(True, True)
        
        self.default_font = Font(family="Microsoft YaHei", size=10)
        self.root.option_add("*Font", self.default_font)
        
        self.selected_files: List[str] = []
        
        self.setup_ui()
        self.converter = None
    
    def setup_ui(self):
        """设置界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置根窗口行列权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 配置main_frame内部列权重
        main_frame.columnconfigure(1, weight=1)
        
        # ========== 源路径选择 ==========
        ttk.Label(main_frame, text="源路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(main_frame, textvariable=self.source_var, width=35)
        self.source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="选择文件夹", command=self.browse_folder, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="选择文件", command=self.browse_file, width=12).pack(side=tk.LEFT, padx=2)
        
        # ========== 目标格式 ==========
        ttk.Label(main_frame, text="目标格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.format_combo = ttk.Combobox(main_frame, values=[
            "PNG", "JPG", "JPEG", "BMP", "GIF", "TIFF", "WEBP", "ICO", "PDF"
        ], width=10)
        self.format_combo.set("PNG")
        self.format_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # ========== 输出路径 ==========
        ttk.Label(main_frame, text="输出路径:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_var, width=35)
        self.output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(main_frame, text="浏览...", command=self.browse_output, width=12).grid(row=2, column=2, padx=5, pady=5)
        
        # ========== 高级选项 ==========
        options_frame = ttk.LabelFrame(main_frame, text="高级选项", padding=10)
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        options_frame.columnconfigure(1, weight=1)
        
        # 新增：文件已存放至单独文件夹（默认不勾选）
        self.separate_folder_var = tk.BooleanVar(value=False)
        self.separate_folder_check = ttk.Checkbutton(options_frame, text="文件已存放至单独文件夹",
                                                    variable=self.separate_folder_var,
                                                    command=self.update_merge_filename)  # 修改：触发时更新PDF文件名
        self.separate_folder_check.pack(anchor=tk.W)
        
        # 原有的PDF合并选项
        self.merge_var = tk.BooleanVar(value=False)
        self.merge_check = ttk.Checkbutton(options_frame, text="转换后合并为PDF", 
                                          variable=self.merge_var, command=self.toggle_merge_options)
        self.merge_check.pack(anchor=tk.W, pady=(5, 0))
        
        merge_name_frame = ttk.Frame(options_frame)
        merge_name_frame.pack(fill=tk.X, pady=(5, 0))
        merge_name_frame.columnconfigure(1, weight=1)
        
        ttk.Label(merge_name_frame, text="PDF文件名:").pack(side=tk.LEFT, padx=(0, 10))
        self.merge_name_var = tk.StringVar()
        self.merge_name_entry = ttk.Entry(merge_name_frame, textvariable=self.merge_name_var, 
                                         width=30, state=tk.DISABLED)
        self.merge_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ========== PDF输出路径预览 ==========
        # 新增：显示PDF输出路径
        pdf_preview_frame = ttk.Frame(main_frame)
        pdf_preview_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(pdf_preview_frame, text="PDF输出路径:").pack(side=tk.LEFT)
        self.pdf_path_var = tk.StringVar(value="未启用PDF合并")
        self.pdf_path_entry = ttk.Entry(pdf_preview_frame, textvariable=self.pdf_path_var, state='readonly', width=50)
        self.pdf_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # ========== 按钮区域 ==========
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.convert_btn = ttk.Button(action_frame, text="开始转换", command=self.start_conversion, width=15)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="清空", command=self.clear, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="预览输出路径", command=self.preview_output, width=15).pack(side=tk.LEFT, padx=5)
        
        # ========== 进度条 ==========
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # ========== 状态栏 ==========
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory(title="选择源文件夹")
        if folder:
            display_folder = folder.replace('/', '\\')
            self.source_var.set(display_folder)
            self.selected_files = []
            self.status_var.set(f"已选择文件夹: {display_folder}")
            self.update_default_output()
            self.update_merge_filename()
            self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def browse_file(self):
        """浏览文件（支持多选）"""
        file_paths = filedialog.askopenfilenames(title="选择一个或多个文件")
        if file_paths:
            self.selected_files = list(file_paths)
            
            if len(file_paths) == 1:
                display_path = file_paths[0].replace('/', '\\')
                self.source_var.set(display_path)
                self.status_var.set(f"已选择1个文件")
            else:
                first_path = file_paths[0].replace('/', '\\')
                display_path = f"{first_path} 等{len(file_paths)}个文件"
                self.source_var.set(display_path)
                self.status_var.set(f"已选择{len(file_paths)}个文件")
            
            self.update_default_output()
            self.update_merge_filename()
            self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def browse_output(self):
        """浏览输出路径"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            display_folder = folder.replace('/', '\\')
            self.output_var.set(display_folder)
            self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def update_default_output(self):
        """根据源路径更新默认输出路径"""
        source_path_str = self.source_var.get()
        target_format = self.format_combo.get().strip()
        
        if not source_path_str or not target_format:
            return
        
        if "等" in source_path_str and "个文件" in source_path_str:
            first_path = source_path_str.split(" 等")[0]
            try:
                source_path = Path(first_path)
            except:
                return
        else:
            try:
                source_path = Path(source_path_str)
            except:
                return
        
        # 根据separate_folder_var状态计算输出路径
        if self.separate_folder_var.get():
            # 勾选时：输出到父目录的目标格式文件夹
            # 示例: D:\...\店员小姐2_1026828\WEBP → D:\...\店员小姐2_1026828\PNG
            if source_path.is_file():
                default_output = source_path.parent.parent / target_format.upper()
            else:
                default_output = source_path.parent / target_format.upper()
        else:
            # 未勾选时：输出到当前目录的目标格式文件夹
            # 示例: D:\...\店员小姐2_1026828 → D:\...\店员小姐2_1026828\PNG
            if source_path.is_file():
                default_output = source_path.parent / target_format.upper()
            else:
                default_output = source_path / target_format.upper()
        
        self.output_var.set(str(default_output).replace('/', '\\'))
        self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def update_merge_filename(self):
        """更新默认PDF合并文件名"""
        # 根据separate_folder_var状态确定使用哪个目录名称作为默认值
        if self.separate_folder_var.get():
            # 勾选"单独文件夹"时，使用父目录名称
            if self.selected_files:
                # 文件列表：使用祖父目录名称
                # 示例: D:\...\店员小姐2_1026828\WEBP\image.webp → 店员小姐2_1026828
                default_name = Path(self.selected_files[0]).parent.parent.name
            elif self.source_var.get():
                source_path = Path(self.source_var.get())
                if source_path.is_file():
                    # 单个文件：使用祖父目录名称
                    # 示例: D:\...\店员小姐2_1026828\WEBP\image.webp → 店员小姐2_1026828
                    default_name = source_path.parent.parent.name
                else:
                    # 文件夹：使用父目录名称
                    # 示例: D:\...\店员小姐2_1026828\WEBP → 店员小姐2_1026828
                    default_name = source_path.parent.name
            else:
                default_name = "merged"
        else:
            # 未勾选"单独文件夹"时，使用当前目录名称
            if self.selected_files:
                # 文件列表：使用父目录名称
                # 示例: D:\...\店员小姐2_1026828\image.png → 店员小姐2_1026828
                default_name = Path(self.selected_files[0]).parent.name
            elif self.source_var.get():
                source_path = Path(self.source_var.get())
                if source_path.is_file():
                    # 单个文件：使用父目录名称
                    # 示例: D:\...\店员小姐2_1026828\image.png → 店员小姐2_1026828
                    default_name = source_path.parent.name
                else:
                    # 文件夹：使用当前目录名称
                    # 示例: D:\...\店员小姐2_1026828 → 店员小姐2_1026828
                    default_name = source_path.name
            else:
                default_name = "merged"
        
        self.merge_name_var.set(default_name)
        self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def toggle_merge_options(self):
        """切换合并选项的可用状态"""
        state = tk.NORMAL if self.merge_var.get() else tk.DISABLED
        self.merge_name_entry.config(state=state)
        self.update_pdf_path_display()  # 新增：更新PDF路径显示
    
    def update_pdf_path_display(self):
        """更新PDF输出路径显示"""
        if not self.merge_var.get():
            self.pdf_path_var.set("未启用PDF合并")
            return
        
        source_path_str = self.source_var.get()
        if not source_path_str:
            self.pdf_path_var.set("请先选择源路径")
            return
        
        try:
            # 解析源路径
            if "等" in source_path_str and "个文件" in source_path_str:
                first_path = source_path_str.split(" 等")[0]
                source_path = Path(first_path)
            else:
                source_path = Path(source_path_str)
            
            # 确定输入目录
            if self.selected_files:
                input_dir = Path(self.selected_files[0]).parent
            elif source_path.is_file():
                input_dir = source_path.parent
            else:
                input_dir = source_path
            
            # 根据separate_folder选项确定base_dir
            if self.separate_folder_var.get():
                base_dir = input_dir.parent
            else:
                base_dir = input_dir
            
            # 确定PDF文件名和路径
            pdf_name = self.merge_name_var.get() or "merged"
            pdf_path = base_dir / f"{pdf_name}.pdf"
            
            self.pdf_path_var.set(str(pdf_path).replace('/', '\\'))
        except Exception as e:
            self.pdf_path_var.set(f"路径错误: {str(e)}")
    
    def preview_output(self):
        """预览输出路径结构"""
        output_path = self.output_var.get()
        if not output_path:
            messagebox.showwarning("提示", "请先选择源路径和设置目标格式")
            return
        
        # 构建预览信息
        msg = f"输出路径预览:\n\n{output_path}\n\n"
        
        if self.merge_var.get():
            merge_name = self.merge_name_var.get() or "merged"
            # PDF始终输出在output_folder的父目录（即base_dir）
            pdf_path = Path(output_path).parent / f"{merge_name}.pdf"
            pdf_display_path = str(pdf_path).replace('/', '\\')
            msg += f"PDF文件将生成在:\n{pdf_display_path}\n\n"
        
        file_count = len(self.selected_files) if self.selected_files else '全部'
        msg += f"预计处理文件数: {file_count}\n\n"
        msg += "点击'打开输出文件夹'即可查看转换后的文件。"
        
        messagebox.showinfo("输出路径预览", msg)
    
    def start_conversion(self):
        """开始转换"""
        source_path = self.source_var.get()
        target_format = self.format_combo.get().strip()
        output_path = self.output_var.get()
        merge_to_pdf = self.merge_var.get()
        merge_filename = self.merge_name_var.get()
        
        # 验证输入
        if not source_path or not target_format:
            messagebox.showwarning("警告", "请选择源路径和目标格式")
            return
        
        # 检查源路径
        if self.selected_files:
            if not Path(self.selected_files[0]).exists():
                messagebox.showerror("错误", "源文件不存在")
                return
        else:
            if not Path(source_path).exists():
                messagebox.showerror("错误", "源路径不存在")
                return
        
        if merge_to_pdf and not merge_filename:
            messagebox.showwarning("警告", "请设置PDF文件名")
            return
        
        # 验证目标格式支持
        if target_format.lower() not in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp', 'ico', 'pdf']:
            messagebox.showwarning("警告", f"目标格式 '{target_format}' 可能不被支持\n建议从下拉列表选择")
        
        # 禁用按钮
        self.convert_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("正在初始化...")
        
        # 后台执行，传递separate_folder状态
        self.root.after(100, self.run_conversion, source_path, target_format, 
                       output_path, merge_to_pdf, merge_filename, self.separate_folder_var.get())
    
    def run_conversion(self, source_path: str, target_format: str, 
                      output_path: str, merge_to_pdf: bool, merge_filename: str,
                      separate_folder: bool):
        """执行转换"""
        try:
            file_list = self.selected_files if self.selected_files else None
            
            # 创建转换器，传递separate_folder参数
            self.converter = FileConverter(source_path, target_format, 
                                         output_path if output_path else None,
                                         merge_to_pdf, merge_filename, file_list,
                                         separate_folder)
            
            # 检测源格式
            try:
                source_format = self.converter.detect_source_format()
                self.status_var.set(f"检测到源格式: {source_format.upper()}")
            except Exception as e:
                self.status_var.set(f"格式检测失败: {str(e)}")
            
            # 执行转换
            result = self.converter.convert_all(progress_callback=self.update_progress)
            
            # 显示结果
            self.show_result(result)
            
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出现错误:\n{traceback.format_exc()}")
        finally:
            self.convert_btn.config(state=tk.NORMAL)
            self.status_var.set("就绪")
    
    def update_progress(self, value: float, status: str):
        """更新进度"""
        self.progress_var.set(value)
        self.status_var.set(status)
        self.root.update()
    
    def show_result(self, result: Dict):
        """显示转换结果"""
        msg = f"转换完成！\n\n"
        msg += f"共处理: {result['total']} 个文件\n"
        msg += f"成功: {result['success']} 个\n"
        msg += f"失败: {result['failed']} 个\n\n"
        
        if result.get('pdf_merged'):
            pdf_path = result.get('pdf_path', '')
            pdf_display_path = pdf_path.replace('/', '\\') if pdf_path else '未知'
            msg += f"PDF合并: 成功\n"
            msg += f"PDF路径: {pdf_display_path}\n\n"
        
        if result['failed'] > 0:
            msg += "失败文件详情:\n"
            msg += "=" * 50 + "\n"
            for filename, reason in result['failed_files']:
                msg += f"文件: {filename}\n"
                msg += f"原因: {reason}\n"
                msg += "-" * 50 + "\n"
        
        output_display_path = result['output_folder'].replace('/', '\\')
        msg += f"\n输出目录: {output_display_path}"
        
        # 创建结果窗口
        result_window = tk.Toplevel(self.root)
        result_window.title("转换报告")
        result_window.geometry("700x550")
        
        text_frame = ttk.Frame(result_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert(tk.END, msg)
        text_widget.config(state=tk.DISABLED)
        
        # 按钮
        btn_frame = ttk.Frame(result_window, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="打开输出文件夹", 
                 command=lambda: os.startfile(result['output_folder'])).pack(side=tk.LEFT)
        
        if result.get('pdf_path') and Path(result['pdf_path']).exists():
            ttk.Button(btn_frame, text="打开PDF文件", 
                     command=lambda: os.startfile(result['pdf_path'])).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="关闭", 
                 command=result_window.destroy).pack(side=tk.RIGHT)
        
        text_widget.see("1.0")
        
        # 高失败率警告
        if result['failed'] > 0 and result['failed'] / result['total'] > 0.1:
            messagebox.showwarning("提示", 
                f"有 {result['failed']} 个文件转换失败，占总数的 {result['failed']/result['total']*100:.1f}%\n\n"
                "常见原因：\n"
                "• 文件损坏\n"
                "• 内存不足（大文件）\n"
                "• 文件被其他程序占用\n"
                "• PDF合并时图片格式不支持\n\n"
                "建议：\n"
                "1. 检查源文件是否完整\n"
                "2. 关闭可能占用文件的程序后重试\n"
                "3. 合并PDF前确保所有图片可正常打开")
    
    def clear(self):
        """清空输入"""
        self.source_var.set("")
        self.selected_files = []
        self.format_combo.set("PNG")
        self.output_var.set("")
        self.separate_folder_var.set(False)  # 重置选项状态
        self.merge_var.set(False)
        self.merge_name_var.set("")
        self.merge_name_entry.config(state=tk.DISABLED)
        self.pdf_path_var.set("未启用PDF合并")  # 重置PDF路径显示
        self.progress_var.set(0)
        self.status_var.set("就绪")
    
    def run(self):
        """运行GUI主循环"""
        self.root.mainloop()

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式
        source_path = sys.argv[1]
        target_format = sys.argv[2] if len(sys.argv) > 2 else "PNG"
        
        try:
            converter = FileConverter(source_path, target_format)
            result = converter.convert_all()
            
            print("=" * 60)
            print("转换完成")
            print("=" * 60)
            print(f"共处理: {result['total']} 个文件")
            print(f"成功: {result['success']} 个")
            print(f"失败: {result['failed']} 个")
            print(f"输出目录: {result['output_folder']}")
            
            if result['failed'] > 0:
                print("\n失败文件:")
                print("-" * 60)
                for filename, reason in result['failed_files']:
                    print(f"文件: {filename}")
                    print(f"原因: {reason}")
                    print("-" * 60)
            
            sys.exit(0 if result['failed'] == 0 else 1)
            
        except Exception as e:
            print(f"错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        # GUI模式
        gui = ConversionGUI()
        gui.run()

if __name__ == "__main__":
    main()