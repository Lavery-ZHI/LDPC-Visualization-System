// lib/pages/optimization_page.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class OptimizationPage extends StatefulWidget {
  const OptimizationPage({super.key});

  @override
  State<OptimizationPage> createState() => _OptimizationPageState();
}

class _OptimizationPageState extends State<OptimizationPage> {
  final TextEditingController _generationsController = TextEditingController(
    text: '50',
  );
  final TextEditingController _populationController = TextEditingController(
    text: '20',
  );
  final TextEditingController _mutationRateController = TextEditingController(
    text: '0.1',
  );

  bool _isOptimizing = false;
  final List<Map<String, dynamic>> _optimizationHistory = [];

  @override
  void dispose() {
    _generationsController.dispose();
    _populationController.dispose();
    _mutationRateController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('LDPC Code Optimization'),
        backgroundColor: Colors.grey[900],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            // 左侧参数设置面板
            Expanded(flex: 1, child: _buildParameterPanel()),
            const SizedBox(width: 16),

            // 右侧结果展示区域
            Expanded(flex: 2, child: _buildResultsPanel()),
          ],
        ),
      ),
    );
  }

  Widget _buildParameterPanel() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Genetic Algorithm Parameters',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 20),

            _buildTextField(
              controller: _generationsController,
              label: 'Generations',
              icon: Icons.loop,
            ),
            const SizedBox(height: 16),

            _buildTextField(
              controller: _populationController,
              label: 'Population Size',
              icon: Icons.group,
            ),
            const SizedBox(height: 16),

            _buildTextField(
              controller: _mutationRateController,
              label: 'Mutation Rate',
              icon: Icons.shuffle,
            ),
            const SizedBox(height: 32),

            // 目标函数选择
            Text(
              'Optimization Target',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),

            RadioListTile<String>(
              title: const Text('Minimize BER'),
              value: 'ber',
              groupValue: 'ber',
              onChanged: (value) {},
              dense: true,
            ),
            RadioListTile<String>(
              title: const Text('Minimize FER'),
              value: 'fer',
              groupValue: 'ber',
              onChanged: (value) {},
              dense: true,
            ),

            const Spacer(),

            // 操作按钮
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isOptimizing ? null : _startOptimization,
                icon: _isOptimizing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.play_arrow),
                label: Text(
                  _isOptimizing ? 'Optimizing...' : 'Start Optimization',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green[700],
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),

            const SizedBox(height: 12),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _clearResults,
                icon: const Icon(Icons.clear),
                label: const Text('Clear Results'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange[700],
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
  }) {
    return TextField(
      controller: controller,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
        isDense: true,
      ),
      keyboardType: TextInputType.number,
    );
  }

  Widget _buildResultsPanel() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Optimization Results',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 20),

            if (_optimizationHistory.isEmpty)
              const Expanded(
                child: Center(
                  child: Text(
                    'No optimization results yet.\nClick "Start Optimization" to begin.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              )
            else
              Expanded(
                child: Column(
                  children: [
                    // 统计信息
                    _buildStatsRow(),
                    const SizedBox(height: 20),

                    // 收敛曲线
                    Expanded(child: _buildConvergenceChart()),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsRow() {
    if (_optimizationHistory.isEmpty) return const SizedBox();

    final lastResult = _optimizationHistory.last;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildStatCard(
          'Best BER',
          '${lastResult['best_ber']?.toStringAsExponential(2) ?? 'N/A'}',
          Colors.green,
        ),
        _buildStatCard(
          'Generation',
          '${lastResult['generation'] ?? 0}',
          Colors.blue,
        ),
        _buildStatCard('Population', _populationController.text, Colors.purple),
      ],
    );
  }

  Widget _buildStatCard(String title, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(title, style: TextStyle(fontSize: 12, color: color)),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConvergenceChart() {
    if (_optimizationHistory.isEmpty) {
      return const Center(child: Text('No data to display'));
    }

    final spots = _optimizationHistory.asMap().entries.map((entry) {
      return FlSpot(
        entry.key.toDouble(),
        (entry.value['best_ber'] as double? ?? 0.0),
      );
    }).toList();

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawHorizontalLine: true,
          drawVerticalLine: true,
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toStringAsExponential(1),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toInt().toString(),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: true),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.blue,
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: Colors.blue.withValues(alpha: 0.1),
            ),
          ),
        ],
      ),
    );
  }

  void _startOptimization() async {
    setState(() {
      _isOptimizing = true;
      _optimizationHistory.clear();
    });

    final generations = int.tryParse(_generationsController.text) ?? 50;

    // 模拟优化过程
    for (int i = 0; i < generations; i++) {
      await Future.delayed(const Duration(milliseconds: 100));

      // 模拟收敛过程
      final progress = i / generations;
      final bestBer = 0.1 * (1.0 - 0.8 * progress) + 0.01 * (1.0 - progress);

      setState(() {
        _optimizationHistory.add({
          'generation': i + 1,
          'best_ber': bestBer,
          'avg_ber': bestBer * 1.5,
        });
      });

      if (!_isOptimizing) break; // 用户取消了优化
    }

    setState(() {
      _isOptimizing = false;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Optimization completed in $generations generations'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  void _clearResults() {
    setState(() {
      _optimizationHistory.clear();
      _isOptimizing = false;
    });
  }
}
