# LDPC可视化编解码仿真系统详细技术文档

## 项目概述

本项目是一个基于Flutter+Python的跨平台LDPC码可视化设计与仿真系统，提供了从图形化设计到性能仿真的完整工具链。系统采用前后端分离架构，前端使用Flutter开发跨平台客户端，后端使用FastAPI构建高性能API服务。

### 核心特性
- **图形化LDPC码设计**: 拖拽式节点编辑，直观的Tanner图构建
- **多算法解码支持**: Min-Sum、Sum-Product等置信传播算法
- **实时仿真引擎**: BER/FER性能曲线生成，支持AWGN/BSC信道
- **智能优化系统**: 遗传算法驱动的码结构优化
- **跨平台部署**: 支持Web、Windows、Android、iOS等多平台

---

## 后端架构详细分析

### 1. FastAPI框架核心

#### 1.1 主应用结构 (main.py)

后端基于FastAPI构建，提供RESTful API服务和WebSocket实时通信。主要特点：

```python
# 应用配置
app = FastAPI(
    title="LDPC SYSTEM API",
    description="基于FastAPI的LDPC编码、仿真和优化后端服务",
    version="1.0.0",
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**核心API端点**：
- `POST /api/v1/encode`: LDPC编码服务
- `POST /api/v1/decode`: LDPC解码服务  
- `POST /api/simulate`: BER/FER仿真服务
- `POST /api/quick-test`: 快速性能测试
- `GET /api/matrix-templates`: 获取预定义矩阵模板
- `POST /api/optimize`: 遗传算法优化

#### 1.2 数据模型 (pydantic_models.py)

使用Pydantic进行严格的数据验证和序列化：

**编码请求模型**：
```python
class EncodeRequest(BaseModel):
    nodes: Optional[List[Node]] = None      # 图形节点数据
    edges: Optional[List[Edge]] = None      # 图形边数据
    h_matrix: Optional[List[List[int]]] = None  # 直接H矩阵输入
    info_bits: Optional[List[int]] = None   # 信息位序列
    snr_db: Optional[float] = 4.0          # 信噪比
```

**解码请求模型**：
```python
class DecodeRequest(BaseModel):
    llr: Optional[List[float]] = None           # 对数似然比输入
    received_signal: Optional[List[float]] = None  # AWGN接收信号
    received_bits: Optional[List[int]] = None   # BSC接收比特
    h_matrix: List[List[int]]                   # 校验矩阵
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
    algorithm: str = Field("min_sum", pattern="^(min_sum|sum_product)$")
    max_iterations: int = Field(50, ge=1, le=200)
```

**仿真请求模型**：
```python
class SimulationRequest(BaseModel):
    h_matrix: List[List[int]]
    snr_range: List[float]
    frames_per_snr: int = Field(1000, ge=100, le=100000)
    max_iterations: int = Field(50, ge=10, le=200)
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
```

#### 1.3 错误处理与性能监控

**错误处理机制**：
- 统一异常处理器 (`error_handler.py`)
- 安全操作装饰器 (`@safe_operation`)
- 详细错误日志记录

**性能监控**：
- 性能监控装饰器 (`@monitor_performance`)
- 系统资源监控 (`performance_utils.py`)
- API响应时间统计

### 2. LDPC算法核心实现

#### 2.1 LDPC码数据结构 (ldpc_models.py)

**LDPCCode类**是整个系统的核心数据结构：

```python
class LDPCCode:
    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        # 存储为CSR稀疏矩阵格式，优化大规模矩阵操作
        if sp.issparse(h_matrix):
            self.H: sp.spmatrix = h_matrix.tocsr()
        else:
            self.H = sp.csr_matrix(h_matrix % 2)
            
        self.m, self.n = self.H.shape  # m个校验节点，n个变量节点
        self._rank: int | None = None   # 延迟计算矩阵秩
        self._G: np.ndarray | None = None  # 延迟计算生成矩阵
```

**关键功能**：
- **GF(2)高斯消元法**: 计算系统生成矩阵G
- **图形数据转换**: 从Tanner图节点/边生成H矩阵
- **码参数计算**: 自动计算码率、信息位长度等参数
- **结构分析**: 度分布、环检测、规则性判断

**生成矩阵构造算法**：
```python
def _compute_generator_matrix(self) -> np.ndarray:
    H_dense = self.H.toarray()
    H_rref, pivots = _row_echelon_gf2(H_dense.copy())
    
    # 信息位列索引 = 非主元列
    info_cols = sorted(set(range(self.n)) - set(pivots))
    self._info_cols = info_cols
    
    k = len(info_cols)
    G = np.zeros((k, self.n), dtype=int)
    
    # 构造系统形式的生成矩阵 [I|P]
    G[np.arange(k), info_cols] = 1  # 单位矩阵部分
    for row_in_H, pivot_col in enumerate(pivots):
        G[:, pivot_col] = H_rref[row_in_H, info_cols]  # 校验部分
        
    return G
```

#### 2.2 LDPC编码器 (ldpc_encoder.py)

**LDPCEncoder类**实现系统化LDPC编码：

```python
class LDPCEncoder:
    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        self.code = LDPCCode(h_matrix)
        self._G: np.ndarray | None = None
    
    def encode(self, info_bits: Sequence[int] | np.ndarray) -> np.ndarray:
        """系统化编码: c = u * G (mod 2)"""
        G = self.generate_g_matrix()
        info_bits = np.asarray(info_bits, dtype=int) % 2
        
        if info_bits.size != self.k:
            raise ValueError(f"信息位长度 {info_bits.size} != 预期 k={self.k}")
            
        return (info_bits @ G) % 2
```

**编码流程**：
1. 验证信息位长度与码参数k匹配
2. 使用生成矩阵G进行线性编码
3. 返回长度为n的系统化码字

**码结构验证**：
```python
def validate_code_structure(self) -> Dict[str, Any]:
    G = self.generate_g_matrix()
    H_dense = self.H.toarray()
    
    # 验证正交性: H * G^T = 0 (mod 2)
    orthogonality = (H_dense @ G.T) % 2
    is_orthogonal = not orthogonality.any()
    
    return {
        "is_orthogonal": is_orthogonal,
        "orthogonality_error": int(orthogonality.sum()),
        "code_rate": self.rate,
        # 结合码结构分析
        **self.code.analyze_code_properties()
    }
```

#### 2.3 LDPC解码器 (ldpc_decoder.py)

**LDPCDecoder类**实现多种置信传播解码算法：

**初始化与预计算**：
```python
class LDPCDecoder:
    def __init__(self, h_matrix, max_iterations=50, min_sum_scaling=0.9, 
                 early_termination=True, osd_order=0):
        self.code = LDPCCode(h_matrix)
        self.max_iterations = max_iterations
        self.min_sum_scaling = min_sum_scaling
        self.osd_order = osd_order  # OSD后处理订单
        
        # 预计算邻接信息提高解码效率
        self._precompute_adjacency()
    
    def _precompute_adjacency(self):
        """预计算变量节点-校验节点邻接关系"""
        H_coo = self.H.tocoo()
        self.var_to_check = [[] for _ in range(self.n)]
        self.check_to_var = [[] for _ in range(self.m)]
        
        for i, j in zip(H_coo.row, H_coo.col):
            self.var_to_check[j].append(i)
            self.check_to_var[i].append(j)
