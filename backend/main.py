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
    description="基于FastAPI的LDPC编码、仿真和优化后端服务",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["基本信息"])
def read_root():
    return {
        "message": "LDPC可视化系统API服务运行中",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.get("/api/status", tags=["基本信息"])
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

@app.get("/api/generate-from-graph", tags=["LDPC生成"])
@app.post("/api/generate-from-graph", tags=["LDPC生成"])
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

@app.post("/api/simulate-from-graph", tags=["LDPC仿真"])
async def simulate_from_graph(graph_data: dict = None):
    """
    从图结构运行LDPC仿真
    """
    try:
        # 使用默认的LDPC码进行仿真
        h_matrix = np.array([
            [1, 1, 1, 0, 0, 0],
            [0, 1, 1, 1, 0, 0],
            [0, 0, 1, 1, 1, 1]
        ], dtype=int)
        
        # 运行快速仿真
        encoder = LDPCEncoder(h_matrix)
        decoder = LDPCDecoder(h_matrix)
        
        # 生成随机信息位
        info_bits = np.random.randint(0, 2, size=3)
        codeword = encoder.encode(info_bits)
        
        # 添加噪声（简单的BSC模型）
        error_prob = 0.1
        received = codeword.copy()
        errors = np.random.random(len(codeword)) < error_prob
        received[errors] = 1 - received[errors]
        
        # 解码
        decoded_bits, stats = decoder.decode(received, algorithm='min-sum')
        
        # 计算BER
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


@app.post("/api/v1/encode", response_model=EncodeResponse, tags=["编码"])
async def encode_ldpc(request: EncodeRequest):
    """
    从输入生成LDPC码并返回编码结果

    支持两种输入方式:
    - 方式1: 通过图形数据(nodes, edges)描述LDPC码
    - 方式2: 直接提供H矩阵和可选的信息位

    返回:
    - H矩阵、G矩阵和码率等信息
    - 如果提供了信息位，还会返回编码后的码字
    """
    try:
        # 决定输入方式
        if request.h_matrix is not None:
            # 方式2: 直接提供H矩阵
            h_matrix = np.array(request.h_matrix, dtype=int)
            encoder = LDPCEncoder(h_matrix)
        else:
            # 方式1: 通过图形数据
            if not request.nodes or not request.edges:
                raise ValueError("使用图形模式时必须提供nodes和edges")

            # 从图形数据转换为H矩阵
            nodes = [node.dict() for node in request.nodes]
            edges = [edge.dict() for edge in request.edges]
            ldpc_code = LDPCCode.from_graph_data(nodes, edges)

            # 创建编码器
            encoder = LDPCEncoder(ldpc_code.H)

        # 生成G矩阵
        g_matrix = encoder.generate_g_matrix()

        # 获取矩阵和码参数
        matrices = encoder.get_matrices()

        # 如果提供了信息位，则编码生成码字
        codeword = None
        if request.info_bits is not None:
            if len(request.info_bits) != encoder.k:
                raise ValueError(f"信息位长度应为{encoder.k}，但收到的长度为{len(request.info_bits)}")
            codeword = encoder.encode(request.info_bits).tolist()

        # 构建响应
        return EncodeResponse(
            h_matrix=matrices["h_matrix"],
            g_matrix=matrices["g_matrix"],
            code_rate=float(encoder.rate),
            n=int(encoder.n),
            k=int(encoder.k),
            m=int(encoder.m),
            codeword=codeword,
            message="LDPC码生成成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"编码失败: {str(e)}")

# 解码接口
@app.post("/api/v1/decode", response_model=DecodeResponse, tags=["解码"])
async def decode_ldpc(request: DecodeRequest):
    """
    LDPC码解码接口

    支持多种输入方式:
    - 方式1: 直接提供LLR (对数似然比)
    - 方式2: 提供接收信号 + AWGN信道参数
    - 方式3: 提供接收比特 + BSC信道参数

    返回:
    - 解码后的码字和信息位
    - 解码统计信息和性能指标
    """
    try:
        # 创建H矩阵
        h_matrix = np.array(request.h_matrix, dtype=int)
        
        # 创建解码器
        decoder = LDPCDecoder(
            h_matrix,
            max_iterations=request.max_iterations,
            early_termination=request.early_termination,
            min_sum_scaling=request.min_sum_scaling
        )
        
        # 计算LLR
        if request.llr is not None:
            # 方式1: 直接使用提供的LLR
            llr = np.array(request.llr, dtype=float)
        elif request.received_signal is not None:
            # 方式2: AWGN信道 - 可使用 noise_variance 或 snr_db
            if request.channel_type != "awgn":
                raise ValueError("使用received_signal时channel_type必须为awgn")

            # 若未提供 noise_variance，则尝试用 snr_db 推算
            noise_var = request.noise_variance
            if noise_var is None:
                if request.snr_db is None:
                    raise ValueError("AWGN信道需要提供noise_variance或snr_db")
                snr_lin = 10 ** (request.snr_db / 10)
                # σ² = 1 / (2 * SNR) (BPSK, 单位能量)
                noise_var = 1.0 / (2.0 * snr_lin)

            received_signal = np.array(request.received_signal, dtype=float)
            llr = decoder.awgn_llr(received_signal, noise_var)
        elif request.received_bits is not None:
            # 方式3: BSC信道
            if request.channel_type != "bsc":
                raise ValueError("使用received_bits时channel_type必须为bsc")
            if request.crossover_probability is None:
                raise ValueError("BSC信道需要提供crossover_probability")
            received_bits = np.array(request.received_bits, dtype=int)
            llr = decoder.bsc_llr(received_bits, request.crossover_probability)
        else:
            raise ValueError("必须提供LLR、received_signal或received_bits之一")
        
        # 验证LLR长度
        if len(llr) != decoder.n:
            raise ValueError(f"LLR长度{len(llr)}与码长{decoder.n}不匹配")
        
        # 执行解码
        decoded_bits, stats = decoder.decode(llr, algorithm=request.algorithm)
        
        # 提取信息位
        information_bits = decoder.extract_information_bits(decoded_bits)
        
        # 获取码参数
        code_parameters = {
            "n": decoder.n,
            "k": decoder.k,
            "m": decoder.m,
            "rate": decoder.rate
        }
        
        # 构建响应
        return DecodeResponse(
            decoded_bits=decoded_bits.tolist(),
            information_bits=information_bits.tolist(),
            statistics=stats,
            h_matrix=h_matrix.tolist(),
            code_parameters=code_parameters,
            message="LDPC解码成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解码失败: {str(e)}")

# TODO: 添加其他API路由:
# - POST /api/simulate
# - POST /api/simulate-from-graph
# - POST /api/optimize
# - GET /api/optimize/{optimization_id}
# - WebSocket /ws/simulate/{session_id}
# - WebSocket /ws/optimize/{session_id}

@app.post("/api/simulate", response_model=SimulationResponse, tags=["仿真"])
async def run_simulation(request: SimulationRequest):
    """运行LDPC BER仿真"""
    try:
        # 验证校验矩阵
        h_matrix = np.array(request.h_matrix, dtype=int)
        if h_matrix.size == 0:
            raise ValueError("校验矩阵不能为空")
        
        # 创建仿真引擎
        engine = SimulationEngine(h_matrix)
        
        # 配置仿真参数
        config = SimulationConfig(
            snr_range=request.snr_range,
            frame_count=request.frames_per_snr,
            channel_type=request.channel_type.lower(),
            max_iterations=request.max_iterations,
            decoder_algorithm=request.algorithm.lower() if hasattr(request, 'algorithm') else 'min_sum'
        )
        
        # 运行仿真
        results = engine.run_simulation(config)
        
        return {
            "simulation_results": results,
            "message": "仿真完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"仿真失败: {str(e)}")

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
    """API端点：运行完整BER仿真"""
    try:
        # 提取参数
        h_matrix_data = request_data.get('h_matrix')
        snr_range = request_data.get('snr_range', [0.0, 2.0, 4.0])
        frames_per_point = request_data.get('frames_per_point', 1000)
        algorithm = request_data.get('algorithm', 'min_sum')
        channel = request_data.get('channel', 'awgn')
        max_iterations = request_data.get('max_iterations', 100)
        target_errors = request_data.get('target_errors', 100)
        
        # 验证H矩阵
        if h_matrix_data is None:
            raise ValueError("缺少H矩阵数据")
            
        h_matrix = np.array(h_matrix_data, dtype=int)
        print(f"仿真使用H矩阵: shape={h_matrix.shape}")
        
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
            "message": "仿真完成"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Simulation error: {error_details}")
        raise HTTPException(status_code=500, detail=f"仿真API失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
