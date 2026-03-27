import 'package:flutter/material.dart';

class SaraColors {
  // Nocturne Slate
  static const primary   = Color(0xFFECEFF1);
  static const secondary = Color(0xFF455A64);
  static const tertiary  = Color(0xFF78909C);
  static const neutral   = Color(0xFF1A1C1E);
  static const surface   = Color(0xFF1E2427);
  static const surface2  = Color(0xFF212426);
  static const surface3  = Color(0xFF263238);
  static const dim       = Color(0xFF37474F);
  static const dimmer    = Color(0xFF263238);
}

ThemeData saraTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: SaraColors.neutral,
    colorScheme: const ColorScheme.dark(
      surface: SaraColors.neutral,
      primary: SaraColors.tertiary,
    ),
    fontFamily: 'Roboto',
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF141618),
      elevation: 0,
      titleTextStyle: TextStyle(
        color: SaraColors.primary,
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
      ),
      iconTheme: IconThemeData(color: SaraColors.secondary),
    ),
    dividerColor: Color(0x0DFFFFFF),
  );
}
