// lib/widgets/status_bar.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';

class StatusBar extends StatelessWidget {
  const StatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, app, child) {
        // 按优先级选择要显示的消息
        String msg = app.decodeResults['message'] ?? '';
        if (msg.isEmpty || msg == 'Decoding data...') {
          msg = app.encodeResults['message'] ?? '';
        }
        if (msg.isEmpty) msg = 'Ready';

        return Container(
          height: 48,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: Colors.grey[900],
            border: const Border(top: BorderSide(color: Colors.grey)),
          ),
          child: Row(
            children: [
              Icon(
                app.isLoading ? Icons.sync : Icons.info_outline,
                color: app.isLoading ? Colors.orange : Colors.white70,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  msg,
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (app.isLoading)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.orange,
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
