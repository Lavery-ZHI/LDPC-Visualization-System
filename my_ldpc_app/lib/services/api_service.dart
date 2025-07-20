import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class ApiService {
  static late Dio _dio;

  // 初始化 Dio 实例
  static void init() {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    // 添加拦截器用于调试
    if (kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: true,
          logPrint: (obj) => debugPrint(obj.toString()),
        ),
      );
    }
  }

  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api';
    }
    return 'http://127.0.0.1:8000/api';
  }

  static String get wsBaseUrl {
    if (kIsWeb) return 'ws://127.0.0.1:8000';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'ws://10.0.2.2:8000';
    }
    return 'ws://127.0.0.1:8000';
  }

  /// 编码模块：生成 LDPC 码
  static Future<Map<String, dynamic>> generateCode({
    required Map<String, dynamic> graphData,
  }) async {
    try {
      final response = await _dio.post('/v1/encode', data: graphData);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 通过H矩阵和信息位进行编码
  static Future<Map<String, dynamic>> encodeWithMatrix({
    required List<List<int>> hMatrix,
    List<int>? infoBits,
  }) async {
    try {
      final data = {
        'h_matrix': hMatrix,
        if (infoBits != null) 'info_bits': infoBits,
      };
      final response = await _dio.post('/v1/encode', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 仿真模块：运行 BER/FER 仿真
  static Future<Map<String, dynamic>> runSimulation({
    required List<List<int>> hMatrix,
    required List<double> snrRange,
    required int framesPerSnr,
    required String channelType,
    required String algorithm,
    required int maxIterations,
  }) async {
    try {
      final response = await _dio.post(
        '/simulate',
        data: {
          'h_matrix': hMatrix,
          'snr_range': snrRange,
          'frames_per_snr': framesPerSnr,
          'channel_type': channelType,
          'algorithm': algorithm,
          'max_iterations': maxIterations,
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 从图结构直接运行仿真
  static Future<Map<String, dynamic>> runSimulationFromGraph(
    Map<String, dynamic> graphData,
  ) async {
    try {
      final response = await _dio.post('/simulate-from-graph', data: graphData);
      return response.data;
    } on DioException catch (e) {
      return {
        'simulation_results': {
          'message': 'Network error: ${e.message}',
          'ber': 'N/A',
        },
      };
    } catch (e) {
      return {
        'simulation_results': {'message': 'Unexpected error: $e', 'ber': 'N/A'},
      };
    }
  }

  /// 优化模块：启动遗传算法优化
  static Future<Map<String, dynamic>> startOptimization({
    required Map<String, dynamic> optimizationParams,
  }) async {
    try {
      final response = await _dio.post('/optimize', data: optimizationParams);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 解码模块：LDPC码解码
  static Future<Map<String, dynamic>> decodeWithLLR({
    required List<double> llr,
    required List<List<int>> hMatrix,
    String algorithm = 'min_sum',
    int maxIterations = 50,
    bool earlyTermination = true,
    double minSumScaling = 0.9,
  }) async {
    try {
      final data = {
        'llr': llr,
        'h_matrix': hMatrix,
        'algorithm': algorithm,
        'max_iterations': maxIterations,
        'early_termination': earlyTermination,
        'min_sum_scaling': minSumScaling,
      };
      final response = await _dio.post('/v1/decode', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 解码模块：AWGN信道解码
  static Future<Map<String, dynamic>> decodeWithAWGN({
    required List<double> receivedSignal,
    required List<List<int>> hMatrix,
    required double noiseVariance,
    String algorithm = 'min_sum',
    int maxIterations = 50,
    bool earlyTermination = true,
    double minSumScaling = 0.9,
  }) async {
    try {
      final data = {
        'received_signal': receivedSignal,
        'h_matrix': hMatrix,
        'channel_type': 'awgn',
        'noise_variance': noiseVariance,
        'algorithm': algorithm,
        'max_iterations': maxIterations,
        'early_termination': earlyTermination,
        'min_sum_scaling': minSumScaling,
      };
      final response = await _dio.post('/v1/decode', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 解码模块：BSC信道解码
  static Future<Map<String, dynamic>> decodeWithBSC({
    required List<int> receivedBits,
    required List<List<int>> hMatrix,
    required double crossoverProbability,
    String algorithm = 'sum_product',
    int maxIterations = 50,
    bool earlyTermination = true,
    double minSumScaling = 0.9,
  }) async {
    try {
      final data = {
        'received_bits': receivedBits,
        'h_matrix': hMatrix,
        'channel_type': 'bsc',
        'crossover_probability': crossoverProbability,
        'algorithm': algorithm,
        'max_iterations': maxIterations,
        'early_termination': earlyTermination,
        'min_sum_scaling': minSumScaling,
      };
      final response = await _dio.post('/v1/decode', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// 仿真模块：运行快速测试
  static Future<Map<String, dynamic>> runQuickTest({
    required List<List<int>> hMatrix,
    required double snrDb,
    required int frames,
  }) async {
    try {
      final response = await _dio.post(
        '/quick-test',
        data: {'h_matrix': hMatrix, 'snr_db': snrDb, 'frames': frames},
      );

      return response.data;
    } on DioException catch (error) {
      throw Exception(_handleDioError(error));
    }
  }

  /// 创建 WebSocket 连接用于实时进度更新
  static WebSocketChannel createWebSocketChannel(String endpoint) {
    final uri = Uri.parse('$wsBaseUrl$endpoint');
    return WebSocketChannel.connect(uri);
  }

  /// 处理 Dio 错误
  static String _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return '连接超时，请检查网络连接';
      case DioExceptionType.sendTimeout:
        return '发送超时，请重试';
      case DioExceptionType.receiveTimeout:
        return '响应超时，请重试';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final message = error.response?.data?['error'] ?? '服务器错误';
        return 'HTTP $statusCode: $message';
      case DioExceptionType.cancel:
        return '请求已取消';
      case DioExceptionType.unknown:
        return '网络连接失败，请检查网络设置';
      default:
        return '未知错误: ${error.message}';
    }
  }
}
