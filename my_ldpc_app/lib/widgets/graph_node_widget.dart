// lib/widgets/graph_node_widget.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';

class GraphNodeWidget extends StatelessWidget {
  final Node node;

  const GraphNodeWidget({super.key, required this.node});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, appProvider, child) {
        final isSelected = appProvider.selectedNode?.id == node.id;

        return GestureDetector(
          onTap: () => appProvider.tapNode(node),
          onPanUpdate: (details) {
            appProvider.updateNodePosition(node.id, details.delta);
          },
          onLongPress: () => _showNodeProperties(context),
          child: Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              shape: node.isVariableNode ? BoxShape.circle : BoxShape.rectangle,
              color: _getNodeColor(isSelected),
              border: Border.all(
                color: isSelected 
                    ? const Color(0xFFFFA726) // Soft orange highlight
                    : const Color(0xFFE8E8F0).withValues(alpha: 0.6), // Soft white border
                width: isSelected ? 3 : 1.5,
              ),
              borderRadius: node.isVariableNode
                  ? null
                  : BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.15), // Soft shadow
                  blurRadius: 6,
                  offset: const Offset(2, 3),
                ),
                if (isSelected) // Add glow effect when selected
                  BoxShadow(
                    color: _getNodeColor(true).withValues(alpha: 0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 0),
                  ),
              ],
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    node.id,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      shadows: [
                        Shadow(
                          color: Colors.black45,
                          offset: Offset(1, 1),
                          blurRadius: 2,
                        ),
                      ],
                    ),
                  ),
                  Text(
                    _getNodeDegree(context).toString(),
                    style: const TextStyle(
                      color: Color(0xFFE8E8F0),
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
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

  Color _getNodeColor(bool isSelected) {
    if (isSelected) {
      // 选中状态：更亮的颜色
      return node.isVariableNode 
          ? const Color(0xFF64B5F6) // 柔和的亮蓝色
          : const Color(0xFF81C784); // 柔和的绿色替代红色
    }
    // 未选中状态：更深的颜色
    return node.isVariableNode 
        ? const Color(0xFF4A90E2) // 柔和的蓝色
        : const Color(0xFF66BB6A); // 柔和的绿色替代红色
  }

  int _getNodeDegree(BuildContext context) {
    final edges = context.read<AppProvider>().edges;
    return edges
        .where((edge) => edge.fromId == node.id || edge.toId == node.id)
        .length;
  }

  void _showNodeProperties(BuildContext context) {
    final degree = _getNodeDegree(context);

    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Node Properties'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('ID: ${node.id}'),
              Text(
                'Type: ${node.isVariableNode ? "Variable Node" : "Check Node"}',
              ),
              Text('Degree: $degree'),
              Text(
                'Position: (${node.position.dx.toInt()}, ${node.position.dy.toInt()})',
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
            TextButton(
              onPressed: () {
                context.read<AppProvider>().removeNode(node.id);
                Navigator.of(context).pop();
              },
              child: const Text('Delete', style: TextStyle(color: Color(0xFFEF5350))), // 更柔和的红色
            ),
          ],
        );
      },
    );
  }
}
