// lib/providers/app_provider.dart
import 'package:flutter/material.dart';
import 'dart:math';
import '../services/api_service.dart';

// 升级Node类，增加一个布尔值来区分节点类型
class Node {
  final String id;
  Offset position;
  final bool isVariableNode; // true: 变量节点 (V), false: 校验节点 (C)

  Node({
    required this.id,
    required this.position,
    required this.isVariableNode,
  });
}

/// 图中的一条边
class Edge {
  final String fromId;
  final String toId;
  Edge({required this.fromId, required this.toId});
}

class AppProvider with ChangeNotifier {
  // --- 状态变量 ---
  bool _isLoading = false;
  // 【修正】将结果设为非空，并给一个初始值，可以避免很多null-check错误
  Map<String, dynamic> _simulationResults = {
    'message': 'Ready. Draw your graph and run simulation.',
    'ber': 'N/A',
  };

  // 编码相关状态
  Map<String, dynamic> _encodeResults = {
    'message': 'Ready. Generate LDPC code.',
    'h_matrix': null,
    'g_matrix': null,
    'code_rate': null,
    'n': null,
    'k': null,
    'm': null,
    'codeword': null,
  };

  // 解码相关状态
  Map<String, dynamic> _decodeResults = {
    'message': 'Ready. Decode received data.',
    'decoded_bits': null,
    'information_bits': null,
    'statistics': null,
    'algorithm_used': null,
    'channel_type': null,
  };

  final List<Node> _nodes = [];
  final List<Edge> _edges = [];
  int _vnCounter = 0; // 变量节点计数器
  int _cnCounter = 0; // 校验节点计数器

  Node? _selectedNode;

  // 【新增】添加回我们需要的控制器
  final TextEditingController snrController = TextEditingController(
    text: '4.0',
  );
  final TextEditingController frameCountController = TextEditingController(
    text: '1000',
  );
  final TextEditingController infoBitsController = TextEditingController(
    text: '1,0',
  );

  // 解码参数控制器
  final TextEditingController llrController = TextEditingController(
    text: '1.5,-2.3,0.8,-1.2',
  );
  final TextEditingController receivedSignalController = TextEditingController(
    text: '1.2,-1.8,0.9,-1.1',
  );
  final TextEditingController receivedBitsController = TextEditingController(
    text: '1,0,1,0',
  );
  final TextEditingController noiseVarianceController = TextEditingController(
    text: '0.5',
  );
  final TextEditingController crossoverProbabilityController =
      TextEditingController(text: '0.1');
  final TextEditingController maxIterationsController = TextEditingController(
    text: '50',
  );
  final TextEditingController minSumScalingController = TextEditingController(
    text: '0.9',
  );

  // 解码配置状态
  String _selectedDecodeMode = 'bsc'; // 默认使用BSC模式
  String _selectedAlgorithm = 'min_sum'; // 'min_sum', 'sum_product'
  bool _earlyTermination = true;

  // BSC输入的比特数组
  List<int> _receivedBits = [1, 0, 1, 0];

  // Info Bits输入的比特数组
  List<int> _infoBits = [1, 0];

  // --- Getters ---
  bool get isLoading => _isLoading;
  Map<String, dynamic> get simulationResults => _simulationResults;
  Map<String, dynamic> get encodeResults => _encodeResults;
  Map<String, dynamic> get decodeResults => _decodeResults;
  List<Node> get nodes => List.unmodifiable(_nodes);
  List<Edge> get edges => List.unmodifiable(_edges);
  Node? get selectedNode => _selectedNode;
  String get statusMessage => _simulationResults['message'] as String;
  String get encodeMessage => _encodeResults['message'] as String;
  String get decodeMessage => _decodeResults['message'] as String;
  String get selectedDecodeMode => _selectedDecodeMode;
  String get selectedAlgorithm => _selectedAlgorithm;
  bool get earlyTermination => _earlyTermination;
  List<int> get receivedBits => List.unmodifiable(_receivedBits);
  List<int> get infoBits => List.unmodifiable(_infoBits);

  // --- 方法 ---

  // 【修正】将 addNode 拆分为两个具体的方法
  void addVariableNode() {
    _vnCounter++;
    _nodes.add(
      Node(
        id: 'V$_vnCounter',
        position: Offset(250.0 + Random().nextDouble() * 100, 200.0),
        isVariableNode: true, // 标记为变量节点
      ),
    );
    notifyListeners();
  }

