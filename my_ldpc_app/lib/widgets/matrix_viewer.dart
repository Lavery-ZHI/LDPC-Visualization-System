// lib/widgets/matrix_viewer.dart
import 'package:flutter/material.dart';

class MatrixViewer extends StatefulWidget {
  final List<List<int>>? matrix;
  final String title;
  final double cellSize;
  final bool showInfo; // 是否显示行/列/密度等信息栏

  const MatrixViewer({
    super.key,
    this.matrix,
    this.title = 'Matrix',
    this.cellSize = 30.0,
    this.showInfo = true,
  });

  @override
  State<MatrixViewer> createState() => _MatrixViewerState();
}

class _MatrixViewerState extends State<MatrixViewer> {
  double _scale = 1.0;
  final TransformationController _transformationController =
      TransformationController();
  bool _hasInitialized = false;

  @override
  void dispose() {
    _transformationController.dispose();
    super.dispose();
  }

  void _initializeMatrixView(Size availableSize, int rows, int cols) {
    if (_hasInitialized || rows == 0 || cols == 0) return;
    
    // 计算合适的初始缩放比例，确保矩阵完全可见
    final cellSize = widget.cellSize;
    final matrixWidth = cols * cellSize;
    final matrixHeight = rows * cellSize;
    
    final scaleX = (availableSize.width - 40) / matrixWidth;
    final scaleY = (availableSize.height - 40) / matrixHeight;
    final optimalScale = (scaleX < scaleY ? scaleX : scaleY).clamp(0.1, 1.0);
    
    if (optimalScale < 1.0) {
      _scale = optimalScale;
      _transformationController.value = Matrix4.identity()..scale(optimalScale);
    }
    
    _hasInitialized = true;
  }

  @override
  void didUpdateWidget(MatrixViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 当矩阵数据变化时，重置初始化状态
    if (oldWidget.matrix != widget.matrix) {
      _hasInitialized = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.matrix == null || widget.matrix!.isEmpty) {
      return Container(
        decoration: BoxDecoration(
          color: Colors.grey[800],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey[600]!),
        ),
        child: const Center(
          child: Text(
            'No matrix data available',
            style: TextStyle(color: Colors.white54),
          ),
        ),
      );
    }

    final matrix = widget.matrix!;
    final rows = matrix.length;
    final cols = matrix.isNotEmpty ? matrix[0].length : 0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact =
            constraints.maxWidth < 200 || constraints.maxHeight < 150;

