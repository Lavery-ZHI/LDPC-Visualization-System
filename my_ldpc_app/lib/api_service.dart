// lib/api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Network configuration - use appropriate URL based on platform
  // Android emulator: use '10.0.2.2', iOS simulator/desktop/web: use '127.0.0.1'
  static const String _baseUrl = 'http://127.0.0.1:8000/api';

  /// Get available LDPC matrix templates
  static Future<Map<String, dynamic>> getMatrixTemplates() async {
    final url = Uri.parse('$_baseUrl/matrix-templates');
    final headers = {"Content-Type": "application/json"};

    try {
      final response = await http.get(url, headers: headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception(
          'Failed to fetch matrix templates: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Network error fetching templates: $e');
    }
  }

  /// Generate LDPC matrix from template
  static Future<Map<String, dynamic>> generateMatrixFromTemplate(
    String templateName,
  ) async {
    final url = Uri.parse(
      '$_baseUrl/generate-template?template_name=$templateName',
    );
    final headers = {"Content-Type": "application/json"};

    try {
      final response = await http.post(url, headers: headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception(
          'Failed to generate matrix from template: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Network error generating matrix: $e');
    }
  }

  /// Get system performance metrics
  static Future<Map<String, dynamic>> getPerformanceMetrics() async {
    final url = Uri.parse('$_baseUrl/performance-metrics');
    final headers = {"Content-Type": "application/json"};

    try {
      final response = await http.get(url, headers: headers);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception(
          'Failed to fetch performance metrics: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Network error fetching metrics: $e');
    }
  }

  /// Enhanced code generation with template support
  static Future<Map<String, dynamic>> generateCode({
    String templateName = 'simple_6_3',
  }) async {
    final url = Uri.parse(
      '$_baseUrl/generate-from-graph?template_name=$templateName',
    );
    final headers = {"Content-Type": "application/json"};

    final body = jsonEncode({});

    try {
      final response = await http.post(url, headers: headers, body: body);

      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);

        // Check if operation was successful
        if (result['success'] == true) {
          return result;
        } else {
          // Handle API-level errors with detailed messages
          final error = result['error'];
          throw Exception(
            'Code generation failed: ${error['message']}\n'
            'Suggestions: ${error['suggestions']?.join(', ') ?? 'None'}',
          );
        }
      } else {
        throw Exception(
          'Failed to generate code - HTTP ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Network error occurred during code generation: $e');
    }
  }

  static Future<Map<String, dynamic>> runQuickTest({
    required List<List<int>> hMatrix,
    required double snrDb,
    required int frames,
    String algorithm = 'min_sum',
    String channel = 'awgn',
  }) async {
    final url = Uri.parse('$_baseUrl/quick-test');
    final headers = {"Content-Type": "application/json"};

    final body = jsonEncode({
      'h_matrix': hMatrix,
      'snr_db': snrDb,
      'frames': frames,
      'algorithm': algorithm,
      'channel': channel,
    });

    try {
      final response = await http.post(url, headers: headers, body: body);

      if (response.statusCode == 200) {
        // 快速测试成功
        return jsonDecode(response.body);
      } else {
        // 快速测试失败, 状态码: ${response.statusCode}
        throw Exception('Quick test failed: ${response.statusCode}');
      }
    } catch (e) {
      // 快速测试网络错误: $e
      throw Exception('Quick test network error: $e');
    }
  }

  static Future<Map<String, dynamic>> runBERSimulation({
    required List<double> snrRange,
    required int framesPerPoint,
    String algorithm = 'min_sum',
    String channel = 'awgn',
    int maxIterations = 100,
    double targetErrors = 100,
  }) async {
    final url = Uri.parse('$_baseUrl/simulate');
    final headers = {"Content-Type": "application/json"};

    final body = jsonEncode({
      'snr_range': snrRange,
      'frames_per_point': framesPerPoint,
      'algorithm': algorithm,
      'channel': channel,
      'max_iterations': maxIterations,
      'target_errors': targetErrors,
    });

    try {
      final response = await http.post(url, headers: headers, body: body);

      if (response.statusCode == 200) {
        // BER仿真成功
        return jsonDecode(response.body);
      } else {
        // BER仿真失败, 状态码: ${response.statusCode}
        throw Exception('BER simulation failed: ${response.statusCode}');
      }
    } catch (e) {
      // BER仿真网络错误: $e
      throw Exception('BER simulation network error: $e');
    }
  }

  static Future<Map<String, dynamic>> runSimulation({
    required List<List<int>> hMatrix,
    required List<double> snrRange,
    required int framesPerSnr,
    required String channelType,
    required String algorithm,
    required int maxIterations,
  }) async {
    final url = Uri.parse('$_baseUrl/simulate');
    final headers = {"Content-Type": "application/json"};

    final body = jsonEncode({
      'h_matrix': hMatrix,
      'snr_range': snrRange,
      'frames_per_point': framesPerSnr,
      'algorithm': algorithm,
      'channel': channelType,
      'max_iterations': maxIterations,
      'target_errors': 100,
    });

    try {
      final response = await http.post(url, headers: headers, body: body);

      if (response.statusCode == 200) {
        // 仿真成功
        return jsonDecode(response.body);
      } else {
        // 仿真失败, 状态码: ${response.statusCode}
        throw Exception('Simulation failed: ${response.statusCode}');
      }
    } catch (e) {
      // 仿真网络错误: $e
      throw Exception('Simulation network error: $e');
    }
  }
}
