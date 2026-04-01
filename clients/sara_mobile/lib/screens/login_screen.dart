import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  final VoidCallback onSignedIn;
  const LoginScreen({super.key, required this.onSignedIn});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _loading = false;
  String? _error;

  Future<void> _signIn() async {
    setState(() { _loading = true; _error = null; });
    final ok = await AuthService().signIn();
    if (!mounted) return;
    if (ok) {
      widget.onSignedIn();
    } else {
      setState(() {
        _loading = false;
        _error = 'No se pudo iniciar sesión. Intenta de nuevo.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SaraColors.neutral,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Avatar
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF1E2225),
                  border: Border.all(color: const Color(0xFF455A64), width: 1.5),
                ),
                child: const Center(
                  child: Text('S',
                    style: TextStyle(
                      fontSize: 28, fontWeight: FontWeight.bold,
                      color: Color(0xFF78909C),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              const Text('SARA',
                style: TextStyle(
                  fontSize: 30, fontWeight: FontWeight.w700,
                  color: Color(0xFFECEFF1), letterSpacing: 2,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Asistente Adaptativo',
                style: TextStyle(fontSize: 12, color: Color(0xFF546E7A),
                  letterSpacing: 1.5),
              ),
              const SizedBox(height: 48),

              // Botón Google
              _loading
                ? const CircularProgressIndicator(
                    color: Color(0xFF78909C), strokeWidth: 2)
                : SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _signIn,
                    icon: _GoogleIcon(),
                    label: const Text('Continuar con Google'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFECEFF1),
                      side: const BorderSide(color: Color(0xFF37474F)),
                      backgroundColor: const Color(0xFF1E2427),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                      textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                    ),
                  ),
                ),

              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!,
                  style: const TextStyle(color: Color(0xFFEF5350), fontSize: 12),
                  textAlign: TextAlign.center,
                ),
              ],

              const SizedBox(height: 24),
              const Text(
                'El acceso requiere autorización del creador',
                style: TextStyle(fontSize: 11, color: Color(0xFF37474F)),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GoogleIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 20, height: 20,
      child: CustomPaint(painter: _GooglePainter()),
    );
  }
}

class _GooglePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2;

    // Simplified G logo using 4 arcs
    paint.color = const Color(0xFFEA4335);
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -0.3, 1.4, true, paint);

    paint.color = const Color(0xFF34A853);
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r),
      1.1, 1.6, true, paint);

    paint.color = const Color(0xFFFBBC05);
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r),
      2.7, 0.9, true, paint);

    paint.color = const Color(0xFF4285F4);
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r),
      3.6, 1.3, true, paint);

    // Centro blanco
    paint.color = SaraColors.neutral;
    canvas.drawCircle(Offset(cx, cy), r * 0.55, paint);

    // Línea horizontal del G
    paint.color = const Color(0xFF4285F4);
    canvas.drawRect(
      Rect.fromLTWH(cx, cy - r * 0.12, r, r * 0.24), paint);
  }

  @override
  bool shouldRepaint(_) => false;
}
