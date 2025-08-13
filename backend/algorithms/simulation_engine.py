"""LDPC Simulation Engine module - integrates encoder and decoder for BER performance simulation."""
from __future__ import annotations

import numpy as np
import time
from typing import Dict, List, Tuple, Callable, Optional, Any
from dataclasses import dataclass

from .ldpc_encoder import LDPCEncoder
from .ldpc_decoder import LDPCDecoder

__all__ = ["SimulationEngine", "SimulationResults", "SimulationConfig"]


@dataclass
class SimulationConfig:
    """Simulation configuration parameters."""
    snr_range: List[float]  # SNR range (dB)
    frame_count: int = 1000  # Number of frames per SNR point
    max_errors: int = 100  # Maximum number of error frames (early stopping criterion)
    min_frames: int = 100  # Minimum number of frames for simulation
    channel_type: str = "awgn"  # Channel type: "awgn", "bsc"
    decoder_algorithm: str = "min_sum"  # Decoding algorithm
    max_iterations: int = 50  # Maximum decoding iterations
    min_sum_scaling: float = 0.9  # Min-Sum scaling factor
    early_termination: bool = True  # Early termination for decoding
    progress_interval: int = 10  # Progress callback interval (number of frames)


@dataclass
class SimulationResults:
    """Simulation result data."""
    snr_db: List[float]  # SNR points (dB)
    ber: List[float]  # Bit Error Rate
    fer: List[float]  # Frame Error Rate
    total_frames: List[int]  # Total frames per SNR point
    error_frames: List[int]  # Error frames per SNR point
    avg_iterations: List[float]  # Average iterations
    simulation_time: float  # Total simulation time (s)
    config: SimulationConfig  # Simulation configuration


