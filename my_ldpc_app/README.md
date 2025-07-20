# LDPC Designer & Optimizer

一个用 Flutter 开发的跨平台 LDPC 码可视化设计与优化应用，支持 Web、桌面和移动平台。

## 功能特性

### 🎨 图形化设计界面
- **可视化节点编辑**: 拖拽式添加变量节点（圆形）和校验节点（方形）
- **交互式连线**: 点击节点创建边连接，支持实时连线预览
- **节点属性查看**: 长按节点查看ID、类型、度数和位置信息
- **多种图形模板**: 内置 (3,6) 规则、(4,8) 规则和不规则 LDPC 码模板
- **随机图生成**: 一键生成随机 LDPC 图结构

### 📊 实时分析与展示
- **H 矩阵可视化**: 支持缩放、平移的交互式矩阵查看器
- **BER 性能曲线**: 实时绘制 BER 随 SNR 变化的性能曲线
- **码率计算**: 自动计算并显示码率、码长等参数
- **稀疏度统计**: 显示矩阵密度和图的连通性信息

### 🔬 仿真与优化
- **LDPC 编码**: 从图结构生成奇偶校验矩阵 H 和生成矩阵 G
- **BER 仿真**: 可配置 SNR 范围和帧数的误码率仿真
- **遗传算法优化**: 支持码结构优化，实时显示收敛过程
- **WebSocket 实时推送**: 长时间仿真的进度实时更新

## 快速开始

### 环境要求
- Flutter 3.8+ 
- Python 3.8+

### 安装依赖

**前端依赖**
```bash
flutter pub get
```

**后端依赖**
```bash
cd backend
pip install fastapi uvicorn pydantic numpy python-multipart
```

### 启动应用

**方法 1: 手动启动**

1. 启动后端服务器:
```bash
cd backend
python main.py
```

2. 启动 Flutter 应用:
```bash
flutter run -d chrome  # Web 版本
flutter run -d windows # Windows 桌面版本
```

### 访问地址
- 前端应用: http://localhost:xxxxx (Flutter 输出的端口)
- 后端 API: http://127.0.0.1:5000
- API 文档: http://127.0.0.1:5000/docs

## 使用指南

### 1. 创建 LDPC 图
1. 点击 "Add Variable" 添加变量节点（蓝色圆形）
2. 点击 "Add Check" 添加校验节点（红色方形）  
3. 点击两个不同类型的节点来创建连线
4. 长按节点查看属性或删除节点

### 2. 生成 LDPC 码
1. 构建好图结构后，点击 "Generate H & G Matrices"
2. 查看右侧面板中生成的 H 矩阵可视化
3. 确认码率和其他参数

### 3. 运行仿真
1. 设置 SNR 值和仿真帧数
2. 点击 "Run Simulation" 开始仿真
3. 观察实时更新的 BER 曲线

### 4. 优化码结构
1. 点击工具栏中的优化按钮进入优化页面
2. 设置遗传算法参数
3. 观察收敛曲线和最优结果

## 项目结构

```
lib/
├── main.dart                 # 应用入口
├── providers/
│   └── app_provider.dart     # 状态管理
├── screens/
│   └── main_screen.dart      # 主界面
├── pages/
│   └── optimization_page.dart# 优化页面
├── widgets/
│   ├── control_panel.dart    # 控制面板
│   ├── graph_canvas.dart     # 图形画布
│   ├── graph_node_widget.dart# 节点组件
│   ├── results_display.dart  # 结果展示
│   └── matrix_viewer.dart    # 矩阵查看器
└── services/
    └── api_service.dart      # API 服务
```
