// lib/widgets/resizable_panels.dart
import 'package:flutter/material.dart';

class ResizablePanels extends StatefulWidget {
  final Widget leftPanel;
  final Widget centerPanel;
  final Widget rightPanel;
  final double initialLeftWidth;
  final double initialRightWidth;
  final double minPanelWidth;

  const ResizablePanels({
    super.key,
    required this.leftPanel,
    required this.centerPanel,
    required this.rightPanel,
    this.initialLeftWidth = 350.0,
    this.initialRightWidth = 400.0,
    this.minPanelWidth = 250.0,
  });

  @override
  State<ResizablePanels> createState() => _ResizablePanelsState();
}

class _ResizablePanelsState extends State<ResizablePanels> {
  late double _leftWidth;
  late double _rightWidth;
  double _totalWidth = 0;

  @override
  void initState() {
    super.initState();
    _leftWidth = widget.initialLeftWidth;
    _rightWidth = widget.initialRightWidth;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        _totalWidth = constraints.maxWidth;

        // 确保宽度不超出边界
        _leftWidth = _leftWidth.clamp(
          widget.minPanelWidth,
          _totalWidth - widget.minPanelWidth * 2,
        );
        _rightWidth = _rightWidth.clamp(
          widget.minPanelWidth,
          _totalWidth - widget.minPanelWidth * 2,
        );

        double centerWidth =
            _totalWidth - _leftWidth - _rightWidth - 16; // 减去分割器宽度
        if (centerWidth < widget.minPanelWidth) {
          // 调整以确保中间面板有最小宽度
          double excess = widget.minPanelWidth - centerWidth;
          _leftWidth = (_leftWidth - excess / 2).clamp(
            widget.minPanelWidth,
            _totalWidth,
          );
          _rightWidth = (_rightWidth - excess / 2).clamp(
            widget.minPanelWidth,
            _totalWidth,
          );
          centerWidth = _totalWidth - _leftWidth - _rightWidth - 16;
        }

        return Row(
          children: [
            // 左侧面板
            SizedBox(width: _leftWidth, child: widget.leftPanel),

            // 左侧分割器
            _buildDivider(
              onDrag: (delta) {
                setState(() {
                  _leftWidth = (_leftWidth + delta).clamp(
                    widget.minPanelWidth,
                    _totalWidth - _rightWidth - widget.minPanelWidth - 16,
                  );
                });
              },
            ),

            // 中间面板
            SizedBox(width: centerWidth, child: widget.centerPanel),

            // 右侧分割器
            _buildDivider(
              onDrag: (delta) {
                setState(() {
                  _rightWidth = (_rightWidth - delta).clamp(
                    widget.minPanelWidth,
                    _totalWidth - _leftWidth - widget.minPanelWidth - 16,
                  );
                });
              },
            ),

            // 右侧面板
            SizedBox(width: _rightWidth, child: widget.rightPanel),
          ],
        );
      },
    );
  }

  Widget _buildDivider({required Function(double) onDrag}) {
    return MouseRegion(
      cursor: SystemMouseCursors.resizeColumn,
      child: GestureDetector(
        onPanUpdate: (details) {
          onDrag(details.delta.dx);
        },
        child: Container(
          width: 8,
          color: Colors.transparent,
          child: Center(
            child: Container(
              width: 2,
              color: Colors.grey[600],
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ),
    );
  }
}

// 竖直方向的可调整面板（用于Tab布局中的上下分割）
class ResizableVerticalPanels extends StatefulWidget {
  final Widget topPanel;
  final Widget bottomPanel;
  final double initialTopHeight;
  final double minPanelHeight;

  const ResizableVerticalPanels({
    super.key,
    required this.topPanel,
    required this.bottomPanel,
    this.initialTopHeight = 400.0,
    this.minPanelHeight = 200.0,
  });

  @override
  State<ResizableVerticalPanels> createState() =>
      _ResizableVerticalPanelsState();
}

class _ResizableVerticalPanelsState extends State<ResizableVerticalPanels> {
  late double _topHeight;

  @override
  void initState() {
    super.initState();
    _topHeight = widget.initialTopHeight;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final totalHeight = constraints.maxHeight;
        _topHeight = _topHeight.clamp(
          widget.minPanelHeight,
          totalHeight - widget.minPanelHeight - 8,
        );
        final bottomHeight = totalHeight - _topHeight - 8;

        return Column(
          children: [
            // 上面板
            SizedBox(height: _topHeight, child: widget.topPanel),

            // 分割器
            _buildHorizontalDivider(
              onDrag: (delta) {
                setState(() {
                  _topHeight = (_topHeight + delta).clamp(
                    widget.minPanelHeight,
                    totalHeight - widget.minPanelHeight - 8,
                  );
                });
              },
            ),

            // 下面板
            SizedBox(height: bottomHeight, child: widget.bottomPanel),
          ],
        );
      },
    );
  }

  Widget _buildHorizontalDivider({required Function(double) onDrag}) {
    return MouseRegion(
      cursor: SystemMouseCursors.resizeRow,
      child: GestureDetector(
        onPanUpdate: (details) {
          onDrag(details.delta.dy);
        },
        child: Container(
          height: 8,
          color: Colors.transparent,
          child: Center(
            child: Container(
              height: 2,
              color: Colors.grey[600],
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ),
    );
  }
}
