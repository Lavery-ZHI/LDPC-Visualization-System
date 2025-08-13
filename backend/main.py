from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import numpy as np
import asyncio
from typing import Dict, List, Any

# Enhanced imports for new functionality
from utils.matrix_templates import LDPCMatrixTemplates
from utils.error_handler import error_handler, safe_operation
from utils.performance_utils import performance_monitor, monitor_performance

from models.pydantic_models import (
    EncodeRequest, EncodeResponse, DecodeRequest, DecodeResponse,
    SimulationRequest, SimulationResponse, GraphSimulationRequest, 
    OptimizeRequest, OptimizeResponse, OptimizeStatusResponse
)
from algorithms.ldpc_encoder import LDPCEncoder
from algorithms.ldpc_decoder import LDPCDecoder
from algorithms.simulation_engine import SimulationEngine, SimulationConfig
from models.ldpc_models import LDPCCode


app = FastAPI(
    title="LDPC SYSTEM API",
    description="FastAPI-based LDPC encoding, simulation and optimization backend service",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Basic Info"])
def read_root():
    return {
        "message": "LDPC visualization system API service running",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.get("/api/status", tags=["Basic Info"])
def check_status():
    return {
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/api/matrix-templates", tags=["LDPC Matrix Templates"])
async def get_matrix_templates():
    """Get list of available LDPC matrix templates"""
    try:
        templates = LDPCMatrixTemplates.get_available_templates()
        return {
            "success": True,
            "message": "Matrix templates retrieved successfully",
            "templates": templates
        }
    except Exception as e:
        error_details = error_handler.handle_simulation_error({}, e)
        error_handler.log_error(error_details)
        return error_handler.format_error_response(error_details)

@app.post("/api/generate-template", tags=["LDPC Matrix Templates"])
async def generate_matrix_template(template_name: str):
    """Generate H matrix from template"""
    try:
        h_matrix = LDPCMatrixTemplates.get_template_by_name(template_name)
        
        if h_matrix is None:
            raise HTTPException(
                status_code=400, 
                detail=f"Template '{template_name}' not found or generation failed"
            )
        
        # Validate the generated matrix
        validation_result = LDPCMatrixTemplates.validate_template(h_matrix)
        
        if not validation_result.get('valid', False):
            raise HTTPException(
                status_code=500,
                detail=f"Generated matrix validation failed: {validation_result.get('error')}"
            )
        
        return {
            "success": True,
            "message": f"Matrix template '{template_name}' generated successfully",
            "h_matrix": h_matrix.tolist(),
            "validation": validation_result,
            "template_name": template_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_details = error_handler.handle_matrix_validation_error(None, e)
        error_handler.log_error(error_details)
        raise HTTPException(status_code=500, detail=error_details.message)

@app.get("/api/performance-metrics", tags=["Performance Monitoring"])
async def get_performance_metrics():
    """Get system performance metrics"""
    try:
        metrics = performance_monitor.get_performance_summary()
        return {
            "success": True,
            "message": "Performance metrics retrieved successfully",
            "metrics": metrics
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to retrieve performance metrics",
            "error": str(e)
        }

@app.get("/api/generate-from-graph", tags=["LDPC Generation"])
@app.post("/api/generate-from-graph", tags=["LDPC Generation"])
@safe_operation("matrix_validation")
async def generate_ldpc_from_graph(template_name: str = "simple_6_3"):
    """
    Enhanced LDPC code generation with template support
    Returns H matrix, G matrix, and validation information
    """
    try:
        # Use template-based generation
        h_matrix = LDPCMatrixTemplates.get_template_by_name(template_name)
        
        if h_matrix is None:
            # Fallback to simple default matrix
            h_matrix = np.array([
                [1, 1, 1, 0, 0, 0],
                [0, 1, 1, 1, 0, 0],
                [0, 0, 1, 1, 1, 1]
            ], dtype=np.uint8)
        
        # Validate matrix
        validation_result = LDPCMatrixTemplates.validate_template(h_matrix)
        
        if not validation_result.get('valid', False):
            raise Exception(f"Matrix validation failed: {validation_result.get('error')}")
        
        encoder = LDPCEncoder(h_matrix)
        
        # Calculate G matrix (if possible)
        g_matrix = None
        try:
            g_matrix = encoder.get_generator_matrix()
        except Exception as e:
            # Log warning but continue
            print(f"Warning: Could not generate G matrix: {e}")
        
        return {
            "success": True,
            "message": "LDPC code generated successfully",
            "h_matrix": h_matrix.tolist(),
            "g_matrix": g_matrix.tolist() if g_matrix is not None else None,
            "validation": validation_result,
            "template_used": template_name,
            "parameters": {
                "code_length": validation_result['n'],
                "info_length": validation_result['k'],
                "parity_length": validation_result['m'],
                "code_rate": validation_result['rate']
            }
        }
        
    except Exception as e:
        error_details = error_handler.handle_matrix_validation_error(h_matrix if 'h_matrix' in locals() else None, e)
        error_handler.log_error(error_details)
        return error_handler.format_error_response(error_details)

@app.post("/api/simulate-from-graph", tags=["LDPC Simulation"])
async def simulate_from_graph(graph_data: dict = None):
    """
    Run LDPC simulation from graph structure
    """
    try:
        # Use default LDPC code for simulation
        h_matrix = np.array([
            [1, 1, 1, 0, 0, 0],
            [0, 1, 1, 1, 0, 0],
            [0, 0, 1, 1, 1, 1]
        ], dtype=int)
        
        # Run quick simulation
        encoder = LDPCEncoder(h_matrix)
        decoder = LDPCDecoder(h_matrix)
        
        # Generate random information bits
        info_bits = np.random.randint(0, 2, size=3)
        codeword = encoder.encode(info_bits)
        
        # Add noise (simple BSC model)
        error_prob = 0.1
        received = codeword.copy()
        errors = np.random.random(len(codeword)) < error_prob
        received[errors] = 1 - received[errors]
        
        # Decode
        decoded_bits, stats = decoder.decode(received, algorithm='min-sum')
        
        # Calculate BER
        bit_errors = np.sum(decoded_bits != info_bits)
        ber = bit_errors / len(info_bits)
        
        return {
            "simulation_results": {
                "message": "Graph simulation completed",
                "ber": ber,
                "info_bits": info_bits.tolist(),
                "decoded_bits": decoded_bits.tolist(),
                "iterations": stats.get('iterations', 0),
                "converged": stats.get('converged', False)
            }
        }
        
    except Exception as e:
        return {
            "simulation_results": {
                "message": f"Simulation failed: {str(e)}",
                "ber": "N/A"
            }
        }


@app.post("/api/v1/encode", response_model=EncodeResponse, tags=["Encoding"])
async def encode_ldpc(request: EncodeRequest):
    """
    Generate LDPC code from input and return encoding results

    Supports two input modes:
    - Mode 1: Describe LDPC code through graph data (nodes, edges)
    - Mode 2: Directly provide H matrix and optional information bits

    Returns:
    - H matrix, G matrix and code rate information
    - If information bits are provided, also returns encoded codeword
    """
    try:
        # Determine input mode
        if request.h_matrix is not None:
            # Mode 2: Directly provide H matrix
            h_matrix = np.array(request.h_matrix, dtype=int)
            encoder = LDPCEncoder(h_matrix)
        else:
            # Mode 1: Through graph data
            if not request.nodes or not request.edges:
                raise ValueError("nodes and edges must be provided when using graph mode")

            # Convert graph data to H matrix
            nodes = [node.dict() for node in request.nodes]
            edges = [edge.dict() for edge in request.edges]
            ldpc_code = LDPCCode.from_graph_data(nodes, edges)

            # Create encoder
            encoder = LDPCEncoder(ldpc_code.H)

        # Generate G matrix
        g_matrix = encoder.generate_g_matrix()

        # Get matrix and code parameters
        matrices = encoder.get_matrices()

        # If information bits are provided, encode to generate codeword
        codeword = None
        if request.info_bits is not None:
            if len(request.info_bits) != encoder.k:
                raise ValueError(f"Information bits length should be {encoder.k}, but received length {len(request.info_bits)}")
            codeword = encoder.encode(request.info_bits).tolist()

        # Build response
        return EncodeResponse(
            h_matrix=matrices["h_matrix"],
            g_matrix=matrices["g_matrix"],
            code_rate=float(encoder.rate),
            n=int(encoder.n),
            k=int(encoder.k),
            m=int(encoder.m),
            codeword=codeword,
            message="LDPC code generated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Encoding failed: {str(e)}")

# Decoding interface
@app.post("/api/v1/decode", response_model=DecodeResponse, tags=["Decoding"])
async def decode_ldpc(request: DecodeRequest):
    """
    LDPC code decoding interface

    Supports multiple input modes:
    - Mode 1: Directly provide LLR (Log Likelihood Ratio)
    - Mode 2: Provide received signal + AWGN channel parameters
    - Mode 3: Provide received bits + BSC channel parameters

    Returns:
    - Decoded codeword and information bits
    - Decoding statistics and performance metrics
    """
    try:
        # Create H matrix
        h_matrix = np.array(request.h_matrix, dtype=int)
        
        # Create decoder
        decoder = LDPCDecoder(
            h_matrix,
            max_iterations=request.max_iterations,
            early_termination=request.early_termination,
            min_sum_scaling=request.min_sum_scaling
        )
        
        # Calculate LLR
        if request.llr is not None:
            # Mode 1: Directly use provided LLR
            llr = np.array(request.llr, dtype=float)
        elif request.received_signal is not None:
            # Mode 2: AWGN channel - can use noise_variance or snr_db
            if request.channel_type != "awgn":
                raise ValueError("Channel type must be 'awgn' when using received_signal")

            # If noise_variance not provided, calculate from snr_db
            noise_var = request.noise_variance
            if noise_var is None:
                if request.snr_db is None:
                    raise ValueError("AWGN channel requires either noise_variance or snr_db")
                snr_lin = 10 ** (request.snr_db / 10)
                # σ² = 1 / (2 * SNR) (BPSK, unit energy)
                noise_var = 1.0 / (2.0 * snr_lin)

            received_signal = np.array(request.received_signal, dtype=float)
            llr = decoder.awgn_llr(received_signal, noise_var)
        elif request.received_bits is not None:
            # Mode 3: BSC channel
            if request.channel_type != "bsc":
                raise ValueError("Channel type must be 'bsc' when using received_bits")
            if request.crossover_probability is None:
                raise ValueError("BSC channel requires crossover_probability")
            received_bits = np.array(request.received_bits, dtype=int)
            llr = decoder.bsc_llr(received_bits, request.crossover_probability)
        else:
            raise ValueError("Must provide one of: llr, received_signal, or received_bits")
        
        # Validate LLR length
        if len(llr) != decoder.n:
            raise ValueError(f"LLR length {len(llr)} does not match code length {decoder.n}")
        
        # Perform decoding
        decoded_bits, stats = decoder.decode(llr, algorithm=request.algorithm)
        
        # Extract information bits
        information_bits = decoder.extract_information_bits(decoded_bits)
        
        # Get code parameters
        code_parameters = {
            "n": decoder.n,
            "k": decoder.k,
            "m": decoder.m,
            "rate": decoder.rate
        }
        
        # Build response
        return DecodeResponse(
            decoded_bits=decoded_bits.tolist(),
            information_bits=information_bits.tolist(),
            statistics=stats,
            h_matrix=h_matrix.tolist(),
            code_parameters=code_parameters,
            message="LDPC decoding successful"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decoding failed: {str(e)}")

# TODO: Add other API routes:
# - POST /api/simulate
# - POST /api/simulate-from-graph
# - POST /api/optimize
# - GET /api/optimize/{optimization_id}
# - WebSocket /ws/simulate/{session_id}
# - WebSocket /ws/optimize/{session_id}

@app.post("/api/simulate", response_model=SimulationResponse, tags=["Simulation"])
async def run_simulation(request: SimulationRequest):
    """Run LDPC BER simulation"""
    try:
        # Validate parity check matrix
        h_matrix = np.array(request.h_matrix, dtype=int)
        if h_matrix.size == 0:
            raise ValueError("Parity check matrix cannot be empty")
        
        # Create simulation engine
        engine = SimulationEngine(h_matrix)
        
        # Configure simulation parameters
        config = SimulationConfig(
            snr_range=request.snr_range,
            frame_count=request.frames_per_snr,
            channel_type=request.channel_type.lower(),
            max_iterations=request.max_iterations,
            decoder_algorithm=request.algorithm.lower() if hasattr(request, 'algorithm') else 'min_sum'
        )
        
        # Run simulation
        results = engine.run_simulation(config)
        
        return {
            "simulation_results": results,
            "message": "Simulation completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Simulation failed: {str(e)}")

@app.post("/api/quick-test", tags=["Quick Test"])
@safe_operation("simulation")
@monitor_performance
async def api_quick_test(request_data: dict):
    """
    Enhanced quick test API endpoint - Single SNR point rapid testing
    
    Features:
    - Input validation with detailed error messages
    - Performance monitoring
    - Enhanced error handling
    - Memory optimization for large matrices
    
    Parameters:
    - h_matrix: Parity check matrix (required)
    - snr_db: Single SNR value in dB (default: 2.0)
    - frames: Number of frames, max 50 for quick test (default: 10)
    - algorithm: Decoding algorithm - 'min_sum' or 'sum_product' (default: 'min_sum')
    - channel: Channel type - 'awgn' or 'bsc' (default: 'awgn')
    """
    try:
        # Enhanced parameter extraction with validation
        h_matrix_data = request_data.get('h_matrix')
        snr_db = request_data.get('snr_db', 2.0)
        frames = min(request_data.get('frames', 10), 50)  # Limit for quick test
        algorithm = request_data.get('algorithm', 'min_sum')
        channel = request_data.get('channel', 'awgn')
        
        # Validate inputs
        if h_matrix_data is None:
            raise ValueError("H matrix is required for quick test")
            
        if not isinstance(snr_db, (int, float)) or snr_db < -20 or snr_db > 30:
            raise ValueError("SNR must be between -20 and 30 dB")
            
        if algorithm not in ['min_sum', 'sum_product']:
            raise ValueError("Algorithm must be 'min_sum' or 'sum_product'")
            
        if channel not in ['awgn', 'bsc']:
            raise ValueError("Channel must be 'awgn' or 'bsc'")
        
        # Convert and validate H matrix
        h_matrix = np.array(h_matrix_data, dtype=np.uint8)
        
        # Validate matrix using enhanced error handler
        validation_result = LDPCMatrixTemplates.validate_template(h_matrix)
        if not validation_result.get('valid', False):
            raise ValueError(f"Invalid H matrix: {validation_result.get('error', 'Unknown validation error')}")
        
        print(f"Quick test started - Matrix: {h_matrix.shape}, SNR: {snr_db}dB, Frames: {frames}")
        
        # Create encoder and decoder with error handling
        encoder = LDPCEncoder(h_matrix)
        decoder = LDPCDecoder(h_matrix, max_iterations=50)  # Lower iterations for quick test
        
        # Run simulation using existing engine
        config = SimulationConfig(
            snr_range=[snr_db],
            frames_per_snr=frames,
            channel_type=channel,
            algorithm=algorithm,
            max_iterations=50
        )
        
        engine = SimulationEngine(encoder, decoder, config)
        
        # Get single SNR result
        results = engine.run_ber_simulation()
        snr_result = results['ber_data'][0]  # First (and only) SNR point
        
        # Enhanced response with detailed metrics
        response = {
            "success": True,
            "message": "Quick test completed successfully",
            "test_parameters": {
                "h_matrix_shape": h_matrix.shape,
                "snr_db": snr_db,
                "frames_tested": frames,
                "algorithm": algorithm,
                "channel": channel,
                "code_parameters": {
                    "n": validation_result['n'],
                    "k": validation_result['k'], 
                    "m": validation_result['m'],
                    "rate": validation_result['rate']
                }
            },
            "results": {
                "ber": snr_result['ber'],
                "bit_errors": snr_result['bit_errors'],
                "total_bits": snr_result['total_bits'],
                "frame_error_rate": snr_result.get('fer', 0.0),
                "average_iterations": snr_result.get('avg_iterations', 0),
                "convergence_rate": (frames - snr_result.get('error_frames', 0)) / frames
            },
            "matrix_validation": validation_result,
            "performance_notes": [
                f"Test completed in {frames} frames",
                f"Matrix density: {np.mean(h_matrix):.1%}",
                f"Decoder converged in avg {snr_result.get('avg_iterations', 0):.1f} iterations"
            ]
        }
        
        return response
        
    except ValueError as ve:
        error_details = error_handler.handle_simulation_error(request_data, ve)
        error_handler.log_error(error_details)
        return error_handler.format_error_response(error_details)

@app.post("/api/simulate", tags=["Full Simulation"])
@safe_operation("simulation")
@monitor_performance
async def api_simulate(request_data: dict):
    """API endpoint: Run complete BER simulation"""
    try:
        # Extract parameters
        h_matrix_data = request_data.get('h_matrix')
        snr_range = request_data.get('snr_range', [0.0, 2.0, 4.0])
        frames_per_point = request_data.get('frames_per_point', 1000)
        algorithm = request_data.get('algorithm', 'min_sum')
        channel = request_data.get('channel', 'awgn')
        max_iterations = request_data.get('max_iterations', 100)
        target_errors = request_data.get('target_errors', 100)
        
        # Validate H matrix
        if h_matrix_data is None:
            raise ValueError("Missing H matrix data")
            
        h_matrix = np.array(h_matrix_data, dtype=int)
        print(f"Simulation using H matrix: shape={h_matrix.shape}")
        
        engine = SimulationEngine(h_matrix)
        
        config = SimulationConfig(
            snr_range=snr_range,
            frame_count=frames_per_point,
            decoder_algorithm=algorithm,
            channel_type=channel,
            max_iterations=max_iterations,
            max_errors=int(target_errors)
        )
        
        result = engine.run_simulation(config)
        
        return {
            "simulation_results": result,
            "message": "Simulation completed"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Simulation error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Simulation API failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)
