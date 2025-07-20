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
                color: isSelected ? Colors.amber : Colors.white,
                width: isSelected ? 3 : 2,
              ),
              borderRadius: node.isVariableNode
                  ? null
                  : BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: Colors.black26,
                  blurRadius: 4,
                  offset: const Offset(2, 2),
                ),
              ],
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    node.id,
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                  Text(
                    _getNodeDegree(context).toString(),
                    style: TextStyle(color: Colors.white70, fontSize: 10),
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
      return node.isVariableNode ? Colors.blue[400]! : Colors.red[400]!;
    }
    return node.isVariableNode ? Colors.blue[600]! : Colors.red[600]!;
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
              child: const Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        );
      },
    );
  }
}
