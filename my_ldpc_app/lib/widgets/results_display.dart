// lib/widgets/results_display.dart
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/app_provider.dart';
import 'matrix_viewer.dart';

class ResultsDisplay extends StatelessWidget {
  const ResultsDisplay({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return LayoutBuilder(
          builder: (context, constraints) {
            final isCompact =
                constraints.maxWidth < 400 || constraints.maxHeight < 600;

            return Card(
              margin: const EdgeInsets.all(8.0),
              elevation: 4.0,
              child: SizedBox(
                height: double.infinity,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Results & Analysis',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 16),

                      // 编码完成后仅显示基本参数，可在矩阵区查看
                      // 矩阵展示部分
                      _buildMatricesSection(
                        appProvider,
                        constraints,
                        isCompact,
                      ),
                      const SizedBox(height: 12),

                      // 编码结果展示
                      _buildCodewordSection(appProvider),
                      const SizedBox(height: 12),

                      // 解码结果展示（去除顶部状态文字，保留结果与统计）
                      _buildDecodeResultsSection(appProvider),
                      const SizedBox(height: 12),

                      // 仿真状态信息
                      _buildSimulationStatusSection(appProvider),
                      const SizedBox(height: 12),

                      // BER/FER 曲线
                      if (!isCompact) ...[
                        SizedBox(
                          height: 250,
                          child: _buildChartSection(appProvider),
                        ),
                      ],

                      // 底部间距
                      const SizedBox(height: 20),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMatricesSection(
    AppProvider appProvider,
    BoxConstraints constraints,
    bool isCompact,
  ) {
    final results = appProvider.encodeResults;
    final hMatrix = results['h_matrix'];
    final gMatrix = results['g_matrix'];

    // 设置高度与 cellSize - 优化矩阵显示空间
    final matrixHeight = isCompact
        ? 180.0
        : (constraints.maxHeight * 0.35).clamp(200.0, 320.0);

    final cellSize = isCompact
        ? 16.0
        : (constraints.maxWidth / 30).clamp(16.0, 24.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'LDPC Matrices',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            // H Matrix
            Expanded(
              child: Container(
                height: matrixHeight,
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: Colors.grey[800],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'H Matrix',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Expanded(
                      child: hMatrix != null
                          ? MatrixViewer(
                              matrix: _convertToIntMatrix(hMatrix),
                              title: 'H',
                              cellSize: cellSize,
                              showInfo: false,
                            )
                          : const Center(child: Text('N/A')),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            // G Matrix
            Expanded(
              child: Container(
                height: matrixHeight,
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: Colors.grey[800],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'G Matrix',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Expanded(
                      child: gMatrix != null
                          ? MatrixViewer(
                              matrix: _convertToIntMatrix(gMatrix),
                              title: 'G',
                              cellSize: cellSize,
                              showInfo: false,
                            )
                          : const Center(child: Text('N/A')),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildCodewordSection(AppProvider appProvider) {
    final results = appProvider.encodeResults;
    final codeword = results['codeword'];

    if (codeword == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: Colors.grey[800],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Encoded Codeword',
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.grey[700],
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              codeword.join(' '),
              style: TextStyle(
                color: Colors.green[300],
                fontFamily: 'monospace',
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Length: ${codeword.length} bits',
            style: TextStyle(color: Colors.white70, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildDecodeResultsSection(AppProvider appProvider) {
    final results = appProvider.decodeResults;
    final decodedBits = results['decoded_bits'];
    final informationBits = results['information_bits'];
    final statistics = results['statistics'];
    final algorithmUsed = results['algorithm_used'];
    final channelType = results['channel_type'];

    // 若没有解码结果，直接返回 SizedBox.shrink 交由底部状态栏提示
    if (decodedBits == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: Colors.grey[800],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Decode Results:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 12),

          _buildBitsDisplay('Decoded Bits', decodedBits, Colors.blue[300]!),

          if (informationBits != null) ...[
            const SizedBox(height: 12),

            // 原始信息位 vs 解码信息位比较
            _buildInfoBitsComparison(appProvider, informationBits),

            const SizedBox(height: 8),
            _buildBitsDisplay(
              'Information Bits (Decoded)',
              informationBits,
              Colors.green[300]!,
            ),
          ],

          if (statistics != null) ...[
            const SizedBox(height: 12),
            _buildDecodingStatistics(statistics, algorithmUsed, channelType),
          ],
        ],
      ),
    );
  }

  Widget _buildBitsDisplay(String title, List<dynamic> bits, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.w500,
            color: Colors.white,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.grey[700],
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            bits.join(' '),
            style: TextStyle(
              color: color,
              fontFamily: 'monospace',
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDecodingStatistics(
    Map<String, dynamic> statistics,
    String? algorithmUsed,
    String? channelType,
  ) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.grey[700],
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Decoding Statistics',
            style: TextStyle(
              fontWeight: FontWeight.w500,
              color: Colors.white,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (statistics['iterations'] != null)
                      _buildStatItem(
                        'Iterations',
                        statistics['iterations'].toString(),
                      ),
                    if (statistics['converged'] != null)
                      _buildStatItem(
                        'Converged',
                        statistics['converged'].toString(),
                      ),
                    if (algorithmUsed != null)
                      _buildStatItem('Algorithm', algorithmUsed),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (statistics['syndrome_norm'] != null)
                      _buildStatItem(
                        'Syndrome Norm',
                        statistics['syndrome_norm'].toStringAsFixed(4),
                      ),
                    if (statistics['llr_magnitude'] != null)
                      _buildStatItem(
                        'LLR Magnitude',
                        statistics['llr_magnitude'].toStringAsFixed(4),
                      ),
                    if (channelType != null)
                      _buildStatItem('Channel', channelType.toUpperCase()),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: TextStyle(color: Colors.white54, fontSize: 11),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSimulationStatusSection(AppProvider appProvider) {
    final results = appProvider.simulationResults;
    final message = results['message'] as String? ?? 'Ready';
    final ber = results['ber']?.toString() ?? 'N/A';

    return Container(
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: Colors.grey[800],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Simulation Status',
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          Text(message, style: TextStyle(color: Colors.white70)),
          if (ber != 'N/A')
            Text(
              'BER: $ber',
              style: TextStyle(
                color: Colors.green[300],
                fontWeight: FontWeight.bold,
              ),
            ),
        ],
      ),
    );
  }
  // 移除未使用的方法

  Widget _buildChartSection(AppProvider appProvider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 标题行
        Row(
          children: [
            Text(
              'BER Performance & Simulation',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // 仿真结果显示区域
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(8.0),
            decoration: BoxDecoration(
              color: Colors.grey[800],
              borderRadius: BorderRadius.circular(8),
            ),
            child: _buildSimulationResults(appProvider),
          ),
        ),
      ],
    );
  }

  // 构建仿真结果显示
  Widget _buildSimulationResults(AppProvider appProvider) {
    if (appProvider.simulationResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.show_chart, size: 48, color: Colors.grey[400]),
            SizedBox(height: 8),
            Text(
              'No simulation data available.\nRun Quick Test or Full Simulation to see BER performance.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white54),
            ),
          ],
        ),
      );
    }

    final message = appProvider.simulationResults['message'] ?? '';

    // 显示错误信息
    if (appProvider.simulationResults.containsKey('error')) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.red[900],
          border: Border.all(color: Colors.red[700]!),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(Icons.error, color: Colors.red[300]),
                const SizedBox(width: 8),
                Text(
                  'Simulation Failed',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.red[300],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message, style: TextStyle(color: Colors.white70)),
          ],
        ),
      );
    }

    // 显示快速测试结果
    if (appProvider.simulationResults.containsKey('test_result')) {
      return _buildQuickTestResults(
        appProvider.simulationResults['test_result'],
      );
    }

    // 显示完整仿真结果
    if (appProvider.simulationResults.containsKey('simulation_results')) {
      return _buildFullSimulationResults(
        appProvider.simulationResults['simulation_results'],
      );
    }

    // 显示基本消息
    return Center(
      child: Text(message, style: TextStyle(color: Colors.white70)),
    );
  }

  // 快速测试结果显示
  Widget _buildQuickTestResults(Map<String, dynamic> testResult) {
    final snrDb = testResult['snr_db']?.toString() ?? 'N/A';
    final ber = testResult['ber']?.toStringAsExponential(2) ?? 'N/A';
    final fer = testResult['fer']?.toStringAsExponential(2) ?? 'N/A';
    final simTime = testResult['simulation_time']?.toStringAsFixed(3) ?? 'N/A';
    final avgIter = testResult['avg_iterations']?.toStringAsFixed(1) ?? 'N/A';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.green[900],
            border: Border.all(color: Colors.green[700]!),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green[300]),
              const SizedBox(width: 8),
              Text(
                'Quick Test Results',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.green[300],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: SingleChildScrollView(
            child: Table(
              columnWidths: const {
                0: FlexColumnWidth(1),
                1: FlexColumnWidth(1),
              },
              children: [
                _buildTableRow('SNR', '$snrDb dB'),
                _buildTableRow('BER', ber),
                _buildTableRow('FER', fer),
                _buildTableRow('Sim Time', '$simTime s'),
                _buildTableRow('Avg Iterations', avgIter),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // 完整仿真结果显示
  Widget _buildFullSimulationResults(Map<String, dynamic> simResults) {
    final snrList = List<double>.from(simResults['snr_db'] ?? []);
    final berList = List<double>.from(simResults['ber'] ?? []);
    final ferList = List<double>.from(simResults['fer'] ?? []);

    if (snrList.isEmpty) {
      return Center(
        child: Text(
          'No simulation data',
          style: TextStyle(color: Colors.white54),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.green[900],
            border: Border.all(color: Colors.green[700]!),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green[300]),
              const SizedBox(width: 8),
              Text(
                'Simulation Complete',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.green[300],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Expanded(child: _buildBERChart(snrList, berList, ferList)),
      ],
    );
  }

  TableRow _buildTableRow(String label, String value) {
    return TableRow(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Text(
            label,
            style: TextStyle(fontWeight: FontWeight.w500, color: Colors.white),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Text(value, style: TextStyle(color: Colors.white70)),
        ),
      ],
    );
  }

  Widget _buildBERChart(
    List<double> snrList,
    List<double> berList,
    List<double> ferList,
  ) {
    if (snrList.isEmpty || berList.isEmpty) {
      return Center(
        child: Text(
          'No valid BER data points',
          style: TextStyle(color: Colors.white54),
        ),
      );
    }

    // 创建BER数据点
    final berSpots = <FlSpot>[];
    for (int i = 0; i < math.min(snrList.length, berList.length); i++) {
      if (berList[i] > 0) {
        berSpots.add(FlSpot(snrList[i], math.log(berList[i]) / math.log(10)));
      }
    }

    // 创建FER数据点（如果有）
    final ferSpots = <FlSpot>[];
    if (ferList.isNotEmpty) {
      for (int i = 0; i < math.min(snrList.length, ferList.length); i++) {
        if (ferList[i] > 0) {
          ferSpots.add(FlSpot(snrList[i], math.log(ferList[i]) / math.log(10)));
        }
      }
    }

    final allSpots = [...berSpots, ...ferSpots];
    if (allSpots.isEmpty) {
      return Center(
        child: Text(
          'No valid data points to display',
          style: TextStyle(color: Colors.white54),
        ),
      );
    }

    // 计算Y轴范围
    final minY = allSpots.map((spot) => spot.y).reduce(math.min);
    final maxY = allSpots.map((spot) => spot.y).reduce(math.max);
    final yRange = maxY - minY;
    final yMin = minY - yRange * 0.1;
    final yMax = maxY + yRange * 0.1;

    return Column(
      children: [
        // 美化的图例
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.grey[800]!.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[600]!, width: 0.5),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.analytics, color: Colors.white, size: 16),
              SizedBox(width: 8),
              Text(
                'Performance Curves:',
                style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
              ),
              SizedBox(width: 16),
              if (berSpots.isNotEmpty) ...[
                Container(
                  width: 20,
                  height: 3,
                  decoration: BoxDecoration(
                    color: const Color(0xFF2196F3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                SizedBox(width: 6),
                Text('BER', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500)),
              ],
              if (ferSpots.isNotEmpty) ...[
                SizedBox(width: 20),
                Container(
                  width: 20,
                  height: 3,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE53E3E),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                SizedBox(width: 6),
                Text('FER', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500)),
              ],
            ],
          ),
        ),
        SizedBox(height: 8),
        // 图表
        Expanded(
          child: LineChart(
            LineChartData(
              minY: yMin,
              maxY: yMax,
              gridData: FlGridData(
                show: true,
                drawHorizontalLine: true,
                drawVerticalLine: true,
                horizontalInterval: 1.0,
                verticalInterval: 0.5,
                getDrawingHorizontalLine: (value) {
                  return FlLine(
                    color: Colors.grey[500]!.withValues(alpha: 0.3),
                    strokeWidth: 0.8,
                    dashArray: [3, 3],
                  );
                },
                getDrawingVerticalLine: (value) {
                  return FlLine(
                    color: Colors.grey[500]!.withValues(alpha: 0.3),
                    strokeWidth: 0.8,
                    dashArray: [3, 3],
                  );
                },
              ),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  axisNameWidget: RotatedBox(
                    quarterTurns: 3,
                    child: Text(
                      'Error Rate (log₁₀)',
                      style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 50,
                    interval: 1.0, // Y轴间隔
                    getTitlesWidget: (value, meta) {
                      return Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: Text(
                          value.toStringAsFixed(0),
                          style: TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.w500),
                        ),
                      );
                    },
                  ),
                ),
                bottomTitles: AxisTitles(
                  axisNameWidget: Text(
                    'SNR (dB)',
                    style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 35,
                    interval: 0.5, // 显示0.5的间隔
                    getTitlesWidget: (value, meta) {
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          value % 1 == 0 ? '${value.toInt()}' : value.toStringAsFixed(1),
                          style: TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.w500),
                        ),
                      );
                    },
                  ),
                ),
                rightTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                topTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
              ),
              borderData: FlBorderData(
                show: true,
                border: Border.all(color: Colors.grey[500]!, width: 1.5),
              ),
              lineBarsData: [
                // BER曲线
                if (berSpots.isNotEmpty)
                  LineChartBarData(
                    spots: berSpots,
                    isCurved: true,
                    curveSmoothness: 0.3,
                    color: const Color(0xFF2196F3), // 更亮的蓝色
                    barWidth: 3,
                    isStrokeCapRound: true,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, percent, barData, index) {
                        return FlDotCirclePainter(
                          radius: 4,
                          color: const Color(0xFF2196F3),
                          strokeWidth: 2,
                          strokeColor: Colors.white,
                        );
                      },
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: const Color(0xFF2196F3).withValues(alpha: 0.1),
                    ),
                    shadow: Shadow(
                      color: const Color(0xFF2196F3).withValues(alpha: 0.3),
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ),
                // FER曲线
                if (ferSpots.isNotEmpty)
                  LineChartBarData(
                    spots: ferSpots,
                    isCurved: true,
                    curveSmoothness: 0.3,
                    color: const Color(0xFFE53E3E), // 更亮的红色
                    barWidth: 3,
                    isStrokeCapRound: true,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, percent, barData, index) {
                        return FlDotCirclePainter(
                          radius: 4,
                          color: const Color(0xFFE53E3E),
                          strokeWidth: 2,
                          strokeColor: Colors.white,
                        );
                      },
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: const Color(0xFFE53E3E).withValues(alpha: 0.1),
                    ),
                    shadow: Shadow(
                      color: const Color(0xFFE53E3E).withValues(alpha: 0.3),
                      blurRadius: 3,
                      offset: const Offset(0, 2),
                    ),
                  ),
              ],
              // 添加触摸交互
              lineTouchData: LineTouchData(
                enabled: true,
                touchTooltipData: LineTouchTooltipData(
                  tooltipBgColor: Colors.black87,
                  tooltipRoundedRadius: 8,
                  tooltipPadding: const EdgeInsets.all(8),
                  getTooltipItems: (touchedSpots) {
                    return touchedSpots.map((spot) {
                      final snr = spot.x.toStringAsFixed(1);
                      final errorRate = math.pow(10, spot.y).toStringAsExponential(2);
                      final lineColor = spot.barIndex == 0 
                          ? const Color(0xFF2196F3) 
                          : const Color(0xFFE53E3E);
                      final label = spot.barIndex == 0 ? 'BER' : 'FER';
                      
                      return LineTooltipItem(
                        '$label\nSNR: $snr dB\nRate: $errorRate',
                        TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w500,
                          fontSize: 11,
                        ),
                        children: [
                          TextSpan(
                            text: '\n●',
                            style: TextStyle(
                              color: lineColor,
                              fontSize: 16,
                            ),
                          ),
                        ],
                      );
                    }).toList();
                  },
                ),
                getTouchedSpotIndicator: (barData, spotIndexes) {
                  return spotIndexes.map((index) {
                    return TouchedSpotIndicatorData(
                      FlLine(
                        color: barData.color!.withValues(alpha: 0.8),
                        strokeWidth: 2,
                        dashArray: [3, 3],
                      ),
                      FlDotData(
                        getDotPainter: (spot, percent, barData, index) {
                          return FlDotCirclePainter(
                            radius: 6,
                            color: barData.color!,
                            strokeWidth: 2,
                            strokeColor: Colors.white,
                          );
                        },
                      ),
                    );
                  }).toList();
                },
              ),
            ),
          ),
        ),
      ],
    );
  }

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

  Widget _buildInfoBitsComparison(
    AppProvider appProvider,
    List informationBits,
  ) {
    final originalInfoBits = appProvider.infoBits;
    final decodedInfoBits = informationBits.cast<int>();

    // 计算错误数
    int errors = 0;
    for (
      int i = 0;
      i < originalInfoBits.length && i < decodedInfoBits.length;
      i++
    ) {
      if (originalInfoBits[i] != decodedInfoBits[i]) errors++;
    }

    final isSuccess = errors == 0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isSuccess ? Colors.green[800] : Colors.red[800],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isSuccess ? Colors.green[400]! : Colors.red[400]!,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isSuccess ? Icons.check_circle : Icons.error,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                isSuccess ? 'Perfect Recovery!' : 'Decoding Failed',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // 原始信息位
          Row(
            children: [
              const SizedBox(
                width: 120,
                child: Text(
                  'Original Info:',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ),
              Expanded(
                child: _buildCompactBitDisplay(
                  originalInfoBits,
                  Colors.blue[600]!,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),

          // 解码信息位
          Row(
            children: [
              const SizedBox(
                width: 120,
                child: Text(
                  'Decoded Info:',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ),
              Expanded(
                child: _buildCompactBitDisplay(
                  decodedInfoBits,
                  isSuccess ? Colors.green[600]! : Colors.red[600]!,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          Text(
            isSuccess
                ? 'All information bits recovered correctly!'
                : '$errors information bit error(s) detected.',
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactBitDisplay(List<int> bits, Color color) {
    return Wrap(
      spacing: 3,
      runSpacing: 3,
      children: bits
          .map(
            (bit) => Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: Colors.white24),
              ),
              child: Center(
                child: Text(
                  bit.toString(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          )
          .toList(),
    );
  }
}
