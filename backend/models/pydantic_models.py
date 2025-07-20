from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Union
import numpy as np

# 图形数据模型
class Node(BaseModel):
    id: str
    type: str  # "variable" 或 "check"

class Edge(BaseModel):
    fromId: str
    toId: str

class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    snr_db: Optional[float] = 4.0

# 编码请求和响应模型
class EncodeRequest(BaseModel):
    # 支持两种输入方式: 图形描述或直接H矩阵+信息位
    nodes: Optional[List[Node]] = None
    edges: Optional[List[Edge]] = None
    h_matrix: Optional[List[List[int]]] = None
    info_bits: Optional[List[int]] = None
    snr_db: Optional[float] = 4.0

    @model_validator(mode='after')
    def validate_input_type(self) -> 'EncodeRequest':
        # 验证输入类型：要么提供nodes+edges，要么提供h_matrix
        has_graph = self.nodes and self.edges
        has_matrix = self.h_matrix is not None

        if not has_graph and not has_matrix:
            raise ValueError("必须提供图形数据(nodes+edges)或H矩阵(h_matrix)")

        return self

class EncodeResponse(BaseModel):
    h_matrix: List[List[int]]
    g_matrix: List[List[int]]
    code_rate: float
    n: int  # 码长
    k: int  # 信息位长度
    m: int  # 校验位长度
    message: str
    codeword: Optional[List[int]] = None  # 添加码字字段

# 仿真请求和响应模型
class SimulationRequest(BaseModel):
    h_matrix: List[List[int]]
    snr_range: List[float]
    frames_per_snr: int = Field(1000, ge=100, le=100000)
    max_iterations: int = Field(50, ge=10, le=200)
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
    algorithm: str = Field("min_sum", pattern="^(min_sum|sum_product)$")
    target_ber: Optional[float] = Field(None, ge=1e-6, le=1e-1)

class BERPoint(BaseModel):
    snr: float
    ber: float
    fer: float

class SimulationResponse(BaseModel):
    simulation_results: Dict[str, Any]

# 快速图仿真请求
class GraphSimulationRequest(GraphData):
    frame_count: int = Field(100, ge=10, le=10000)
    max_iterations: int = Field(20, ge=5, le=100)

# 优化请求和响应模型
class OptimizeRequest(BaseModel):
    n: int  # 码长
    k: int  # 信息位长度
    population_size: int = Field(50, ge=10, le=200)
    generations: int = Field(100, ge=10, le=1000)
    mutation_rate: float = Field(0.1, ge=0.01, le=0.5)
    target_snr: float

class OptimizeResponse(BaseModel):
    optimization_id: str
    message: str

class OptimizeStatusResponse(BaseModel):
    status: str
    current_generation: Optional[int] = None
    best_fitness: Optional[float] = None
    convergence_curve: Optional[List[float]] = None

# 解码请求和响应模型
class DecodeRequest(BaseModel):
    # 支持两种输入方式: 直接LLR或接收信号+信道参数
    llr: Optional[List[float]] = None
    received_signal: Optional[List[float]] = None
    received_bits: Optional[List[int]] = None
    h_matrix: List[List[int]]
    
    # 信道参数
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
    noise_variance: Optional[float] = Field(0.5, gt=0)
    crossover_probability: Optional[float] = Field(0.1, gt=0, lt=0.5)
    # 新增：直接指定 SNR(dB)，后端自动推算噪声方差 (仅 AWGN)
    snr_db: Optional[float] = Field(None, ge=0)
    
    # 解码参数
    algorithm: str = Field("min_sum", pattern="^(min_sum|sum_product)$")
    max_iterations: int = Field(50, ge=1, le=200)
    early_termination: bool = True
    min_sum_scaling: float = Field(0.9, gt=0, le=1.0)

    @model_validator(mode='after')
    def validate_input_and_channel(self) -> 'DecodeRequest':
        # 验证输入：要么提供LLR，要么提供接收信号/比特
        has_llr = self.llr is not None
        has_signal = self.received_signal is not None
        has_bits = self.received_bits is not None
        
        if not has_llr and not has_signal and not has_bits:
            raise ValueError("必须提供LLR、接收信号或接收比特之一")
        
        if sum([has_llr, has_signal, has_bits]) > 1:
            raise ValueError("只能提供LLR、接收信号或接收比特中的一种")
        
        # 验证信道类型与输入匹配 / 参数完整性
        if self.channel_type == "awgn":
            if has_bits:
                raise ValueError("AWGN信道不能使用received_bits，请使用received_signal")
            if not has_llr and not has_signal:
                raise ValueError("AWGN信道需要LLR或received_signal")
            # 如果提供received_signal，但没有噪声方差，则至少需要snr_db
            if has_signal and self.noise_variance is None and self.snr_db is None:
                raise ValueError("AWGN信道使用received_signal时需要提供noise_variance或snr_db")
        
        elif self.channel_type == "bsc":
            if has_signal:
                raise ValueError("BSC信道不能使用received_signal，请使用received_bits")
            if not has_llr and not has_bits:
                raise ValueError("BSC信道需要LLR或received_bits")
            if has_bits and self.crossover_probability is None:
                raise ValueError("BSC信道使用received_bits时需要crossover_probability")
        
        return self

class DecodeResponse(BaseModel):
    decoded_bits: List[int]
    information_bits: List[int]
    statistics: Dict[str, Any]
    h_matrix: List[List[int]]
    code_parameters: Dict[str, Any]
    message: str

# WebSocket消息模型
class SimulationProgressMessage(BaseModel):
    type: str = "progress"
    current_frame: int
    total_frames: int
    current_snr: float
    intermediate_ber: float
    message: str

class OptimizationProgressMessage(BaseModel):
    type: str = "generation_complete"
    generation: int
    total_generations: int
    best_fitness: float
    average_fitness: float
    convergence_data: Dict[str, Any]
