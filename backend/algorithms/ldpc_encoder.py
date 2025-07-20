"""围绕 :class:`LDPCCode` 构建的高级编码器。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence
import numpy as np
import scipy.sparse as sp
from models.ldpc_models import LDPCCode

__all__ = ["LDPCEncoder"]


class LDPCEncoder:
    """将 *k* 个信息位编码为长度为 *n* 的 LDPC 码字。"""

    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        # 处理稀疏矩阵输入
        if sp.issparse(h_matrix):
            h_matrix = h_matrix.astype(np.uint8)       # 稀疏域保持整型
            h_matrix.data %= 2                         # 万一有 2、-1 之类

        # 实例化 LDPC 码模型——这会执行验证。
        self.code = LDPCCode(h_matrix)
        # 延迟属性
        self._G: np.ndarray | None = None

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
    # 核心例程
    # ------------------------------------------------------------------
    def generate_g_matrix(self) -> np.ndarray:
        """返回（并缓存）系统生成矩阵 *G*。"""
        if self._G is None:
            self._G = self.code.G  # 触发 LDPCCode 内部的延迟计算
        return self._G

    def encode(self, info_bits: Sequence[int] | np.ndarray) -> np.ndarray:
        """将 *info_bits* (长度 *k*) 编码为 LDPC 码字。"""
        G = self.generate_g_matrix()  # 确保在检查长度*之前*最终确定 *k*
        info_bits = np.asarray(info_bits, dtype=int) % 2
        if info_bits.ndim != 1:
            raise ValueError("info_bits 必须是一维向量")
        if info_bits.size != self.k:
            raise ValueError(f"info_bits 长度 {info_bits.size} != 预期 k={self.k}")
        return (info_bits @ G) % 2

    # ------------------------------------------------------------------
    # 诊断
    # ------------------------------------------------------------------
    def validate_code_structure(self) -> Dict[str, Any]:
        G = self.generate_g_matrix()
        H_dense = self.H.toarray()
        orthogonality = (H_dense @ G.T) % 2
        is_orthogonal = not orthogonality.any()
        result: Dict[str, Any] = {
            "is_orthogonal": is_orthogonal,
            "orthogonality_error": int(orthogonality.sum()) if not is_orthogonal else 0,
            "k": self.k,
            "n": self.n,
            "code_rate": self.rate,
        }
        result.update(self.code.analyze_code_properties())
        return result

    # 用于 API 响应的便捷辅助函数
    def get_matrices(self) -> Dict[str, Any]:
        G = self.generate_g_matrix()
        return {
            "h_matrix": self.H.toarray().tolist(),
            "g_matrix": G.tolist(),
            "info_cols": self.code.info_cols,
        }