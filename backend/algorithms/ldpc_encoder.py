"""High-level encoder built around :class:`LDPCCode`."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence
import numpy as np
import scipy.sparse as sp
from models.ldpc_models import LDPCCode

__all__ = ["LDPCEncoder"]


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
    # Core routines
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Diagnostics
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

    # Convenient helper function for API responses
    def get_matrices(self) -> Dict[str, Any]:
        G = self.generate_g_matrix()
        return {
            "h_matrix": self.H.toarray().tolist(),
            "g_matrix": G.tolist(),
            "info_cols": self.code.info_cols,
        }