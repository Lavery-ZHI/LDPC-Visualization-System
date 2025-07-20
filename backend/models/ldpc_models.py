"""LDPC 码的核心数据结构工具。
针对清晰度、类型安全和大型稀疏矩阵进行了优化。
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Any, Sequence
import numpy as np
import scipy.sparse as sp

__all__ = ["LDPCCode"]


def _row_echelon_gf2(A: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """返回 GF(2) 上 *A* 的*简化*行阶梯形式和主元列索引。"""
    A = (A % 2).astype(np.uint8, copy=True)   # ★ 关键：保整型 & 限定到 {0,1}
    m, n = A.shape
    r = 0  # 当前行
    pivots: List[int] = []
    for c in range(n):
        # 找到列 *c* 中包含 1 的行
        pivot_row = np.argmax(A[r:, c] == 1) + r if np.any(A[r:, c] == 1) else -1
        if pivot_row == -1:
            continue
        # 将主元行移到正确位置
        if pivot_row != r:
            A[[r, pivot_row]] = A[[pivot_row, r]]
        # 消除列 *c* 中的其他 1
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]  # GF(2) 上的异或操作
        pivots.append(c)
        r += 1
        if r == m:
            break
    return A, pivots


def _rank_gf2(A: np.ndarray) -> int:
    """使用高斯消元法计算 GF(2) 上的矩阵秩。"""
    _, pivots = _row_echelon_gf2(A.copy())
    return len(pivots)


class LDPCCode:
    """LDPC 奇偶校验矩阵和相关辅助函数的轻量级容器。"""

    def __init__(self, h_matrix: Sequence | np.ndarray | sp.spmatrix):
        if isinstance(h_matrix, list):  # 允许嵌套列表
            h_matrix = np.array(h_matrix, dtype=int)
        if not isinstance(h_matrix, (np.ndarray, sp.spmatrix)):
            raise TypeError("h_matrix 必须是类数组或 scipy 稀疏矩阵")

        if sp.issparse(h_matrix):
            self.H: sp.spmatrix = h_matrix.tocsr()
        else:
            self.H = sp.csr_matrix(h_matrix % 2)  # 始终存储为 CSR 矩阵 (模 2)

        if self.H.nnz == 0:
            raise ValueError("H 矩阵不能全为零")

        self.m, self.n = self.H.shape
        self._rank: int | None = None  # 延迟计算
        self._G: np.ndarray | None = None
        self._info_cols: List[int] | None = None  # 信息位列索引（延迟赋值）

    # ---------------------------------------------------------------------
    # 基本属性
    # ---------------------------------------------------------------------
    @property
    def rank(self) -> int:
        if self._rank is None:
            self._rank = _rank_gf2(self.H.toarray())
        return self._rank

    @property
    def k(self) -> int:  # 消息长度
        return self.n - self.rank

    @property
    def rate(self) -> float:
        return self.k / self.n

    @property
    def G(self) -> np.ndarray:
        """系统生成矩阵 *G* (k × n)。延迟计算。"""
        if self._G is None:
            self._G = self._compute_generator_matrix()
        return self._G

    # 新增：信息位列索引属性
    @property
    def info_cols(self) -> List[int]:
        """返回信息位在码字中的列索引列表。触发 G 的生成以保证可用。"""
        if self._info_cols is None:
            # 确保已生成 G，同步 _info_cols
            _ = self.G  # 触发 _compute_generator_matrix()
        return self._info_cols  # type: ignore

    @classmethod
    def from_graph_data(
            cls,
            nodes: List[Dict],  # [{'id':'V0','type':'variable'}, …]
            edges: List[Dict],  # [{'fromId':'V0','toId':'C0'}, …]
    ) -> "LDPCCode":
        """
        将 Tanner 图描述转换为 LDPCCode。
        变量节点列索引按 V0,V1,… 排序，校验节点行索引按 C0,C1,… 排序。
        """
        # --- 1. 筛选变量 / 校验节点 ---
        var_ids = [n["id"] for n in nodes if n["type"] == "variable"]
        chk_ids = [n["id"] for n in nodes if n["type"] == "check"]

        if not var_ids or not chk_ids:
            raise ValueError("图形数据必须至少包含一个 variable 和一个 check 节点")

        n = len(var_ids)
        m = len(chk_ids)

        var_map = {vid: idx for idx, vid in enumerate(var_ids)}
        chk_map = {cid: idx for idx, cid in enumerate(chk_ids)}

        # --- 2. 构建稀疏坐标列表 ---
        row_idx, col_idx, data = [], [], []
        for e in edges:
            vid, cid = e["fromId"], e["toId"]
            # 确保方向无所谓（V→C 或 C→V）
            if vid in chk_map and cid in var_map:
                vid, cid = cid, vid  # 交换，保证 vid 是变量
            if vid not in var_map or cid not in chk_map:
                raise ValueError(f"非法边: {vid}->{cid}")
            row_idx.append(chk_map[cid])
            col_idx.append(var_map[vid])
            data.append(1)

        H = sp.csr_matrix((data, (row_idx, col_idx)), shape=(m, n), dtype=np.uint8)
        return cls(H)

    # ------------------------------------------------------------------
    # 生成矩阵构造
    # ------------------------------------------------------------------
    def _compute_generator_matrix(self) -> np.ndarray:
        H_dense = self.H.toarray()
        H_rref, pivots = _row_echelon_gf2(H_dense.copy())

        all_cols = set(range(self.n))
        info_cols = sorted(all_cols - set(pivots))  # 未用作主元的列
        # 将 info_cols 保存，供外部提取信息位
        self._info_cols = info_cols
        k = len(info_cols)
        if k != self.k:
            raise RuntimeError("构建 G 矩阵时维度不一致")

        G = np.zeros((k, self.n), dtype=int)
        # 标识部分
        G[np.arange(k), info_cols] = 1
        # 奇偶校验部分 (行对应于 H 中的主元)
        for row_in_H, pivot_col in enumerate(pivots):
            G[:, pivot_col] = H_rref[row_in_H, info_cols]
        # 验证正交性
        if np.any((H_dense @ G.T) % 2):
            raise RuntimeError("内部错误：H·Gᵀ 不为零")
        return G

    # ------------------------------------------------------------------
    # 结构分析辅助函数 (度分布等)
    # ------------------------------------------------------------------
    def _degree_vectors(self) -> Tuple[np.ndarray, np.ndarray]:
        H_dense = self.H.toarray()
        return np.sum(H_dense, axis=0), np.sum(H_dense, axis=1)  # (变量节点度, 校验节点度)

    def analyze_code_properties(self) -> Dict[str, Any]:
        var_deg, check_deg = self._degree_vectors()
        is_regular = (
            len(np.unique(var_deg)) == 1 and len(np.unique(check_deg)) == 1
        )
        properties: Dict[str, Any] = {
            "code_length": self.n,
            "message_length": self.k,
            "code_rate": self.rate,
            "is_regular": is_regular,
            "variable_node_degree": (
                int(var_deg[0]) if is_regular else var_deg.astype(int).tolist()
            ),
            "check_node_degree": (
                int(check_deg[0]) if is_regular else check_deg.astype(int).tolist()
            ),
            "min_distance_estimate": int(check_deg.min() + 1),
            "has_4cycle": self._has_length_4_cycle(),
            "var_degree_distribution": self._distribution(var_deg),
            "check_degree_distribution": self._distribution(check_deg),
        }
        return properties

    @staticmethod
    def _distribution(degrees: np.ndarray) -> Dict[int, float]:
        uniq, cnt = np.unique(degrees, return_counts=True)
        total = degrees.size
        return {int(d): float(c / total) for d, c in zip(uniq, cnt)}

    def _has_length_4_cycle(self) -> bool:
        # 高效的 4 环检查：查找 HᵀH 中非零的非对角线元素
        HtH = (self.H.T @ self.H).tocoo()
        # 移除对角线元素
        mask = HtH.row != HtH.col
        return bool(mask.sum())