```

**Min-Sum算法实现**（带归一化优化）：
```python
def _decode_min_sum(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict]:
    # 初始化变量-校验节点消息
    v2c_messages = {}  # 变量到校验节点消息
    c2v_messages = {}  # 校验到变量节点消息
    
    for var_idx in range(self.n):
        v2c_messages[var_idx] = {}
        for check_idx in self.var_to_check[var_idx]:
            v2c_messages[var_idx][check_idx] = llr_input[var_idx]
    
    # 计算归一化因子
    avg_check_degree = np.mean([len(self.check_to_var[i]) for i in range(self.m)])
    normalization_factor = 1.0 / (0.75 + 0.25 * avg_check_degree / 4.0)
    
    for iteration in range(self.max_iterations):
        # 校验节点更新
        for check_idx in range(self.m):
            connected_vars = self.check_to_var[check_idx]
            
            for target_var in connected_vars:
                other_vars = [v for v in connected_vars if v != target_var]
                if not other_vars:
                    continue
                    
                messages = [v2c_messages[v][check_idx] for v in other_vars]
                signs = [1 if msg >= 0 else -1 for msg in messages]
                abs_messages = [abs(msg) for msg in messages]
                
                sign_product = np.prod(signs)
                min_abs = min(abs_messages)
                
                # 应用缩放和归一化
                c2v_messages[check_idx][target_var] = (
                    self.min_sum_scaling * sign_product * min_abs * normalization_factor
                )
        
        # 变量节点更新 + 后验计算
        posterior_llr = llr_input.copy()
        for var_idx in range(self.n):
            for check_idx in self.var_to_check[var_idx]:
                posterior_llr[var_idx] += c2v_messages[check_idx][var_idx]
        
        decoded_bits = (posterior_llr < 0).astype(int)
        
        # 早期终止检查
        if self.early_termination:
            syndrome = (self.H @ decoded_bits) % 2
            if np.all(syndrome == 0):
                converged = True
                break
```

**Sum-Product算法实现**（对数域优化）：
```python
def _decode_sum_product(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict]:
    """Sum-Product算法，使用对数域提升数值稳定性"""
    
    for iteration in range(self.max_iterations):
        # 校验节点更新（对数域tanh规则）
        for check_idx in range(self.m):
            for target_var in connected_vars:
                other_vars = [v for v in connected_vars if v != target_var]
                if not other_vars:
                    continue
                
                # 对数域Sum-Product: prod(tanh(LLR/2)) -> 2*atanh()
                tanh_msgs = [np.tanh(v2c_messages[v][check_idx] / 2.0) for v in other_vars]
                prod_tanh = np.prod(tanh_msgs)
                
                # 数值稳定性处理
                prod_tanh = np.clip(prod_tanh, -1 + 1e-10, 1 - 1e-10)
                c2v_messages[check_idx][target_var] = 2.0 * np.arctanh(prod_tanh)
```

**OSD后处理**：
```python
# OSD (Ordered Statistics Decoding) 后处理
if not converged and self.osd_order >= 0:
    osd_applied = True
    # 按置信度排序，翻转最不可靠的比特组合
    uncertain_indices = np.argsort(np.abs(posterior_llr))[:self.osd_order + 1]
    
    for flip_set in combinations(uncertain_indices, self.osd_order + 1):
        temp_bits = decoded_bits.copy()
        temp_bits[list(flip_set)] = 1 - temp_bits[list(flip_set)]
        
        syndrome = (self.H @ temp_bits) % 2
        if np.all(syndrome == 0):
            decoded_bits = temp_bits
            converged = True
            break
```

**信道LLR计算**：
```python
def awgn_llr(self, received_signal: np.ndarray, noise_variance: float) -> np.ndarray:
    """AWGN信道LLR计算: LLR = 2*r/σ² (BPSK调制)"""
    return 2.0 * received_signal / noise_variance

def bsc_llr(self, received_bits: np.ndarray, crossover_probability: float) -> np.ndarray:
    """BSC信道LLR计算: LLR = log((1-p)/p) * (1-2*r)"""
    log_ratio = np.log((1 - crossover_probability) / crossover_probability)
    return log_ratio * (1 - 2 * received_bits)
```

### 3. 仿真引擎实现

#### 3.1 仿真引擎核心 (simulation_engine.py)

**SimulationEngine类**实现完整的BER/FER性能仿真：

```python
class SimulationEngine:
    def __init__(self, h_matrix: np.ndarray):
        self.h_matrix = np.asarray(h_matrix, dtype=int)
        self.encoder = LDPCEncoder(h_matrix)
        self.decoder = LDPCDecoder(h_matrix)
        
        # 码参数
        self.n = self.decoder.n  # 码长
        self.k = self.decoder.k  # 信息位长度
        self.rate = self.decoder.rate  # 码率
```

**BER仿真主循环**：
```python
def run_ber_simulation(self, config: SimulationConfig, 
                      progress_callback=None) -> SimulationResults:
    start_time = time.time()
    
    # 更新解码器参数
    self.decoder.max_iterations = config.max_iterations
    self.decoder.min_sum_scaling = config.min_sum_scaling
    
    results = []
    for snr_idx, snr_db in enumerate(config.snr_range):
        if self.should_stop:
            break
            
        # 单个SNR点仿真
        snr_result = self._simulate_snr_point(
            snr_db, config, snr_idx, len(config.snr_range), progress_callback
        )
        results.append(snr_result)
    
    return SimulationResults(
        snr_db=config.snr_range,
        ber=[r['ber'] for r in results],
        fer=[r['fer'] for r in results],
        simulation_time=time.time() - start_time,
        config=config
    )
```

**单SNR点仿真**：
```python
def _simulate_snr_point(self, snr_db: float, config: SimulationConfig, 
                       snr_idx: int, total_snr_points: int, progress_callback=None):
    total_frames = 0
    error_frames = 0
    total_bit_errors = 0
    total_iterations = 0
    
    # 噪声方差计算
    if config.channel_type == "awgn":
        noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
    elif config.channel_type == "bsc":
        crossover_prob = 0.5 * np.exp(-10 ** (snr_db / 10))
        crossover_prob = np.clip(crossover_prob, 1e-6, 0.49)
    
    # 蒙特卡洛仿真循环
    while (total_frames < config.frame_count and 
           (error_frames < config.max_errors or total_frames < config.min_frames)):
        
        # 1. 生成随机信息位
        info_bits = np.random.randint(0, 2, self.k)
        
        # 2. LDPC编码
        encoded_bits = self.encoder.encode(info_bits)
        
        # 3. 信道传输
        if config.channel_type == "awgn":
            received_signal, _ = self._awgn_channel(encoded_bits, noise_variance)
            llr = self.decoder.awgn_llr(received_signal, noise_variance)
        elif config.channel_type == "bsc":
            received_bits = self._bsc_channel(encoded_bits, crossover_prob)
            llr = self.decoder.bsc_llr(received_bits, crossover_prob)
        
        # 4. LDPC解码
        decoded_bits, decode_stats = self.decoder.decode(llr, config.decoder_algorithm)
        total_iterations += decode_stats['iterations']
        
        # 5. 错误统计
        decoded_info_bits = self.decoder.extract_information_bits(decoded_bits)
        bit_errors = np.sum(info_bits != decoded_info_bits)
        total_bit_errors += bit_errors
        
        if bit_errors > 0:
            error_frames += 1
        total_frames += 1
        
        # 6. 进度回调
        if progress_callback and total_frames % config.progress_interval == 0:
            current_ber = total_bit_errors / (total_frames * self.k)
            progress_callback({
                'snr_db': snr_db,
                'frames_completed': total_frames,
                'current_ber': current_ber,
                'avg_iterations': total_iterations / total_frames
            })
    
    # 计算最终统计结果
    ber = total_bit_errors / (total_frames * self.k)
    fer = error_frames / total_frames
    avg_iterations = total_iterations / total_frames
    
    return {'ber': ber, 'fer': fer, 'avg_iterations': avg_iterations}
```

**信道模拟**：
```python
def _awgn_channel(self, transmitted_bits: np.ndarray, noise_variance: float):
    """AWGN信道: BPSK调制 + 高斯噪声"""
    # BPSK调制: 0 -> +1, 1 -> -1
    transmitted_signal = 1 - 2 * transmitted_bits.astype(float)
    
    # 添加高斯噪声
    noise = np.random.normal(0, np.sqrt(noise_variance), len(transmitted_signal))
    received_signal = transmitted_signal + noise
    
    return received_signal, (received_signal < 0).astype(int)

def _bsc_channel(self, transmitted_bits: np.ndarray, crossover_prob: float):
    """BSC信道: 随机比特翻转"""
    flip_mask = np.random.random(len(transmitted_bits)) < crossover_prob
    return transmitted_bits ^ flip_mask.astype(int)
