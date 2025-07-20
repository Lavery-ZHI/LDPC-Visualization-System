"""
Performance optimization utilities for LDPC system
Provides tools for monitoring, profiling and optimizing simulation performance.
"""

import time
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Performance monitoring will be limited.")

import numpy as np
from typing import Dict, List, Callable, Any, Optional
from functools import wraps
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Container for performance measurement results"""
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: Optional[float] = None
    error_count: int = 0

class PerformanceMonitor:
    """Monitor and optimize LDPC simulation performance"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.logger = logging.getLogger(__name__)
        
    def measure_performance(self, func: Callable) -> Callable:
        """Decorator to measure function performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start measurements
            start_time = time.perf_counter()
            
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                start_memory = process.memory_info().rss / 1024 / 1024  # MB
                start_cpu = psutil.cpu_percent()
            else:
                start_memory = 0
                start_cpu = 0
            
            try:
                result = func(*args, **kwargs)
                error_count = 0
            except Exception as e:
                self.logger.error(f"Function {func.__name__} failed: {e}")
                error_count = 1
                raise
            finally:
                # End measurements
                end_time = time.perf_counter()
                
                if PSUTIL_AVAILABLE:
                    end_memory = process.memory_info().rss / 1024 / 1024  # MB
                    end_cpu = psutil.cpu_percent()
                    memory_usage = end_memory - start_memory
                    cpu_usage = (start_cpu + end_cpu) / 2
                else:
                    memory_usage = 0
                    cpu_usage = 0
                
                metrics = PerformanceMetrics(
                    execution_time=end_time - start_time,
                    memory_usage_mb=memory_usage,
                    cpu_usage_percent=cpu_usage,
                    error_count=error_count
                )
                
                self.metrics_history.append(metrics)
                
                self.logger.info(f"Performance - {func.__name__}: "
                               f"Time={metrics.execution_time:.3f}s, "
                               f"Memory={metrics.memory_usage_mb:.1f}MB, "
                               f"CPU={metrics.cpu_usage_percent:.1f}%")
                
            return result
        return wrapper
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        if not self.metrics_history:
            return {"message": "No performance data available"}
            
        times = [m.execution_time for m in self.metrics_history]
        memories = [m.memory_usage_mb for m in self.metrics_history]
        cpu_usages = [m.cpu_usage_percent for m in self.metrics_history]
        
        return {
            "total_runs": len(self.metrics_history),
            "average_time": np.mean(times),
            "min_time": np.min(times),
            "max_time": np.max(times),
            "average_memory_mb": np.mean(memories),
            "peak_memory_mb": np.max(memories),
            "average_cpu_percent": np.mean(cpu_usages),
            "total_errors": sum(m.error_count for m in self.metrics_history)
        }

class SimulationOptimizer:
    """Optimize LDPC simulation parameters for better performance"""
    
    @staticmethod
    def optimize_batch_size(total_frames: int, available_memory_gb: float = None) -> int:
        """Calculate optimal batch size based on available memory"""
        if available_memory_gb is None:
            if PSUTIL_AVAILABLE:
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
            else:
                available_memory_gb = 4.0  # Default conservative estimate
        
        # Conservative estimate: 1GB can handle ~10000 frames
        max_batch_from_memory = int(available_memory_gb * 10000)
        
        # Also consider CPU cores
        cpu_cores = mp.cpu_count()
        max_batch_from_cpu = cpu_cores * 1000
        
        # Choose conservative estimate
        optimal_batch = min(max_batch_from_memory, max_batch_from_cpu, total_frames)
        
        # Ensure minimum batch size
        return max(optimal_batch, 100)
    
    @staticmethod
    def should_use_parallel(matrix_size: tuple, frame_count: int) -> bool:
        """Determine if parallel processing would be beneficial"""
        n, k = matrix_size
        
        # Use parallel for large matrices or many frames
        if n > 1000 or frame_count > 1000:
            return True
        
        # Check if we have enough CPU cores
        if mp.cpu_count() >= 4:
            return True
            
        return False
    
    @staticmethod
    def get_optimal_thread_count() -> int:
        """Get optimal number of threads for current system"""
        cpu_cores = mp.cpu_count()
        
        # Leave some cores for system operations
        if cpu_cores >= 8:
            return cpu_cores - 2
        elif cpu_cores >= 4:
            return cpu_cores - 1
        else:
            return cpu_cores

class ParallelSimulationRunner:
    """Run LDPC simulations in parallel for better performance"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or SimulationOptimizer.get_optimal_thread_count()
        
    def run_parallel_ber_simulation(self, 
                                  simulation_func: Callable,
                                  snr_points: List[float],
                                  frames_per_point: int,
                                  **kwargs) -> Dict[str, Any]:
        """Run BER simulation with parallel processing"""
        
        # Split work across processes
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for snr in snr_points:
                future = executor.submit(
                    simulation_func,
                    snr_db=snr,
                    frames=frames_per_point,
                    **kwargs
                )
                futures.append((snr, future))
            
            # Collect results
            results = {}
            for snr, future in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results[snr] = result
                except Exception as e:
                    logging.error(f"Simulation failed for SNR {snr}: {e}")
                    results[snr] = {"error": str(e)}
                    
        return results

