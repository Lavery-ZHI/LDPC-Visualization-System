# Appendix A: Source Code Implementation

This appendix presents the key source code implementations of the LDPC visualization system developed in this thesis. The code demonstrates practical applications of the theoretical concepts discussed in the main chapters, particularly the LDPC encoding, decoding algorithms, and performance simulation methods.

## A.1 LDPC Code Data Structure

The fundamental data structure for LDPC codes handles parity check matrix operations and code parameter calculations over GF(2).

```python
class LDPCCode:
    """Core data structure for LDPC codes with sparse matrix optimization."""
    
    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        if sp.issparse(h_matrix):
            self.H: sp.spmatrix = h_matrix.tocsr()
        else:
            self.H = sp.csr_matrix(h_matrix % 2)  # Store as CSR matrix (mod 2)
        
        self.m, self.n = self.H.shape
        self._rank: int | None = None
        self._G: np.ndarray | None = None

    @property
    def k(self) -> int:
        """Information bit length: k = n - rank(H)"""
        return self.n - self.rank

    @property
    def rate(self) -> float:
        """Code rate: R = k/n"""
        return self.k / self.n

    def _compute_generator_matrix(self) -> np.ndarray:
        """Generate systematic generator matrix G using Gaussian elimination."""
        H_dense = self.H.toarray()
        H_rref, pivots = _row_echelon_gf2(H_dense.copy())
        
        # Identify information bit positions
        all_cols = set(range(self.n))
        info_cols = sorted(all_cols - set(pivots))
        k = len(info_cols)
        
        # Construct systematic G = [I_k | P]
        G = np.zeros((k, self.n), dtype=int)
        G[np.arange(k), info_cols] = 1  # Identity part
        
        # Parity part from reduced row echelon form
        for row_in_H, pivot_col in enumerate(pivots):
            G[:, pivot_col] = H_rref[row_in_H, info_cols]
        
        return G
```

## A.2 LDPC Encoder Implementation

The encoder implements systematic LDPC encoding where information bits appear directly in the transmitted codeword.

```python
class LDPCEncoder:
    """Systematic LDPC encoder: c = u·G (mod 2)"""
    
    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        self.code = LDPCCode(h_matrix)
        self._G: np.ndarray | None = None

    def encode(self, info_bits: Sequence[int] | np.ndarray) -> np.ndarray:
        """
        Encode k information bits into n-bit LDPC codeword.
        
        Args:
            info_bits: Binary information vector of length k
            
        Returns:
            Binary codeword vector of length n
        """
        G = self.generate_g_matrix()
        info_bits = np.asarray(info_bits, dtype=int) % 2
        
        if info_bits.size != self.k:
            raise ValueError(f"Expected {self.k} info bits, got {info_bits.size}")
        
        return (info_bits @ G) % 2

    def generate_g_matrix(self) -> np.ndarray:
        """Generate and cache systematic generator matrix."""
        if self._G is None:
            self._G = self.code.G
        return self._G
```

## A.3 LDPC Decoder with Belief Propagation

The decoder implements the Min-Sum belief propagation algorithm for iterative LDPC decoding.

