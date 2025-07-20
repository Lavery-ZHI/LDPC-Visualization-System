// lib/widgets/control_panel.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';

class ControlPanel extends StatelessWidget {
  const ControlPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(8.0),
      elevation: 4.0,
      child: SizedBox(
        height: double.infinity,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'LDPC Designer',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 16),

              // 图构建部分
              _buildGraphSection(context),
              const SizedBox(height: 16),

              // 编码生成部分
              _buildEncodingSection(context),
              const SizedBox(height: 16),

              // 解码部分
              _buildDecodingSection(context),
              const SizedBox(height: 16),

              // 仿真部分
              _buildSimulationSection(context),
              const SizedBox(height: 16),

              // 操作按钮
              _buildActionButtons(context),

              // 底部间距
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGraphSection(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Graph Construction',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: appProvider.addVariableNode,
                    icon: Icon(Icons.circle_outlined),
                    label: Text('Add Variable'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue[600],
                      padding: EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: appProvider.addCheckNode,
                    icon: Icon(Icons.square_outlined),
                    label: Text('Add Check'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red[600],
                      padding: EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8.0),
              decoration: BoxDecoration(
                color: Colors.grey[800],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Column(
                    children: [
                      Text(
                        'V-Nodes',
                        style: TextStyle(fontSize: 12, color: Colors.blue[300]),
                      ),
                      Text(
                        '${appProvider.nodes.where((n) => n.isVariableNode).length}',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  Column(
                    children: [
                      Text(
                        'C-Nodes',
                        style: TextStyle(fontSize: 12, color: Colors.red[300]),
                      ),
                      Text(
                        '${appProvider.nodes.where((n) => !n.isVariableNode).length}',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  Column(
                    children: [
                      Text(
                        'Edges',
                        style: TextStyle(fontSize: 12, color: Colors.white70),
                      ),
                      Text(
                        '${appProvider.edges.length}',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildEncodingSection(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'LDPC Encoding',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            // 生成LDPC码按钮
            ElevatedButton.icon(
              onPressed: appProvider.nodes.isEmpty
                  ? null
                  : () => appProvider.generateLDPCCode(),
              icon: const Icon(Icons.code),
              label: const Text('Generate LDPC Code'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green[700],
                minimumSize: const Size.fromHeight(50),
              ),
            ),

            const SizedBox(height: 12),

            // 信息位输入和编码
            if (appProvider.encodeResults['h_matrix'] != null) ...[
              _buildInfoBitsInputWidget(appProvider),
            ],

            // 编码参数显示
            if (appProvider.encodeResults['n'] != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12.0),
                decoration: BoxDecoration(
                  color: Colors.grey[800],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildParamDisplay('n', appProvider.encodeResults['n']),
                        _buildParamDisplay('k', appProvider.encodeResults['k']),
                        _buildParamDisplay('m', appProvider.encodeResults['m']),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _buildParamDisplay(
                          'Rate',
                          appProvider.encodeResults['code_rate']
                              ?.toStringAsFixed(3),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _buildDecodingSection(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'LDPC Decoding',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),

            // 解码模式和算法选择
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: appProvider.selectedDecodeMode,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Input Mode',
                      border: OutlineInputBorder(),
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 8,
                      ),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'llr', child: Text('LLR')),
                      DropdownMenuItem(value: 'awgn', child: Text('AWGN')),
                      DropdownMenuItem(value: 'bsc', child: Text('BSC')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        appProvider.setDecodeMode(value);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: appProvider.selectedAlgorithm,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Algorithm',
                      border: OutlineInputBorder(),
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 8,
                      ),
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'min_sum',
                        child: Text('Min-Sum'),
                      ),
                      DropdownMenuItem(
                        value: 'sum_product',
                        child: Text('Sum-Product'),
                      ),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        appProvider.setAlgorithm(value);
                      }
                    },
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // 解码参数输入
            _buildCompactDecodeParameters(appProvider),

            const SizedBox(height: 8),

            // 解码按钮
            ElevatedButton.icon(
              onPressed: appProvider.encodeResults['h_matrix'] == null
                  ? null
                  : () => appProvider.decodeData(),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Decode Data'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange[700],
                minimumSize: const Size.fromHeight(40),
              ),
            ),

            // 解码状态指示
            if (appProvider.decodeResults['decoded_bits'] != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: Colors.green[800],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle,
                      color: Colors.white,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Decoded ${appProvider.decodeResults['decoded_bits'].length} bits',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _buildCompactDecodeParameters(AppProvider appProvider) {
    return Column(
      children: [
        // 通用参数
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: appProvider.maxIterationsController,
                decoration: const InputDecoration(
                  labelText: 'Max Iter',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 8,
                  ),
                ),
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: appProvider.minSumScalingController,
                decoration: const InputDecoration(
                  labelText: 'Scaling',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 8,
                  ),
                ),
                keyboardType: TextInputType.number,
              ),
            ),
          ],
        ),

        const SizedBox(height: 8),

        // 根据解码模式显示不同的输入字段
        if (appProvider.selectedDecodeMode == 'llr') ...[
          Row(
            children: [
              Expanded(
                flex: 3,
                child: TextField(
                  controller: appProvider.llrController,
                  decoration: const InputDecoration(
                    labelText: 'LLR Values',
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 8,
                    ),
                    helperText: 'e.g., 1.5,-2.3,0.8',
                  ),
                  keyboardType: TextInputType.text,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 1,
                child: Column(
                  children: [
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () => appProvider.generateLLRFromCodeword(),
                        icon: const Icon(Icons.auto_fix_high, size: 14),
                        label: const Text(
                          'Generate',
                          style: TextStyle(fontSize: 11),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue,
                          padding: const EdgeInsets.symmetric(vertical: 4),
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () => appProvider.convertBSCtoLLR(),
                        icon: const Icon(Icons.transform, size: 14),
                        label: const Text(
                          'From BSC',
                          style: TextStyle(fontSize: 11),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.purple,
                          padding: const EdgeInsets.symmetric(vertical: 4),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ] else if (appProvider.selectedDecodeMode == 'awgn') ...[
          Row(
            children: [
              Expanded(
                flex: 3,
                child: TextField(
                  controller: appProvider.receivedSignalController,
                  decoration: const InputDecoration(
                    labelText: 'Received Signal',
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 8,
                    ),
                    helperText: 'e.g., 1.2,-1.8,0.9',
                  ),
                  keyboardType: TextInputType.text,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 1,
                child: ElevatedButton.icon(
                  onPressed: () => appProvider.generateAWGNSignal(),
                  icon: const Icon(Icons.generating_tokens, size: 14),
                  label: const Text('Generate', style: TextStyle(fontSize: 11)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: TextField(
                  controller: appProvider.noiseVarianceController,
                  decoration: const InputDecoration(
                    labelText: 'Noise Variance',
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 8,
                    ),
                    helperText: 'e.g., 0.5',
                  ),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 8),
              const Text('SNR(dB):'),
              const SizedBox(width: 4),
              Expanded(
                flex: 1,
                child: DropdownButton<String>(
                  isExpanded: true,
                  hint: const Text('Select'),
                  items: ['0', '2', '4', '6', '8', '10'].map((snr) {
                    return DropdownMenuItem<String>(
                      value: snr,
                      child: Text('${snr}dB'),
                    );
                  }).toList(),
                  onChanged: (snr) => appProvider.setSNRdB(double.parse(snr!)),
                ),
              ),
            ],
          ),
        ] else if (appProvider.selectedDecodeMode == 'bsc') ...[
          _buildBitInputWidget(appProvider),
          const SizedBox(height: 8),
          // Error Probability输入和预设值
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: appProvider.crossoverProbabilityController,
                decoration: const InputDecoration(
                  labelText: 'Error Probability (信道错误率)',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 8,
                  ),
                  helperText: 'BSC信道中每个比特的翻转概率',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 4),
              // 预设值按钮
              Wrap(
                spacing: 4,
                children: [
                  _buildErrorProbabilityPreset(appProvider, '0.01', '优质信道'),
                  _buildErrorProbabilityPreset(appProvider, '0.05', '良好信道'),
                  _buildErrorProbabilityPreset(appProvider, '0.1', '一般信道'),
                  _buildErrorProbabilityPreset(appProvider, '0.2', '较差信道'),
                ],
              ),
            ],
          ),
        ],

        // 早期终止开关
        Row(
          children: [
            Checkbox(
              value: appProvider.earlyTermination,
              onChanged: (value) {
                appProvider.setEarlyTermination(value ?? true);
              },
            ),
            const Text('Early Termination', style: TextStyle(fontSize: 12)),
          ],
        ),
      ],
    );
  }

  Widget _buildParamDisplay(String label, dynamic value) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: Colors.white70),
        ),
        Text(
          value?.toString() ?? '-',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildSimulationSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Simulation Parameters',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),

        Consumer<AppProvider>(
          builder: (context, appProvider, child) {
            return Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: appProvider.snrController,
                        decoration: const InputDecoration(
                          labelText: 'SNR (dB)',
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: appProvider.frameCountController,
                        decoration: const InputDecoration(
                          labelText: 'Frames',
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed:
                      appProvider.isLoading ||
                          appProvider.nodes.isEmpty ||
                          appProvider.edges.isEmpty
                      ? null
                      : appProvider.runSimulation,
                  icon: appProvider.isLoading
                      ? SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Icon(Icons.play_arrow),
                  label: Text(
                    appProvider.isLoading ? 'Running...' : 'Run Simulation',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.purple[700],
                    minimumSize: const Size.fromHeight(50),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildActionButtons(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return Column(
          children: [
            ElevatedButton.icon(
              onPressed: appProvider.clearCanvas,
              icon: Icon(Icons.clear_all),
              label: Text('Clear Canvas'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange[700],
                minimumSize: const Size.fromHeight(45),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: appProvider.generateRandomGraph,
                    icon: Icon(Icons.shuffle),
                    label: Text('Random'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal[600],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _showTemplateDialog(context),
                    icon: Icon(Icons.dashboard),
                    label: Text('Template'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.indigo[600],
                    ),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }

  void _showTemplateDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Load Template'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: Icon(Icons.looks_3),
                title: Text('(3,6) Regular LDPC'),
                subtitle: Text('Variable degree 3, Check degree 6'),
                onTap: () {
                  context.read<AppProvider>().loadTemplate('3_6_regular');
                  Navigator.of(context).pop();
                },
              ),
              ListTile(
                leading: Icon(Icons.looks_4),
                title: Text('(4,8) Regular LDPC'),
                subtitle: Text('Variable degree 4, Check degree 8'),
                onTap: () {
                  context.read<AppProvider>().loadTemplate('4_8_regular');
                  Navigator.of(context).pop();
                },
              ),
              ListTile(
                leading: Icon(Icons.scatter_plot),
                title: Text('Irregular LDPC'),
                subtitle: Text('Mixed degree distribution'),
                onTap: () {
                  context.read<AppProvider>().loadTemplate('irregular');
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('Cancel'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildBitInputWidget(AppProvider appProvider) {
    // 确保receivedBits数组有合适的长度
    final encodeResults = appProvider.encodeResults;
    final n = encodeResults['n'] as int?;

    if (n == null || n <= 0) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey[800],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey[600]!),
        ),
        child: const Text(
          'Please generate LDPC code first to set the codeword length.',
          style: TextStyle(color: Colors.white70),
          textAlign: TextAlign.center,
        ),
      );
    }

    // 如果receivedBits长度不匹配，初始化它
    if (appProvider.receivedBits.length != n) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        appProvider.initializeReceivedBits(n);
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Received Bits:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: () => appProvider.setReceivedBitsFromCodeword(),
              icon: const Icon(Icons.copy, size: 16),
              label: const Text(
                'Copy from Codeword',
                style: TextStyle(fontSize: 12),
              ),
            ),
            const SizedBox(width: 4),
            TextButton.icon(
              onPressed: () => appProvider.addRandomErrorsToReceivedBits(),
              icon: const Icon(Icons.error_outline, size: 16),
              label: const Text('Add Errors', style: TextStyle(fontSize: 12)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.grey[850],
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[600]!),
          ),
          child: _buildBitGrid(appProvider, n),
        ),
      ],
    );
  }

  Widget _buildBitGrid(AppProvider appProvider, int length) {
    const int bitsPerRow = 8; // 每行显示8个比特
    final rows = (length / bitsPerRow).ceil();

    return Column(
      children: [
        for (int row = 0; row < rows; row++) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (int col = 0; col < bitsPerRow; col++) ...[
                () {
                  final index = row * bitsPerRow + col;
                  if (index >= length) return const SizedBox.shrink();

                  final bit = appProvider.receivedBits.length > index
                      ? appProvider.receivedBits[index]
                      : 0;

                  return Padding(
                    padding: const EdgeInsets.all(2),
                    child: _buildBitButton(appProvider, index, bit),
                  );
                }(),
              ],
            ],
          ),
          if (row < rows - 1) const SizedBox(height: 4),
        ],
      ],
    );
  }

  Widget _buildBitButton(AppProvider appProvider, int index, int bit) {
    return GestureDetector(
      onTap: () => appProvider.updateReceivedBit(index, 1 - bit), // 切换0/1
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: bit == 1 ? Colors.green[600] : Colors.red[600],
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: bit == 1 ? Colors.green[300]! : Colors.red[300]!,
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            bit.toString(),
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoBitsInputWidget(AppProvider appProvider) {
    // 获取信息位长度k
    final encodeResults = appProvider.encodeResults;
    final k = encodeResults['k'] as int?;

    if (k == null || k <= 0) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey[800],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey[600]!),
        ),
        child: const Text(
          'Generate LDPC code first to determine information bit length.',
          style: TextStyle(color: Colors.white70),
          textAlign: TextAlign.center,
        ),
      );
    }

    // 如果infoBits长度不匹配，初始化它
    if (appProvider.infoBits.length != k) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        appProvider.initializeInfoBits(k);
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Information Bits:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: () => appProvider.generateRandomInfoBits(),
              icon: const Icon(Icons.shuffle, size: 16),
              label: const Text('Random', style: TextStyle(fontSize: 12)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.grey[850],
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[600]!),
          ),
          child: _buildInfoBitGrid(appProvider, k),
        ),
        const SizedBox(height: 8),
        ElevatedButton.icon(
          onPressed: appProvider.isLoading
              ? null
              : () => appProvider.encodeInfoBits(),
          icon: const Icon(Icons.play_arrow),
          label: const Text('Encode Info Bits'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.purple[700],
            minimumSize: const Size.fromHeight(40),
          ),
        ),
      ],
    );
  }

  Widget _buildInfoBitGrid(AppProvider appProvider, int length) {
    const int bitsPerRow = 8; // 每行显示8个比特
    final rows = (length / bitsPerRow).ceil();

    return Column(
      children: [
        for (int row = 0; row < rows; row++) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (int col = 0; col < bitsPerRow; col++) ...[
                () {
                  final index = row * bitsPerRow + col;
                  if (index >= length) return const SizedBox.shrink();

                  final bit = appProvider.infoBits.length > index
                      ? appProvider.infoBits[index]
                      : 0;

                  return Padding(
                    padding: const EdgeInsets.all(2),
                    child: _buildInfoBitButton(appProvider, index, bit),
                  );
                }(),
              ],
            ],
          ),
          if (row < rows - 1) const SizedBox(height: 4),
        ],
      ],
    );
  }

  Widget _buildInfoBitButton(AppProvider appProvider, int index, int bit) {
    return GestureDetector(
      onTap: () => appProvider.updateInfoBit(index, 1 - bit), // 切换0/1
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: bit == 1 ? Colors.blue[600] : Colors.grey[600],
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: bit == 1 ? Colors.blue[300]! : Colors.grey[400]!,
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            bit.toString(),
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildErrorProbabilityPreset(
    AppProvider appProvider,
    String value,
    String label,
  ) {
    return SizedBox(
      height: 28,
      child: ElevatedButton(
        onPressed: () {
          appProvider.crossoverProbabilityController.text = value;
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.grey[700],
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          minimumSize: Size.zero,
          visualDensity: VisualDensity.compact,
        ),
        child: Text(
          '$value\n$label',
          style: const TextStyle(fontSize: 9),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
