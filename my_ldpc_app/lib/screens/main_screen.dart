// lib/screens/main_screen.dart
import 'package:flutter/material.dart';
import 'package:my_ldpc_app/providers/app_provider.dart';
import 'package:my_ldpc_app/widgets/control_panel.dart';
import 'package:my_ldpc_app/widgets/graph_canvas.dart';
import 'package:my_ldpc_app/widgets/results_display.dart';
import 'package:my_ldpc_app/widgets/resizable_panels.dart';
import 'package:my_ldpc_app/widgets/status_bar.dart';
import 'package:my_ldpc_app/pages/optimization_page.dart';
import 'package:provider/provider.dart';

class MainScreen extends StatelessWidget {
  const MainScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('LDPC Designer & Optimizer'),
        backgroundColor: Colors.grey[900],
        elevation: 0,
        actions: [
          Consumer<AppProvider>(
            builder: (context, appProvider, child) {
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: appProvider.isLoading
                      ? Colors.orange[800]
                      : Colors.green[800],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (appProvider.isLoading)
                      const SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      ),
                    if (appProvider.isLoading) const SizedBox(width: 8),
                    Text(
                      appProvider.isLoading ? 'Processing...' : 'Ready',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          IconButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const OptimizationPage(),
                ),
              );
            },
            icon: const Icon(Icons.tune),
            tooltip: 'Optimization',
          ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          // 响应式布局：根据屏幕宽度决定布局方式
          final screenWidth = constraints.maxWidth;

          // 调整断点，更好的响应式体验
          if (screenWidth < 900) {
            // 小屏幕：使用Tab布局
            return _buildTabletLayout();
          } else if (screenWidth < 1400) {
            // 中屏幕：使用简化的两栏布局
            return _buildMediumLayout(screenWidth);
          } else {
            // 大屏幕：使用三栏布局
            return _buildDesktopLayout(screenWidth);
          }
        },
      ),
      bottomNavigationBar: const StatusBar(),
    );
  }

  Widget _buildDesktopLayout(double screenWidth) {
    // 计算初始宽度，调整左侧面板宽度
    final initialLeftWidth = (screenWidth * 0.22).clamp(320.0, 400.0);
    final initialRightWidth = (screenWidth * 0.28).clamp(350.0, 450.0);

    return ResizablePanels(
      initialLeftWidth: initialLeftWidth,
      initialRightWidth: initialRightWidth,
      minPanelWidth: 300.0,
      leftPanel: const ControlPanel(),
      centerPanel: Container(
        margin: const EdgeInsets.all(8.0),
        decoration: BoxDecoration(
          color: Colors.grey[850],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey[700]!, width: 1),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: const GraphCanvas(),
        ),
      ),
      rightPanel: const ResultsDisplay(),
    );
  }

  Widget _buildMediumLayout(double screenWidth) {
    // 中屏幕：使用左右两栏布局
    final leftPanelWidth = (screenWidth * 0.35).clamp(320.0, 450.0);

    return Row(
      children: [
        // 左侧控制面板
        SizedBox(width: leftPanelWidth, child: const ControlPanel()),

        // 右侧分为图形和结果的上下布局
        Expanded(
          child: Column(
            children: [
              // 图形区域
              Expanded(
                flex: 3,
                child: Container(
                  margin: const EdgeInsets.all(8.0),
                  decoration: BoxDecoration(
                    color: Colors.grey[850],
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey[700]!, width: 1),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: const GraphCanvas(),
                  ),
                ),
              ),

              // 结果区域
              Expanded(flex: 2, child: const ResultsDisplay()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTabletLayout() {
    return DefaultTabController(
      length: 4,
      child: Column(
        children: [
          Container(
            color: Colors.grey[900],
            child: const TabBar(
              indicatorColor: Colors.blue,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.grey,
              isScrollable: true,
              tabs: [
                Tab(icon: Icon(Icons.settings), text: 'Controls'),
                Tab(icon: Icon(Icons.scatter_plot), text: 'Graph'),
                Tab(icon: Icon(Icons.analytics), text: 'Results'),
                Tab(icon: Icon(Icons.view_column), text: 'Split'),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              children: [
                // 控制面板页
                const ControlPanel(),

                // 图形编辑页
                Container(
                  margin: const EdgeInsets.all(8.0),
                  decoration: BoxDecoration(
                    color: Colors.grey[850],
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey[700]!, width: 1),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: const GraphCanvas(),
                  ),
                ),

                // 结果显示页
                const ResultsDisplay(),

                // 分割视图页 - 可调整的上下布局
                ResizableVerticalPanels(
                  initialTopHeight: 400.0,
                  minPanelHeight: 200.0,
                  topPanel: Container(
                    margin: const EdgeInsets.all(8.0),
                    decoration: BoxDecoration(
                      color: Colors.grey[850],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[700]!, width: 1),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: const GraphCanvas(),
                    ),
                  ),
                  bottomPanel: const ResultsDisplay(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
