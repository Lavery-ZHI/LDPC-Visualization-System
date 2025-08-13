from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Union
import numpy as np

# Graph data models
class Node(BaseModel):
    id: str
    type: str  # "variable" or "check"

class Edge(BaseModel):
    fromId: str
    toId: str

class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    snr_db: Optional[float] = 4.0

# Encoding request and response models
class EncodeRequest(BaseModel):
    # Supports two input methods: graph description or direct H matrix + info bits
    nodes: Optional[List[Node]] = None
    edges: Optional[List[Edge]] = None
    h_matrix: Optional[List[List[int]]] = None
    info_bits: Optional[List[int]] = None
    snr_db: Optional[float] = 4.0

    @model_validator(mode='after')
    def validate_input_type(self) -> 'EncodeRequest':
        # Validate input type: either provide nodes+edges, or h_matrix
        has_graph = self.nodes and self.edges
        has_matrix = self.h_matrix is not None

        if not has_graph and not has_matrix:
            raise ValueError("Must provide either graph data (nodes+edges) or H matrix (h_matrix)")

        return self

class EncodeResponse(BaseModel):
    h_matrix: List[List[int]]
    g_matrix: List[List[int]]
    code_rate: float
    n: int  # Codeword length
    k: int  # Info bit length
    m: int  # Check bit length
    message: str
    codeword: Optional[List[int]] = None  # Add codeword field

# Simulation request and response models
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

# Quick graph simulation request
class GraphSimulationRequest(GraphData):
    frame_count: int = Field(100, ge=10, le=10000)
    max_iterations: int = Field(20, ge=5, le=100)

# Optimization request and response models
class OptimizeRequest(BaseModel):
    n: int  # Codeword length
    k: int  # Info bit length
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

# Decoding request and response models
class DecodeRequest(BaseModel):
    # Supports two input methods: direct LLR or received signal + channel parameters
    llr: Optional[List[float]] = None
    received_signal: Optional[List[float]] = None
    received_bits: Optional[List[int]] = None
    h_matrix: List[List[int]]
    
    # Channel parameters
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
    noise_variance: Optional[float] = Field(0.5, gt=0)
    crossover_probability: Optional[float] = Field(0.1, gt=0, lt=0.5)
    # New: directly specify SNR(dB), backend automatically calculates noise variance (AWGN only)
    snr_db: Optional[float] = Field(None, ge=0)
    
    # Decoding parameters
    algorithm: str = Field("min_sum", pattern="^(min_sum|sum_product)$")
    max_iterations: int = Field(50, ge=1, le=200)
    early_termination: bool = True
    min_sum_scaling: float = Field(0.9, gt=0, le=1.0)

    @model_validator(mode='after')
    def validate_input_and_channel(self) -> 'DecodeRequest':
        # Validate input: must provide one of LLR, received signal, or received bits
        has_llr = self.llr is not None
        has_signal = self.received_signal is not None
        has_bits = self.received_bits is not None
        
        if not has_llr and not has_signal and not has_bits:
            raise ValueError("Must provide one of LLR, received signal, or received bits")
        
        if sum([has_llr, has_signal, has_bits]) > 1:
            raise ValueError("Can only provide one of LLR, received signal, or received bits")
        
        # Validate channel type matches input / parameter integrity
        if self.channel_type == "awgn":
            if has_bits:
                raise ValueError("AWGN channel cannot use received_bits, please use received_signal")
            if not has_llr and not has_signal:
                raise ValueError("AWGN channel requires LLR or received_signal")
            # If received_signal is provided without noise_variance, snr_db is required
            if has_signal and self.noise_variance is None and self.snr_db is None:
                raise ValueError("AWGN channel with received_signal requires noise_variance or snr_db")
        
        elif self.channel_type == "bsc":
            if has_signal:
                raise ValueError("BSC channel cannot use received_signal, please use received_bits")
            if not has_llr and not has_bits:
                raise ValueError("BSC channel requires LLR or received_bits")
            if has_bits and self.crossover_probability is None:
                raise ValueError("BSC channel with received_bits requires crossover_probability")
        
        return self

class DecodeResponse(BaseModel):
    decoded_bits: List[int]
    information_bits: List[int]
    statistics: Dict[str, Any]
    h_matrix: List[List[int]]
    code_parameters: Dict[str, Any]
    message: str

# WebSocket message models
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
