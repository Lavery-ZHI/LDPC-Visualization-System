"""围绕 :class:`LDPCCode` 构建的高级解码器。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple, Optional
import numpy as np
import scipy.sparse as sp
from models.ldpc_models import LDPCCode
from itertools import combinations  # 新增：用于 OSD 组合生成

__all__ = ["LDPCDecoder"]


class LDPCDecoder:
    """使用置信传播（BP）算法解码 LDPC 码字。"""

    def __init__(
        self,
        h_matrix: Sequence | np.ndarray | sp.spmatrix,
        max_iterations: int = 50,
        min_sum_scaling: float = 0.9,
        convergence_threshold: float = 1e-6,
        early_termination: bool = True,
        osd_order: int = 0  # 新增：OSD 订单，控制翻转比特数 (0 表示简单翻转最低置信位)
    ):
        """
        初始化 LDPC 解码器。

        参数:
            h_matrix: 奇偶校验矩阵 H
            max_iterations: 最大迭代次数
            min_sum_scaling: Min-Sum 算法缩放因子
            convergence_threshold: 收敛阈值
            early_termination: 是否启用早期终止
            osd_order: OSD 后处理订单 (默认 0，表示基本后处理)
        """
        # 处理稀疏矩阵输入
        if sp.issparse(h_matrix):
            h_matrix = h_matrix.astype(np.uint8)  # type: ignore
            h_matrix.data = h_matrix.data % 2  # type: ignore

        # 实例化 LDPC 码模型
        self.code = LDPCCode(h_matrix)
        
        # 解码参数
        self.max_iterations = max_iterations
        self.min_sum_scaling = min_sum_scaling
        self.convergence_threshold = convergence_threshold
        self.early_termination = early_termination
        self.osd_order = osd_order  # 新增
        
        # 预计算邻接信息以提高效率
        self._precompute_adjacency()
        
        # 解码统计信息
        self.last_decode_stats = {}
        
        # 调试选项
        self.debug_mode = False

    # ------------------------------------------------------------------
    # 公共属性
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
    # 预计算邻接信息
    # ------------------------------------------------------------------
    def _precompute_adjacency(self):
        """预计算变量节点和校验节点的邻接信息。"""
        H_coo = self.H.tocoo()  # type: ignore
        
        # 变量节点到校验节点的邻接列表
        self.var_to_check = [[] for _ in range(self.n)]
        # 校验节点到变量节点的邻接列表
        self.check_to_var = [[] for _ in range(self.m)]
        
        for i, j in zip(H_coo.row, H_coo.col):
            self.var_to_check[j].append(i)
            self.check_to_var[i].append(j)

    # ------------------------------------------------------------------
    # LLR 计算
    # ------------------------------------------------------------------
    def awgn_llr(self, received_signal: np.ndarray, noise_variance: float) -> np.ndarray:
        """
        计算 AWGN 信道的对数似然比（LLR）。
        
        参数:
            received_signal: 接收信号 (长度 n)
            noise_variance: 噪声方差 σ²
            
        返回:
            LLR 值数组
        """
        received_signal = np.asarray(received_signal, dtype=float)
        if received_signal.size != self.n:
            raise ValueError(f"接收信号长度 {received_signal.size} != 码字长度 {self.n}")
        
        # LLR = 2 * r / σ² (假设发送 +1/-1)
        llr = 2.0 * received_signal / noise_variance
        return llr

    def bsc_llr(self, received_bits: np.ndarray, crossover_probability: float) -> np.ndarray:
        """
        计算二进制对称信道（BSC）的对数似然比（LLR）。
        
        参数:
            received_bits: 接收比特 (0/1, 长度 n)
            crossover_probability: 交叉概率 p
            
        返回:
            LLR 值数组
        """
        received_bits = np.asarray(received_bits, dtype=int) % 2
        if received_bits.size != self.n:
            raise ValueError(f"接收比特长度 {received_bits.size} != 码字长度 {self.n}")
        
        if crossover_probability <= 0 or crossover_probability >= 0.5:
            raise ValueError("交叉概率必须在 (0, 0.5) 范围内")
        
        # LLR = log((1-p)/p) * (1-2*r)
        log_ratio = np.log((1 - crossover_probability) / crossover_probability)
        llr = log_ratio * (1 - 2 * received_bits)
        return llr

    # ------------------------------------------------------------------
    # BP 解码算法 (Min-Sum)
    # ------------------------------------------------------------------
    def decode(
        self,
        llr_input: np.ndarray,
        algorithm: str = "min_sum"
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        使用 BP 算法解码 LDPC 码字。
        
        参数:
            llr_input: 输入 LLR 值 (长度 n)
            algorithm: 解码算法 ("min_sum" 或 "sum_product")
            
        返回:
            (解码比特, 解码统计信息)
        """
        llr_input = np.asarray(llr_input, dtype=float)
        if llr_input.size != self.n:
            raise ValueError(f"LLR 输入长度 {llr_input.size} != 码字长度 {self.n}")
        
        if algorithm == "min_sum" or algorithm == "min-sum":
            return self._decode_min_sum(llr_input)
        elif algorithm == "sum_product" or algorithm == "sum-product":
            return self._decode_sum_product(llr_input)
        else:
            raise ValueError(f"不支持的解码算法: {algorithm}")

    def _decode_min_sum(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Min-Sum 算法实现（优化：引入 Normalized Min-Sum 变体，并添加 OSD 后处理）。"""
        # 初始化消息
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
        
        # 计算平均校验节点度，用于归一化因子
        avg_check_degree = np.mean([len(self.check_to_var[i]) for i in range(self.m)])
        normalization_factor = 1.0 / (0.75 + 0.25 * avg_check_degree / 4.0)  # 示例归一化公式
        
        converged = False
        osd_applied = False
        for iteration in range(self.max_iterations):
            # 校验节点更新
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
                    
                    # 应用归一化因子
                    c2v_messages[check_idx][target_var] = (
                        self.min_sum_scaling * sign_product * min_abs * normalization_factor
                    )
            
            # 变量节点更新
            for var_idx in range(self.n):
                connected_checks = self.var_to_check[var_idx]
                
                for target_check in connected_checks:
                    other_checks = [c for c in connected_checks if c != target_check]
                    message_sum = llr_input[var_idx]
                    for check_idx in other_checks:
                        message_sum += c2v_messages[check_idx][var_idx]
                    v2c_messages[var_idx][target_check] = message_sum
            
            # 计算后验 LLR 和硬判决
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
        
        # 新增：OSD 后处理（如果未收敛，尝试翻转低置信比特）
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
        
        # 统计信息
        final_syndrome = (self.H @ decoded_bits) % 2  # type: ignore
        stats = {
            "iterations": iteration + 1,
            "converged": converged,
            "syndrome_weight": int(np.sum(final_syndrome)),
            "final_llr": posterior_llr.tolist(),
            "parity_check_satisfied": bool(np.all(final_syndrome == 0)),
            "osd_applied": osd_applied  # 新增：指示是否应用了 OSD
        }
        
        self.last_decode_stats = stats
        return decoded_bits, stats

    def _decode_sum_product(self, llr_input: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Sum-Product 算法实现（优化：转移到对数域以提升数值稳定性，并添加 OSD 后处理）。"""
        # 辅助函数：对数域加法
        def log_sum_exp(a, b):
            max_val = np.maximum(a, b)
            return max_val + np.log1p(np.exp(-np.abs(a - b)))
        
        # 初始化消息（在对数域：存储 log(P0 / P1) = LLR）
        v2c_messages = {}
        c2v_messages = {}
        
        for var_idx in range(self.n):
            v2c_messages[var_idx] = {}
            for check_idx in self.var_to_check[var_idx]:
                v2c_messages[var_idx][check_idx] = llr_input[var_idx]
        
        for check_idx in range(self.m):
            c2v_messages[check_idx] = {}
            for var_idx in self.check_to_var[check_idx]:
                c2v_messages[check_idx][var_idx] = 0.0  # LLR=0 表示 P0=P1=0.5
        
        converged = False
        osd_applied = False
        for iteration in range(self.max_iterations):
            # 校验节点更新（对数域 tanh 规则）
            for check_idx in range(self.m):
                connected_vars = self.check_to_var[check_idx]
                
                for target_var in connected_vars:
                    other_vars = [v for v in connected_vars if v != target_var]
                    
                    if len(other_vars) == 0:
                        c2v_messages[check_idx][target_var] = 0.0
                        continue
                    
                    # 对数域 Sum-Product：prod tanh(v2c / 2) * 2 * atanh
                    tanh_msgs = [np.tanh(v2c_messages[v][check_idx] / 2.0) for v in other_vars]
                    prod_tanh = np.prod(tanh_msgs)
                    
                    # 优化：使用 atanh 并剪裁以避免数值不稳定
                    prod_tanh = np.clip(prod_tanh, -1 + 1e-10, 1 - 1e-10)
                    c2v_messages[check_idx][target_var] = 2.0 * np.arctanh(prod_tanh)
            
            # 变量节点更新（对数域简单加法）
            for var_idx in range(self.n):
                connected_checks = self.var_to_check[var_idx]
                
                for target_check in connected_checks:
                    other_checks = [c for c in connected_checks if c != target_check]
                    message_sum = llr_input[var_idx]
                    for check_idx in other_checks:
                        message_sum += c2v_messages[check_idx][var_idx]
                    v2c_messages[var_idx][target_check] = message_sum
            
            # 计算后验 LLR（同变量节点更新）
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
        
        # 新增：OSD 后处理（如果未收敛，尝试翻转低置信比特）
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
        
        # 统计信息
        final_syndrome = (self.H @ decoded_bits) % 2  # type: ignore
        stats = {
            "iterations": iteration + 1,
            "converged": converged,
            "syndrome_weight": int(np.sum(final_syndrome)),
            "final_llr": posterior_llr.tolist(),
            "parity_check_satisfied": bool(np.all(final_syndrome == 0)),
            "osd_applied": osd_applied  # 新增：指示是否应用了 OSD
        }
        
        self.last_decode_stats = stats
        return decoded_bits, stats

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def validate_codeword(self, codeword: np.ndarray) -> bool:
        """验证码字是否满足奇偶校验约束。"""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"码字长度 {codeword.size} != 期望长度 {self.n}")
        
        syndrome = (self.H @ codeword) % 2  # type: ignore
        return bool(np.all(syndrome == 0))

    def get_syndrome(self, codeword: np.ndarray) -> np.ndarray:
        """计算码字的校验子。"""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"码字长度 {codeword.size} != 期望长度 {self.n}")
        
        return (self.H @ codeword) % 2  # type: ignore

    def extract_information_bits(self, codeword: np.ndarray) -> np.ndarray:
        """从解码后的码字中提取信息位。"""
        codeword = np.asarray(codeword, dtype=int) % 2
        if codeword.size != self.n:
            raise ValueError(f"码字长度 {codeword.size} != 期望长度 {self.n}")
        
        # 根据生成矩阵的单位子矩阵所在列提取信息位
        info_cols = self.code.info_cols
        return codeword[info_cols]

    # ------------------------------------------------------------------
    # 诊断和分析
    # ------------------------------------------------------------------
    def analyze_decoder_performance(self) -> Dict[str, Any]:
        """分析解码器性能和结构。"""
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
        """比较Min-Sum和Sum-Product算法的性能。"""
        llr_input = np.asarray(llr_input, dtype=float)
        
        results = {}
        
        # 测试Min-Sum算法
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
        
        # 测试Sum-Product算法
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
        
        # 比较结果
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