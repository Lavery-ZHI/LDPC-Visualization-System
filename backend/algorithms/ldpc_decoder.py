"""High-level LDPC decoder built around :class:`LDPCCode`."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple, Optional
import numpy as np
import scipy.sparse as sp
from models.ldpc_models import LDPCCode
from itertools import combinations  # For OSD combination generation

__all__ = ["LDPCDecoder"]


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
        """
        Initialize LDPC decoder.

        Args:
            h_matrix: Parity check matrix H
            max_iterations: Maximum number of iterations
            min_sum_scaling: Min-Sum algorithm scaling factor
            convergence_threshold: Convergence threshold
            early_termination: Enable early termination
            osd_order: OSD post-processing order (default 0)
        """
        # Handle sparse matrix input
        if sp.issparse(h_matrix):
            h_matrix = h_matrix.astype(np.uint8)  # type: ignore
            h_matrix.data = h_matrix.data % 2  # type: ignore

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
        
        # Decoding statistics
        self.last_decode_stats = {}
        
        # Debug options
        self.debug_mode = False

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------
    @property
    def H(self):
        return self.code.H

    @property
    def m(self):
        return self.code.m

    @property
    def n(self):
        return self.code.n

    @property
    def k(self):
        return self.code.k

    @property
    def rate(self):
        return self.code.rate

    # ------------------------------------------------------------------
    # Precompute adjacency information
    # ------------------------------------------------------------------
    def _precompute_adjacency(self):
        """Precompute adjacency lists for variable and check nodes."""
        H_coo = self.H.tocoo()  # type: ignore
        
        # Variable node to check node adjacency lists
        self.var_to_check = [[] for _ in range(self.n)]
        # Check node to variable node adjacency lists
        self.check_to_var = [[] for _ in range(self.m)]
        
        for i, j in zip(H_coo.row, H_coo.col):
            self.var_to_check[j].append(i)
            self.check_to_var[i].append(j)

    # ------------------------------------------------------------------
    # LLR calculation
    # ------------------------------------------------------------------
    def awgn_llr(self, received_signal: np.ndarray, noise_variance: float) -> np.ndarray:
        """
        Calculate Log-Likelihood Ratio (LLR) for AWGN channel.
        
        Args:
            received_signal: Received signal (length n)
            noise_variance: Noise variance σ²
            
        Returns:
            Array of LLR values
        """
        received_signal = np.asarray(received_signal, dtype=float)
        if received_signal.size != self.n:
            raise ValueError(f"Received signal length {received_signal.size} != codeword length {self.n}")
        
        # LLR = 2 * r / σ² (assuming transmitted +1/-1)
        llr = 2.0 * received_signal / noise_variance
        return llr

    def bsc_llr(self, received_bits: np.ndarray, crossover_probability: float) -> np.ndarray:
        """
        Calculate Log-Likelihood Ratio (LLR) for Binary Symmetric Channel (BSC).
        
        Args:
            received_bits: Received bits (0/1, length n)
            crossover_probability: Crossover probability p
            
        Returns:
            Array of LLR values
        """
        received_bits = np.asarray(received_bits, dtype=int) % 2
        if received_bits.size != self.n:
            raise ValueError(f"Received bits length {received_bits.size} != codeword length {self.n}")
        
        if crossover_probability <= 0 or crossover_probability >= 0.5:
            raise ValueError("Crossover probability must be in range (0, 0.5)")
        
        # LLR = log((1-p)/p) * (1-2*r)
        log_ratio = np.log((1 - crossover_probability) / crossover_probability)
        llr = log_ratio * (1 - 2 * received_bits)
        return llr

    # ------------------------------------------------------------------
    # BP decoding algorithms (Min-Sum)
    # ------------------------------------------------------------------
    def decode(
        self,
        llr_input: np.ndarray,
        algorithm: str = "min_sum"
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Decode LDPC codeword using BP algorithm.
        
        Args:
            llr_input: Input LLR values (length n)
            algorithm: Decoding algorithm ("min_sum" or "sum_product")
            
        Returns:
            (decoded_bits, decoding_statistics)
        """
        llr_input = np.asarray(llr_input, dtype=float)
        if llr_input.size != self.n:
            raise ValueError(f"LLR input length {llr_input.size} != codeword length {self.n}")
        
        if algorithm == "min_sum" or algorithm == "min-sum":
            return self._decode_min_sum(llr_input)
        elif algorithm == "sum_product" or algorithm == "sum-product":
            return self._decode_sum_product(llr_input)
        else:
            raise ValueError(f"Unsupported decoding algorithm: {algorithm}")

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
        osd_applied = False
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
                syndrome = (self.H @ decoded_bits) % 2  # type: ignore
                if np.all(syndrome == 0):
                    converged = True
                    break
        
        # OSD post-processing (if not converged, try flipping low-confidence bits)
        if not converged and self.osd_order >= 0:
            osd_applied = True
            uncertain_indices = np.argsort(np.abs(posterior_llr))[:self.osd_order + 1]
            for flip_set in combinations(uncertain_indices, self.osd_order + 1):
                temp_bits = decoded_bits.copy()
                temp_bits[list(flip_set)] = 1 - temp_bits[list(flip_set)]
                syndrome = (self.H @ temp_bits) % 2  # type: ignore
                if np.all(syndrome == 0):
                    decoded_bits = temp_bits
                    converged = True
                    break
        
        # Statistics
        final_syndrome = (self.H @ decoded_bits) % 2  # type: ignore
        stats = {
            "iterations": iteration + 1,
            "converged": converged,
            "syndrome_weight": int(np.sum(final_syndrome)),
            "final_llr": posterior_llr.tolist(),
            "parity_check_satisfied": bool(np.all(final_syndrome == 0)),
            "osd_applied": osd_applied
        }
        
        self.last_decode_stats = stats
        return decoded_bits, stats

    def _decode_sum_product(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Sum-Product algorithm implementation with log-domain operations for numerical stability and OSD post-processing."""
        # Helper function: log-domain addition
        def log_sum_exp(a, b):
            max_val = np.maximum(a, b)
            return max_val + np.log1p(np.exp(-np.abs(a - b)))
        
        # Initialize messages (in log domain: store log(P0 / P1) = LLR)
        v2c_messages = {}
        c2v_messages = {}
        
        for var_idx in range(self.n):
            v2c_messages[var_idx] = {}
            for check_idx in self.var_to_check[var_idx]:
                v2c_messages[var_idx][check_idx] = llr_input[var_idx]
        
        for check_idx in range(self.m):
            c2v_messages[check_idx] = {}
            for var_idx in self.check_to_var[check_idx]:
                c2v_messages[check_idx][var_idx] = 0.0  # LLR=0 means P0=P1=0.5
        
        converged = False
        osd_applied = False
        for iteration in range(self.max_iterations):
            # Check node update (log-domain tanh rule)
            for check_idx in range(self.m):
                connected_vars = self.check_to_var[check_idx]
                
                for target_var in connected_vars:
                    other_vars = [v for v in connected_vars if v != target_var]
                    
                    if len(other_vars) == 0:
                        c2v_messages[check_idx][target_var] = 0.0
                        continue
                    
                    # Log-domain Sum-Product: prod tanh(v2c / 2) * 2 * atanh
                    tanh_msgs = [np.tanh(v2c_messages[v][check_idx] / 2.0) for v in other_vars]
                    prod_tanh = np.prod(tanh_msgs)
                    
                    # Clip to avoid numerical instability
                    prod_tanh = np.clip(prod_tanh, -1 + 1e-10, 1 - 1e-10)
                    c2v_messages[check_idx][target_var] = 2.0 * np.arctanh(prod_tanh)
            
            # Variable node update (log-domain simple addition)
            for var_idx in range(self.n):
                connected_checks = self.var_to_check[var_idx]
                
                for target_check in connected_checks:
                    other_checks = [c for c in connected_checks if c != target_check]
                    message_sum = llr_input[var_idx]
                    for check_idx in other_checks:
                        message_sum += c2v_messages[check_idx][var_idx]
                    v2c_messages[var_idx][target_check] = message_sum
            
            # Calculate posterior LLR (same as variable node update)
            posterior_llr = llr_input.copy()
            for var_idx in range(self.n):
                for check_idx in self.var_to_check[var_idx]:
                    posterior_llr[var_idx] += c2v_messages[check_idx][var_idx]
            
            decoded_bits = (posterior_llr < 0).astype(int)
            
            if self.early_termination:
                syndrome = (self.H @ decoded_bits) % 2  # type: ignore
                if np.all(syndrome == 0):
                    converged = True
                    break
        
        # OSD post-processing (if not converged, try flipping low-confidence bits)
        if not converged and self.osd_order >= 0:
            osd_applied = True
            uncertain_indices = np.argsort(np.abs(posterior_llr))[:self.osd_order + 1]
            for flip_set in combinations(uncertain_indices, self.osd_order + 1):
                temp_bits = decoded_bits.copy()
                temp_bits[list(flip_set)] = 1 - temp_bits[list(flip_set)]
                syndrome = (self.H @ temp_bits) % 2  # type: ignore
                if np.all(syndrome == 0):
                    decoded_bits = temp_bits
                    converged = True
                    break
        
        # Statistics
        final_syndrome = (self.H @ decoded_bits) % 2  # type: ignore
        stats = {
            "iterations": iteration + 1,
            "converged": converged,
            "syndrome_weight": int(np.sum(final_syndrome)),
            "final_llr": posterior_llr.tolist(),
            "parity_check_satisfied": bool(np.all(final_syndrome == 0)),
            "osd_applied": osd_applied
        }
        
        self.last_decode_stats = stats
        return decoded_bits, stats

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def validate_codeword(self, codeword: np.ndarray) -> bool:
        """Validate if codeword satisfies parity check constraints."""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"Codeword length {codeword.size} != expected length {self.n}")
        
        syndrome = (self.H @ codeword) % 2  # type: ignore
        return bool(np.all(syndrome == 0))

    def get_syndrome(self, codeword: np.ndarray) -> np.ndarray:
        """Calculate syndrome of codeword."""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"Codeword length {codeword.size} != expected length {self.n}")
        
        return (self.H @ codeword) % 2  # type: ignore

    def extract_information_bits(self, codeword: np.ndarray) -> np.ndarray:
        """Extract information bits from decoded codeword."""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"Codeword length {codeword.size} != expected length {self.n}")
        
        # Extract information bits based on systematic generator matrix columns
        info_cols = self.code.info_cols
        return codeword[info_cols]

    # ------------------------------------------------------------------
    # Diagnostics and analysis
    # ------------------------------------------------------------------
    def analyze_decoder_performance(self) -> Dict[str, Any]:
        """Analyze decoder performance and structure."""
        var_degrees = [len(self.var_to_check[i]) for i in range(self.n)]
        check_degrees = [len(self.check_to_var[i]) for i in range(self.m)]
        
        analysis = {
            "code_parameters": {
                "n": self.n,
                "k": self.k,
                "m": self.m,
                "rate": self.rate,
            },
            "degree_distribution": {
                "variable_degrees": var_degrees,
                "check_degrees": check_degrees,
                "avg_variable_degree": np.mean(var_degrees),
                "avg_check_degree": np.mean(check_degrees),
            },
            "decoder_parameters": {
                "max_iterations": self.max_iterations,
                "min_sum_scaling": self.min_sum_scaling,
                "early_termination": self.early_termination,
            },
            "last_decode_stats": self.last_decode_stats,
        }
        
        return analysis

    def compare_algorithms(self, llr_input: np.ndarray) -> Dict[str, Any]:
        """Compare performance of Min-Sum and Sum-Product algorithms."""
        llr_input = np.asarray(llr_input, dtype=float)
        
        results = {}
        
        # Test Min-Sum algorithm
        try:
            min_sum_bits, min_sum_stats = self._decode_min_sum(llr_input)
            results['min_sum'] = {
                'decoded_bits': min_sum_bits.tolist(),
                'stats': min_sum_stats,
                'success': True
            }
        except Exception as e:
            results['min_sum'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test Sum-Product algorithm
        try:
            sum_prod_bits, sum_prod_stats = self._decode_sum_product(llr_input)
            results['sum_product'] = {
                'decoded_bits': sum_prod_bits.tolist(),
                'stats': sum_prod_stats,
                'success': True
            }
        except Exception as e:
            results['sum_product'] = {
                'success': False,
                'error': str(e)
            }
        
        # Compare results
        if results['min_sum']['success'] and results['sum_product']['success']:
            min_sum_converged = results['min_sum']['stats']['converged']
            sum_prod_converged = results['sum_product']['stats']['converged']
            min_sum_iterations = results['min_sum']['stats']['iterations']
            sum_prod_iterations = results['sum_product']['stats']['iterations']
            
            results['comparison'] = {
                'both_converged': min_sum_converged and sum_prod_converged,
                'min_sum_better': min_sum_converged and not sum_prod_converged,
                'sum_product_better': sum_prod_converged and not min_sum_converged,
                'iteration_difference': sum_prod_iterations - min_sum_iterations,
                'results_match': np.array_equal(
                    results['min_sum']['decoded_bits'],
                    results['sum_product']['decoded_bits']
                )
            }
        
        return results