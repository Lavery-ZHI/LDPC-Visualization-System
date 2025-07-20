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
            color: Colors.grey[850],
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
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Nodes: ${appProvider.nodes.length}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'Edges: ${appProvider.edges.length}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'Variable: ${appProvider.nodes.where((n) => n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'Check: ${appProvider.nodes.where((n) => !n.isVariableNode).length}',
                            style: const TextStyle(
                              color: Colors.white,
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
      ..color = Colors.white70
      ..strokeWidth = 2.0;

    final selectedPaint = Paint()
      ..color = Colors.amber
      ..strokeWidth = 3.0;

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