```

#### 3.2 仿真配置管理

**SimulationConfig数据类**：
```python
@dataclass
class SimulationConfig:
    snr_range: List[float]          # SNR扫描范围 (dB)
    frame_count: int = 1000         # 每个SNR点的帧数
    max_errors: int = 100           # 最大错误帧数（早期停止）
    min_frames: int = 100           # 最小仿真帧数
    channel_type: str = "awgn"      # 信道类型
    decoder_algorithm: str = "min_sum"  # 解码算法
    max_iterations: int = 50        # 解码最大迭代次数
    min_sum_scaling: float = 0.9    # Min-Sum缩放因子
    early_termination: bool = True  # 解码早期终止
    progress_interval: int = 10     # 进度回调间隔
```

### 4. 矩阵模板系统

#### 4.1 预定义模板库 (matrix_templates.py)

**LDPCMatrixTemplates类**提供多种预定义LDPC码：

```python
class LDPCMatrixTemplates:
    @staticmethod
    def get_available_templates() -> Dict[str, Dict]:
        return {
            "simple_6_3": {
                "name": "Simple (6,3) LDPC Code",
                "description": "Basic demonstration code with rate 1/2",
                "n": 6, "k": 3, "rate": 0.5,
                "complexity": "Low"
            },
            "ieee_648_324": {
                "name": "IEEE 802.11n (648,324) LDPC",
                "description": "WiFi standard LDPC code with rate 1/2",
                "n": 648, "k": 324, "rate": 0.5,
                "complexity": "High"
            },
            "dvb_s2_16200": {
                "name": "DVB-S2 (16200,10800) LDPC",
                "description": "Satellite TV standard LDPC code",
                "n": 16200, "k": 10800, "rate": 0.667,
                "complexity": "Very High"
            }
        }
```

**模板生成方法**：
- `simple_6_3()`: 基础演示码，适合教学
- `hamming_7_4()`: 经典汉明码LDPC适配
- `regular_12_6()`: 规则LDPC码，列重3，行重6
- `irregular_24_12()`: 不规则LDPC码，变量节点度分布[2,3,4]
- `ieee_802_11n()`: WiFi标准LDPC码
- `dvb_s2()`: 卫星电视标准LDPC码

**模板验证**：
```python
@staticmethod
def validate_template(h_matrix: np.ndarray) -> Dict[str, Any]:
    """验证LDPC矩阵的有效性"""
    if h_matrix.size == 0:
        return {'valid': False, 'error': 'Empty matrix'}
    
    m, n = h_matrix.shape
    if m >= n:
        return {'valid': False, 'error': 'Invalid matrix dimensions'}
    
    # 计算码参数
    rank = _rank_gf2(h_matrix)
    k = n - rank
    rate = k / n if n > 0 else 0
    
    return {
        'valid': True,
        'n': n, 'k': k, 'm': m, 'rank': rank, 'rate': rate,
        'density': np.mean(h_matrix),
        'min_row_weight': np.min(np.sum(h_matrix, axis=1)),
        'min_col_weight': np.min(np.sum(h_matrix, axis=0))
    }
```

### 5. 优化算法（预留接口）

虽然genetic_optimizer.py文件较小，但系统预留了遗传算法优化接口：

**优化请求模型**：
```python
class OptimizeRequest(BaseModel):
    n: int                    # 码长
    k: int                    # 信息位长度
    population_size: int = 50 # 种群大小
    generations: int = 100    # 进化代数
    mutation_rate: float = 0.1 # 变异率
    target_snr: float         # 目标SNR点
```

---

## 前端架构详细分析

### 1. Flutter应用结构

#### 1.1 应用入口 (main.dart)

```dart
void main() {
  ApiService.init();  // 初始化API服务
  
  runApp(
    ChangeNotifierProvider(
      create: (context) => AppProvider(),  // 全局状态管理
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LDPC Designer',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,  // 深色主题
        ),
      ),
      home: const MainScreen(),
    );
  }
}
```

**设计特点**：
- Material Design 3深色主题
- Provider状态管理模式
- 单页面应用架构
- 响应式UI设计

#### 1.2 状态管理 (app_provider.dart)

**AppProvider类**是整个应用的状态管理中心，使用Provider模式：

```dart
class AppProvider with ChangeNotifier {
  // 核心状态变量
  bool _isLoading = false;
  Map<String, dynamic> _simulationResults = {};
  Map<String, dynamic> _encodeResults = {};
  Map<String, dynamic> _decodeResults = {};
  
  // 图形数据
  final List<Node> _nodes = [];
  final List<Edge> _edges = [];
  int _vnCounter = 0;  // 变量节点计数器
  int _cnCounter = 0;  // 校验节点计数器
  Node? _selectedNode;
  
  // 输入控制器
  final TextEditingController snrController = TextEditingController();
  final TextEditingController frameCountController = TextEditingController();
  final TextEditingController infoBitsController = TextEditingController();
  // ... 更多控制器
```

**图形操作方法**：
```dart
// 添加变量节点
void addVariableNode() {
  _vnCounter++;
  _nodes.add(Node(
    id: 'V$_vnCounter',
    position: Offset(250.0 + Random().nextDouble() * 100, 200.0),
    isVariableNode: true,
  ));
  notifyListeners();
}

// 添加校验节点
void addCheckNode() {
  _cnCounter++;
  _nodes.add(Node(
    id: 'C$_cnCounter', 
    position: Offset(550.0 + Random().nextDouble() * 100, 200.0),
    isVariableNode: false,
  ));
  notifyListeners();
}

// 节点点击处理：连边逻辑
void tapNode(Node node) {
  if (_selectedNode == null) {
    _selectedNode = node;  // 选中节点
  } else {
    if (_selectedNode!.id != node.id) {
      // 创建边连接
      _edges.add(Edge(fromId: _selectedNode!.id, toId: node.id));
    }
    _selectedNode = null;  // 取消选中
  }
  notifyListeners();
}
```

**编码操作**：
```dart
Future<void> generateLDPCCode() async {
  if (_nodes.isEmpty || _edges.isEmpty) {
    _encodeResults = {'message': 'Error: Please draw a graph first.'};
    return;
  }

  _isLoading = true;
  notifyListeners();

  try {
    // 构造图形数据
    final graphData = {
      'nodes': _nodes.map((n) => {
        'id': n.id,
        'type': n.isVariableNode ? 'variable' : 'check',
      }).toList(),
      'edges': _edges.map((e) => {
        'fromId': e.fromId, 
        'toId': e.toId
      }).toList(),
    };

    // 调用后端API
    final data = await ApiService.generateCode(graphData: graphData);

    _encodeResults = {
      'message': data['message'] ?? 'LDPC code generated successfully.',
      'h_matrix': data['h_matrix'],
      'g_matrix': data['g_matrix'], 
      'code_rate': data['code_rate'],
      'n': data['n'], 'k': data['k'], 'm': data['m'],
      'codeword': data['codeword'],
    };
  } catch (e) {
    _encodeResults = {'message': 'Error: ${e.toString()}'};
  } finally {
    _isLoading = false;
    notifyListeners();
  }
}
```

**解码操作**（支持多种信道）：
```dart
Future<void> decodeData() async {
  // 根据选择的解码模式调用不同API
  Map<String, dynamic> data;
  
  switch (_selectedDecodeMode) {
    case 'llr':
      final llrValues = llrController.text
          .split(',')
          .map((s) => double.tryParse(s.trim()) ?? 0.0)
          .toList();
      
      data = await ApiService.decodeWithLLR(
        llr: llrValues,
        hMatrix: hMatrix,
        algorithm: _selectedAlgorithm,
        maxIterations: maxIterations,
        earlyTermination: _earlyTermination,
      );
      break;
      
    case 'awgn':
      final receivedSignal = receivedSignalController.text
          .split(',')
          .map((s) => double.tryParse(s.trim()) ?? 0.0)
          .toList();
      
      data = await ApiService.decodeWithAWGN(
        receivedSignal: receivedSignal,
        hMatrix: hMatrix,
        noiseVariance: noiseVariance,
        algorithm: _selectedAlgorithm,
      );
      break;
      
    case 'bsc':
      data = await ApiService.decodeWithBSC(
        receivedBits: _receivedBits,
        hMatrix: hMatrix,
        crossoverProbability: crossoverProb,
        algorithm: _selectedAlgorithm,
      );
      break;
  }
  
  _decodeResults = {
    'message': data['message'],
    'decoded_bits': data['decoded_bits'],
    'information_bits': data['information_bits'],
    'statistics': data['statistics'],
  };
}
```

**便捷功能**：
```dart
// 从码字生成LLR（模拟AWGN信道）
void generateLLRFromCodeword({double snrDb = 4.0}) {
  final codeword = _encodeResults['codeword'];
  if (codeword == null) return;

  // BPSK调制: 0 -> +1, 1 -> -1
  final modulated = codeword.map<double>((bit) => 1.0 - 2.0 * bit);

  // 计算噪声方差
  final snrLinear = pow(10, snrDb / 10.0);
  final noiseVariance = 1.0 / (2.0 * snrLinear);
  final noiseStd = sqrt(noiseVariance);

  // 添加高斯噪声并计算LLR
  final random = Random();
  final llrValues = modulated.map<double>((signal) {
    final noise = _generateGaussian(random) * noiseStd;
    final receivedSignal = signal + noise;
    return (2.0 * receivedSignal) / noiseVariance;
  }).toList();

  llrController.text = llrValues.map((v) => v.toStringAsFixed(3)).join(',');
  notifyListeners();
}

// BSC比特转LLR
void convertBSCtoLLR() {
  final crossoverProb = double.tryParse(crossoverProbabilityController.text) ?? 0.1;
  final logRatio = log((1 - crossoverProb) / crossoverProb);
  
  final llrValues = _receivedBits.map<double>((bit) {
    return logRatio * (1 - 2 * bit);
  }).toList();
  
  llrController.text = llrValues.map((v) => v.toStringAsFixed(3)).join(',');
}
```

### 2. API服务层

#### 2.1 网络通信 (api_service.dart)

**ApiService类**封装所有后端API调用：

```dart
class ApiService {
  static late Dio _dio;
  
