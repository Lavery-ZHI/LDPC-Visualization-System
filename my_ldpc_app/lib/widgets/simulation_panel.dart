import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';

class SimulationPanel extends StatefulWidget {
  const SimulationPanel({super.key});

  @override
  State<SimulationPanel> createState() => _SimulationPanelState();
}

class _SimulationPanelState extends State<SimulationPanel> {
  final _snrStartController = TextEditingController(text: '0');
  final _snrEndController = TextEditingController(text: '10');
  final _snrStepController = TextEditingController(text: '2');
  final _framesController = TextEditingController(text: '1000');
  final _maxIterationsController = TextEditingController(text: '50');

  String _selectedChannel = 'awgn';
  String _selectedAlgorithm = 'min_sum';

  @override
  void dispose() {
    _snrStartController.dispose();
    _snrEndController.dispose();
    _snrStepController.dispose();
    _framesController.dispose();
    _maxIterationsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 标题
                Row(
                  children: [
                    Icon(Icons.settings, color: Colors.blue[600]),
                    const SizedBox(width: 8),
                    Text(
                      '仿真参数',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 16),

                // SNR范围设置
                Text(
                  'SNR 范围 (dB)',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _snrStartController,
                        decoration: const InputDecoration(
                          labelText: '起始',
                          border: OutlineInputBorder(),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _snrEndController,
                        decoration: const InputDecoration(
                          labelText: '结束',
                          border: OutlineInputBorder(),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _snrStepController,
                        decoration: const InputDecoration(
                          labelText: '步长',
                          border: OutlineInputBorder(),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 16),

                // 帧数设置
                Text(
                  '仿真参数',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _framesController,
                  decoration: const InputDecoration(
                    labelText: '每个SNR点的帧数',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  keyboardType: TextInputType.number,
                ),

                const SizedBox(height: 12),

                TextField(
                  controller: _maxIterationsController,
                  decoration: const InputDecoration(
                    labelText: '最大迭代次数',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  keyboardType: TextInputType.number,
                ),

                const SizedBox(height: 16),

                // 信道类型选择
                Text(
                  '信道类型',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedChannel,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'awgn',
                      child: Text('AWGN (高斯白噪声)'),
                    ),
                    DropdownMenuItem(
                      value: 'bsc',
                      child: Text('BSC (二进制对称信道)'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedChannel = value!;
                    });
                  },
                ),

                const SizedBox(height: 12),

                // 解码算法选择
                Text(
                  '解码算法',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedAlgorithm,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'min_sum',
                      child: Text('Min-Sum 算法'),
                    ),
                    DropdownMenuItem(
                      value: 'sum_product',
                      child: Text('Sum-Product 算法'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedAlgorithm = value!;
                    });
                  },
                ),

                const SizedBox(height: 20),

                // 运行仿真按钮
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: provider.isLoading
                        ? null
                        : () => _runSimulation(provider),
                    icon: provider.isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.play_arrow),
                    label: Text(provider.isLoading ? '仿真中...' : '运行仿真'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      backgroundColor: Colors.blue[600],
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _runSimulation(AppProvider provider) async {
    // 在异步操作前获取 ScaffoldMessenger
    final scaffoldMessenger = ScaffoldMessenger.of(context);

    // 验证是否有H矩阵
    if (provider.encodeResults['h_matrix'] == null) {
      scaffoldMessenger.showSnackBar(
        const SnackBar(
          content: Text('请先生成校验矩阵'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    try {
      // 解析SNR范围
      final snrStart = double.parse(_snrStartController.text);
      final snrEnd = double.parse(_snrEndController.text);
      final snrStep = double.parse(_snrStepController.text);
      final frames = int.parse(_framesController.text);
      final maxIter = int.parse(_maxIterationsController.text);

      if (snrStart >= snrEnd || snrStep <= 0) {
        throw ArgumentError('SNR参数无效');
      }

      if (frames < 10 || maxIter < 1) {
        throw ArgumentError('仿真参数无效');
      }

      // 生成SNR范围
      List<double> snrRange = [];
      for (double snr = snrStart; snr <= snrEnd; snr += snrStep) {
        snrRange.add(snr);
      }

      // 运行仿真
      await provider.runBERSimulation(
        snrRange: snrRange,
        framesPerSnr: frames,
        channelType: _selectedChannel,
        algorithm: _selectedAlgorithm,
        maxIterations: maxIter,
      );

      if (mounted) {
        scaffoldMessenger.showSnackBar(
          const SnackBar(content: Text('仿真完成！'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        scaffoldMessenger.showSnackBar(
          SnackBar(
            content: Text('仿真失败: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