class SimulationEngine:
    """LDPC Simulation Engine - performs BER/FER performance simulations."""

    def __init__(self, h_matrix: np.ndarray):
        """
        Initializes the simulation engine.

        Args:
            h_matrix: LDPC parity check matrix
        """
        self.h_matrix = np.asarray(h_matrix, dtype=int)
        
        # Initialize encoder and decoder
        self.encoder = LDPCEncoder(h_matrix)
        self.decoder = LDPCDecoder(h_matrix)
        
        # Code parameters
        self.n = self.decoder.n  # Codeword length
        self.k = self.decoder.k  # Information bits length
        self.rate = self.decoder.rate  # Code rate
        
        # Simulation status
        self.is_running = False
        self.should_stop = False

    def run_ber_simulation(
        self,
        config: SimulationConfig,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> SimulationResults:
        """
        Runs BER/FER performance simulation.

        Args:
            config: Simulation configuration
            progress_callback: Progress callback function

        Returns:
            Simulation results
        """
        self.is_running = True
        self.should_stop = False
        start_time = time.time()

        # Update decoder parameters
        self.decoder.max_iterations = config.max_iterations
        self.decoder.min_sum_scaling = config.min_sum_scaling
        self.decoder.early_termination = config.early_termination

        # Results storage
        snr_results = []
        ber_results = []
        fer_results = []
        total_frames_results = []
        error_frames_results = []
        avg_iterations_results = []

        total_snr_points = len(config.snr_range)

        for snr_idx, snr_db in enumerate(config.snr_range):
            if self.should_stop:
                break

            # Simulate a single SNR point
            snr_result = self._simulate_snr_point(
                snr_db, config, snr_idx, total_snr_points, progress_callback
            )

            snr_results.append(snr_db)
            ber_results.append(snr_result['ber'])
            fer_results.append(snr_result['fer'])
            total_frames_results.append(snr_result['total_frames'])
            error_frames_results.append(snr_result['error_frames'])
            avg_iterations_results.append(snr_result['avg_iterations'])

        simulation_time = time.time() - start_time
        self.is_running = False

        return SimulationResults(
            snr_db=snr_results,
            ber=ber_results,
            fer=fer_results,
            total_frames=total_frames_results,
            error_frames=error_frames_results,
            avg_iterations=avg_iterations_results,
            simulation_time=simulation_time,
            config=config
        )

    def _simulate_snr_point(
        self,
        snr_db: float,
        config: SimulationConfig,
        snr_idx: int,
        total_snr_points: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Simulate a single SNR point."""
        
        # Statistics variables
        total_frames = 0
        error_frames = 0
        total_bit_errors = 0
        total_iterations = 0

        # Noise variance calculation (for AWGN)
        if config.channel_type == "awgn":
            noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
        elif config.channel_type == "bsc":
            # Relationship between crossover probability and SNR for BSC (simplified model)
            crossover_prob = 0.5 * np.exp(-10 ** (snr_db / 10))
            crossover_prob = np.clip(crossover_prob, 1e-6, 0.49)

        while (total_frames < config.frame_count and 
               (error_frames < config.max_errors or total_frames < config.min_frames)):
            
            if self.should_stop:
                break

            # Generate random information bits
            info_bits = np.random.randint(0, 2, self.k)
            
            # Encoding
            try:
                encoded_bits = self.encoder.encode(info_bits)
            except Exception as e:
                print(f"Encoding error: {e}")
                continue

            # Channel transmission
            if config.channel_type == "awgn":
                received_signal, received_bits = self._awgn_channel(
                    encoded_bits, noise_variance
                )
                # Compute LLR
                llr = self.decoder.awgn_llr(received_signal, noise_variance)
            elif config.channel_type == "bsc":
                received_bits = self._bsc_channel(encoded_bits, crossover_prob)
                # Compute LLR
                llr = self.decoder.bsc_llr(received_bits, crossover_prob)
            else:
                raise ValueError(f"Unsupported channel type: {config.channel_type}")

            # Decoding
            try:
                decoded_bits, decode_stats = self.decoder.decode(
                    llr, config.decoder_algorithm
                )
                total_iterations += decode_stats['iterations']
            except Exception as e:
                print(f"Decoding error: {e}")
                continue

            # Extract information bits
            try:
                decoded_info_bits = self.decoder.extract_information_bits(decoded_bits)
            except Exception as e:
                print(f"Information bit extraction error: {e}")
                continue

            # Error statistics
            bit_errors = np.sum(info_bits != decoded_info_bits)
            total_bit_errors += bit_errors
            
            if bit_errors > 0:
                error_frames += 1

            total_frames += 1

            # Progress callback
            if (progress_callback and 
                total_frames % config.progress_interval == 0):
                
                current_ber = total_bit_errors / (total_frames * self.k) if total_frames > 0 else 0
                current_fer = error_frames / total_frames if total_frames > 0 else 0
                
                progress_info = {
                    'snr_idx': snr_idx,
                    'total_snr_points': total_snr_points,
                    'snr_db': snr_db,
                    'frames_completed': total_frames,
                    'total_frames_target': config.frame_count,
                    'error_frames': error_frames,
                    'current_ber': current_ber,
                    'current_fer': current_fer,
                    'avg_iterations': total_iterations / total_frames if total_frames > 0 else 0
                }
                progress_callback(progress_info)

        # Calculate final results
        ber = total_bit_errors / (total_frames * self.k) if total_frames > 0 else 0
        fer = error_frames / total_frames if total_frames > 0 else 0
        avg_iterations = total_iterations / total_frames if total_frames > 0 else 0

        return {
            'ber': ber,
            'fer': fer,
            'total_frames': total_frames,
            'error_frames': error_frames,
            'avg_iterations': avg_iterations
        }

    def _awgn_channel(self, transmitted_bits: np.ndarray, noise_variance: float) -> Tuple[np.ndarray, np.ndarray]:
        """AWGN channel simulation."""
        # BPSK modulation: 0 -> +1, 1 -> -1
        transmitted_signal = 1 - 2 * transmitted_bits.astype(float)
        
        # Add Gaussian noise
        noise = np.random.normal(0, np.sqrt(noise_variance), len(transmitted_signal))
        received_signal = transmitted_signal + noise
        
        # Hard decision (for statistics only)
        received_bits = (received_signal < 0).astype(int)
        
        return received_signal, received_bits

    def _bsc_channel(self, transmitted_bits: np.ndarray, crossover_prob: float) -> np.ndarray:
        """BSC channel simulation."""
        # Generate random flip pattern
        flip_mask = np.random.random(len(transmitted_bits)) < crossover_prob
        received_bits = transmitted_bits ^ flip_mask.astype(int)
        return received_bits

    def stop_simulation(self):
        """Stop simulation."""
        self.should_stop = True

    def get_code_info(self) -> Dict[str, Any]:
        """Get code information."""
        return {
            'n': self.n,
            'k': self.k,
            'm': self.decoder.m,
            'rate': self.rate,
            'variable_degrees': [len(self.decoder.var_to_check[i]) for i in range(self.n)],
            'check_degrees': [len(self.decoder.check_to_var[i]) for i in range(self.decoder.m)]
        }

    def estimate_simulation_time(self, config: SimulationConfig) -> float:
        """Estimate simulation time (seconds)."""
        # Estimate based on empirical formula
        frames_per_snr = config.frame_count
        snr_points = len(config.snr_range)
        
        # Assume average processing time per frame (milliseconds)
        time_per_frame_ms = 0.1 + (self.n * config.max_iterations * 0.001)
        
        total_time_seconds = (frames_per_snr * snr_points * time_per_frame_ms) / 1000
        
        return total_time_seconds

    def run_quick_test(self, snr_db: float, frames: int = 100) -> Dict[str, Any]:
        """Quick test for a single SNR point."""
        config = SimulationConfig(
            snr_range=[snr_db],
            frame_count=frames,
            max_errors=frames,  # Do not stop early
            min_frames=frames
        )
        
        results = self.run_ber_simulation(config)
        
        if len(results.ber) > 0:
            return {
                'snr_db': snr_db,
                'ber': results.ber[0],
                'fer': results.fer[0],
                'frames': results.total_frames[0],
                'avg_iterations': results.avg_iterations[0],
                'simulation_time': results.simulation_time
            }
        else:
            return {
                'snr_db': snr_db,
                'ber': 0,
                'fer': 0,
                'frames': 0,
                'avg_iterations': 0,
                'simulation_time': results.simulation_time
            }

    def run_simulation(self, config: SimulationConfig) -> Dict[str, Any]:
        """Run simulation and return results as a dictionary (for API)."""
        results = self.run_ber_simulation(config)
        
        return {
            'snr_db': results.snr_db,
            'ber': results.ber,
            'fer': results.fer,
            'frames_simulated': results.total_frames,
            'error_frames': results.error_frames,
            'iterations': results.avg_iterations,
            'simulation_time': results.simulation_time,
            'config': {
                'snr_range': config.snr_range,
                'frame_count': config.frame_count,
                'algorithm': config.decoder_algorithm,
                'channel_type': config.channel_type,
                'max_iterations': config.max_iterations
            }
        }


# Helper functions
def create_snr_range(start: float, stop: float, step: float) -> List[float]:
    """Create SNR range."""
    return list(np.arange(start, stop + step/2, step))


def format_simulation_summary(results: SimulationResults) -> str:
    """Format simulation result summary."""
    summary = f"LDPC Simulation Results Summary\n"
    summary += f"{'='*50}\n"
    summary += f"Code parameters: n={results.config.snr_range}, k={len(results.snr_db)}\n"
    summary += f"Frame count: {results.config.frame_count}\n"
    summary += f"Channel type: {results.config.channel_type}\n"
    summary += f"Decoding algorithm: {results.config.decoder_algorithm}\n"
    summary += f"Simulation time: {results.simulation_time:.2f} s\n\n"

    summary += f"{'SNR(dB)':<8} {'BER':<12} {'FER':<12} {'Frames':<8} {'Iterations':<10}\n"
    summary += f"{'-'*50}\n"
    
    for i in range(len(results.snr_db)):
        summary += f"{results.snr_db[i]:<8.1f} "
        summary += f"{results.ber[i]:<12.2e} "
        summary += f"{results.fer[i]:<12.2e} "
        summary += f"{results.total_frames[i]:<8d} "
        summary += f"{results.avg_iterations[i]:<8.1f}\n"
    
    return summary


if __name__ == '__main__':
    # Example: create a simple LDPC code and run simulation
    from models.ldpc_code_tools import make_ldpc_from_alist
    
    # Create H matrix from alist file
    alist_file = "path/to/your/code.alist"  # Replace with your alist file path
    try:
        H, _ = make_ldpc_from_alist(alist_file)
    except FileNotFoundError:
        print("Alist file not found. Using a simple parity check matrix for demonstration.")
        H = np.array([[1, 1, 1, 0, 0, 0],
                      [0, 0, 1, 1, 1, 0],
                      [1, 0, 0, 0, 1, 1]], dtype=int)

    # Create simulation engine
    engine = SimulationEngine(H)
    
    # Configure simulation
    snr_range = create_snr_range(0, 4, 0.5)
    config = SimulationConfig(
        snr_range=snr_range,
        frame_count=1000,
        max_errors=100,
        decoder_algorithm="min_sum"
    )
    
    # Run simulation
    results = engine.run_ber_simulation(config)
    
    # Print results
    print(format_simulation_summary(results))
    
    # Quick test
    quick_test_results = engine.run_quick_test(snr_db=3.0, frames=200)
    print("\nQuick Test Results:")
    print(quick_test_results)