"""Core data structure tools for LDPC codes.
Optimized for clarity, type safety, and large sparse matrices.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Any, Sequence
import numpy as np
import scipy.sparse as sp

__all__ = ["LDPCCode"]


def _row_echelon_gf2(A: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """Return the *reduced* row echelon form of *A* over GF(2) and pivot column indices."""
    A = (A % 2).astype(np.uint8, copy=True)   # ★ Key: preserve integer type & limit to {0,1}
    m, n = A.shape
    r = 0  # current row
    pivots: List[int] = []
    for c in range(n):
        # Find row containing 1 in column *c*
        pivot_row = np.argmax(A[r:, c] == 1) + r if np.any(A[r:, c] == 1) else -1
        if pivot_row == -1:
            continue
        # Move pivot row to correct position
        if pivot_row != r:
            A[[r, pivot_row]] = A[[pivot_row, r]]
        # Eliminate other 1s in column *c*
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]  # XOR operation over GF(2)
        pivots.append(c)
        r += 1
        if r == m:
            break
    return A, pivots


def _rank_gf2(A: np.ndarray) -> int:
    """Calculate matrix rank over GF(2) using Gaussian elimination."""
    _, pivots = _row_echelon_gf2(A.copy())
    return len(pivots)


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

    # ---------------------------------------------------------------------
    # Basic properties
    # ---------------------------------------------------------------------
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

    @property
    def G(self) -> np.ndarray:
        """Systematic generator matrix *G* (k × n). Lazy computation."""
        if self._G is None:
            self._G = self._compute_generator_matrix()
        return self._G

    # New: Information bit column indices property
    @property
    def info_cols(self) -> List[int]:
        """Return list of information bit column indices in codeword. Triggers G generation to ensure availability."""
        if self._info_cols is None:
            # Ensure G is generated, synchronize _info_cols
            _ = self.G  # trigger _compute_generator_matrix()
        return self._info_cols  # type: ignore

    @classmethod
    def from_graph_data(
            cls,
            nodes: List[Dict],  # [{'id':'V0','type':'variable'}, …]
            edges: List[Dict],  # [{'fromId':'V0','toId':'C0'}, …]
    ) -> "LDPCCode":
        """
        Convert Tanner graph description to LDPCCode.
        Variable node column indices sorted by V0,V1,… Check node row indices sorted by C0,C1,…
        """
        # --- 1. Filter variable / check nodes ---
        var_ids = [n["id"] for n in nodes if n["type"] == "variable"]
        chk_ids = [n["id"] for n in nodes if n["type"] == "check"]

        if not var_ids or not chk_ids:
            raise ValueError("Graph data must contain at least one variable and one check node")

        n = len(var_ids)
        m = len(chk_ids)

        var_map = {vid: idx for idx, vid in enumerate(var_ids)}
        chk_map = {cid: idx for idx, cid in enumerate(chk_ids)}

        # --- 2. Build sparse coordinate list ---
        row_idx, col_idx, data = [], [], []
        for e in edges:
            vid, cid = e["fromId"], e["toId"]
            # Ensure direction doesn't matter (V→C or C→V)
            if vid in chk_map and cid in var_map:
                vid, cid = cid, vid  # swap, ensure vid is variable
            if vid not in var_map or cid not in chk_map:
                raise ValueError(f"Invalid edge: {vid}->{cid}")
            row_idx.append(chk_map[cid])
            col_idx.append(var_map[vid])
            data.append(1)

        H = sp.csr_matrix((data, (row_idx, col_idx)), shape=(m, n), dtype=np.uint8)
        return cls(H)

    # ------------------------------------------------------------------
    # Generator matrix construction
    # ------------------------------------------------------------------
    def _compute_generator_matrix(self) -> np.ndarray:
        H_dense = self.H.toarray()
        H_rref, pivots = _row_echelon_gf2(H_dense.copy())

        all_cols = set(range(self.n))
        info_cols = sorted(all_cols - set(pivots))  # columns not used as pivots
        # Save info_cols for external information bit extraction
        self._info_cols = info_cols
        k = len(info_cols)
        if k != self.k:
            raise RuntimeError("Dimension inconsistency when building G matrix")

        G = np.zeros((k, self.n), dtype=int)
        # Identity part
        G[np.arange(k), info_cols] = 1
        # Parity check part (rows correspond to pivots in H)
        for row_in_H, pivot_col in enumerate(pivots):
            G[:, pivot_col] = H_rref[row_in_H, info_cols]
        # Verify orthogonality
        if np.any((H_dense @ G.T) % 2):
            raise RuntimeError("Internal error: H·Gᵀ is not zero")
        return G

    # ------------------------------------------------------------------
    # Structure analysis helper functions (degree distribution, etc.)
    # ------------------------------------------------------------------
    def _degree_vectors(self) -> Tuple[np.ndarray, np.ndarray]:
        H_dense = self.H.toarray()
        return np.sum(H_dense, axis=0), np.sum(H_dense, axis=1)  # (variable node degrees, check node degrees)

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
        # Efficient 4-cycle check: find non-zero off-diagonal elements in HᵀH
        HtH = (self.H.T @ self.H).tocoo()
        # Remove diagonal elements
        mask = HtH.row != HtH.col
        return bool(mask.sum())