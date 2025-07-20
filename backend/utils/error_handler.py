"""
Enhanced error handling and user feedback system for LDPC operations.
Provides comprehensive error messages and user-friendly feedback.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import numpy as np

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error category types"""
    MATRIX_VALIDATION = "matrix_validation"
    ENCODING = "encoding"
    DECODING = "decoding" 
    SIMULATION = "simulation"
    PERFORMANCE = "performance"
    NETWORK = "network"
    INPUT_VALIDATION = "input_validation"

@dataclass
class ErrorDetails:
    """Structured error information"""
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    suggestions: List[str]
    technical_details: Optional[str] = None
    error_data: Optional[Dict[str, Any]] = None

class LDPCErrorHandler:
    """Centralized error handling for LDPC operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def handle_matrix_validation_error(self, matrix: np.ndarray, error: Exception) -> ErrorDetails:
        """Handle matrix validation errors with detailed feedback"""
        
        if matrix is None:
            return ErrorDetails(
                code="MATRIX_NULL",
                message="Matrix cannot be null or empty",
                category=ErrorCategory.MATRIX_VALIDATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Provide a valid H matrix",
                    "Check matrix generation process",
                    "Use matrix templates from the library"
                ]
            )
        
        if not isinstance(matrix, np.ndarray):
            return ErrorDetails(
                code="MATRIX_TYPE_INVALID",
                message="Matrix must be a numpy array",
                category=ErrorCategory.MATRIX_VALIDATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Convert input to numpy array using np.array()",
                    "Check data type compatibility",
                    "Ensure matrix is 2-dimensional"
                ],
                technical_details=f"Received type: {type(matrix)}"
            )
        
        if len(matrix.shape) != 2:
            return ErrorDetails(
                code="MATRIX_DIMENSION_INVALID",
                message="Matrix must be 2-dimensional",
                category=ErrorCategory.MATRIX_VALIDATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Reshape matrix to 2D format",
                    "Check matrix construction process",
                    "Verify input data structure"
                ],
                technical_details=f"Current shape: {matrix.shape}"
            )
        
        m, n = matrix.shape
        
        if m >= n:
            return ErrorDetails(
                code="MATRIX_RANK_INVALID",
                message="Number of parity bits must be less than code length",
                category=ErrorCategory.MATRIX_VALIDATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    f"Reduce number of rows (current: {m}, should be < {n})",
                    "Check code rate requirements",
                    "Use standard LDPC code parameters"
                ],
                technical_details=f"Matrix dimensions: {m}×{n}, Rate would be: {(n-m)/n:.3f}"
            )
        
        # Check for all-zero rows or columns
        zero_rows = np.sum(np.sum(matrix, axis=1) == 0)
        zero_cols = np.sum(np.sum(matrix, axis=0) == 0)
        
        if zero_rows > 0 or zero_cols > 0:
            return ErrorDetails(
                code="MATRIX_ZERO_ELEMENTS",
                message="Matrix contains all-zero rows or columns",
                category=ErrorCategory.MATRIX_VALIDATION,
                severity=ErrorSeverity.WARNING,
                suggestions=[
                    "Remove or fix all-zero rows/columns",
                    "Check matrix construction algorithm",
                    "Verify degree distributions"
                ],
                technical_details=f"Zero rows: {zero_rows}, Zero columns: {zero_cols}"
            )
        
        # Generic validation error
        return ErrorDetails(
            code="MATRIX_VALIDATION_FAILED",
            message="Matrix validation failed",
            category=ErrorCategory.MATRIX_VALIDATION,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check matrix format and values",
                "Ensure matrix contains only 0s and 1s",
                "Verify matrix construction process"
            ],
            technical_details=str(error)
        )
    
    def handle_encoding_error(self, info_bits: np.ndarray, error: Exception) -> ErrorDetails:
        """Handle encoding operation errors"""
        
        if info_bits is None:
            return ErrorDetails(
                code="INFO_BITS_NULL",
                message="Information bits cannot be null",
                category=ErrorCategory.ENCODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Provide valid information bits",
                    "Check input data generation",
                    "Ensure proper bit array format"
                ]
            )
        
        if not isinstance(info_bits, np.ndarray):
            return ErrorDetails(
                code="INFO_BITS_TYPE_INVALID", 
                message="Information bits must be a numpy array",
                category=ErrorCategory.ENCODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Convert to numpy array: np.array(info_bits)",
                    "Check data type compatibility",
                    "Ensure binary values (0 or 1)"
                ],
                technical_details=f"Received type: {type(info_bits)}"
            )
        
        if len(info_bits.shape) != 1:
            return ErrorDetails(
                code="INFO_BITS_DIMENSION_INVALID",
                message="Information bits must be 1-dimensional array",
                category=ErrorCategory.ENCODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Flatten array using info_bits.flatten()",
                    "Check input data structure",
                    "Ensure proper bit sequence format"
                ],
                technical_details=f"Current shape: {info_bits.shape}"
            )
        
        # Check for invalid bit values
        if not np.all(np.isin(info_bits, [0, 1])):
            return ErrorDetails(
                code="INFO_BITS_VALUES_INVALID",
                message="Information bits must contain only 0s and 1s",
                category=ErrorCategory.ENCODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Convert values to binary (0 or 1)",
                    "Check data preprocessing",
                    "Apply modulo 2 operation if needed"
                ],
                technical_details=f"Unique values found: {np.unique(info_bits)}"
            )
        
        return ErrorDetails(
            code="ENCODING_FAILED",
            message="Encoding operation failed",
            category=ErrorCategory.ENCODING,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check matrix compatibility with info bits length",
                "Verify encoder initialization",
                "Ensure sufficient system resources"
            ],
            technical_details=str(error)
        )
    
    def handle_decoding_error(self, received_signal: np.ndarray, error: Exception) -> ErrorDetails:
        """Handle decoding operation errors"""
        
        if received_signal is None:
            return ErrorDetails(
                code="RECEIVED_SIGNAL_NULL",
                message="Received signal cannot be null",
                category=ErrorCategory.DECODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Provide valid received signal",
                    "Check channel simulation output",
                    "Verify signal processing chain"
                ]
            )
        
        if not isinstance(received_signal, np.ndarray):
            return ErrorDetails(
                code="RECEIVED_SIGNAL_TYPE_INVALID",
                message="Received signal must be a numpy array",
                category=ErrorCategory.DECODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Convert to numpy array: np.array(received_signal)",
                    "Check signal processing output format",
                    "Ensure proper data type conversion"
                ],
                technical_details=f"Received type: {type(received_signal)}"
            )
        
        if len(received_signal.shape) != 1:
            return ErrorDetails(
                code="RECEIVED_SIGNAL_DIMENSION_INVALID",
                message="Received signal must be 1-dimensional array",
                category=ErrorCategory.DECODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Flatten signal using received_signal.flatten()",
                    "Check signal processing output",
                    "Verify channel simulation format"
                ],
                technical_details=f"Current shape: {received_signal.shape}"
            )
        
        # Check for NaN or infinite values
        if np.any(np.isnan(received_signal)) or np.any(np.isinf(received_signal)):
            return ErrorDetails(
                code="RECEIVED_SIGNAL_INVALID_VALUES",
                message="Received signal contains NaN or infinite values",
                category=ErrorCategory.DECODING,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Check channel simulation parameters",
                    "Verify noise generation process",
                    "Apply signal clipping if necessary"
                ],
                technical_details=f"NaN count: {np.sum(np.isnan(received_signal))}, "
                                f"Inf count: {np.sum(np.isinf(received_signal))}"
            )
        
        return ErrorDetails(
            code="DECODING_FAILED",
            message="Decoding operation failed", 
            category=ErrorCategory.DECODING,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check decoder parameters and initialization",
                "Verify signal-to-noise ratio settings",
                "Ensure sufficient iterations for convergence"
            ],
            technical_details=str(error)
        )
    
    def handle_simulation_error(self, params: Dict[str, Any], error: Exception) -> ErrorDetails:
        """Handle simulation setup and execution errors"""
        
        snr_range = params.get('snr_range', [])
        frames = params.get('frames', 0)
        
        if not snr_range:
            return ErrorDetails(
                code="SNR_RANGE_EMPTY",
                message="SNR range cannot be empty",
                category=ErrorCategory.SIMULATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Provide valid SNR range, e.g., [0, 2, 4, 6, 8]",
                    "Check simulation parameter configuration",
                    "Ensure at least one SNR point"
                ]
            )
        
        if frames <= 0:
            return ErrorDetails(
                code="FRAMES_INVALID",
                message="Number of frames must be positive",
                category=ErrorCategory.SIMULATION,
                severity=ErrorSeverity.ERROR,
                suggestions=[
                    "Set frames to positive integer, e.g., 1000",
                    "Check simulation configuration",
                    "Consider computational resources"
                ],
                technical_details=f"Current frames: {frames}"
            )
        
        if max(snr_range) - min(snr_range) > 30:
            return ErrorDetails(
                code="SNR_RANGE_TOO_WIDE",
                message="SNR range is very wide, may cause numerical issues",
                category=ErrorCategory.SIMULATION,
                severity=ErrorSeverity.WARNING,
                suggestions=[
                    "Consider narrower SNR range for better accuracy",
                    "Split simulation into multiple runs",
                    "Check if extreme SNR values are necessary"
                ],
                technical_details=f"SNR range: {min(snr_range)} to {max(snr_range)} dB"
            )
        
        return ErrorDetails(
            code="SIMULATION_FAILED",
            message="Simulation execution failed",
            category=ErrorCategory.SIMULATION,
            severity=ErrorSeverity.ERROR,
            suggestions=[
                "Check all simulation parameters",
                "Verify system resources availability",
                "Review error logs for specific issues"
            ],
            technical_details=str(error)
        )
    
    def format_error_response(self, error_details: ErrorDetails) -> Dict[str, Any]:
        """Format error details for API response"""
        return {
            "success": False,
            "error": {
                "code": error_details.code,
                "message": error_details.message,
                "category": error_details.category.value,
                "severity": error_details.severity.value,
                "suggestions": error_details.suggestions,
                "technical_details": error_details.technical_details,
                "error_data": error_details.error_data
            }
        }
    
    def log_error(self, error_details: ErrorDetails):
        """Log error with appropriate level"""
        if error_details.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{error_details.code}: {error_details.message}")
        elif error_details.severity == ErrorSeverity.ERROR:
            self.logger.error(f"{error_details.code}: {error_details.message}")
        elif error_details.severity == ErrorSeverity.WARNING:
            self.logger.warning(f"{error_details.code}: {error_details.message}")
        else:
            self.logger.info(f"{error_details.code}: {error_details.message}")

# Global error handler instance
error_handler = LDPCErrorHandler()

def safe_operation(operation_type: str = "general"):
    """Decorator for safe operation execution with error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_details = None
                
                if operation_type == "matrix_validation":
                    matrix = args[0] if args else kwargs.get('matrix')
                    error_details = error_handler.handle_matrix_validation_error(matrix, e)
                elif operation_type == "encoding":
                    info_bits = args[0] if args else kwargs.get('info_bits')
                    error_details = error_handler.handle_encoding_error(info_bits, e)
                elif operation_type == "decoding":
                    received_signal = args[0] if args else kwargs.get('received_signal')
                    error_details = error_handler.handle_decoding_error(received_signal, e)
                elif operation_type == "simulation":
                    params = kwargs
                    error_details = error_handler.handle_simulation_error(params, e)
                else:
                    error_details = ErrorDetails(
                        code="OPERATION_FAILED",
                        message="Operation failed with unknown error",
                        category=ErrorCategory.INPUT_VALIDATION,
                        severity=ErrorSeverity.ERROR,
                        suggestions=["Check operation parameters", "Review error logs"],
                        technical_details=str(e)
                    )
                
                error_handler.log_error(error_details)
                return error_handler.format_error_response(error_details)
                
        return wrapper
    return decorator
