# LDPC 解码前端功能使用指南

## 🎯 功能概述

Flutter前端现已集成完整的LDPC解码功能，支持三种解码模式：
- **直接LLR解码**：提供对数似然比进行解码
- **AWGN信道解码**：提供接收信号和噪声方差
- **BSC信道解码**：提供接收比特和错误概率

## 🚀 快速开始

### 1. 启动应用

```bash
# 方法1: 使用启动脚本
./start_frontend.bat

# 方法2: 手动启动
flutter pub get
flutter run -d windows
```

### 2. 基本操作流程

1. **创建LDPC图**
   - 点击"Add Variable"添加变量节点
   - 点击"Add Check"添加校验节点
   - 在图形区域点击节点进行连接

2. **生成LDPC码**
   - 点击"Generate LDPC Code"按钮
   - 系统会生成H矩阵和G矩阵

3. **配置解码参数**
   - 选择解码模式（LLR/AWGN/BSC）
   - 选择解码算法（Min-Sum/Sum-Product）
   - 设置解码参数

4. **执行解码**
   - 点击"Decode Data"按钮
   - 查看解码结果

## 📊 解码模式详解

### LLR模式 (直接对数似然比)
```
输入格式: 1.5,-2.3,0.8,-1.2,2.1,-0.9,1.7,-1.8
说明: 直接提供每个比特的LLR值
适用: 已知准确的信道信息
```

### AWGN模式 (加性高斯白噪声)
```
接收信号: 1.2,-1.8,0.9,-1.1,1.9,-0.8,1.6,-1.7
噪声方差: 0.5
说明: 系统自动计算LLR值
适用: AWGN信道环境
```

### BSC模式 (二进制对称信道)
```
接收比特: 1,0,1,0,1,0,1,0
错误概率: 0.1
说明: 系统根据错误概率计算LLR
适用: 数字通信系统
```

## ⚙️ 解码参数说明

| 参数 | 说明 | 默认值 | 范围 |
|------|------|--------|------|
| Max Iterations | 最大迭代次数 | 50 | 1-200 |
| Min-Sum Scaling | Min-Sum算法缩放因子 | 0.9 | 0.1-1.0 |
| Early Termination | 早期终止 | 启用 | 布尔值 |
| Algorithm | 解码算法 | Min-Sum | Min-Sum/Sum-Product |

## 📈 解码结果解读

### 基本信息
- **解码比特**: 完整的解码码字
- **信息比特**: 提取的信息位
- **解码状态**: 成功/失败状态

### 统计信息
- **迭代次数**: 实际使用的迭代次数
- **收敛状态**: 是否收敛到有效码字
- **校验子范数**: 解码精度指标
- **LLR幅度**: 信号强度指标

## 🎨 界面功能

### 控制面板
- **图构建区**: 添加节点和连接
- **编码区**: 生成LDPC码和编码信息位
- **解码区**: 配置解码参数和执行解码
- **仿真区**: 运行BER/FER仿真

### 结果显示
- **矩阵显示**: H矩阵和G矩阵可视化
- **编码结果**: 码字和参数显示
- **解码结果**: 解码比特和统计信息
- **性能图表**: BER/FER曲线

## 🔧 高级功能

### 1. 批量测试
```dart
// 创建多个测试用例
final testCases = [
  {'llr': [1.5, -2.3, 0.8, -1.2], 'algorithm': 'min_sum'},
  {'llr': [2.1, -1.8, 1.2, -0.9], 'algorithm': 'sum_product'},
];
```

### 2. 性能对比
- Min-Sum vs Sum-Product算法性能
- 不同迭代次数的收敛分析
- 不同信道条件下的解码效果

### 3. 自定义模板
```dart
// 加载预定义模板
appProvider.loadTemplate('3_6_regular');
appProvider.loadTemplate('4_8_regular');
appProvider.loadTemplate('irregular');
```

## 📋 使用示例

### 示例1: 基本LLR解码
```
1. 创建4个变量节点，2个校验节点
2. 适当连接形成二分图
3. 生成LDPC码
4. 解码模式: LLR
5. 输入: 1.5,-2.3,0.8,-1.2
6. 点击"Decode Data"
```

### 示例2: AWGN信道解码
```
1. 使用现有LDPC码
2. 解码模式: AWGN
3. 接收信号: 1.2,-1.8,0.9,-1.1
4. 噪声方差: 0.5
5. 算法: Min-Sum
6. 点击"Decode Data"
```

### 示例3: BSC信道解码
```
1. 使用现有LDPC码
2. 解码模式: BSC
3. 接收比特: 1,0,1,0
4. 错误概率: 0.1
5. 算法: Sum-Product
6. 点击"Decode Data"
```

## 🐛 常见问题

### Q1: 解码失败怎么办？
- 检查H矩阵是否正确生成
- 确认输入数据长度与码长匹配
- 尝试增加最大迭代次数
- 检查信道参数设置

### Q2: 收敛速度慢？
- 使用Min-Sum算法（速度更快）
- 启用早期终止
- 调整Min-Sum缩放因子
- 优化图结构设计

### Q3: 解码精度不够？
- 使用Sum-Product算法（精度更高）
- 增加迭代次数
- 检查信道参数设置
- 优化H矩阵设计

## 🔍 技术细节

### 前端架构
- **状态管理**: Provider模式
- **网络请求**: Dio库
- **UI组件**: Material Design
- **图表显示**: fl_chart库

### 后端集成
- **编码接口**: POST /api/v1/encode
- **解码接口**: POST /api/v1/decode
- **仿真接口**: POST /api/simulate
- **WebSocket**: 实时进度更新

### 性能优化
- **并行处理**: 多线程解码
- **内存管理**: 智能缓存
- **UI响应**: 异步操作
- **错误处理**: 完善的异常管理

## 📚 相关资源

- [LDPC码理论基础](https://ldpc.md)
- [Flutter开发指南](https://flutter.dev/docs)
- [Provider状态管理](https://pub.dev/packages/provider)
- [Dio网络请求](https://pub.dev/packages/dio)

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境
```bash
flutter --version  # >= 3.8.0
dart --version     # >= 3.0.0
```

### 项目结构
```
lib/
├── main.dart              # 应用入口
├── providers/            # 状态管理
├── services/             # API服务
├── widgets/              # UI组件
└── screens/              # 页面
```

---

📧 有问题？请联系开发团队或查看项目文档。 