  void addCheckNode() {
    _cnCounter++;
    _nodes.add(
      Node(
        id: 'C$_cnCounter',
        position: Offset(550.0 + Random().nextDouble() * 100, 200.0),
        isVariableNode: false, // 标记为校验节点
      ),
    );
    notifyListeners();
  }

  // 保留旧的 addNode 方法，但现在它添加变量节点
  void addNode() {
    addVariableNode();
  }

  //—— 更新节点位置（拖拽时调用） ——//
  void updateNodePosition(String nodeId, Offset delta) {
    try {
      final node = _nodes.firstWhere((n) => n.id == nodeId);
      node.position += delta;
      notifyListeners();
    } catch (e) {
      /* 找不到节点 */
    }
  }

  //—— 点击某个节点：如果已有选中节点则连边，否则选中 ——//
  void tapNode(Node node) {
    if (_selectedNode == null) {
      _selectedNode = node;
    } else {
      if (_selectedNode!.id != node.id) {
        _edges.add(Edge(fromId: _selectedNode!.id, toId: node.id));
      }
      _selectedNode = null;
    }
    notifyListeners();
  }

  //—— 点击空白区域，取消选中 ——//
  void tapCanvas() {
    if (_selectedNode != null) {
      _selectedNode = null;
      notifyListeners();
    }
  }

  void clearCanvas() {
    // 清除图形元素
    _nodes.clear();
    _edges.clear();
    _vnCounter = 0;
    _cnCounter = 0;
    _selectedNode = null;

    // 重置加载状态
    _isLoading = false;

    // 清除所有结果数据 - 恢复到初始消息
    _simulationResults = {
      'message': 'Ready. Draw your graph and run simulation.',
      'ber': 'N/A',
    };

    _encodeResults = {
      'message': 'Ready. Generate LDPC code.',
      'h_matrix': null,
      'g_matrix': null,
      'code_rate': null,
      'n': null,
      'k': null,
      'm': null,
      'codeword': null,
    };

    _decodeResults = {
      'message': 'Ready. Decode received data.',
      'decoded_bits': null,
      'information_bits': null,
      'statistics': null,
      'algorithm_used': null,
      'channel_type': null,
    };

    // 重置所有输入控制器到初始默认值
    snrController.text = '4.0';
    frameCountController.text = '1000';
    infoBitsController.text = '1,0';
    llrController.text = '1.5,-2.3,0.8,-1.2';
    receivedSignalController.text = '1.2,-1.8,0.9,-1.1';
    receivedBitsController.text = '1,0,1,0';
    noiseVarianceController.text = '0.5';
    crossoverProbabilityController.text = '0.1';
    maxIterationsController.text = '50';
    minSumScalingController.text = '0.9';

    // 重置解码参数到默认值
    _selectedDecodeMode = 'bsc';
    _selectedAlgorithm = 'min_sum';
    _earlyTermination = true;

    // 重置比特数组到默认值
    _receivedBits = [1, 0, 1, 0];
    _infoBits = [1, 0];

    notifyListeners();
  }

  //—— 删除节点 ——//
  void removeNode(String nodeId) {
    _nodes.removeWhere((node) => node.id == nodeId);
    // 同时删除与该节点相关的边
    _edges.removeWhere((edge) => edge.fromId == nodeId || edge.toId == nodeId);
    // 如果删除的是当前选中的节点，取消选中
    if (_selectedNode?.id == nodeId) {
      _selectedNode = null;
    }
    notifyListeners();
  }

