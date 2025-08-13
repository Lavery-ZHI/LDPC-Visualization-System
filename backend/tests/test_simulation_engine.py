"""Test simulation engine functionality."""
import numpy as np
import sys
import os

# Add path to import modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from algorithms.simulation_engine import SimulationEngine, SimulationConfig, create_snr_range


def test_simulation_engine():
    """Test basic simulation engine functionality."""
    print("Testing LDPC simulation engine...")
    
    # Create a simple LDPC parity check matrix (7,4) Hamming code
    H = np.array([
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [0, 1, 1, 1, 0, 0, 1]
    ], dtype=int)
    
    print(f"Using parity check matrix H (shape: {H.shape})")
    
    # Initialize simulation engine
    try:
        engine = SimulationEngine(H)
        print(f"✓ Simulation engine initialized successfully")
        
        # Get code information
        code_info = engine.get_code_info()
        print(f"✓ Code parameters: n={code_info['n']}, k={code_info['k']}, rate={code_info['rate']:.3f}")
        
    except Exception as e:
        print(f"✗ Simulation engine initialization failed: {e}")
        return False
    
    # Quick test
    print("\nExecuting quick test...")
    try:
        test_result = engine.run_quick_test(snr_db=2.0, frames=50)
        print(f"✓ Quick test completed:")
        print(f"  SNR: {test_result['snr_db']} dB")
        print(f"  BER: {test_result['ber']:.2e}")
        print(f"  FER: {test_result['fer']:.2e}")
        print(f"  Simulation time: {test_result['simulation_time']:.3f} seconds")
        print(f"  Average iterations: {test_result['avg_iterations']:.1f}")
        
    except Exception as e:
        print(f"✗ Quick test failed: {e}")
        return False
    
    # Complete simulation test
    print("\nExecuting complete simulation test...")
    
    # Create simulation configuration
    config = SimulationConfig(
        snr_range=create_snr_range(0.0, 4.0, 1.0),  # 0, 1, 2, 3, 4 dB
        frame_count=100,
        max_errors=50,
        min_frames=50,
        channel_type="awgn",
        decoder_algorithm="min_sum",
        progress_interval=25
    )
    
    print(f"SNR range: {config.snr_range} dB")
    print(f"Frames per point: {config.frame_count}")
    
    # Progress callback function
    def progress_callback(info):
        print(f"  Progress: SNR {info['snr_db']:.1f} dB, "
              f"frames {info['frames_completed']}/{info['total_frames_target']}, "
              f"current BER: {info['current_ber']:.2e}")
    
    try:
        # Estimate simulation time
        estimated_time = engine.estimate_simulation_time(config)
        print(f"Estimated simulation time: {estimated_time:.1f} seconds")
        
        # Run simulation
        results = engine.run_ber_simulation(config, progress_callback)
        
        print(f"✓ Simulation completed! Total time: {results.simulation_time:.2f} seconds")
        print(f"\nResults summary:")
        print(f"{'SNR(dB)':<8} {'BER':<12} {'FER':<12} {'Frames':<8}")
        print("-" * 40)
        
        for i in range(len(results.snr_db)):
            print(f"{results.snr_db[i]:<8.1f} "
                  f"{results.ber[i]:<12.2e} "
                  f"{results.fer[i]:<12.2e} "
                  f"{results.total_frames[i]:<8d}")
        
        return True
        
    except Exception as e:
        print(f"✗ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bsc_channel():
    """Test BSC channel."""
    print("\n\nTesting BSC channel...")
    
    # Create parity check matrix
    H = np.array([
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [0, 1, 1, 1, 0, 0, 1]
    ], dtype=int)
    
    engine = SimulationEngine(H)
    
    # BSC simulation configuration
    config = SimulationConfig(
        snr_range=[5.0, 10.0],  # For BSC, SNR used to calculate crossover probability
        frame_count=100,
        channel_type="bsc",
        decoder_algorithm="sum_product",  # Test Sum-Product algorithm
        progress_interval=50
    )
    
    def progress_callback(info):
        print(f"  BSC progress: SNR {info['snr_db']:.1f} dB, "
              f"BER: {info['current_ber']:.2e}")
    
    try:
        results = engine.run_ber_simulation(config, progress_callback)
        print(f"✓ BSC simulation completed!")
        
        for i in range(len(results.snr_db)):
            print(f"SNR {results.snr_db[i]:.1f} dB: "
                  f"BER={results.ber[i]:.2e}, "
                  f"FER={results.fer[i]:.2e}")
        
        return True
        
    except Exception as e:
        print(f"✗ BSC simulation failed: {e}")
        return False


if __name__ == "__main__":
    print("LDPC Simulation Engine Test")
    print("=" * 50)
    
    # Test basic functionality
    success1 = test_simulation_engine()
    
    # Test BSC channel
    success2 = test_bsc_channel()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
