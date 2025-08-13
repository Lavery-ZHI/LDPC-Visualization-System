// lib/widgets/graph_canvas.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import 'graph_node_widget.dart';

class GraphCanvas extends StatelessWidget {
  const GraphCanvas({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        return GestureDetector(
          onTap: () => appProvider.tapCanvas(),
          child: Container(
            width: double.infinity,
            height: double.infinity,
            color: const Color(0xFF1E1E2E), // 更柔和的画布背景
            child: CustomPaint(
              painter: EdgePainter(
                edges: appProvider.edges,
                nodes: appProvider.nodes,
                selectedNode: appProvider.selectedNode,
              ),
              child: Stack(
                children: [
                  // 绘制所有节点
                  ...appProvider.nodes.map((node) {
                    return Positioned(
                      left: node.position.dx - 25, // 节点半径补偿
                      top: node.position.dy - 25,
                      child: GraphNodeWidget(node: node),
                    );
                  }),

                  // 显示图信息
                  Positioned(
                    top: 10,
                    left: 10,
                    child: Container(
                      padding: const EdgeInsets.all(8.0),
                      decoration: BoxDecoration(
                        color: const Color(0xFF2A2A3A).withValues(alpha: 0.9), // Soft info box background
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(0xFF4A90E2).withValues(alpha: 0.3),
                          width: 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Nodes: ${appProvider.nodes.length}',
                            style: const TextStyle(
                              color: Color(0xFFE8E8F0), // 更柔和的白色
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            'Edges: ${appProvider.edges.length}',
                            style: const TextStyle(
                              color: Color(0xFFE8E8F0),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            'Variable: ${appProvider.nodes.where((n) => n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Color(0xFFB8B8C8), // 更柔和的次要文字颜色
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'Check: ${appProvider.nodes.where((n) => !n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Color(0xFFB8B8C8),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

/// 自定义画笔，用于绘制边
class EdgePainter extends CustomPainter {
  final List<Edge> edges;
  final List<Node> nodes;
  final Node? selectedNode;

  EdgePainter({required this.edges, required this.nodes, this.selectedNode});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFB8B8C8).withValues(alpha: 0.6) // Soft connection color
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round; // 圆润的线条端点

    final selectedPaint = Paint()
      ..color = const Color(0xFFFFA726) // 更柔和的橙色高亮
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    // 创建节点ID到位置的映射
    final nodePositions = <String, Offset>{};
    for (final node in nodes) {
      nodePositions[node.id] = node.position;
    }

    // 绘制所有边
    for (final edge in edges) {
      final fromPos = nodePositions[edge.fromId];
      final toPos = nodePositions[edge.toId];

      if (fromPos != null && toPos != null) {
        // 如果当前边连接到选中的节点，高亮显示
        final isSelected =
            selectedNode != null &&
            (edge.fromId == selectedNode!.id || edge.toId == selectedNode!.id);

        canvas.drawLine(fromPos, toPos, isSelected ? selectedPaint : paint);
      }
    }

    // 如果有选中的节点，绘制指向光标的虚线（可选功能）
    if (selectedNode != null) {
      final selectedPaint = Paint()
        ..color = Colors.amber.withValues(alpha: 0.5)
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;

      // 绘制选中节点的光环
      canvas.drawCircle(selectedNode!.position, 35, selectedPaint);
    }
  }

  @override
  bool shouldRepaint(EdgePainter oldDelegate) {
    return oldDelegate.edges != edges ||
        oldDelegate.nodes != nodes ||
        oldDelegate.selectedNode != selectedNode;
  }
}
