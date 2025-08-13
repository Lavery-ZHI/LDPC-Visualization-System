// lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:my_ldpc_app/providers/app_provider.dart';
import 'package:my_ldpc_app/screens/main_screen.dart';
import 'package:my_ldpc_app/services/api_service.dart';

void main() {
  ApiService.init();

  runApp(
    ChangeNotifierProvider(
      create: (context) => AppProvider(),
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LDPC Studio',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4A90E2), // Soft blue
          brightness: Brightness.dark,
        ).copyWith(
          surface: const Color(0xFF1E1E2E), // Soft dark background
          surfaceContainerHighest: const Color(0xFF2A2A3A), // Card background
          primary: const Color(0xFF4A90E2), // Primary color
          secondary: const Color(0xFF64B5F6), // Secondary color
          onSurface: const Color(0xFFE8E8F0), // Text color
          onSurfaceVariant: const Color(0xFFB8B8C8), // Secondary text color
        ),
        scaffoldBackgroundColor: const Color(0xFF1A1A28), // Main background
        cardTheme: const CardThemeData(
          elevation: 2, // Lower shadow
          color: Color(0xFF2A2A3A), // Soft card background
          surfaceTintColor: Colors.transparent,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF4A90E2),
            foregroundColor: Colors.white,
            elevation: 1, // Lower button shadow
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: const Color(0xFF4A90E2),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xFF4A90E2),
            side: const BorderSide(color: Color(0xFF4A90E2)),
          ),
        ),
      ),
      debugShowCheckedModeBanner: false,
      home: const MainScreen(),
    );
  }
}
