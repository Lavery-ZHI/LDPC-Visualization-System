import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/app_provider.dart';
import 'dart:math';

class BERChart extends StatefulWidget {
  const BERChart({super.key});

  @override
  State<BERChart> createState() => _BERChartState();
}

class _BERChartState extends State<BERChart>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;
  bool _showBER = true;
  bool _showFER = true;
  bool _showGrid = true;
  bool _showPoints = true;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOutCubic,
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        return Column(
          children: [
            // 图表控制面板
            _buildControlPanel(),
            const SizedBox(height: 16),
            // 主图表
            Expanded(child: _buildChart(provider)),
          ],
        );
      },
    );
  }

  Widget _buildControlPanel() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Column(
        children: [
          // 第一行：显示选项
          Row(
            children: [
              const Icon(Icons.tune, size: 16, color: Colors.grey),
              const SizedBox(width: 8),
              const Text(
                '显示选项:',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 16),
              _buildToggleChip('BER', _showBER, Colors.blue, (value) {
                setState(() => _showBER = value);
              }),
              const SizedBox(width: 8),
              _buildToggleChip('FER', _showFER, Colors.red, (value) {
                setState(() => _showFER = value);
              }),
              const SizedBox(width: 8),
              _buildToggleChip('网格', _showGrid, Colors.grey, (value) {
                setState(() => _showGrid = value);
              }),
              const SizedBox(width: 8),
              _buildToggleChip('数据点', _showPoints, Colors.orange, (value) {
                setState(() => _showPoints = value);
              }),
            ],
          ),
          const SizedBox(height: 8),
          // 第二行：图例
          Row(
            children: [
              const Icon(Icons.legend_toggle, size: 16, color: Colors.grey),
              const SizedBox(width: 8),
              const Text('图例:', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(width: 16),
              _buildLegendItem('误比特率 (BER)', Colors.blue),
              const SizedBox(width: 16),
              _buildLegendItem('误帧率 (FER)', Colors.red),
              const Spacer(),
              // 重新动画按钮
              IconButton(
                onPressed: () {
                  _animationController.reset();
                  _animationController.forward();
                },
                icon: const Icon(Icons.refresh),
                tooltip: '重新播放动画',
                iconSize: 20,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildToggleChip(
    String label,
    bool value,
    Color color,
    Function(bool) onChanged,
  ) {
    return FilterChip(
      label: Text(label, style: const TextStyle(fontSize: 12)),
      selected: value,
      onSelected: onChanged,
      selectedColor: color.withValues(alpha: 0.2),
      checkmarkColor: color,
      side: BorderSide(color: color, width: 1),
      labelStyle: TextStyle(
        color: value ? color : Colors.grey[600],
        fontWeight: value ? FontWeight.bold : FontWeight.normal,
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      children: [
        Container(
          width: 16,
          height: 3,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }

  Widget _buildChart(AppProvider provider) {
    if (provider.simulationResults.isEmpty) {
      return Container(
        decoration: BoxDecoration(
          color: Colors.grey[50],
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey[300]!),
        ),
        child: const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.show_chart, size: 64, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                '暂无仿真数据',
                style: TextStyle(fontSize: 16, color: Colors.grey),
              ),
              SizedBox(height: 8),
              Text(
                '运行仿真后将显示 BER/FER 性能曲线',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }

    // 获取仿真数据
    Map<String, dynamic>? simResults;

    if (provider.simulationResults.containsKey('simulation_results')) {
      simResults = provider.simulationResults['simulation_results'];
    } else if (provider.simulationResults.containsKey('test_result')) {
      // 将快速测试结果转换为图表格式
      final testResult = provider.simulationResults['test_result'];
      simResults = {
        'snr_db': [testResult['snr_db']],
        'ber': [testResult['ber']],
        'fer': [testResult['fer']],
      };
    }

    if (simResults == null) {
      return const Center(child: Text('仿真数据格式错误'));
    }

    final snrList = List<double>.from(simResults['snr_db'] ?? []);
    final berList = List<double>.from(simResults['ber'] ?? []);
    final ferList = List<double>.from(simResults['fer'] ?? []);

    if (snrList.isEmpty || berList.isEmpty || ferList.isEmpty) {
      return const Center(child: Text('仿真数据为空'));
    }

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.1),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          padding: const EdgeInsets.all(16),
          child: _buildLineChart(snrList, berList, ferList),
        );
      },
    );
  }

  Widget _buildLineChart(
    List<double> snrList,
    List<double> berList,
    List<double> ferList,
  ) {
    // 准备BER数据点
    final berSpots = <FlSpot>[];
    final ferSpots = <FlSpot>[];

    for (int i = 0; i < snrList.length; i++) {
      final snr = snrList[i];
      final ber = berList[i];
      final fer = ferList[i];

      // 转换为对数坐标，避免log(0)
      final berLog = ber > 0 ? log10(ber) : -10;
      final ferLog = fer > 0 ? log10(fer) : -10;

      // 应用动画进度
      final progress = _animation.value;
      final animatedX = snrList.first + (snr - snrList.first) * progress;

      if (animatedX <= snr) {
        berSpots.add(FlSpot(snr, berLog.toDouble()));
        ferSpots.add(FlSpot(snr, ferLog.toDouble()));
      }
    }

    // 计算Y轴范围
    final allValues = [
      if (_showBER) ...berSpots.map((s) => s.y),
      if (_showFER) ...ferSpots.map((s) => s.y),
    ];

    if (allValues.isEmpty) {
      return const Center(child: Text('请至少选择一种曲线显示'));
    }

    final minY = allValues.reduce(min);
    final maxY = allValues.reduce(max);
    final yRange = max(maxY - minY, 1.0); // 确保有最小范围
    final yMargin = yRange * 0.15; // 15% 边距

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: _showGrid,
          drawVerticalLine: true,
          drawHorizontalLine: true,
          horizontalInterval: 0.5,
          verticalInterval: 1,
          getDrawingHorizontalLine: (value) {
            return FlLine(
              color: Colors.grey[300]!,
              strokeWidth: 0.8,
              dashArray: [5, 5],
            );
          },
          getDrawingVerticalLine: (value) {
            return FlLine(
              color: Colors.grey[300]!,
              strokeWidth: 0.8,
              dashArray: [5, 5],
            );
          },
        ),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: 1,
              getTitlesWidget: (value, meta) {
                return Container(
                  margin: const EdgeInsets.only(top: 8),
                  child: Text(
                    '${value.toInt()}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: Colors.black87,
                    ),
                  ),
                );
              },
            ),
            axisNameWidget: Container(
              margin: const EdgeInsets.only(top: 8),
              child: const Text(
                'SNR (dB)',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
            ),
            axisNameSize: 25,
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              interval: 0.5,
              getTitlesWidget: (value, meta) {
                return Container(
                  margin: const EdgeInsets.only(right: 8),
                  child: Text(
                    '10^${value.toStringAsFixed(1)}',
                    style: const TextStyle(fontSize: 10, color: Colors.black87),
                  ),
                );
              },
            ),
            axisNameWidget: const RotatedBox(
              quarterTurns: 3,
              child: Text(
                'Error Rate',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
            ),
            axisNameSize: 25,
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(
          show: true,
          border: Border.all(color: Colors.grey[400]!, width: 1.5),
        ),
        minX: snrList.first,
        maxX: snrList.last,
        minY: minY - yMargin,
        maxY: maxY + yMargin,
        lineBarsData: [
          // BER 曲线
          if (_showBER)
            LineChartBarData(
              spots: berSpots,
              isCurved: true,
              curveSmoothness: 0.3,
              color: Colors.blue,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: _showPoints,
                getDotPainter: (spot, percent, barData, index) {
                  return FlDotCirclePainter(
                    radius: 5,
                    color: Colors.blue,
                    strokeWidth: 2,
                    strokeColor: Colors.white,
                  );
                },
              ),
              belowBarData: BarAreaData(
                show: true,
                color: Colors.blue.withValues(alpha: 0.1),
              ),
              shadow: Shadow(
                color: Colors.blue.withValues(alpha: 0.3),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ),
          // FER 曲线
          if (_showFER)
            LineChartBarData(
              spots: ferSpots,
              isCurved: true,
              curveSmoothness: 0.3,
              color: Colors.red,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                show: _showPoints,
                getDotPainter: (spot, percent, barData, index) {
                  return FlDotCirclePainter(
                    radius: 5,
                    color: Colors.red,
                    strokeWidth: 2,
                    strokeColor: Colors.white,
                  );
                },
              ),
              belowBarData: BarAreaData(
                show: true,
                color: Colors.red.withValues(alpha: 0.1),
              ),
              shadow: Shadow(
                color: Colors.red.withValues(alpha: 0.3),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ),
        ],
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            tooltipBgColor: Colors.black87,
            tooltipRoundedRadius: 8,
            tooltipPadding: const EdgeInsets.all(12),
            getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
              return touchedBarSpots.map((barSpot) {
                final flSpot = barSpot;
                final snr = flSpot.x.toStringAsFixed(1);
                final value = pow(10, flSpot.y).toStringAsExponential(2);
                final label =
                    (_showBER && barSpot.barIndex == 0) ||
                        (!_showBER && _showFER)
                    ? (_showBER && barSpot.barIndex == 0 ? 'BER' : 'FER')
                    : 'FER';
                final color =
                    (_showBER && barSpot.barIndex == 0) ||
                        (!_showBER && _showFER)
                    ? (_showBER && barSpot.barIndex == 0
                          ? Colors.blue
                          : Colors.red)
                    : Colors.red;

                return LineTooltipItem(
                  '📊 $label\n🎯 SNR: $snr dB\n📉 $label: $value',
                  TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                  children: [
                    TextSpan(
                      text: '\n━━━━━━━━━━',
                      style: TextStyle(color: color, fontSize: 8),
                    ),
                  ],
                );
              }).toList();
            },
          ),
          touchCallback:
              (FlTouchEvent event, LineTouchResponse? touchResponse) {
                // 可以在这里添加触摸回调逻辑
              },
          getTouchedSpotIndicator:
              (LineChartBarData barData, List<int> spotIndexes) {
                return spotIndexes.map((spotIndex) {
                  return TouchedSpotIndicatorData(
                    FlLine(
                      color: barData.color!.withValues(alpha: 0.8),
                      strokeWidth: 2,
                      dashArray: [3, 3],
                    ),
                    FlDotData(
                      getDotPainter: (spot, percent, barData, index) {
                        return FlDotCirclePainter(
                          radius: 8,
                          color: barData.color!,
                          strokeWidth: 3,
                          strokeColor: Colors.white,
                        );
                      },
                    ),
                  );
                }).toList();
              },
        ),
      ),
    );
  }
}

// 辅助函数：计算log10
double log10(double x) => log(x) / ln10;