class MemoryOptimizer:
    """Optimize memory usage in LDPC simulations"""
    
    @staticmethod
    def use_sparse_matrices() -> bool:
        """Determine if sparse matrices should be used based on system memory"""
        if PSUTIL_AVAILABLE:
            available_gb = psutil.virtual_memory().available / (1024**3)
            return available_gb < 4.0  # Use sparse if less than 4GB available
        else:
            return True  # Conservative default when psutil unavailable
    
    @staticmethod
    def estimate_memory_usage(n: int, k: int, frames: int, use_sparse: bool = False) -> float:
        """Estimate memory usage in MB for given parameters"""
        
        # H matrix memory
        if use_sparse:
            # Assume ~10% density for sparse representation
            h_memory = (n - k) * n * 0.1 * 8 / (1024 * 1024)  # bytes to MB
        else:
            h_memory = (n - k) * n * 8 / (1024 * 1024)  # bytes to MB
        
        # Signal processing memory (LLR, received signals, etc.)
        signal_memory = frames * n * 8 * 4 / (1024 * 1024)  # 4 copies of signals
        
        # Decoder state memory
        decoder_memory = n * (n - k) * 8 * 2 / (1024 * 1024)  # message passing
        
        total_mb = h_memory + signal_memory + decoder_memory
        
        return total_mb
    
    @staticmethod
    def suggest_optimization(n: int, k: int, frames: int) -> Dict[str, Any]:
        """Suggest memory optimizations for given parameters"""
        
        dense_memory = MemoryOptimizer.estimate_memory_usage(n, k, frames, False)
        sparse_memory = MemoryOptimizer.estimate_memory_usage(n, k, frames, True)
        
        if PSUTIL_AVAILABLE:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
        else:
            available_mb = 4096  # Conservative 4GB default
        
        suggestions = []
        
        if dense_memory > available_mb * 0.8:
            suggestions.append("Use sparse matrix representation")
            
        if frames > 10000:
            optimal_batch = SimulationOptimizer.optimize_batch_size(frames)
            suggestions.append(f"Process in batches of {optimal_batch} frames")
            
        if n > 5000:
            suggestions.append("Consider using lower precision (float32 instead of float64)")
            
        return {
            "estimated_memory_dense_mb": float(dense_memory),
            "estimated_memory_sparse_mb": float(sparse_memory),
            "available_memory_mb": float(available_mb),
            "memory_sufficient": dense_memory < available_mb * 0.8,
            "suggestions": suggestions
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorators for easy use
def monitor_performance(func):
    """Decorator to monitor function performance"""
    return performance_monitor.measure_performance(func)

def optimize_for_performance(func):
    """Decorator that applies common performance optimizations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Auto-optimize based on parameters
        if 'frames' in kwargs and kwargs['frames'] > 5000:
            # Suggest batch processing for large frame counts
            logging.info("Large frame count detected - consider batch processing")
            
        if 'h_matrix' in kwargs:
            h_matrix = kwargs['h_matrix']
            if hasattr(h_matrix, 'shape'):
                n, m = h_matrix.shape[1], h_matrix.shape[0]
                memory_info = MemoryOptimizer.suggest_optimization(n, n-m, kwargs.get('frames', 1000))
                
                if not memory_info['memory_sufficient']:
                    logging.warning("Insufficient memory detected. Suggestions: " + 
                                   ", ".join(memory_info['suggestions']))
        
        return func(*args, **kwargs)
    
    return wrapper