```python
class LDPCDecoder:
    """LDPC decoder using Min-Sum belief propagation algorithm."""
    
    def __init__(self, h_matrix, max_iterations=50, min_sum_scaling=0.9):
        self.code = LDPCCode(h_matrix)
        self.max_iterations = max_iterations
        self.min_sum_scaling = min_sum_scaling
        self._precompute_adjacency()

    def _precompute_adjacency(self):
        """Build adjacency lists for efficient message passing."""
        H_coo = self.H.tocoo()
        self.var_to_check = [[] for _ in range(self.n)]
        self.check_to_var = [[] for _ in range(self.m)]
        
        for i, j in zip(H_coo.row, H_coo.col):
            self.var_to_check[j].append(i)
            self.check_to_var[i].append(j)

    def decode(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Decode received LLR values using Min-Sum algorithm.
        
        Args:
            llr_input: Log-likelihood ratios for each bit position
            
        Returns:
            Tuple of (decoded_bits, decoding_statistics)
        """
        return self._decode_min_sum(llr_input)

    def _decode_min_sum(self, llr_input: np.ndarray):
        """Min-Sum belief propagation with normalization."""
        # Initialize variable-to-check and check-to-variable messages
        v2c_messages = {}
        c2v_messages = {}
        
        # Initialize messages
        for var_idx in range(self.n):
            v2c_messages[var_idx] = {}
            for check_idx in self.var_to_check[var_idx]:
                v2c_messages[var_idx][check_idx] = llr_input[var_idx]
        
        # Iterative message passing
        for iteration in range(self.max_iterations):
            # Check node update: compute minimum magnitude with sign product
            for check_idx in range(self.m):
                connected_vars = self.check_to_var[check_idx]
                for target_var in connected_vars:
                    other_vars = [v for v in connected_vars if v != target_var]
                    if len(other_vars) == 0:
                        continue
                    
                    messages = [v2c_messages[v][check_idx] for v in other_vars]
                    signs = [1 if msg >= 0 else -1 for msg in messages]
                    abs_messages = [abs(msg) for msg in messages]
                    
                    # Min-Sum update rule
                    sign_product = np.prod(signs)
                    min_magnitude = min(abs_messages)
                    c2v_messages[check_idx][target_var] = (
                        self.min_sum_scaling * sign_product * min_magnitude
                    )
            
            # Variable node update: sum all incoming messages
            for var_idx in range(self.n):
                connected_checks = self.var_to_check[var_idx]
                for target_check in connected_checks:
                    other_checks = [c for c in connected_checks if c != target_check]
                    message_sum = llr_input[var_idx]
                    for check_idx in other_checks:
                        message_sum += c2v_messages[check_idx][var_idx]
                    v2c_messages[var_idx][target_check] = message_sum
            
            # Compute posterior LLR and make hard decision
            posterior_llr = llr_input.copy()
            for var_idx in range(self.n):
                for check_idx in self.var_to_check[var_idx]:
                    posterior_llr[var_idx] += c2v_messages[check_idx][var_idx]
            
            decoded_bits = (posterior_llr < 0).astype(int)
            
            # Check convergence via syndrome calculation
            syndrome = (self.H @ decoded_bits) % 2
            if np.all(syndrome == 0):
                return decoded_bits, {
                    "iterations": iteration + 1,
                    "converged": True,
                    "syndrome_weight": 0
                }
        
        return decoded_bits, {
            "iterations": self.max_iterations,
            "converged": False,
            "syndrome_weight": int(np.sum((self.H @ decoded_bits) % 2))
        }

    def awgn_llr(self, received_signal: np.ndarray, noise_variance: float):
        """Convert AWGN received signal to LLR values."""
        return 2.0 * received_signal / noise_variance
```

## A.4 Simulation Engine for BER Performance Analysis

The simulation engine orchestrates Monte Carlo simulations to evaluate LDPC code performance.

