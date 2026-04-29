import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme.dart';
import '../monitoring/monitoring_channel.dart';

class PermissionOnboardingScreen extends StatefulWidget {
  final VoidCallback onComplete;
  const PermissionOnboardingScreen({super.key, required this.onComplete});

  @override
  State<PermissionOnboardingScreen> createState() => _PermissionOnboardingScreenState();
}

class _PermissionOnboardingScreenState extends State<PermissionOnboardingScreen>
    with WidgetsBindingObserver {
  int _step = 0;
  bool _waitingForSettings = false;

  // Pasos: [mic, notif, usageStats, notifListener, accessibility, battery]
  static const int _totalSteps = 6;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _runStep());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Cuando el usuario vuelve de Ajustes, verificamos si concedió el permiso.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _waitingForSettings) {
      _waitingForSettings = false;
      // Pequeño delay para que el sistema registre el cambio
      Future.delayed(const Duration(milliseconds: 500), _advance);
    }
  }

  Future<void> _runStep() async {
    if (!mounted) return;
    switch (_step) {
      case 0:
        await _requestMic();
      case 1:
        await _requestNotif();
      case 2:
        await _requestSpecial(
          title: 'Uso de aplicaciones',
          description: 'Necesito ver cuánto tiempo pasa el niño en cada app.\n\nEn la siguiente pantalla, busca "SARA" y actívalo.',
          icon: Icons.bar_chart_rounded,
          openSettings: MonitoringChannel.openUsageAccessSettings,
        );
      case 3:
        await _requestSpecial(
          title: 'Acceso a notificaciones',
          description: 'Necesito leer las notificaciones de WhatsApp, Telegram e Instagram para detectar contenido inapropiado.\n\nEn la siguiente pantalla, activa "SARA Control Parental".',
          icon: Icons.mark_chat_unread_outlined,
          openSettings: MonitoringChannel.openNotificationAccessSettings,
        );
      case 4:
        await _requestSpecial(
          title: 'Accesibilidad (URLs)',
          description: 'Necesito ver las páginas web visitadas en Chrome o Firefox.\n\nEn la siguiente pantalla, activa "SARA Monitoreo Web".',
          icon: Icons.language_rounded,
          openSettings: MonitoringChannel.openAccessibilitySettings,
        );
      case 5:
        await _requestSpecial(
          title: 'Sin restricción de batería',
          description: 'Para que el monitoreo no se detenga, desactiva la optimización de batería para SARA.\n\nEn la siguiente pantalla, busca "SARA" y selecciona "No restringir".',
          icon: Icons.battery_saver_outlined,
          openSettings: MonitoringChannel.openBatterySettings,
        );
      default:
        await _finish();
    }
  }

  Future<void> _requestMic() async {
    final status = await Permission.microphone.request();
    if (!mounted) return;
    if (status.isPermanentlyDenied) {
      await _showDeniedDialog('Micrófono', 'Necesario para hablar con SARA por voz.');
    }
    _advance();
  }

  Future<void> _requestNotif() async {
    final status = await Permission.notification.request();
    if (!mounted) return;
    if (status.isPermanentlyDenied) {
      await _showDeniedDialog('Notificaciones', 'Necesario para que SARA te envíe recordatorios.');
    }
    _advance();
  }

  Future<void> _requestSpecial({
    required String title,
    required String description,
    required IconData icon,
    required Future<void> Function() openSettings,
  }) async {
    if (!mounted) return;
    final proceed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => _PermissionDialog(
        title: title,
        description: description,
        icon: icon,
      ),
    );
    if (proceed == true) {
      _waitingForSettings = true;
      await openSettings();
    } else {
      _advance();
    }
  }

  Future<void> _showDeniedDialog(String name, String reason) async {
    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E2427),
        title: Text(name, style: const TextStyle(color: SaraColors.primary, fontSize: 15)),
        content: Text(
          '$reason\n\nPuedes activarlo más tarde en Ajustes del dispositivo.',
          style: const TextStyle(color: SaraColors.tertiary, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Entendido', style: TextStyle(color: SaraColors.secondary)),
          ),
        ],
      ),
    );
  }

  void _advance() {
    if (!mounted) return;
    setState(() => _step++);
    if (_step < _totalSteps) {
      _runStep();
    } else {
      _finish();
    }
  }

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('permissions_onboarding_done', true);
    if (mounted) widget.onComplete();
  }

  @override
  Widget build(BuildContext context) {
    final progress = (_step / _totalSteps).clamp(0.0, 1.0);
    final stepLabels = [
      'Micrófono',
      'Notificaciones',
      'Uso de apps',
      'Acceso notif.',
      'Accesibilidad',
      'Batería',
    ];

    return Scaffold(
      backgroundColor: SaraColors.neutral,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              Container(
                width: 64, height: 64,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF1E2225),
                  border: Border.all(color: const Color(0xFF455A64), width: 1.5),
                ),
                child: const Center(
                  child: Text('S', style: TextStyle(
                    fontSize: 26, fontWeight: FontWeight.bold, color: Color(0xFF78909C),
                  )),
                ),
              ),
              const SizedBox(height: 24),
              const Text('Configuración inicial',
                style: TextStyle(
                  color: SaraColors.primary, fontSize: 22, fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'SARA necesita algunos permisos para funcionar correctamente. Te los pediremos uno a uno.',
                style: TextStyle(color: SaraColors.tertiary, fontSize: 13, height: 1.5),
                textAlign: TextAlign.center,
              ),
              const Spacer(),
              // Progreso
              Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _step < _totalSteps ? stepLabels[_step] : 'Completado',
                        style: const TextStyle(color: SaraColors.secondary, fontSize: 12),
                      ),
                      Text(
                        '${_step.clamp(0, _totalSteps)} / $_totalSteps',
                        style: const TextStyle(color: SaraColors.dim, fontSize: 11),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress,
                      backgroundColor: const Color(0xFF1E2427),
                      color: SaraColors.secondary,
                      minHeight: 4,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              // Chips de pasos
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: List.generate(_totalSteps, (i) {
                  final done = i < _step;
                  final active = i == _step;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: done
                          ? const Color(0x2066BB6A)
                          : active
                              ? const Color(0x20455A64)
                              : const Color(0xFF1A1C1E),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: done
                            ? const Color(0x8066BB6A)
                            : active
                                ? SaraColors.secondary
                                : const Color(0xFF263238),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (done)
                          const Icon(Icons.check, size: 11, color: Color(0xFF66BB6A))
                        else
                          Icon(Icons.circle,
                            size: 7,
                            color: active ? SaraColors.secondary : SaraColors.dim),
                        const SizedBox(width: 5),
                        Text(stepLabels[i],
                          style: TextStyle(
                            fontSize: 11,
                            color: done
                                ? const Color(0xFF66BB6A)
                                : active
                                    ? SaraColors.primary
                                    : SaraColors.dim,
                          )),
                      ],
                    ),
                  );
                }),
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }
}

class _PermissionDialog extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;

  const _PermissionDialog({
    required this.title,
    required this.description,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF1E2427),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      contentPadding: const EdgeInsets.fromLTRB(24, 20, 24, 0),
      actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      title: Row(
        children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: const Color(0x20455A64),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 18, color: SaraColors.secondary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(title, style: const TextStyle(
              color: SaraColors.primary, fontSize: 15, fontWeight: FontWeight.w600,
            )),
          ),
        ],
      ),
      content: Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(
          description,
          style: const TextStyle(color: SaraColors.tertiary, fontSize: 13, height: 1.6),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Ahora no', style: TextStyle(color: SaraColors.dim, fontSize: 13)),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, true),
          style: FilledButton.styleFrom(
            backgroundColor: SaraColors.secondary,
            foregroundColor: SaraColors.primary,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          ),
          child: const Text('Ir a Ajustes', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}