  static void init() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));
    
    // 调试拦截器
    if (kDebugMode) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
      ));
    }
  }
  
  // 跨平台URL配置
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:9999/api';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:9999/api';  // Android模拟器
    }
    return 'http://127.0.0.1:9999/api';
  }
}
```

**编码API**：
```dart
static Future<Map<String, dynamic>> generateCode({
  required Map<String, dynamic> graphData,
}) async {
  try {
    final response = await _dio.post('/v1/encode', data: graphData);
    return response.data;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

static Future<Map<String, dynamic>> encodeWithMatrix({
  required List<List<int>> hMatrix,
  List<int>? infoBits,
}) async {
  final data = {
    'h_matrix': hMatrix,
    if (infoBits != null) 'info_bits': infoBits,
  };
  final response = await _dio.post('/v1/encode', data: data);
  return response.data;
}
```

**解码API**：
```dart
static Future<Map<String, dynamic>> decodeWithLLR({
  required List<double> llr,
  required List<List<int>> hMatrix,
  String algorithm = 'min_sum',
  int maxIterations = 50,
  bool earlyTermination = true,
  double minSumScaling = 0.9,
}) async {
  final data = {
    'llr': llr,
    'h_matrix': hMatrix,
    'algorithm': algorithm,
    'max_iterations': maxIterations,
    'early_termination': earlyTermination,
    'min_sum_scaling': minSumScaling,
  };
  final response = await _dio.post('/v1/decode', data: data);
  return response.data;
}

static Future<Map<String, dynamic>> decodeWithAWGN({
  required List<double> receivedSignal,
  required List<List<int>> hMatrix,
  required double noiseVariance,
  // ... 其他参数
}) async {
  final data = {
    'received_signal': receivedSignal,
    'h_matrix': hMatrix,
    'channel_type': 'awgn',
    'noise_variance': noiseVariance,
    // ... 其他字段
  };
  final response = await _dio.post('/v1/decode', data: data);
  return response.data;
}
```

**仿真API**：
```dart
static Future<Map<String, dynamic>> runSimulation({
  required List<List<int>> hMatrix,
  required List<double> snrRange,
  required int framesPerSnr,
  required String channelType,
  required String algorithm,
  required int maxIterations,
}) async {
  final response = await _dio.post('/simulate', data: {
    'h_matrix': hMatrix,
    'snr_range': snrRange,
    'frames_per_snr': framesPerSnr,
    'channel_type': channelType,
    'algorithm': algorithm,
    'max_iterations': maxIterations,
  });
  return response.data;
}
```

**错误处理**：
```dart
static String _handleDioError(DioException error) {
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
      return '连接超时，请检查网络连接';
    case DioExceptionType.sendTimeout:
      return '发送超时，请重试';
    case DioExceptionType.receiveTimeout:
      return '响应超时，请重试';
    case DioExceptionType.badResponse:
      final statusCode = error.response?.statusCode;
      final message = error.response?.data?['error'] ?? '服务器错误';
      return 'HTTP $statusCode: $message';
    case DioExceptionType.cancel:
      return '请求已取消';
    case DioExceptionType.unknown:
      return '网络连接失败，请检查网络设置';
    default:
      return '未知错误: ${error.message}';
  }
}
```

### 3. UI组件系统

#### 3.1 图形绘制画布 (graph_canvas.dart)

**GraphCanvas组件**实现交互式Tanner图编辑：

```dart
class GraphCanvas extends StatelessWidget {
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return GestureDetector(
          onTap: () => appProvider.tapCanvas(),  // 点击空白取消选中
          child: Container(
            color: Colors.grey[850],
            child: CustomPaint(
              painter: EdgePainter(  // 自定义绘制器
                edges: appProvider.edges,
                nodes: appProvider.nodes,
                selectedNode: appProvider.selectedNode,
              ),
              child: Stack(
                children: [
                  // 绘制所有节点
                  ...appProvider.nodes.map((node) {
                    return Positioned(
                      left: node.position.dx - 25,
                      top: node.position.dy - 25,
                      child: GraphNodeWidget(node: node),
                    );
                  }),
                  
                  // 显示图信息面板
                  Positioned(
                    top: 10, left: 10,
                    child: GraphInfoPanel(appProvider: appProvider),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
```

**EdgePainter自定义绘制器**：
```dart
class EdgePainter extends CustomPainter {
  final List<Edge> edges;
  final List<Node> nodes;
  final Node? selectedNode;
  
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white70
      ..strokeWidth = 2.0;
    
    // 绘制所有边
    for (final edge in edges) {
      final fromNode = nodes.firstWhere((n) => n.id == edge.fromId);
      final toNode = nodes.firstWhere((n) => n.id == edge.toId);
      
      canvas.drawLine(
        fromNode.position,
        toNode.position,
        paint,
      );
    }
    
    // 如果有选中节点，绘制预览线
    if (selectedNode != null) {
      final previewPaint = Paint()
        ..color = Colors.yellow.withOpacity(0.6)
        ..strokeWidth = 2.0
        ..strokeCap = StrokeCap.round;
      
      // 绘制从选中节点到鼠标位置的预览线
      // (实际实现需要鼠标位置追踪)
    }
  }
  
  bool shouldRepaint(EdgePainter oldDelegate) {
    return edges != oldDelegate.edges || 
           nodes != oldDelegate.nodes ||
           selectedNode != oldDelegate.selectedNode;
  }
}
```

#### 3.2 节点组件 (graph_node_widget.dart)

**GraphNodeWidget**实现可拖拽的节点：

```dart
class GraphNodeWidget extends StatelessWidget {
  final Node node;
  
  Widget build(BuildContext context) {
    final appProvider = Provider.of<AppProvider>(context, listen: false);
    final isSelected = appProvider.selectedNode?.id == node.id;
    
    return GestureDetector(
      onTap: () => appProvider.tapNode(node),
      onPanUpdate: (details) {
        appProvider.updateNodePosition(node.id, details.delta);
      },
      onLongPress: () => _showNodeContextMenu(context),
      
      child: Container(
        width: 50, height: 50,
        decoration: BoxDecoration(
          shape: node.isVariableNode ? BoxShape.circle : BoxShape.rectangle,
          color: node.isVariableNode ? Colors.blue : Colors.red,
          border: isSelected ? Border.all(color: Colors.yellow, width: 3) : null,
          boxShadow: [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 4,
              offset: Offset(2, 2),
            ),
          ],
        ),
        child: Center(
          child: Text(
            node.id,
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
  
  void _showNodeContextMenu(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Node ${node.id}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Type: ${node.isVariableNode ? "Variable" : "Check"}'),
            Text('Position: (${node.position.dx.toInt()}, ${node.position.dy.toInt()})'),
            Text('Degree: ${_calculateNodeDegree()}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              Provider.of<AppProvider>(context, listen: false)
                  .removeNode(node.id);
            },
            child: Text('Delete'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Close'),
          ),
        ],
      ),
    );
  }
}
```

#### 3.3 矩阵查看器 (matrix_viewer.dart)

**MatrixViewer组件**提供交互式矩阵可视化：

```dart
class MatrixViewer extends StatefulWidget {
  final List<List<int>>? matrix;
  final String title;
  final double cellSize;
  final bool showInfo;
  
  const MatrixViewer({
    this.matrix,
    this.title = 'Matrix',
    this.cellSize = 30.0,
    this.showInfo = true,
  });
}

class _MatrixViewerState extends State<MatrixViewer> {
  double _scale = 1.0;
  final TransformationController _transformationController = 
      TransformationController();
  
  Widget build(BuildContext context) {
    if (widget.matrix == null || widget.matrix!.isEmpty) {
      return _buildEmptyState();
    }
    
    final matrix = widget.matrix!;
    final rows = matrix.length;
    final cols = matrix[0].length;
    
    return Column(
      children: [
        // 矩阵信息栏
        if (widget.showInfo) _buildInfoBar(rows, cols),
        
        // 可缩放的矩阵视图
        Expanded(
          child: InteractiveViewer(
            transformationController: _transformationController,
            boundaryMargin: EdgeInsets.all(20),
            minScale: 0.1,
            maxScale: 5.0,
            child: _buildMatrixGrid(matrix),
          ),
        ),
        
        // 缩放控制栏
        _buildZoomControls(),
      ],
    );
  }
  
  Widget _buildMatrixGrid(List<List<int>> matrix) {
    return Container(
      padding: EdgeInsets.all(10),
      child: Column(
        children: matrix.asMap().entries.map((rowEntry) {
          final rowIndex = rowEntry.key;
          final row = rowEntry.value;
          
          return Row(
            children: row.asMap().entries.map((colEntry) {
              final colIndex = colEntry.key;
              final value = colEntry.value;
              
              return Container(
                width: widget.cellSize,
                height: widget.cellSize,
                decoration: BoxDecoration(
                  color: value == 1 ? Colors.white : Colors.grey[800],
                  border: Border.all(
                    color: Colors.grey[600]!,
                    width: 0.5,
                  ),
                ),
                child: value == 1 ? Center(
                  child: Text(
                    '1',
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: widget.cellSize * 0.4,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ) : null,
              );
            }).toList(),
          );
        }).toList(),
      ),
    );
  }
  
  Widget _buildInfoBar(int rows, int cols) {
    final density = _calculateDensity();
    
    return Container(
      padding: EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.grey[850],
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        children: [
          Text('${widget.title}: '),
          Text('${rows}×${cols} '),
          Text('Density: ${(density * 100).toStringAsFixed(1)}% '),
          Spacer(),
          Text('Scale: ${(_scale * 100).toInt()}%'),
        ],
      ),
    );
  }
  
  double _calculateDensity() {
    if (widget.matrix == null) return 0.0;
    int ones = 0;
    int total = 0;
    
    for (final row in widget.matrix!) {
      for (final value in row) {
        if (value == 1) ones++;
        total++;
      }
    }
    
    return total > 0 ? ones / total : 0.0;
  }
}
```

### 4. 模板与工具功能

#### 4.1 LDPC码模板

前端提供多种预定义LDPC码模板：

```dart
void loadTemplate(String templateType) {
  clearCanvas();
  
  switch (templateType) {
    case '3_6_regular':
      _loadRegularTemplate(3, 6);  // (3,6)规则码
      break;
    case '4_8_regular':
      _loadRegularTemplate(4, 8);  // (4,8)规则码
      break;
    case 'irregular':
      _loadIrregularTemplate();    // 不规则码
      break;
  }
  
  _simulationResults = {
    'message': 'Template "$templateType" loaded successfully.',
    'ber': 'N/A',
  };
  notifyListeners();
}

void _loadRegularTemplate(int variableDegree, int checkDegree) {
  final int variableNodeCount = checkDegree;
  final int checkNodeCount = variableDegree;
  
  // 添加变量节点（左侧）
  for (int i = 0; i < variableNodeCount; i++) {
    _vnCounter++;
    _nodes.add(Node(
      id: 'V$_vnCounter',
      position: Offset(150.0, 100.0 + i * 60.0),
      isVariableNode: true,
    ));
  }
  
  // 添加校验节点（右侧）
  for (int i = 0; i < checkNodeCount; i++) {
    _cnCounter++;
    _nodes.add(Node(
      id: 'C$_cnCounter',
      position: Offset(550.0, 120.0 + i * 90.0),
      isVariableNode: false,
    ));
  }
  
  // 轮转连接确保规则度分布
  final variableNodes = _nodes.where((n) => n.isVariableNode).toList();
  final checkNodes = _nodes.where((n) => !n.isVariableNode).toList();
  
  int edgeCounter = 0;
  for (final vNode in variableNodes) {
    for (int e = 0; e < variableDegree; e++) {
      final cNode = checkNodes[edgeCounter % checkNodes.length];
      _edges.add(Edge(fromId: vNode.id, toId: cNode.id));
      edgeCounter++;
    }
  }
}
```

#### 4.2 随机图生成

```dart
void generateRandomGraph() {
  clearCanvas();
  
  final random = Random();
  const variableNodeCount = 6;
  const checkNodeCount = 4;
  
  // 添加变量节点
  for (int i = 0; i < variableNodeCount; i++) {
    _vnCounter++;
    _nodes.add(Node(
      id: 'V$_vnCounter',
      position: Offset(
        100.0 + random.nextDouble() * 300,
        100.0 + random.nextDouble() * 200,
      ),
      isVariableNode: true,
    ));
  }
  
  // 添加校验节点
  for (int i = 0; i < checkNodeCount; i++) {
    _cnCounter++;
    _nodes.add(Node(
      id: 'C$_cnCounter',
      position: Offset(
        500.0 + random.nextDouble() * 300,
        100.0 + random.nextDouble() * 200,
      ),
      isVariableNode: false,
    ));
  }
  
  // 随机连边
  final variableNodes = _nodes.where((n) => n.isVariableNode).toList();
  final checkNodes = _nodes.where((n) => !n.isVariableNode).toList();
  
  for (final vNode in variableNodes) {
    final degree = 2 + random.nextInt(2);  // 度数2-3
    final targets = checkNodes.toList()..shuffle();
    
    for (int i = 0; i < degree && i < targets.length; i++) {
      _edges.add(Edge(fromId: vNode.id, toId: targets[i].id));
    }
  }
}
```

---

## 前后端通信机制

### 1. HTTP API通信

#### 1.1 RESTful API设计

系统采用标准RESTful API设计，主要端点包括：

**编码相关**：
- `POST /api/v1/encode` - LDPC编码服务
  - 输入：图形数据或H矩阵+信息位
  - 输出：H矩阵、G矩阵、码率参数、码字

**解码相关**：  
- `POST /api/v1/decode` - LDPC解码服务
  - 支持多种输入：LLR、AWGN接收信号、BSC接收比特
  - 支持多种算法：Min-Sum、Sum-Product
  - 输出：解码比特、信息位、解码统计信息

**仿真相关**：
- `POST /api/simulate` - 完整BER仿真
- `POST /api/quick-test` - 快速性能测试
- `POST /api/simulate-from-graph` - 从图直接仿真

**工具相关**：
- `GET /api/matrix-templates` - 获取可用模板
- `POST /api/generate-template` - 生成模板矩阵
- `GET /api/performance-metrics` - 性能监控

#### 1.2 请求/响应格式

**编码请求示例**：
```json
{
  "nodes": [
    {"id": "V1", "type": "variable"},
    {"id": "V2", "type": "variable"},
    {"id": "C1", "type": "check"}
  ],
  "edges": [
    {"fromId": "V1", "toId": "C1"},
    {"fromId": "V2", "toId": "C1"}
  ],
  "info_bits": [1, 0]
}
```

**编码响应示例**：
```json
{
  "h_matrix": [[1, 1, 1, 0, 0, 0], [0, 1, 1, 1, 0, 0]],
  "g_matrix": [[1, 0, 0, 1, 1, 0], [0, 1, 0, 1, 0, 1]],
  "code_rate": 0.5,
  "n": 6, "k": 3, "m": 3,
  "codeword": [1, 0, 0, 1, 1, 0],
  "message": "LDPC code generated successfully"
}
```

**解码请求示例**：
```json
{
  "received_bits": [1, 0, 1, 0, 1, 0],
  "h_matrix": [[1, 1, 1, 0, 0, 0], [0, 1, 1, 1, 0, 0]],
  "channel_type": "bsc",
  "crossover_probability": 0.1,
  "algorithm": "min_sum",
  "max_iterations": 50,
  "early_termination": true
}
```

**仿真请求示例**：
```json
{
  "h_matrix": [[1, 1, 1, 0, 0, 0], [0, 1, 1, 1, 0, 0]],
  "snr_range": [0.0, 1.0, 2.0, 3.0, 4.0],
  "frames_per_snr": 1000,
  "channel_type": "awgn",
  "algorithm": "min_sum",
  "max_iterations": 50
}
```

#### 1.3 错误处理机制

**后端错误处理**：
```python
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid input",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )
```

**前端错误处理**：
```dart
static String _handleDioError(DioException error) {
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
      return '连接超时，请检查网络连接';
    case DioExceptionType.badResponse:
      final statusCode = error.response?.statusCode;
      final message = error.response?.data?['error'] ?? '服务器错误';
      return 'HTTP $statusCode: $message';
    default:
      return '网络错误: ${error.message}';
  }
}
```

### 2. WebSocket实时通信（预留）

#### 2.1 实时进度更新

系统预留WebSocket接口用于长时间仿真的实时进度更新：

**后端WebSocket端点**：
```python
@app.websocket("/ws/simulate/{session_id}")
async def simulation_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        while True:
            # 接收前端消息
            data = await websocket.receive_text()
            request = json.loads(data)
            
            # 运行仿真并发送进度更新
            await run_simulation_with_progress(request, websocket)
            
    except WebSocketDisconnect:
        print(f"Client {session_id} disconnected")

async def run_simulation_with_progress(request, websocket):
    config = SimulationConfig(**request)
    engine = SimulationEngine(request['h_matrix'])
    
    async def progress_callback(progress_info):
        await websocket.send_text(json.dumps({
            'type': 'progress',
            'data': progress_info
        }))
    
    results = await engine.run_ber_simulation(config, progress_callback)
    
    # 发送最终结果
    await websocket.send_text(json.dumps({
        'type': 'completed',
        'data': results
    }))
```

**前端WebSocket客户端**：
```dart
void _connectWebSocket() {
  final channel = ApiService.createWebSocketChannel('/ws/simulate/session_123');
  
  channel.stream.listen(
    (message) {
      final data = json.decode(message);
      
      switch (data['type']) {
        case 'progress':
          _updateSimulationProgress(data['data']);
          break;
        case 'completed':
          _handleSimulationComplete(data['data']);
          break;
        case 'error':
          _handleSimulationError(data['message']);
          break;
      }
    },
    onError: (error) {
      print('WebSocket error: $error');
    },
    onDone: () {
      print('WebSocket connection closed');
    },
  );
  
  // 发送仿真请求
  channel.sink.add(json.encode({
    'h_matrix': hMatrix,
    'snr_range': snrRange,
    'frames_per_snr': framesPerSnr,
  }));
}
```

### 3. 跨平台适配

#### 3.1 网络配置

不同平台的网络配置适配：

```dart
static String get baseUrl {
  if (kIsWeb) {
    // Web平台：直接访问
    return 'http://127.0.0.1:9999/api';
  }
  
  if (defaultTargetPlatform == TargetPlatform.android) {
    // Android模拟器：使用特殊IP
    return 'http://10.0.2.2:9999/api';
  }
  
  if (defaultTargetPlatform == TargetPlatform.iOS) {
    // iOS模拟器：使用localhost
    return 'http://localhost:9999/api';
  }
  
  // 桌面平台：默认localhost
  return 'http://127.0.0.1:9999/api';
}

static String get wsBaseUrl {
  // WebSocket URL适配
  return baseUrl.replaceFirst('http', 'ws').replaceFirst('/api', '');
}
```

#### 3.2 启动脚本

**Windows批处理脚本** (`start_full_app.bat`)：
```batch
@echo off
title LDPC 完整应用启动器

echo [1/4] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python未安装
    pause
    exit /b 1
)

echo [2/4] 检查Flutter环境...
flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Flutter未安装
    pause
    exit /b 1
)

echo [3/4] 启动后端服务器...
cd /d "%~dp0backend"
start "LDPC Backend" cmd /k "python main.py"

echo [4/4] 等待后端启动（5秒）...
timeout /t 5 /nobreak >nul

echo [5/5] 启动前端应用...
cd /d "%~dp0my_ldpc_app"
start "LDPC Frontend" cmd /k "flutter run -d windows"

echo 应用启动完成！
```

**Linux/macOS Shell脚本** (`start_app.sh`)：
```bash
#!/bin/bash
echo "Starting LDPC Designer Application..."

echo "[1/3] Starting Backend Server..."
cd backend
python3 main.py &
BACKEND_PID=$!

echo "[2/3] Waiting for backend to start..."
sleep 3

echo "[3/3] Starting Flutter Web Application..."
cd ../my_ldpc_app
flutter run -d chrome

# 清理后台进程
trap "kill $BACKEND_PID" EXIT
```

---

## 核心算法技术细节

### 1. LDPC编码算法

#### 1.1 系统化编码

系统化LDPC编码确保码字的前k位就是信息位，便于信息位提取：

**生成矩阵构造**：
1. 对H矩阵进行GF(2)高斯消元
2. 找到主元列作为校验位位置
3. 非主元列作为信息位位置
4. 构造系统形式生成矩阵G = [I_k | P]

```python
def _compute_generator_matrix(self) -> np.ndarray:
    H_dense = self.H.toarray()
    H_rref, pivots = _row_echelon_gf2(H_dense.copy())
    
    # 信息位列 = 所有列 - 主元列
    all_cols = set(range(self.n))
    info_cols = sorted(all_cols - set(pivots))
    self._info_cols = info_cols
    
    k = len(info_cols)
    G = np.zeros((k, self.n), dtype=int)
    
    # 单位矩阵部分：G[:, info_cols] = I_k
    G[np.arange(k), info_cols] = 1
    
    # 校验矩阵部分：G[:, pivots] = P
    for row_in_H, pivot_col in enumerate(pivots):
        G[:, pivot_col] = H_rref[row_in_H, info_cols]
    
    # 验证正交性：H @ G^T = 0 (mod 2)
    assert not np.any((H_dense @ G.T) % 2)
    
    return G
```

**编码过程**：
```python
def encode(self, info_bits: np.ndarray) -> np.ndarray:
    """c = u @ G (mod 2)"""
    G = self.generate_g_matrix()
    return (info_bits @ G) % 2
```

#### 1.2 GF(2)高斯消元

在二进制域GF(2)上的高斯消元法，用于矩阵行简化：

```python
def _row_echelon_gf2(A: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """GF(2)上的简化行阶梯形式"""
    A = (A % 2).astype(np.uint8, copy=True)
    m, n = A.shape
    r = 0  # 当前行
    pivots: List[int] = []
    
    for c in range(n):  # 遍历每一列
        # 寻找主元（第一个1）
        pivot_row = -1
        for i in range(r, m):
            if A[i, c] == 1:
                pivot_row = i
                break
        
        if pivot_row == -1:
            continue  # 这一列全为0，跳过
        
        # 交换行，将主元移至当前行
        if pivot_row != r:
            A[[r, pivot_row]] = A[[pivot_row, r]]
        
        # 消元：将该列其他1变为0
        for i in range(m):
            if i != r and A[i, c] == 1:
                A[i] ^= A[r]  # GF(2)上的异或操作
        
        pivots.append(c)
        r += 1
        if r == m:
            break
    
    return A, pivots
```

### 2. LDPC解码算法

#### 2.1 置信传播算法框架

置信传播（Belief Propagation）是LDPC解码的核心算法，基于双子图上的消息传递：

**算法框架**：
1. **初始化**：变量节点用信道LLR初始化
2. **校验节点更新**：聚合相邻变量节点消息
3. **变量节点更新**：结合信道信息和校验节点消息
4. **后验计算**：计算后验LLR并硬判决
5. **收敛检查**：验证奇偶校验约束

#### 2.2 Min-Sum算法

Min-Sum是Sum-Product算法的简化版本，计算复杂度更低：

**校验节点更新规则**：
```python
# 校验节点 c 到变量节点 v 的消息
def check_to_var_message(connected_vars, target_var, v2c_messages):
    other_vars = [v for v in connected_vars if v != target_var]
    if not other_vars:
        return 0.0
    
    # 收集其他变量节点的消息
    messages = [v2c_messages[v][check_idx] for v in other_vars]
    
    # Min-Sum规则：符号乘积 × 最小幅度
    signs = [1 if msg >= 0 else -1 for msg in messages]
    abs_messages = [abs(msg) for msg in messages]
    
    sign_product = np.prod(signs)
    min_magnitude = min(abs_messages)
    
    # 应用缩放因子提升性能
    return self.min_sum_scaling * sign_product * min_magnitude
```

**变量节点更新规则**：
```python
# 变量节点 v 到校验节点 c 的消息
def var_to_check_message(connected_checks, target_check, c2v_messages, channel_llr):
    other_checks = [c for c in connected_checks if c != target_check]
    
    # 信道LLR + 其他校验节点消息之和
    message_sum = channel_llr
    for check_idx in other_checks:
        message_sum += c2v_messages[check_idx][var_idx]
    
    return message_sum
```

**归一化Min-Sum优化**：
```python
# 自适应归一化因子
avg_check_degree = np.mean([len(self.check_to_var[i]) for i in range(self.m)])
normalization_factor = 1.0 / (0.75 + 0.25 * avg_check_degree / 4.0)

# 应用归一化
c2v_message = (
    self.min_sum_scaling * sign_product * min_abs * normalization_factor
)
```

#### 2.3 Sum-Product算法

Sum-Product算法在对数域实现，提供最优的MAP解码性能：

**校验节点更新（对数域tanh规则）**：
```python
def check_node_update_sum_product(connected_vars, target_var, v2c_messages):
    other_vars = [v for v in connected_vars if v != target_var]
    if not other_vars:
        return 0.0
    
    # 对数域Sum-Product：∏tanh(LLR/2) -> 2*atanh(∏)
    tanh_values = [np.tanh(v2c_messages[v][check_idx] / 2.0) for v in other_vars]
    product = np.prod(tanh_values)
    
    # 数值稳定性处理
    product = np.clip(product, -1 + 1e-10, 1 - 1e-10)
    
    return 2.0 * np.arctanh(product)
```

**变量节点更新（对数域加法）**：
```python
def var_node_update_sum_product(connected_checks, target_check, c2v_messages, channel_llr):
    other_checks = [c for c in connected_checks if c != target_check]
    
    # 对数域简单求和
    message_sum = channel_llr
    for check_idx in other_checks:
        message_sum += c2v_messages[check_idx][var_idx]
    
    return message_sum
```

#### 2.4 OSD后处理

有序统计解码（OSD）用于处理BP算法未收敛的情况：

```python
def ordered_statistics_decoding(self, decoded_bits, posterior_llr):
    """OSD后处理：翻转最不可靠的比特组合"""
    if self.osd_order <= 0:
        return decoded_bits, False
    
    # 按可靠性排序：|LLR|越小越不可靠
    uncertain_indices = np.argsort(np.abs(posterior_llr))[:self.osd_order + 1]
    
    # 尝试所有可能的翻转组合
    for flip_count in range(1, self.osd_order + 2):
        for flip_set in combinations(uncertain_indices, flip_count):
            # 翻转选定比特
            temp_bits = decoded_bits.copy()
            temp_bits[list(flip_set)] = 1 - temp_bits[list(flip_set)]
            
            # 检查奇偶校验约束
            syndrome = (self.H @ temp_bits) % 2
            if np.all(syndrome == 0):
                return temp_bits, True  # 找到有效码字
    
    return decoded_bits, False  # OSD失败
```

### 3. 信道模型与LLR计算

#### 3.1 AWGN信道

加性高斯白噪声信道模型：

**信道模型**：
```python
def awgn_channel(transmitted_bits, snr_db):
    # BPSK调制：0 -> +1, 1 -> -1
    symbols = 1 - 2 * transmitted_bits.astype(float)
    
    # 噪声方差计算
    snr_linear = 10 ** (snr_db / 10)
    noise_variance = 1.0 / (2.0 * snr_linear)  # 假设单位符号能量
    
    # 添加高斯噪声
    noise = np.random.normal(0, np.sqrt(noise_variance), len(symbols))
    received_signal = symbols + noise
    
    return received_signal, noise_variance
```

**LLR计算**：
```python
def awgn_llr(received_signal, noise_variance):
    """AWGN信道LLR：L(c) = 2*r/σ²"""
    return 2.0 * received_signal / noise_variance
```

#### 3.2 BSC信道

二进制对称信道模型：

**信道模型**：
```python
def bsc_channel(transmitted_bits, crossover_prob):
    """BSC信道：以概率p翻转每个比特"""
    flip_mask = np.random.random(len(transmitted_bits)) < crossover_prob
    received_bits = transmitted_bits ^ flip_mask.astype(int)
    return received_bits
```

**LLR计算**：
```python
def bsc_llr(received_bits, crossover_prob):
    """BSC信道LLR：L(c) = log((1-p)/p) * (1-2*r)"""
    if crossover_prob <= 0 or crossover_prob >= 0.5:
        raise ValueError("交叉概率必须在(0, 0.5)范围内")
    
    log_ratio = np.log((1 - crossover_prob) / crossover_prob)
    return log_ratio * (1 - 2 * received_bits)
```

### 4. 性能仿真算法

#### 4.1 蒙特卡洛仿真

使用蒙特卡洛方法估计BER/FER性能：

```python
def monte_carlo_simulation(snr_db, config):
    """单SNR点蒙特卡洛仿真"""
    total_frames = 0
    error_frames = 0
    total_bit_errors = 0
    total_iterations = 0
    
    # 噪声参数计算
    if config.channel_type == "awgn":
        noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
    elif config.channel_type == "bsc":
        crossover_prob = 0.5 * np.exp(-10 ** (snr_db / 10))
    
    while (total_frames < config.frame_count and 
           error_frames < config.max_errors):
        
        # 1. 生成随机信息序列
        info_bits = np.random.randint(0, 2, self.k)
        
        # 2. LDPC编码
        codeword = self.encoder.encode(info_bits)
        
        # 3. 信道传输
        if config.channel_type == "awgn":
            received_signal, _ = self._awgn_channel(codeword, noise_variance)
            llr = self.decoder.awgn_llr(received_signal, noise_variance)
        else:
            received_bits = self._bsc_channel(codeword, crossover_prob)
            llr = self.decoder.bsc_llr(received_bits, crossover_prob)
        
        # 4. LDPC解码
        decoded_bits, stats = self.decoder.decode(llr, config.algorithm)
        total_iterations += stats['iterations']
        
        # 5. 错误统计
        decoded_info = self.decoder.extract_information_bits(decoded_bits)
        bit_errors = np.sum(info_bits != decoded_info)
        total_bit_errors += bit_errors
        
        if bit_errors > 0:
            error_frames += 1
        
        total_frames += 1
    
    # 性能指标计算
    ber = total_bit_errors / (total_frames * self.k)
    fer = error_frames / total_frames
    avg_iterations = total_iterations / total_frames
    
    return {
        'ber': ber,
        'fer': fer, 
        'avg_iterations': avg_iterations,
        'total_frames': total_frames
    }
```

#### 4.2 早期停止策略

为提高仿真效率，采用早期停止策略：

```python
class EarlyStoppingStrategy:
    def __init__(self, min_errors=100, min_frames=1000, max_frames=100000):
        self.min_errors = min_errors      # 最少错误帧数
        self.min_frames = min_frames      # 最少仿真帧数
        self.max_frames = max_frames      # 最大仿真帧数
    
    def should_stop(self, error_frames, total_frames):
        # 达到最大帧数
        if total_frames >= self.max_frames:
            return True
        
        # 达到最小帧数且足够错误样本
        if (total_frames >= self.min_frames and 
            error_frames >= self.min_errors):
            return True
        
        return False
    
    def estimate_confidence_interval(self, ber, total_bits):
        """估计BER的95%置信区间"""
        if ber == 0:
            return 0, 3.0 / total_bits  # 使用Rule of Three
        
        # 使用正态近似
        std_error = np.sqrt(ber * (1 - ber) / total_bits)
        margin = 1.96 * std_error  # 95%置信区间
        
        return max(0, ber - margin), ber + margin
```

---

## 系统特色与创新点

### 1. 图形化设计界面

#### 1.1 直观的Tanner图编辑

- **拖拽式节点操作**：变量节点（圆形）和校验节点（方形）
- **智能连线系统**：点击节点自动连线，支持实时预览
- **节点属性查看**：长按显示节点ID、类型、度数、位置
- **多种输入模式**：手动绘制、模板加载、随机生成

#### 1.2 实时参数计算

- **码参数自动计算**：码长n、信息位长度k、码率R
- **结构分析**：度分布、规则性检测、环长分析
- **矩阵密度统计**：稀疏度可视化、连通性检查

### 2. 多算法解码支持

#### 2.1 置信传播算法族

- **Min-Sum算法**：低复杂度，适合硬件实现
- **Sum-Product算法**：最优MAP性能，对数域数值稳定
- **归一化Min-Sum**：自适应归一化因子，性能接近Sum-Product
- **OSD后处理**：处理BP未收敛情况，提升错误平层性能

#### 2.2 解码参数优化

- **自适应迭代控制**：早期终止、最大迭代次数限制
- **缩放因子调优**：Min-Sum缩放因子自动优化
- **数值稳定性**：对数域运算、饱和处理

### 3. 多信道仿真引擎

#### 3.1 信道模型支持

- **AWGN信道**：BPSK调制、高斯噪声、LLR计算
- **BSC信道**：二进制对称、交叉概率可调
- **信道参数自动适配**：SNR转噪声方差、概率转LLR

#### 3.2 高效仿真算法

- **蒙特卡洛仿真**：大数定律保证统计精度
- **早期停止策略**：最小错误数、置信区间估计
- **进度实时更新**：WebSocket推送、中断恢复

### 4. 跨平台部署

#### 4.1 多平台适配

- **Web应用**：Chrome、Firefox、Safari支持
- **桌面应用**：Windows、macOS、Linux原生
- **移动应用**：Android、iOS触控优化
- **网络自适应**：平台特定API基址配置

#### 4.2 响应式设计

- **自适应布局**：屏幕尺寸自动调整
- **触控友好**：手势操作、长按菜单
- **暗色主题**：护眼模式、专业外观

### 5. 性能优化策略

#### 5.1 后端优化

- **稀疏矩阵存储**：CSR格式、内存高效
- **邻接表预计算**：BP算法加速、减少查找时间
- **并行仿真**：多线程、异步处理
- **内存池管理**：避免频繁分配释放

#### 5.2 前端优化

- **状态管理优化**：Provider精确更新、避免过度重建
- **Canvas高效绘制**：CustomPainter、只重绘变化部分
- **网络请求优化**：连接池、超时控制、错误重试
- **数据缓存**：结果本地存储、减少重复计算

---

## 开发环境与部署

### 1. 开发环境搭建

#### 1.1 后端环境

**Python环境要求**：
- Python 3.8+
- NumPy 1.26.0+（矩阵运算）
- SciPy 1.11.3+（稀疏矩阵）
- FastAPI 0.110+（Web框架）
- Uvicorn 0.24.0+（ASGI服务器）
- Pydantic 2.4.2+（数据验证）

**安装命令**：
```bash
cd backend
pip install -r requirements.txt
```

#### 1.2 前端环境

**Flutter环境要求**：
- Flutter 3.8+
- Dart 3.8+

**依赖包**：
- provider: 6.1.2（状态管理）
- dio: 5.3.2（HTTP客户端）
- web_socket_channel: 2.4.0（WebSocket）
- fl_chart: 0.64.0（图表绘制）

**安装命令**：
```bash
cd my_ldpc_app
flutter pub get
```

### 2. 本地开发

#### 2.1 后端启动

```bash
cd backend
python main.py
# 服务运行在 http://127.0.0.1:9999
# API文档: http://127.0.0.1:9999/docs
```

#### 2.2 前端启动

```bash
cd my_ldpc_app

# Web版本
flutter run -d chrome

# Windows桌面版
flutter run -d windows

# Android版（需要模拟器或设备）
flutter run -d android
```

#### 2.3 一键启动脚本

**Windows**：
```bash
start_full_app.bat
```

**Linux/macOS**：
```bash
chmod +x my_ldpc_app/start_app.sh
./my_ldpc_app/start_app.sh
```

### 3. 生产部署

#### 3.1 后端部署

**Docker容器化**：
```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
EXPOSE 9999

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]
```

**systemd服务**：
```ini
[Unit]
Description=LDPC Backend API
After=network.target

[Service]
Type=simple
User=ldpc
WorkingDirectory=/opt/ldpc/backend
ExecStart=/usr/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 3.2 前端部署

**Web版本构建**：
```bash
cd my_ldpc_app
flutter build web --release
# 输出到 build/web/
```

**桌面版本构建**：
```bash
# Windows
flutter build windows --release

# macOS
flutter build macos --release

# Linux
flutter build linux --release
```

**Nginx配置**：
```nginx
server {
    listen 80;
    server_name ldpc.example.com;
    
    # 前端静态文件
    location / {
        root /var/www/ldpc/web;
        try_files $uri $uri/ /index.html;
    }
    
    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:9999/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket代理
    location /ws/ {
        proxy_pass http://127.0.0.1:9999/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 总结

本LDPC可视化编解码仿真系统是一个功能完整、技术先进的教学和科研工具。系统在以下方面表现出色：

### 技术优势

1. **完整的LDPC工具链**：从图形设计到性能仿真的一站式解决方案
2. **多算法支持**：Min-Sum、Sum-Product等主流解码算法
3. **高性能仿真**：优化的蒙特卡洛仿真引擎，支持多信道模型
4. **跨平台部署**：Flutter+FastAPI架构，支持Web/桌面/移动多平台
5. **用户友好界面**：直观的图形化操作，实时参数反馈

### 系统特色

1. **图形化设计**：拖拽式Tanner图编辑，可视化矩阵查看
2. **实时仿真**：WebSocket推送进度，交互式BER曲线
3. **智能优化**：遗传算法码结构优化（预留接口）
4. **模板丰富**：内置多种标准LDPC码模板
5. **教学友好**：详细的解码统计信息，算法对比功能

### 应用价值

1. **教育教学**：信息论课程的理想演示工具
2. **科学研究**：LDPC码性能分析和算法验证平台
3. **工程应用**：通信系统设计的原型验证工具
4. **技术培训**：企业培训和技术交流的实用工具

该系统展现了现代软件工程在信息论教学和科研中的巨大潜力，为LDPC码的学习、研究和应用提供了强有力的技术支撑。通过图形化界面降低了学习门槛，通过高性能算法满足了专业需求，是一个真正意义上的产学研一体化平台。