```python
class SimulationEngine:
    """Monte Carlo simulation engine for LDPC BER/FER analysis."""
    
    def __init__(self, h_matrix: np.ndarray):
        self.encoder = LDPCEncoder(h_matrix)
        self.decoder = LDPCDecoder(h_matrix)
        self.n = self.decoder.n
        self.k = self.decoder.k
        self.rate = self.decoder.rate

    def run_ber_simulation(self, config: SimulationConfig) -> SimulationResults:
        """
        Execute complete BER simulation over SNR range.
        
        Args:
            config: Simulation parameters including SNR range, frame count
            
        Returns:
            BER/FER results for each SNR point
        """
        ber_results = []
        fer_results = []
        
        for snr_db in config.snr_range:
            snr_result = self._simulate_snr_point(snr_db, config)
            ber_results.append(snr_result['ber'])
            fer_results.append(snr_result['fer'])
        
        return SimulationResults(
            snr_db=config.snr_range,
            ber=ber_results,
            fer=fer_results,
            config=config
        )

    def _simulate_snr_point(self, snr_db: float, config: SimulationConfig):
        """Simulate single SNR point with error counting."""
        noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
        total_frames = 0
        error_frames = 0
        total_bit_errors = 0
        
        while (total_frames < config.frame_count and 
               error_frames < config.max_errors):
            
            # Generate random information bits
            info_bits = np.random.randint(0, 2, self.k)
            
            # Encode
            codeword = self.encoder.encode(info_bits)
            
            # AWGN channel transmission
            transmitted_signal = 1 - 2 * codeword.astype(float)  # BPSK mapping
            noise = np.random.normal(0, np.sqrt(noise_variance), self.n)
            received_signal = transmitted_signal + noise
            
            # Decode
            llr = self.decoder.awgn_llr(received_signal, noise_variance)
            decoded_bits, stats = self.decoder.decode(llr)
            decoded_info = self.decoder.extract_information_bits(decoded_bits)
            
            # Count errors
            bit_errors = np.sum(info_bits != decoded_info)
            total_bit_errors += bit_errors
            if bit_errors > 0:
                error_frames += 1
            total_frames += 1
        
        return {
            'ber': total_bit_errors / (total_frames * self.k),
            'fer': error_frames / total_frames,
            'total_frames': total_frames
        }

    def _awgn_channel(self, transmitted_bits, noise_variance):
        """AWGN channel with BPSK modulation."""
        transmitted_signal = 1 - 2 * transmitted_bits.astype(float)
        noise = np.random.normal(0, np.sqrt(noise_variance), len(transmitted_signal))
        return transmitted_signal + noise
```

## A.5 Interactive Graph Visualization Frontend

The Flutter frontend provides interactive Tanner graph construction capabilities.

```dart
class GraphCanvas extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return CustomPaint(
          painter: EdgePainter(
            edges: appProvider.edges,
            nodes: appProvider.nodes,
          ),
          child: Stack(
            children: [
              // Render graph nodes
              ...appProvider.nodes.map((node) {
                return Positioned(
                  left: node.position.dx - 25,
                  top: node.position.dy - 25,
                  child: GraphNodeWidget(node: node),
                );
              }),
            ],
          ),
        );
      },
    );
  }
}

class EdgePainter extends CustomPainter {
  final List<Edge> edges;
  final List<Node> nodes;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.blue.withOpacity(0.6)
      ..strokeWidth = 2.0;

    // Create node position mapping
    final nodePositions = <String, Offset>{};
    for (final node in nodes) {
      nodePositions[node.id] = node.position;
    }

    // Draw edges between variable and check nodes
    for (final edge in edges) {
      final fromPos = nodePositions[edge.fromId];
      final toPos = nodePositions[edge.toId];
      
      if (fromPos != null && toPos != null) {
        canvas.drawLine(fromPos, toPos, paint);
      }
    }
  }

  @override
  bool shouldRepaint(EdgePainter oldDelegate) => true;
}
```

## A.6 API Service Layer

The API service handles communication between the Flutter frontend and Python backend.

```dart
class ApiService {
  static late Dio _dio;

  static Future<Map<String, dynamic>> runSimulation({
    required List<List<int>> hMatrix,
    required List<double> snrRange,
    required int framesPerSnr,
    required String algorithm,
  }) async {
    try {
      final response = await _dio.post('/simulate', data: {
        'h_matrix': hMatrix,
        'snr_range': snrRange,
        'frames_per_snr': framesPerSnr,
        'algorithm': algorithm,
      });
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  static Future<Map<String, dynamic>> generateCode({
    required Map<String, dynamic> graphData,
  }) async {
    final response = await _dio.post('/v1/encode', data: graphData);
    return response.data;
  }
}
```

---

**Note:** This appendix presents selected core implementations from the LDPC visualization system. The complete source code, including additional utility functions, error handling, optimization algorithms, and comprehensive test suites, is available in the project repository at: https://github.com/[repository-link]

The full implementation includes approximately 3,000 lines of Python backend code and 2,500 lines of Dart frontend code, demonstrating production-quality software engineering practices for scientific computing applications.