        return Card(
          child: Padding(
            padding: EdgeInsets.all(isCompact ? 8.0 : 16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 标题和控制按钮
                if (!isCompact)
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${widget.title} ($rows×$cols)',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                fontSize: isCompact ? 12 : 16,
                              ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      IconButton(
                        onPressed: _zoomIn,
                        icon: const Icon(Icons.zoom_in),
                        iconSize: 16,
                      ),
                      IconButton(
                        onPressed: _zoomOut,
                        icon: const Icon(Icons.zoom_out),
                        iconSize: 16,
                      ),
                      IconButton(
                        onPressed: _resetZoom,
                        icon: const Icon(Icons.center_focus_weak),
                        iconSize: 16,
                      ),
                    ],
                  ),

                // 紧凑模式的标题
                if (isCompact)
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${widget.title} ($rows×$cols)',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                            color: Colors.white,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        '${(_scale * 100).toInt()}%',
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.white70,
                        ),
                      ),
                    ],
                  ),

                // 矩阵信息
                if (widget.showInfo && !isCompact)
                  Container(
                    padding: const EdgeInsets.all(8.0),
                    decoration: BoxDecoration(
                      color: Colors.grey[800],
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildInfoItem('Rows', rows.toString()),
                        _buildInfoItem('Cols', cols.toString()),
                        _buildInfoItem('Density', _calculateDensity(matrix)),
                        _buildInfoItem('Zoom', '${(_scale * 100).toInt()}%'),
                      ],
                    ),
                  ),

                SizedBox(height: isCompact ? 4 : 12),

                // 矩阵显示区域
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, matrixConstraints) {
                      // 初始化矩阵视图的最佳缩放
                      WidgetsBinding.instance.addPostFrameCallback((_) {
                        _initializeMatrixView(
                          Size(matrixConstraints.maxWidth, matrixConstraints.maxHeight),
                          rows,
                          cols,
                        );
                      });
                      
                      return Container(
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey[600]!),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: InteractiveViewer(
                          transformationController: _transformationController,
                          minScale: 0.1,
                          maxScale: 8.0,
                          scaleEnabled: false, // 禁用滚轮缩放
                          panEnabled: true, // 保留拖拽平移
                          onInteractionUpdate: (details) {
                            setState(() {
                              _scale = _transformationController.value
                                  .getMaxScaleOnAxis();
                            });
                          },
                          child: _buildMatrixGrid(matrix),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildInfoItem(String label, String value) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: Colors.white70),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
      ],
    );
  }

  Widget _buildMatrixGrid(List<List<int>> matrix) {
    final rows = matrix.length;
    final cols = matrix[0].length;

    return LayoutBuilder(
      builder: (context, constraints) {
        // 如果矩阵过大，优化显示 - 更宽松的显示条件
        final showIndices = widget.cellSize > 16;

        return Center(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SingleChildScrollView(
              child: Container(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    // 列索引头（只在足够大时显示）
                    if (showIndices)
                      Row(
                        children: [
                          SizedBox(width: widget.cellSize), // 空白角落
                          ...List.generate(cols, (col) {
                            return Container(
                              width: widget.cellSize,
                              height: widget.cellSize * 0.7,
                              alignment: Alignment.center,
                              child: Text(
                                '$col',
                                style: TextStyle(
                                  fontSize: (widget.cellSize * 0.4).clamp(
                                    8,
                                    12,
                                  ),
                                  color: Colors.blue,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            );
                          }),
                        ],
                      ),

                    // 矩阵内容
                    ...List.generate(rows, (row) {
                      return Row(
                        children: [
                          // 行索引（只在足够大时显示）
                          if (showIndices)
                            Container(
                              width: widget.cellSize,
                              height: widget.cellSize,
                              alignment: Alignment.center,
                              child: Text(
                                '$row',
                                style: TextStyle(
                                  fontSize: (widget.cellSize * 0.4).clamp(
                                    8,
                                    12,
                                  ),
                                  color: Colors.red,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),

                          // 行数据
                          ...List.generate(cols, (col) {
                            final value = matrix[row][col];
                            return Container(
                              width: widget.cellSize,
                              height: widget.cellSize,
                              decoration: BoxDecoration(
                                color: _getCellColor(value),
                                border: Border.all(
                                  color: Colors.grey[600]!,
                                  width: 1.0,
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  '$value',
                                  style: TextStyle(
                                    fontSize: (widget.cellSize * 0.35).clamp(
                                      8,
                                      14,
                                    ),
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            );
                          }),
                        ],
                      );
                    }),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Color _getCellColor(int value) {
    switch (value) {
      case 1:
        return Colors.blue[500]!;
      case 0:
        return Colors.grey[800]!;
      default:
        return Colors.orange[500]!; // 对于非二进制值
    }
  }

  String _calculateDensity(List<List<int>> matrix) {
    if (matrix.isEmpty) return '0%';

    int totalElements = 0;
    int nonZeroElements = 0;

    for (final row in matrix) {
      for (final element in row) {
        totalElements++;
        if (element != 0) nonZeroElements++;
      }
    }

    final density = totalElements > 0
        ? (nonZeroElements / totalElements) * 100
        : 0.0;
    return '${density.toStringAsFixed(1)}%';
  }

  void _zoomIn() {
    final newScale = (_scale * 1.3).clamp(0.1, 8.0);
    _setScale(newScale);
  }

  void _zoomOut() {
    final newScale = (_scale / 1.3).clamp(0.1, 8.0);
    _setScale(newScale);
  }

  void _resetZoom() {
    _setScale(1.0);
  }

  void _setScale(double scale) {
    _transformationController.value = Matrix4.identity()..scale(scale);
    setState(() {
      _scale = scale;
    });
  }
}
