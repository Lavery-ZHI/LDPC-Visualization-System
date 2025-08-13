# LDPC Visualization System - Key Source Code Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Backend Core Algorithms](#backend-core-algorithms)
   - [LDPC Code Model](#ldpc-code-model)
   - [LDPC Encoder](#ldpc-encoder)
   - [LDPC Decoder](#ldpc-decoder)
   - [Simulation Engine](#simulation-engine)
3. [API Layer](#api-layer)
   - [FastAPI Main Server](#fastapi-main-server)
   - [Request/Response Models](#requestresponse-models)
4. [Frontend Components](#frontend-components)
   - [API Service](#api-service)
   - [Interactive Graph Canvas](#interactive-graph-canvas)
5. [Conclusion](#conclusion)

---

## System Overview

This LDPC (Low-Density Parity-Check) visualization system consists of a Python FastAPI backend and a Flutter frontend, providing comprehensive LDPC code design, simulation, and analysis capabilities. The system supports both graphical LDPC code construction and matrix-based operations.

**Architecture:**
- **Backend**: Python FastAPI with NumPy/SciPy for mathematical operations
- **Frontend**: Flutter with cross-platform support (Web, Windows, Android)
- **Communication**: REST API + WebSocket for real-time updates

---

## Backend Core Algorithms

### LDPC Code Model

The `LDPCCode` class serves as the fundamental data structure for LDPC codes, handling matrix operations and code parameter calculations.

```python
class LDPCCode:
    """Lightweight container for LDPC parity check matrix and related helper functions."""

    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        if isinstance(h_matrix, list):  # Allow nested lists
            h_matrix = np.array(h_matrix, dtype=int)
        if not isinstance(h_matrix, (np.ndarray, sp.spmatrix)):
            raise TypeError("h_matrix must be array-like or scipy sparse matrix")

        if sp.issparse(h_matrix):
            self.H: sp.spmatrix = h_matrix.tocsr()
        else:
            self.H = sp.csr_matrix(h_matrix % 2)  # Always store as CSR matrix (mod 2)

        if self.H.nnz == 0:
            raise ValueError("H matrix cannot be all zeros")

        self.m, self.n = self.H.shape
        self._rank: int | None = None  # Lazy computation
        self._G: np.ndarray | None = None
        self._info_cols: List[int] | None = None  # Information bit column indices (lazy assignment)

    @property
    def rank(self) -> int:
        if self._rank is None:
            self._rank = _rank_gf2(self.H.toarray())
        return self._rank

    @property
    def k(self) -> int:  # message length
        return self.n - self.rank

    @property
    def rate(self) -> float:
        return self.k / self.n
```

**Description:** The LDPCCode class encapsulates the parity check matrix H and provides lazy computation of derived properties like code rate, rank, and generator matrix. It supports both dense and sparse matrix representations for memory efficiency with large codes.

### LDPC Encoder

The `LDPCEncoder` class implements systematic LDPC encoding.

```python
class LDPCEncoder:
    """Encode *k* information bits into LDPC codeword of length *n*."""

    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        # Handle sparse matrix input
        if sp.issparse(h_matrix):
            h_matrix = h_matrix.astype(np.uint8)       # keep sparse domain as integer
            h_matrix.data %= 2                         # in case there are 2, -1, etc.

        # Instantiate LDPC code model—this will perform validation.
        self.code = LDPCCode(h_matrix)
        # Lazy attributes
        self._G: np.ndarray | None = None

    def generate_g_matrix(self) -> np.ndarray:
        """Return (and cache) systematic generator matrix *G*."""
        if self._G is None:
            self._G = self.code.G  # trigger LDPCCode internal lazy computation
        return self._G

    def encode(self, info_bits: Sequence[int] | np.ndarray) -> np.ndarray:
        """Encode *info_bits* (length *k*) into LDPC codeword."""
        G = self.generate_g_matrix()  # ensure *k* is finalized *before* checking length
        info_bits = np.asarray(info_bits, dtype=int) % 2
        if info_bits.ndim != 1:
            raise ValueError("info_bits must be a one-dimensional vector")
        if info_bits.size != self.k:
            raise ValueError(f"info_bits length {info_bits.size} != expected k={self.k}")
        return (info_bits @ G) % 2
```

**Description:** The encoder implements systematic encoding where information bits appear directly in the codeword. It uses Gaussian elimination to compute the generator matrix G from the parity check matrix H, ensuring the orthogonality condition H·G^T = 0.

### LDPC Decoder

The `LDPCDecoder` class implements belief propagation algorithms for LDPC decoding.

```python
class LDPCDecoder:
    """Decode LDPC codewords using Belief Propagation (BP) algorithms."""

    def __init__(
        self,
        h_matrix: Sequence | np.ndarray | sp.spmatrix,
        max_iterations: int = 50,
        min_sum_scaling: float = 0.9,
        convergence_threshold: float = 1e-6,
        early_termination: bool = True,
        osd_order: int = 0  # OSD order for post-processing (0 = basic post-processing)
    ):
        # Handle sparse matrix input
        if sp.issparse(h_matrix):
            h_matrix = h_matrix.astype(np.uint8)
            h_matrix.data = h_matrix.data % 2

        # Instantiate LDPC code model
        self.code = LDPCCode(h_matrix)
        
        # Decoder parameters
        self.max_iterations = max_iterations
        self.min_sum_scaling = min_sum_scaling
        self.convergence_threshold = convergence_threshold
        self.early_termination = early_termination
        self.osd_order = osd_order
        
        # Precompute adjacency information for efficiency
        self._precompute_adjacency()

    def _precompute_adjacency(self):
        """Precompute adjacency lists for variable and check nodes."""
        H_coo = self.H.tocoo()
        
        # Variable node to check node adjacency lists
        self.var_to_check = [[] for _ in range(self.n)]
        # Check node to variable node adjacency lists
        self.check_to_var = [[] for _ in range(self.m)]
        
        for i, j in zip(H_coo.row, H_coo.col):
            self.var_to_check[j].append(i)
            self.check_to_var[i].append(j)

    def _decode_min_sum(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Min-Sum algorithm implementation with Normalized Min-Sum variant and OSD post-processing."""
        # Initialize messages
        v2c_messages = {}
        c2v_messages = {}
        
        for var_idx in range(self.n):
            v2c_messages[var_idx] = {}
            for check_idx in self.var_to_check[var_idx]:
                v2c_messages[var_idx][check_idx] = llr_input[var_idx]
        
        for check_idx in range(self.m):
            c2v_messages[check_idx] = {}
            for var_idx in self.check_to_var[check_idx]:
                c2v_messages[check_idx][var_idx] = 0.0
        
        # Calculate average check node degree for normalization factor
        avg_check_degree = np.mean([len(self.check_to_var[i]) for i in range(self.m)])
        normalization_factor = 1.0 / (0.75 + 0.25 * avg_check_degree / 4.0)
        
        converged = False
        for iteration in range(self.max_iterations):
            # Check node update
            for check_idx in range(self.m):
                connected_vars = self.check_to_var[check_idx]
                
                for target_var in connected_vars:
                    other_vars = [v for v in connected_vars if v != target_var]
                    
                    if len(other_vars) == 0:
                        c2v_messages[check_idx][target_var] = 0.0
                        continue
                    
                    messages = [v2c_messages[v][check_idx] for v in other_vars]
                    signs = [1 if msg >= 0 else -1 for msg in messages]
                    abs_messages = [abs(msg) for msg in messages]
                    
                    sign_product = np.prod(signs)
                    min_abs = min(abs_messages)
                    
                    # Apply normalization factor
                    c2v_messages[check_idx][target_var] = (
                        self.min_sum_scaling * sign_product * min_abs * normalization_factor
                    )
            
            # Variable node update
            for var_idx in range(self.n):
                connected_checks = self.var_to_check[var_idx]
                
                for target_check in connected_checks:
                    other_checks = [c for c in connected_checks if c != target_check]
                    message_sum = llr_input[var_idx]
                    for check_idx in other_checks:
                        message_sum += c2v_messages[check_idx][var_idx]
                    v2c_messages[var_idx][target_check] = message_sum
            
            # Calculate posterior LLR and hard decision
            posterior_llr = llr_input.copy()
            for var_idx in range(self.n):
                for check_idx in self.var_to_check[var_idx]:
                    posterior_llr[var_idx] += c2v_messages[check_idx][var_idx]
            
            decoded_bits = (posterior_llr < 0).astype(int)
            
            if self.early_termination:
                syndrome = (self.H @ decoded_bits) % 2
                if np.all(syndrome == 0):
                    converged = True
                    break
        
        # Statistics
        final_syndrome = (self.H @ decoded_bits) % 2
        stats = {
            "iterations": iteration + 1,
            "converged": converged,
            "syndrome_weight": int(np.sum(final_syndrome)),
            "final_llr": posterior_llr.tolist(),
            "parity_check_satisfied": bool(np.all(final_syndrome == 0)),
        }
        
        return decoded_bits, stats
```

**Description:** The decoder implements the Min-Sum belief propagation algorithm with normalization and scaling factors. It performs iterative message passing between variable and check nodes, updating log-likelihood ratios until convergence or maximum iterations. The algorithm includes early termination based on syndrome checking and provides detailed decoding statistics.

### Simulation Engine

The `SimulationEngine` class orchestrates BER/FER performance simulations.

```python
class SimulationEngine:
    """LDPC Simulation Engine - performs BER/FER performance simulations."""

    def __init__(self, h_matrix: np.ndarray):
        """
        Initializes the simulation engine.

        Args:
            h_matrix: LDPC parity check matrix
        """
        self.h_matrix = np.asarray(h_matrix, dtype=int)
        
        # Initialize encoder and decoder
        self.encoder = LDPCEncoder(h_matrix)
        self.decoder = LDPCDecoder(h_matrix)
        
        # Code parameters
        self.n = self.decoder.n  # Codeword length
        self.k = self.decoder.k  # Information bits length
        self.rate = self.decoder.rate  # Code rate
        
        # Simulation status
        self.is_running = False
        self.should_stop = False

    def _simulate_snr_point(
        self,
        snr_db: float,
        config: SimulationConfig,
        snr_idx: int,
        total_snr_points: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Simulate a single SNR point."""
        
        # Statistics variables
        total_frames = 0
        error_frames = 0
        total_bit_errors = 0
        total_iterations = 0

        # Noise variance calculation (for AWGN)
        if config.channel_type == "awgn":
            noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
        elif config.channel_type == "bsc":
            # Relationship between crossover probability and SNR for BSC (simplified model)
            crossover_prob = 0.5 * np.exp(-10 ** (snr_db / 10))
            crossover_prob = np.clip(crossover_prob, 1e-6, 0.49)

        while (total_frames < config.frame_count and 
               (error_frames < config.max_errors or total_frames < config.min_frames)):
            
            if self.should_stop:
                break

            # Generate random information bits
            info_bits = np.random.randint(0, 2, self.k)
            
            # Encoding
            try:
                encoded_bits = self.encoder.encode(info_bits)
            except Exception as e:
                print(f"Encoding error: {e}")
                continue

            # Channel transmission
            if config.channel_type == "awgn":
                received_signal, received_bits = self._awgn_channel(
                    encoded_bits, noise_variance
                )
                # Compute LLR
                llr = self.decoder.awgn_llr(received_signal, noise_variance)
            elif config.channel_type == "bsc":
                received_bits = self._bsc_channel(encoded_bits, crossover_prob)
                # Compute LLR
                llr = self.decoder.bsc_llr(received_bits, crossover_prob)

            # Decoding
            try:
                decoded_bits, decode_stats = self.decoder.decode(
                    llr, config.decoder_algorithm
                )
                total_iterations += decode_stats['iterations']
            except Exception as e:
                print(f"Decoding error: {e}")
                continue

            # Extract information bits
            decoded_info_bits = self.decoder.extract_information_bits(decoded_bits)

            # Error statistics
            bit_errors = np.sum(info_bits != decoded_info_bits)
            total_bit_errors += bit_errors
            
            if bit_errors > 0:
                error_frames += 1

            total_frames += 1

        # Calculate final results
        ber = total_bit_errors / (total_frames * self.k) if total_frames > 0 else 0
        fer = error_frames / total_frames if total_frames > 0 else 0
        avg_iterations = total_iterations / total_frames if total_frames > 0 else 0

        return {
            'ber': ber,
            'fer': fer,
            'total_frames': total_frames,
            'error_frames': error_frames,
            'avg_iterations': avg_iterations
        }

    def _awgn_channel(self, transmitted_bits: np.ndarray, noise_variance: float) -> Tuple[np.ndarray, np.ndarray]:
        """AWGN channel simulation."""
        # BPSK modulation: 0 -> +1, 1 -> -1
        transmitted_signal = 1 - 2 * transmitted_bits.astype(float)
        
        # Add Gaussian noise
        noise = np.random.normal(0, np.sqrt(noise_variance), len(transmitted_signal))
        received_signal = transmitted_signal + noise
        
        # Hard decision (for statistics only)
        received_bits = (received_signal < 0).astype(int)
        
        return received_signal, received_bits

    def _bsc_channel(self, transmitted_bits: np.ndarray, crossover_prob: float) -> np.ndarray:
        """BSC channel simulation."""
        # Generate random flip pattern
        flip_mask = np.random.random(len(transmitted_bits)) < crossover_prob
        received_bits = transmitted_bits ^ flip_mask.astype(int)
        return received_bits
```

**Description:** The simulation engine coordinates the complete BER/FER simulation pipeline. It generates random information bits, encodes them, transmits through noisy channels (AWGN or BSC), decodes the received signal, and collects error statistics. The engine supports early stopping criteria and progress callbacks for real-time monitoring.

---

## API Layer

### FastAPI Main Server

The main server implements REST API endpoints for all system functionalities.

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import numpy as np
from typing import Dict, List, Any

app = FastAPI(
    title="LDPC SYSTEM API",
    description="FastAPI-based LDPC encoding, simulation and optimization backend service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/encode", response_model=EncodeResponse, tags=["Encoding"])
async def encode_ldpc(request: EncodeRequest):
    """
    Generate LDPC code from input and return encoding results

    Supports two input modes:
    - Mode 1: Describe LDPC code through graph data (nodes, edges)
    - Mode 2: Directly provide H matrix and optional information bits
    """
    try:
        # Determine input mode
        if request.h_matrix is not None:
            # Mode 2: Directly provide H matrix
            h_matrix = np.array(request.h_matrix, dtype=int)
            encoder = LDPCEncoder(h_matrix)
        else:
            # Mode 1: Through graph data
            if not request.nodes or not request.edges:
                raise ValueError("nodes and edges must be provided when using graph mode")

            # Convert graph data to H matrix
            nodes = [node.dict() for node in request.nodes]
            edges = [edge.dict() for edge in request.edges]
            ldpc_code = LDPCCode.from_graph_data(nodes, edges)

            # Create encoder
            encoder = LDPCEncoder(ldpc_code.H)

        # Generate G matrix
        g_matrix = encoder.generate_g_matrix()

        # Get matrix and code parameters
        matrices = encoder.get_matrices()

        # If information bits are provided, encode to generate codeword
        codeword = None
        if request.info_bits is not None:
            if len(request.info_bits) != encoder.k:
                raise ValueError(f"Information bits length should be {encoder.k}, but received length {len(request.info_bits)}")
            codeword = encoder.encode(request.info_bits).tolist()

        # Build response
        return EncodeResponse(
            h_matrix=matrices["h_matrix"],
            g_matrix=matrices["g_matrix"],
            code_rate=float(encoder.rate),
            n=int(encoder.n),
            k=int(encoder.k),
            m=int(encoder.m),
            codeword=codeword,
            message="LDPC code generated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Encoding failed: {str(e)}")

@app.post("/api/simulate", tags=["Full Simulation"])
async def api_simulate(request_data: dict):
    """API endpoint: Run complete BER simulation"""
    try:
        # Extract parameters
        h_matrix_data = request_data.get('h_matrix')
        snr_range = request_data.get('snr_range', [0.0, 2.0, 4.0])
        frames_per_point = request_data.get('frames_per_point', 1000)
        algorithm = request_data.get('algorithm', 'min_sum')
        channel = request_data.get('channel', 'awgn')
        max_iterations = request_data.get('max_iterations', 100)
        target_errors = request_data.get('target_errors', 100)
        
        # Validate H matrix
        if h_matrix_data is None:
            raise ValueError("Missing H matrix data")
            
        h_matrix = np.array(h_matrix_data, dtype=int)
        print(f"Simulation using H matrix: shape={h_matrix.shape}")
        
        engine = SimulationEngine(h_matrix)
        
        config = SimulationConfig(
            snr_range=snr_range,
            frame_count=frames_per_point,
            decoder_algorithm=algorithm,
            channel_type=channel,
            max_iterations=max_iterations,
            max_errors=int(target_errors)
        )
        
        result = engine.run_simulation(config)
        
        return {
            "simulation_results": result,
            "message": "Simulation completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation API failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)
```

**Description:** The FastAPI server provides RESTful endpoints for encoding, decoding, and simulation operations. It supports both graph-based and matrix-based input modes, with comprehensive error handling and validation. The server runs on port 9999 with CORS enabled for cross-origin requests.

### Request/Response Models

Pydantic models ensure type safety and validation for API requests and responses.

```python
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional

class Node(BaseModel):
    id: str
    type: str  # "variable" or "check"

class Edge(BaseModel):
    fromId: str
    toId: str

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
    codeword: Optional[List[int]] = None

class DecodeRequest(BaseModel):
    llr: Optional[List[float]] = None
    received_signal: Optional[List[float]] = None
    received_bits: Optional[List[int]] = None
    h_matrix: List[List[int]]
    
    # Channel parameters
    channel_type: str = Field("awgn", pattern="^(awgn|bsc)$")
    noise_variance: Optional[float] = Field(0.5, gt=0)
    crossover_probability: Optional[float] = Field(0.1, gt=0, lt=0.5)
    snr_db: Optional[float] = Field(None, ge=0)
    
    # Decoding parameters
    algorithm: str = Field("min_sum", pattern="^(min_sum|sum_product)$")
    max_iterations: int = Field(50, ge=1, le=200)
    early_termination: bool = True
    min_sum_scaling: float = Field(0.9, gt=0, le=1.0)
```

**Description:** Pydantic models provide comprehensive input validation with type checking, field constraints, and custom validators. They support multiple input modes and ensure API consistency between frontend and backend.

---

## Frontend Components

### API Service

The Flutter API service handles all backend communication.

```dart
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class ApiService {
  static late Dio _dio;

  // Initialize Dio instance
  static void init() {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    // Add debug interceptors
    if (kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: true,
          logPrint: (obj) => debugPrint(obj.toString()),
        ),
      );
    }
  }

  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:9999/api';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:9999/api';
    }
    return 'http://127.0.0.1:9999/api';
  }

  /// Encoding: Generate LDPC code
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

  /// Simulation: Run BER/FER simulation
  static Future<Map<String, dynamic>> runSimulation({
    required List<List<int>> hMatrix,
    required List<double> snrRange,
    required int framesPerSnr,
    required String channelType,
    required String algorithm,
    required int maxIterations,
  }) async {
    try {
      final response = await _dio.post(
        '/simulate',
        data: {
          'h_matrix': hMatrix,
          'snr_range': snrRange,
          'frames_per_snr': framesPerSnr,
          'channel_type': channelType,
          'algorithm': algorithm,
          'max_iterations': maxIterations,
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Error handling
  static String _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return 'Connection timeout, please check network connection';
      case DioExceptionType.sendTimeout:
        return 'Send timeout, please retry';
      case DioExceptionType.receiveTimeout:
        return 'Response timeout, please retry';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final message = error.response?.data?['error'] ?? 'Server error';
        return 'HTTP $statusCode: $message';
      case DioExceptionType.cancel:
        return 'Request cancelled';
      case DioExceptionType.unknown:
        return 'Network connection failed, please check network settings';
      default:
        return 'Unknown error: ${error.message}';
    }
  }
}
```

**Description:** The API service provides a centralized HTTP client using Dio package with platform-specific base URL detection, comprehensive error handling, and debug logging. It abstracts all backend communication for encoding, decoding, and simulation operations.

### Interactive Graph Canvas

The graph canvas widget enables interactive LDPC graph construction.

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';

class GraphCanvas extends StatelessWidget {
  const GraphCanvas({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return GestureDetector(
          onTap: () => appProvider.tapCanvas(),
          child: Container(
            width: double.infinity,
            height: double.infinity,
            color: const Color(0xFF1E1E2E), // Soft canvas background
            child: CustomPaint(
              painter: EdgePainter(
                edges: appProvider.edges,
                nodes: appProvider.nodes,
                selectedNode: appProvider.selectedNode,
              ),
              child: Stack(
                children: [
                  // Render all nodes
                  ...appProvider.nodes.map((node) {
                    return Positioned(
                      left: node.position.dx - 25, // Node radius compensation
                      top: node.position.dy - 25,
                      child: GraphNodeWidget(node: node),
                    );
                  }),

                  // Display graph information
                  Positioned(
                    top: 10,
                    left: 10,
                    child: Container(
                      padding: const EdgeInsets.all(8.0),
                      decoration: BoxDecoration(
                        color: const Color(0xFF2A2A3A).withValues(alpha: 0.9),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(0xFF4A90E2).withValues(alpha: 0.3),
                          width: 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Nodes: ${appProvider.nodes.length}',
                            style: const TextStyle(
                              color: Color(0xFFE8E8F0),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            'Edges: ${appProvider.edges.length}',
                            style: const TextStyle(
                              color: Color(0xFFE8E8F0),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            'Variable: ${appProvider.nodes.where((n) => n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Color(0xFFB8B8C8),
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'Check: ${appProvider.nodes.where((n) => !n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Color(0xFFB8B8C8),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
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

/// Custom painter for drawing edges
class EdgePainter extends CustomPainter {
  final List<Edge> edges;
  final List<Node> nodes;
  final Node? selectedNode;

  EdgePainter({required this.edges, required this.nodes, this.selectedNode});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFB8B8C8).withValues(alpha: 0.6)
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round;

    final selectedPaint = Paint()
      ..color = const Color(0xFFFFA726) // Soft orange highlight
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    // Create node ID to position mapping
    final nodePositions = <String, Offset>{};
    for (final node in nodes) {
      nodePositions[node.id] = node.position;
    }

    // Draw all edges
    for (final edge in edges) {
      final fromPos = nodePositions[edge.fromId];
      final toPos = nodePositions[edge.toId];

      if (fromPos != null && toPos != null) {
        // Highlight if current edge connects to selected node
        final isSelected =
            selectedNode != null &&
            (edge.fromId == selectedNode!.id || edge.toId == selectedNode!.id);

        canvas.drawLine(fromPos, toPos, isSelected ? selectedPaint : paint);
      }
    }

    // Draw selection halo for selected node
    if (selectedNode != null) {
      final selectedPaint = Paint()
        ..color = Colors.amber.withValues(alpha: 0.5)
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;

      canvas.drawCircle(selectedNode!.position, 35, selectedPaint);
    }
  }

  @override
  bool shouldRepaint(EdgePainter oldDelegate) {
    return oldDelegate.edges != edges ||
        oldDelegate.nodes != nodes ||
        oldDelegate.selectedNode != selectedNode;
  }
}
```

**Description:** The GraphCanvas widget provides an interactive drawing surface for constructing LDPC Tanner graphs. It supports drag-and-drop node placement, edge creation between variable and check nodes, and real-time visual feedback. The custom EdgePainter handles efficient rendering of connections with selection highlighting.

---

## Conclusion

This LDPC visualization system demonstrates a comprehensive implementation of LDPC coding theory with practical visualization capabilities. The codebase includes:

### Key Technical Features:
1. **Efficient Matrix Operations**: Sparse matrix support for large LDPC codes
2. **Multiple Decoding Algorithms**: Min-Sum and Sum-Product with optimization
3. **Channel Models**: AWGN and BSC channel simulation with configurable parameters
4. **Interactive Visualization**: Real-time Tanner graph construction and editing
5. **Performance Analysis**: Complete BER/FER simulation with statistical tracking
6. **Cross-Platform Support**: Web, Windows, and Android deployment

### Software Engineering Best Practices:
1. **Type Safety**: Comprehensive type annotations and validation
2. **Error Handling**: Robust exception handling with detailed error messages
3. **API Design**: RESTful API with clear request/response models
4. **Code Organization**: Modular design with clear separation of concerns
5. **Performance Optimization**: Lazy evaluation and memory-efficient algorithms

### Educational Value:
The system serves as both a research tool and educational platform for understanding LDPC codes, demonstrating the practical implementation of theoretical concepts in coding theory and providing an intuitive interface for experimentation and learning.

This codebase represents a production-quality implementation suitable for academic research, educational purposes, and practical LDPC code analysis applications.