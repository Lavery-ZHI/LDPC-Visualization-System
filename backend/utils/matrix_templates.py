"""
LDPC H Matrix Templates Library
Provides various pre-defined LDPC code templates for different applications.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import math

class LDPCMatrixTemplates:
    """Library of pre-defined LDPC matrix templates"""
    
    @staticmethod
    def get_available_templates() -> Dict[str, Dict]:
        """Get list of all available LDPC matrix templates"""
        return {
            "simple_6_3": {
                "name": "Simple (6,3) LDPC Code",
                "description": "Basic demonstration code with rate 1/2",
                "n": 6, "k": 3, "rate": 0.5,
                "complexity": "Low"
            },
            "hamming_7_4": {
                "name": "Hamming (7,4) LDPC Code", 
                "description": "Classic Hamming code adapted for LDPC",
                "n": 7, "k": 4, "rate": 0.571,
                "complexity": "Low"
            },
            "regular_12_6": {
                "name": "Regular (12,6) LDPC Code",
                "description": "Regular LDPC with column weight 3, row weight 6",
                "n": 12, "k": 6, "rate": 0.5,
                "complexity": "Medium"
            },
            "irregular_24_12": {
                "name": "Irregular (24,12) LDPC Code",
                "description": "Irregular LDPC with variable node degrees [2,3,4]",
                "n": 24, "k": 12, "rate": 0.5,
                "complexity": "Medium"
            },
            "ieee_648_324": {
                "name": "IEEE 802.11n (648,324) LDPC",
                "description": "WiFi standard LDPC code with rate 1/2",
                "n": 648, "k": 324, "rate": 0.5,
                "complexity": "High"
            },
            "dvb_s2_16200": {
                "name": "DVB-S2 (16200,10800) LDPC",
                "description": "Satellite TV standard LDPC code",
                "n": 16200, "k": 10800, "rate": 0.667,
                "complexity": "Very High"
            }
        }
    
    @staticmethod
    def generate_simple_6_3() -> np.ndarray:
        """Generate simple (6,3) LDPC code for demonstration"""
        return np.array([
            [1, 1, 1, 0, 0, 0],
            [0, 1, 1, 1, 0, 0], 
            [0, 0, 1, 1, 1, 1]
        ], dtype=np.uint8)
    
    @staticmethod
    def generate_hamming_7_4() -> np.ndarray:
        """Generate Hamming (7,4) LDPC code"""
        return np.array([
            [1, 1, 0, 1, 1, 0, 0],
            [1, 0, 1, 1, 0, 1, 0],
            [0, 1, 1, 1, 0, 0, 1]
        ], dtype=np.uint8)
    
    @staticmethod
    def generate_regular_12_6(column_weight: int = 3, row_weight: int = 6) -> np.ndarray:
        """Generate regular (12,6) LDPC code with specified weights"""
        n, k = 12, 6
        m = n - k
        
        # Create regular LDPC matrix with column weight 3, row weight 6
        H = np.zeros((m, n), dtype=np.uint8)
        
        # Pattern for regular construction
        positions = [
            [0, 1, 2, 6, 7, 8],    # Row 0
            [1, 2, 3, 7, 8, 9],    # Row 1
            [2, 3, 4, 8, 9, 10],   # Row 2
            [3, 4, 5, 9, 10, 11],  # Row 3
            [4, 5, 0, 10, 11, 6],  # Row 4
            [5, 0, 1, 11, 6, 7]    # Row 5
        ]
        
        for i, row_positions in enumerate(positions):
            for pos in row_positions:
                H[i, pos] = 1
                
        return H
    
    @staticmethod
    def generate_irregular_24_12() -> np.ndarray:
        """Generate irregular (24,12) LDPC code with variable degrees"""
        n, k = 24, 12
        m = n - k
        
        H = np.zeros((m, n), dtype=np.uint8)
        
        # Irregular pattern with different column weights
        # First 8 columns: weight 2
        # Next 8 columns: weight 3  
        # Last 8 columns: weight 4
        
        np.random.seed(42)  # For reproducible results
        
        for col in range(n):
            if col < 8:
                weight = 2
            elif col < 16:
                weight = 3
            else:
                weight = 4
                
            # Randomly place 1s in this column
            row_indices = np.random.choice(m, size=weight, replace=False)
            H[row_indices, col] = 1
        
        # Ensure each row has reasonable weight
        for row in range(m):
            row_weight = np.sum(H[row, :])
            if row_weight < 3:
                # Add more 1s to sparse rows
                zero_cols = np.where(H[row, :] == 0)[0]
                if len(zero_cols) > 0:
                    add_count = min(3 - row_weight, len(zero_cols))
                    add_positions = np.random.choice(zero_cols, size=add_count, replace=False)
                    H[row, add_positions] = 1
                    
        return H
    
    @staticmethod
    def generate_ieee_648_324() -> np.ndarray:
        """Generate IEEE 802.11n (648,324) LDPC code (simplified version)"""
        n, k = 648, 324
        m = n - k
        
        # This is a simplified version - real IEEE codes use structured construction
        H = np.zeros((m, n), dtype=np.uint8)
        
        # Use circulant matrix construction (simplified)
        z = 27  # Sub-matrix size
        
        # Base matrix for IEEE 802.11n rate 1/2
        base_matrix = np.array([
            [0, -1, -1, -1,  0,  0, -1, -1,  0, -1, -1,  0,  1,  0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
            [22, 0, -1, -1, 17, -1,  0,  0, 12, -1, -1, -1, -1,  0,  0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
            [ 6, -1,  0, -1, 10, -1, -1, -1, 24, -1,  0, -1, -1, -1,  0,  0, -1, -1, -1, -1, -1, -1, -1, -1],
            [ 2, -1, -1,  0, 20, -1, -1, -1, 25,  0, -1, -1, -1, -1, -1,  0,  0, -1, -1, -1, -1, -1, -1, -1],
            [23, -1, -1, -1,  3, -1, -1, -1,  0, -1,  9, 11, -1, -1, -1, -1,  0,  0, -1, -1, -1, -1, -1, -1],
            [24, -1, 23,  1, 17, -1,  3, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1,  0,  0, -1, -1, -1, -1, -1],
            [25, -1, -1, -1,  8, -1, -1, -1,  7, 18, -1, -1,  0, -1, -1, -1, -1, -1,  0,  0, -1, -1, -1, -1],
            [13, 24, -1, -1,  0, -1,  8, -1,  6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  0,  0, -1, -1, -1],
            [ 7, 20, -1, 16, 22, 10, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  0,  0, -1, -1],
            [11, -1, -1, -1, 19, -1, -1, -1, 13, -1,  3, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1,  0,  0, -1],
            [25, -1,  8, -1, 23, 18, -1, 14,  9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  0,  0],
            [ 3, -1, -1, -1, 16, -1, -1,  2, 25, 5, -1, -1,  1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  0]
        ])
        
        # Convert base matrix to full H matrix using circulant expansion
        for i in range(base_matrix.shape[0]):
            for j in range(base_matrix.shape[1]):
                if base_matrix[i, j] != -1:
                    # Create circulant submatrix
                    shift = base_matrix[i, j]
                    for k in range(z):
                        row_idx = i * z + k
                        col_idx = j * z + ((k + shift) % z)
                        if row_idx < m and col_idx < n:
                            H[row_idx, col_idx] = 1
        
        return H
    
    @staticmethod
    def generate_dvb_s2_simplified(n: int = 16200, k: int = 10800) -> np.ndarray:
        """Generate simplified DVB-S2 style LDPC code"""
        m = n - k
        H = np.zeros((m, n), dtype=np.uint8)
        
        # Use structured construction similar to DVB-S2
        # This is a simplified version for demonstration
        
        # Set random seed for reproducible results
        np.random.seed(123)
        
        # Create quasi-cyclic structure
        q = 360  # Sub-matrix size for DVB-S2
        
        # Information part - irregular structure
        for col in range(k):
            # Variable column weights based on DVB-S2 profile
            if col < k // 3:
                weight = 3
            elif col < 2 * k // 3:
                weight = 4
            else:
                weight = 5
                
            row_positions = np.random.choice(m, size=weight, replace=False)
            H[row_positions, col] = 1
        
        # Parity part - dual diagonal structure
        for i in range(m):
            # Main diagonal
            if i + k < n:
                H[i, k + i] = 1
            # Secondary diagonal  
            if i > 0 and k + i - 1 < n:
                H[i, k + i - 1] = 1
                
        return H
    
    @staticmethod
    def get_template_by_name(template_name: str) -> Optional[np.ndarray]:
        """Get H matrix for specified template"""
        generators = {
            "simple_6_3": LDPCMatrixTemplates.generate_simple_6_3,
            "hamming_7_4": LDPCMatrixTemplates.generate_hamming_7_4,
            "regular_12_6": LDPCMatrixTemplates.generate_regular_12_6,
            "irregular_24_12": LDPCMatrixTemplates.generate_irregular_24_12,
            "ieee_648_324": LDPCMatrixTemplates.generate_ieee_648_324,
            "dvb_s2_16200": lambda: LDPCMatrixTemplates.generate_dvb_s2_simplified(16200, 10800)
        }
        
        if template_name in generators:
            try:
                return generators[template_name]()
            except Exception as e:
                print(f"Error generating template {template_name}: {e}")
                return None
        else:
            print(f"Template {template_name} not found")
            return None
    
    @staticmethod
    def validate_template(H: np.ndarray) -> Dict[str, Any]:
        """Validate an LDPC matrix template"""
        try:
            m, n = H.shape
            
            # Basic checks
            rank = np.linalg.matrix_rank(H)
            k = n - rank
            
            # Check for all-zero rows or columns
            zero_rows = int(np.sum(np.sum(H, axis=1) == 0))
            zero_cols = int(np.sum(np.sum(H, axis=0) == 0))
            
            # Calculate degree distributions
            row_degrees = np.sum(H, axis=1)
            col_degrees = np.sum(H, axis=0)
            
            return {
                "valid": True,
                "n": int(n),
                "k": int(k),
                "m": int(m),
                "rate": float(k / n),
                "rank": int(rank),
                "zero_rows": zero_rows,
                "zero_cols": zero_cols,
                "min_row_degree": int(np.min(row_degrees)),
                "max_row_degree": int(np.max(row_degrees)),
                "avg_row_degree": float(np.mean(row_degrees)),
                "min_col_degree": int(np.min(col_degrees)),
                "max_col_degree": int(np.max(col_degrees)),
                "avg_col_degree": float(np.mean(col_degrees))
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