  Future<void> runSimulation() async {
    // 检查是否有LDPC码数据
    if (_encodeResults['h_matrix'] == null) {
      _simulationResults = {
        'message': 'Error: Please generate LDPC code first.',
        'ber': 'N/A',
      };
      notifyListeners();
      return;
    }

    _isLoading = true;
    _simulationResults = {'message': 'Running BER simulation...', 'ber': 'N/A'};
    notifyListeners();

    try {
      // 运行完整的BER仿真
      List<double> snrRange = [];
      for (double snr = 0.0; snr <= 6.0; snr += 0.5) {
        snrRange.add(snr);
      }

      await runBERSimulation(
        snrRange: snrRange,
        framesPerSnr: 1000,
        channelType: 'awgn',
        algorithm: 'min_sum',
        maxIterations: 50,
      );
    } catch (e) {
      _simulationResults = {'message': 'Error: ${e.toString()}', 'ber': 'N/A'};
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  //—— 生成LDPC码 ——//
  Future<void> generateLDPCCode() async {
    if (_nodes.isEmpty || _edges.isEmpty) {
      _encodeResults = {
        'message': 'Error: Please draw a graph with nodes and edges.',
        'h_matrix': null,
        'g_matrix': null,
        'code_rate': null,
        'n': null,
        'k': null,
        'm': null,
        'codeword': null,
      };
      notifyListeners();
      return;
    }

    _isLoading = true;
    _encodeResults = {
      'message': 'Generating LDPC code...',
      'h_matrix': null,
      'g_matrix': null,
      'code_rate': null,
      'n': null,
      'k': null,
      'm': null,
      'codeword': null,
    };
    notifyListeners();

    try {
      final graphData = {
        'nodes': _nodes
            .map(
              (n) => {
                'id': n.id,
                'type': n.isVariableNode ? 'variable' : 'check',
              },
            )
            .toList(),
        'edges': _edges
            .map((e) => {'fromId': e.fromId, 'toId': e.toId})
            .toList(),
      };

      final data = await ApiService.generateCode(graphData: graphData);

      _encodeResults = {
        'message': data['message'] ?? 'LDPC code generated successfully.',
        'h_matrix': data['h_matrix'],
        'g_matrix': data['g_matrix'],
        'code_rate': data['code_rate'],
        'n': data['n'],
        'k': data['k'],
        'm': data['m'],
        'codeword': data['codeword'],
      };
    } catch (e) {
      _encodeResults = {
        'message': 'Error: ${e.toString()}',
        'h_matrix': null,
        'g_matrix': null,
        'code_rate': null,
        'n': null,
        'k': null,
        'm': null,
        'codeword': null,
      };
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  //—— 使用当前LDPC码对信息位进行编码 ——//
  Future<void> encodeInfoBits() async {
    if (_encodeResults['h_matrix'] == null) {
      _encodeResults = {
        ..._encodeResults,
        'message': 'Error: Please generate LDPC code first.',
        'codeword': null,
      };
      notifyListeners();
      return;
    }

    // 使用_infoBits数组
    List<int> infoBits;
    final int k = _encodeResults['k'] ?? 0;

    // 如果infoBits数组长度不匹配，自动生成
    if (_infoBits.length != k) {
      if (k > 0) {
        final random = Random();
        _infoBits = List<int>.generate(k, (_) => random.nextInt(2));
        infoBitsController.text = _infoBits.join(',');
      } else {
        _infoBits = [];
      }
    }

    infoBits = _infoBits;

    _isLoading = true;
    _encodeResults = {
      ..._encodeResults,
      'message': 'Encoding info bits...',
      'codeword': null,
    };
    notifyListeners();

    try {
      // 正确转换H矩阵类型
      final hMatrix = _convertToIntMatrix(_encodeResults['h_matrix']);
      if (hMatrix == null) {
        throw Exception('Invalid H matrix format');
      }

      final data = await ApiService.encodeWithMatrix(
        hMatrix: hMatrix,
        infoBits: infoBits,
      );

      _encodeResults = {
        ..._encodeResults,
        'message': data['message'] ?? 'Info bits encoded successfully.',
        'codeword': data['codeword'],
      };
    } catch (e) {
      _encodeResults = {
        ..._encodeResults,
        'message': 'Error: ${e.toString()}',
        'codeword': null,
      };
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // 类型转换辅助方法
  List<List<int>>? _convertToIntMatrix(dynamic matrix) {
    if (matrix is List) {
      return matrix.map<List<int>>((row) {
        if (row is List) {
          return row.map<int>((cell) {
            if (cell is int) return cell;
            if (cell is double) return cell.toInt();
            if (cell is String) return int.tryParse(cell) ?? 0;
            return 0;
          }).toList();
        }
        return <int>[];
      }).toList();
    }
    return null;
  }

  // 解码参数设置方法
  void setDecodeMode(String mode) {
    _selectedDecodeMode = mode;
    notifyListeners();
  }

  void setAlgorithm(String algorithm) {
    _selectedAlgorithm = algorithm;
    notifyListeners();
  }

  void setEarlyTermination(bool enabled) {
    _earlyTermination = enabled;
    notifyListeners();
  }

  // BSC比特输入相关方法
  void updateReceivedBit(int index, int value) {
    if (index >= 0 && index < _receivedBits.length) {
      _receivedBits[index] = value % 2; // 确保只有0或1
      // 同时更新传统的text controller以保持兼容性
      receivedBitsController.text = _receivedBits.join(',');
      notifyListeners();
    }
  }

  void initializeReceivedBits(int length) {
    _receivedBits = List.filled(length, 0);
    receivedBitsController.text = _receivedBits.join(',');
    notifyListeners();
  }

  void setReceivedBitsFromCodeword() {
    final codeword = _encodeResults['codeword'];
    if (codeword != null && codeword is List) {
      _receivedBits = List<int>.from(codeword);
      receivedBitsController.text = _receivedBits.join(',');
      notifyListeners();
    }
  }

  void addRandomErrorsToReceivedBits() {
    if (_receivedBits.isEmpty) return;

    // 获取当前设置的错误概率
    final errorProb =
        double.tryParse(crossoverProbabilityController.text) ?? 0.1;
    final random = Random();

    // 根据错误概率为每个比特添加随机错误
    for (int i = 0; i < _receivedBits.length; i++) {
      if (random.nextDouble() < errorProb) {
        _receivedBits[i] = 1 - _receivedBits[i]; // 翻转比特
      }
    }

    // 更新文本控制器
    receivedBitsController.text = _receivedBits.join(',');
    notifyListeners();
  }

  // Info Bits相关方法
  void updateInfoBit(int index, int value) {
    if (index >= 0 && index < _infoBits.length) {
      _infoBits[index] = value % 2; // 确保只有0或1
      // 同时更新传统的text controller以保持兼容性
      infoBitsController.text = _infoBits.join(',');
      notifyListeners();
    }
  }

  void initializeInfoBits(int length) {
    _infoBits = List.filled(length, 0);
    infoBitsController.text = _infoBits.join(',');
    notifyListeners();
  }

  void generateRandomInfoBits() {
    final int k = _encodeResults['k'] ?? 0;
    if (k > 0) {
      final random = Random();
      _infoBits = List<int>.generate(k, (_) => random.nextInt(2));
      infoBitsController.text = _infoBits.join(',');
      notifyListeners();
    }
  }

  // 解码方法
  Future<void> decodeData() async {
    if (_encodeResults['h_matrix'] == null) {
      _decodeResults = {
        'message': 'Error: Please generate LDPC code first.',
        'decoded_bits': null,
        'information_bits': null,
        'statistics': null,
        'algorithm_used': null,
        'channel_type': null,
      };
      notifyListeners();
      return;
    }

    _isLoading = true;
    _decodeResults = {
      'message': 'Decoding data...',
      'decoded_bits': null,
      'information_bits': null,
      'statistics': null,
      'algorithm_used': null,
      'channel_type': null,
    };
    notifyListeners();

    try {
      final hMatrix = _convertToIntMatrix(_encodeResults['h_matrix']);
      if (hMatrix == null) {
        throw Exception('Invalid H matrix format');
      }

      final maxIterations = int.tryParse(maxIterationsController.text) ?? 50;
      final minSumScaling =
          double.tryParse(minSumScalingController.text) ?? 0.9;

      // 后端期望下划线格式的算法名称，前端也使用下划线格式，不需要转换
      final algorithmForAPI = _selectedAlgorithm;

      Map<String, dynamic> data;

      switch (_selectedDecodeMode) {
        case 'llr':
          // 解析LLR数据
          final llrValues = llrController.text
              .split(',')
              .map((s) => double.tryParse(s.trim()) ?? 0.0)
              .toList();

          data = await ApiService.decodeWithLLR(
            llr: llrValues,
            hMatrix: hMatrix,
            algorithm: algorithmForAPI,
            maxIterations: maxIterations,
            earlyTermination: _earlyTermination,
            minSumScaling: minSumScaling,
          );
          break;

        case 'awgn':
          // 解析接收信号
          final receivedSignal = receivedSignalController.text
              .split(',')
              .map((s) => double.tryParse(s.trim()) ?? 0.0)
              .toList();

          final noiseVariance =
              double.tryParse(noiseVarianceController.text) ?? 0.5;

          data = await ApiService.decodeWithAWGN(
            receivedSignal: receivedSignal,
            hMatrix: hMatrix,
            noiseVariance: noiseVariance,
            algorithm: algorithmForAPI,
            maxIterations: maxIterations,
            earlyTermination: _earlyTermination,
            minSumScaling: minSumScaling,
          );
          break;

        case 'bsc':
          // 使用_receivedBits数组，无需解析文本
          final crossoverProb =
              double.tryParse(crossoverProbabilityController.text) ?? 0.1;

          data = await ApiService.decodeWithBSC(
            receivedBits: _receivedBits,
            hMatrix: hMatrix,
            crossoverProbability: crossoverProb,
            algorithm: algorithmForAPI,
            maxIterations: maxIterations,
            earlyTermination: _earlyTermination,
            minSumScaling: minSumScaling,
          );
          break;

        default:
          throw Exception('Unknown decode mode: $_selectedDecodeMode');
      }

      _decodeResults = {
        'message': data['message'] ?? 'Decoding completed successfully.',
        'decoded_bits': data['decoded_bits'],
        'information_bits': data['information_bits'],
        'statistics': data['statistics'],
        'algorithm_used': _selectedAlgorithm,
        'channel_type': _selectedDecodeMode,
      };
    } catch (e) {
      _decodeResults = {
        'message': 'Error: ${e.toString()}',
        'decoded_bits': null,
        'information_bits': null,
        'statistics': null,
        'algorithm_used': null,
        'channel_type': null,
      };
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // 清空解码结果
  void clearDecodeResults() {
    _decodeResults = {
      'message': 'Ready. Decode received data.',
      'decoded_bits': null,
      'information_bits': null,
      'statistics': null,
      'algorithm_used': null,
      'channel_type': null,
    };
    notifyListeners();
  }

  //—— 生成随机图 ——//
  void generateRandomGraph() {
    clearCanvas();

    final random = Random();
    const variableNodeCount = 6;
    const checkNodeCount = 4;

    // 添加变量节点
    for (int i = 0; i < variableNodeCount; i++) {
      _vnCounter++;
      _nodes.add(
        Node(
          id: 'V$_vnCounter',
          position: Offset(
            100.0 + random.nextDouble() * 300,
            100.0 + random.nextDouble() * 200,
          ),
          isVariableNode: true,
        ),
      );
    }

    // 添加校验节点
    for (int i = 0; i < checkNodeCount; i++) {
      _cnCounter++;
      _nodes.add(
        Node(
          id: 'C$_cnCounter',
          position: Offset(
            500.0 + random.nextDouble() * 300,
            100.0 + random.nextDouble() * 200,
          ),
          isVariableNode: false,
        ),
      );
    }

    // 添加随机边
    final variableNodes = _nodes.where((n) => n.isVariableNode).toList();
    final checkNodes = _nodes.where((n) => !n.isVariableNode).toList();

    for (final vNode in variableNodes) {
      // 每个变量节点连接到2-3个校验节点
      final degree = 2 + random.nextInt(2);
      final targets = checkNodes.toList()..shuffle();

      for (int i = 0; i < degree && i < targets.length; i++) {
        _edges.add(Edge(fromId: vNode.id, toId: targets[i].id));
      }
    }

    _simulationResults = {
      'message':
          'Random graph generated with $variableNodeCount variable nodes and $checkNodeCount check nodes.',
      'ber': 'N/A',
    };
    notifyListeners();
  }

  //—— 加载模板图 ——//
  void loadTemplate(String templateType) {
    clearCanvas();

    switch (templateType) {
      case '3_6_regular':
        _loadRegularTemplate(3, 6);
        break;
      case '4_8_regular':
        _loadRegularTemplate(4, 8);
        break;
      case 'irregular':
        _loadIrregularTemplate();
        break;
    }

    _simulationResults = {
      'message': 'Template "$templateType" loaded successfully.',
      'ber': 'N/A',
    };
    notifyListeners();
  }

  void _loadRegularTemplate(int variableDegree, int checkDegree) {
    // 为了让 (dv, dc) 模板彼此区分，这里按 dc 个变量节点、dv 个校验节点构造最小重复单元。
    final int variableNodeCount = checkDegree; // n = dc
    final int checkNodeCount = variableDegree; // m = dv

    const double vStartY = 100.0;
    const double vSpacing = 60.0;
    for (int i = 0; i < variableNodeCount; i++) {
      _vnCounter++;
      _nodes.add(
        Node(
          id: 'V$_vnCounter',
          position: Offset(150.0, vStartY + i * vSpacing),
          isVariableNode: true,
        ),
      );
    }

    const double cStartY = 120.0;
    const double cSpacing = 90.0;
    for (int i = 0; i < checkNodeCount; i++) {
      _cnCounter++;
      _nodes.add(
        Node(
          id: 'C$_cnCounter',
          position: Offset(550.0, cStartY + i * cSpacing),
          isVariableNode: false,
        ),
      );
    }

    // 轮转连接，确保正则度
    final variableNodesList = _nodes.where((n) => n.isVariableNode).toList();
    final checkNodesList = _nodes.where((n) => !n.isVariableNode).toList();

    int edgeCounter = 0;
    for (final vNode in variableNodesList) {
      for (int e = 0; e < variableDegree; e++) {
        final cNode = checkNodesList[edgeCounter % checkNodesList.length];
        _edges.add(Edge(fromId: vNode.id, toId: cNode.id));
        edgeCounter++;
      }
    }
  }

  void _loadIrregularTemplate() {
    const variableNodeCount = 8;
    const checkNodeCount = 5;

    // 添加变量节点
    for (int i = 0; i < variableNodeCount; i++) {
      _vnCounter++;
      _nodes.add(
        Node(
          id: 'V$_vnCounter',
          position: Offset(150.0, 80.0 + i * 60.0),
          isVariableNode: true,
        ),
      );
    }

    // 添加校验节点
    for (int i = 0; i < checkNodeCount; i++) {
      _cnCounter++;
      _nodes.add(
        Node(
          id: 'C$_cnCounter',
          position: Offset(550.0, 100.0 + i * 100.0),
          isVariableNode: false,
        ),
      );
    }

    // 不规则连接
    final variableNodes = _nodes.where((n) => n.isVariableNode).toList();
    final checkNodes = _nodes.where((n) => !n.isVariableNode).toList();
    final random = Random();

    for (int i = 0; i < variableNodes.length; i++) {
      // 度数分布：50% 度数为2，30% 度数为3，20% 度数为4
      int degree;
      final rand = random.nextDouble();
      if (rand < 0.5) {
        degree = 2;
      } else if (rand < 0.8) {
        degree = 3;
      } else {
        degree = 4;
      }

      final shuffledChecks = checkNodes.toList()..shuffle();
      for (int j = 0; j < degree && j < shuffledChecks.length; j++) {
        _edges.add(
          Edge(fromId: variableNodes[i].id, toId: shuffledChecks[j].id),
        );
      }
    }
  }

  // ==========================================================
  // 仿真相关方法
  // ==========================================================

  /// 运行BER仿真
  /// 运行完整的BER仿真 - 扫描多个SNR点生成完整的性能曲线
  /// 与快速测试(runQuickTest)的区别：
  /// - Quick Test: 单个SNR，少量帧数，快速验证功能
  /// - Full Simulation: 多个SNR点，大量帧数，生成完整的BER曲线
  Future<void> runBERSimulation({
    required List<double> snrRange,
    required int framesPerSnr,
    required String channelType,
    required String algorithm,
    required int maxIterations,
  }) async {
    if (_encodeResults['h_matrix'] == null) {
      throw Exception('请先生成校验矩阵');
    }

    _isLoading = true;
    notifyListeners();

    try {
      final hMatrix = _convertToIntMatrix(_encodeResults['h_matrix']);
      if (hMatrix == null) {
        throw Exception('校验矩阵格式错误');
      }

      final data = await ApiService.runSimulation(
        hMatrix: hMatrix,
        snrRange: snrRange,
        framesPerSnr: framesPerSnr,
        channelType: channelType,
        algorithm: algorithm,
        maxIterations: maxIterations,
      );

      _simulationResults = {
        'message': data['message'] ?? '仿真完成',
        'simulation_results': data['simulation_results'],
        'timestamp': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      _simulationResults = {
        'message': '仿真失败: ${e.toString()}',
        'error': e.toString(),
      };
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ===== 便捷功能方法 =====

  /// 从当前码字生成LLR（模拟AWGN信道）
  void generateLLRFromCodeword({double snrDb = 4.0}) {
    final codeword = _encodeResults['codeword'];
    if (codeword == null || codeword.isEmpty) {
      llrController.text = '';
      return;
    }

    // BPSK调制: 0 -> +1, 1 -> -1
    final codewordInt = List<int>.from(codeword);
    final modulated = codewordInt.map<double>((bit) => 1.0 - 2.0 * bit);

    // 计算噪声方差
    final snrLinear = pow(10, snrDb / 10.0);
    final noiseVariance = 1.0 / (2.0 * snrLinear);
    final noiseStd = sqrt(noiseVariance);

    // 添加高斯噪声并计算LLR
    final random = Random();
    final llrValues = modulated.map<double>((signal) {
      final noise = _generateGaussian(random) * noiseStd;
      final receivedSignal = signal + noise;
      return (2.0 * receivedSignal) / noiseVariance;
    }).toList();

    llrController.text = llrValues.map((v) => v.toStringAsFixed(3)).join(',');
    notifyListeners();
  }

  /// 从BSC模式的接收比特转换为LLR
  void convertBSCtoLLR() {
    if (_receivedBits.isEmpty) {
      llrController.text = '';
      return;
    }

    final crossoverProb =
        double.tryParse(crossoverProbabilityController.text) ?? 0.1;
    if (crossoverProb <= 0 || crossoverProb >= 0.5) {
      llrController.text = '';
      return;
    }

    // BSC信道的LLR计算: LLR = log((1-p)/p) * (1-2*r)
    final logRatio = log((1 - crossoverProb) / crossoverProb);
    final llrValues = _receivedBits.map<double>((bit) {
      return logRatio * (1 - 2 * bit);
    }).toList();

    llrController.text = llrValues.map((v) => v.toStringAsFixed(3)).join(',');
    notifyListeners();
  }

  /// 生成AWGN信道的接收信号
  void generateAWGNSignal({double snrDb = 4.0}) {
    final codeword = _encodeResults['codeword'];
    if (codeword == null || codeword.isEmpty) {
      receivedSignalController.text = '';
      noiseVarianceController.text = '';
      return;
    }

    // BPSK调制: 0 -> +1, 1 -> -1
    final codewordInt = List<int>.from(codeword);
    final modulated = codewordInt.map<double>((bit) => 1.0 - 2.0 * bit);

    // 计算噪声方差
    final snrLinear = pow(10, snrDb / 10.0);
    final noiseVariance = 1.0 / (2.0 * snrLinear);
    final noiseStd = sqrt(noiseVariance);

    // 添加高斯噪声
    final random = Random();
    final receivedSignal = modulated.map<double>((signal) {
      final noise = _generateGaussian(random) * noiseStd;
      return signal + noise;
    }).toList();

    receivedSignalController.text = receivedSignal
        .map((v) => v.toStringAsFixed(3))
        .join(',');
    noiseVarianceController.text = noiseVariance.toStringAsFixed(6);
    notifyListeners();
  }

  /// 设置SNR并自动计算噪声方差
  void setSNRdB(double snrDb) {
    final snrLinear = pow(10, snrDb / 10.0);
    final noiseVariance = 1.0 / (2.0 * snrLinear);
    noiseVarianceController.text = noiseVariance.toStringAsFixed(6);
    notifyListeners();
  }

  /// 生成高斯随机数
  double _generateGaussian(Random random) {
    double u1 = random.nextDouble();
    double u2 = random.nextDouble();
    return sqrt(-2 * log(u1)) * cos(2 * pi * u2);
  }

  @override
  void dispose() {
    snrController.dispose(); // 记得释放控制器
    frameCountController.dispose();
    infoBitsController.dispose();

    // 释放解码控制器
    llrController.dispose();
    receivedSignalController.dispose();
    receivedBitsController.dispose();
    noiseVarianceController.dispose();
    crossoverProbabilityController.dispose();
    maxIterationsController.dispose();
    minSumScalingController.dispose();

    super.dispose();
  }
}
