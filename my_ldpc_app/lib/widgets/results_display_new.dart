// lib/widgets/results_display.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/app_provider.dart';

class ResultsDisplay extends StatelessWidget {
  const ResultsDisplay({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return Card(
          margin: const EdgeInsets.all(16.0),
          elevation: 4.0,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Results & Analysis',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),

                // 状态信息
                _buildStatusSection(appProvider),
                const SizedBox(height: 16),

                // H 矩阵展示
                _buildMatrixSection(appProvider),
                const SizedBox(height: 16),

                // BER/FER 曲线
                Expanded(child: _buildChartSection(appProvider)),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusSection(AppProvider appProvider) {
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
            'Status',
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

  Widget _buildMatrixSection(AppProvider appProvider) {
    final results = appProvider.simulationResults;
    final hMatrix = results['h_matrix'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Parity Check Matrix (H)',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        const SizedBox(height: 8),
        Container(
          height: 120,
          padding: const EdgeInsets.all(8.0),
          decoration: BoxDecoration(
            color: Colors.grey[800],
            borderRadius: BorderRadius.circular(8),
          ),
          child: hMatrix != null
              ? _buildMatrixDisplay(hMatrix)
              : Center(
                  child: Text(
                    'No matrix generated yet.\nRun simulation to generate H matrix.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white54),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildMatrixDisplay(dynamic matrix) {
    if (matrix is List) {
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SingleChildScrollView(
          child: DataTable(
            columns: List.generate(
              (matrix.isNotEmpty && matrix[0] is List)
                  ? (matrix[0] as List).length
                  : 0,
              (index) => DataColumn(
                label: Text(
                  '$index',
                  style: TextStyle(fontSize: 10, color: Colors.white),
                ),
              ),
            ),
            rows: matrix.take(8).map<DataRow>((row) {
              if (row is List) {
                return DataRow(
                  cells: row.map<DataCell>((cell) {
                    return DataCell(
                      Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          color: cell == 1 ? Colors.white : Colors.transparent,
                          border: Border.all(color: Colors.grey, width: 0.5),
                        ),
                        child: Center(
                          child: Text(
                            cell.toString(),
                            style: TextStyle(
                              fontSize: 8,
                              color: cell == 1 ? Colors.black : Colors.white,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                );
              }
              return DataRow(cells: []);
            }).toList(),
          ),
        ),
      );
    }

    return Center(
      child: Text(
        'Matrix format not supported',
        style: TextStyle(color: Colors.white54),
      ),
    );
  }

  Widget _buildChartSection(AppProvider appProvider) {
    final results = appProvider.simulationResults;
    final berData = results['ber_curve'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'BER Performance',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(8.0),
            decoration: BoxDecoration(
              color: Colors.grey[800],
              borderRadius: BorderRadius.circular(8),
            ),
            child: berData != null && berData is List && berData.isNotEmpty
                ? _buildBERChart(berData)
                : Center(
                    child: Text(
                      'No BER data available.\nRun simulation to see performance curve.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white54),
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildBERChart(List berData) {
    final spots = <FlSpot>[];

    for (int i = 0; i < berData.length; i++) {
      if (berData[i] is Map) {
        final point = berData[i] as Map;
        final snr = (point['snr'] as num?)?.toDouble() ?? i.toDouble();
        final ber = (point['ber'] as num?)?.toDouble() ?? 0.0;
        if (ber > 0) {
          spots.add(FlSpot(snr, ber));
        }
      }
    }

    if (spots.isEmpty) {
      return Center(
        child: Text(
          'No valid BER data points',
          style: TextStyle(color: Colors.white54),
        ),
      );
    }

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawHorizontalLine: true,
          drawVerticalLine: true,
          getDrawingHorizontalLine: (value) {
            return FlLine(color: Colors.grey[600]!, strokeWidth: 0.5);
          },
          getDrawingVerticalLine: (value) {
            return FlLine(color: Colors.grey[600]!, strokeWidth: 0.5);
          },
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toStringAsExponential(1),
                  style: TextStyle(fontSize: 10, color: Colors.white),
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
                  '${value.toInt()}',
                  style: TextStyle(fontSize: 10, color: Colors.white),
                );
              },
            ),
          ),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(
          show: true,
          border: Border.all(color: Colors.grey[600]!, width: 1),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.blue,
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: FlDotData(show: true),
            belowBarData: BarAreaData(show: false),
          ),
        ],
      ),
    );
  }
}
