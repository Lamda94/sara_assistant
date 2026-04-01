import 'package:flutter/material.dart';
import '../theme.dart';
import 'monitoring_channel.dart';

/// Pantalla solo para conceder permisos en el dispositivo del hijo.
/// El padre activa/desactiva el monitoreo remotamente desde su panel web.
class MonitoringSetupScreen extends StatefulWidget {
  const MonitoringSetupScreen({super.key});
  @override
  State<MonitoringSetupScreen> createState() => _MonitoringSetupScreenState();
}

class _MonitoringSetupScreenState extends State<MonitoringSetupScreen> {
  Map<String, bool> _perms = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() => _loading = true);
    final perms = await MonitoringChannel.checkPermissions();
    setState(() { _perms = perms; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    final allGranted = (_perms['usageStats'] ?? false) &&
        (_perms['notificationListener'] ?? false) &&
        (_perms['accessibility'] ?? false);

    return Scaffold(
      backgroundColor: SaraColors.neutral,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141618),
        title: Text('Permisos de supervisión', style: TextStyle(color: SaraColors.primary, fontSize: 15)),
        iconTheme: IconThemeData(color: SaraColors.secondary),
        actions: [
          IconButton(icon: const Icon(Icons.refresh, size: 18), onPressed: _refresh),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: allGranted ? Colors.green.withOpacity(0.1) : Colors.amber.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: allGranted ? Colors.greenAccent.withOpacity(0.3) : Colors.amber.withOpacity(0.3),
                    ),
                  ),
                  child: Text(
                    allGranted
                        ? 'Permisos concedidos. El padre puede activar el monitoreo desde su panel.'
                        : 'Concede los permisos para que el padre pueda supervisar este dispositivo.',
                    style: TextStyle(
                      color: allGranted ? Colors.greenAccent : Colors.amber[300],
                      fontSize: 12,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 20),
                _permTile(
                  'Uso de aplicaciones',
                  'Tiempo en cada app durante el día',
                  _perms['usageStats'] ?? false,
                  MonitoringChannel.openUsageAccessSettings,
                ),
                _permTile(
                  'Acceso a notificaciones',
                  'WhatsApp, Telegram, Instagram, TikTok...',
                  _perms['notificationListener'] ?? false,
                  MonitoringChannel.openNotificationAccessSettings,
                ),
                _permTile(
                  'Accesibilidad (URLs)',
                  'Páginas web visitadas en Chrome/Firefox',
                  _perms['accessibility'] ?? false,
                  MonitoringChannel.openAccessibilitySettings,
                ),
                _permTile(
                  'Sin restricción de batería',
                  'Mantiene el monitoreo activo siempre',
                  false,
                  MonitoringChannel.openBatterySettings,
                  alwaysShowButton: true,
                ),
              ],
            ),
    );
  }

  Widget _permTile(String title, String subtitle, bool granted, VoidCallback onTap, {bool alwaysShowButton = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: SaraColors.surface,
        borderRadius: BorderRadius.circular(10),
      ),
      child: ListTile(
        leading: Icon(
          granted ? Icons.check_circle : Icons.radio_button_unchecked,
          color: granted ? Colors.greenAccent : SaraColors.secondary,
          size: 20,
        ),
        title: Text(title, style: TextStyle(color: SaraColors.primary, fontSize: 13)),
        subtitle: Text(subtitle, style: TextStyle(color: SaraColors.tertiary, fontSize: 11)),
        trailing: (alwaysShowButton || !granted)
            ? TextButton(
                onPressed: onTap,
                child: Text('Activar', style: TextStyle(color: SaraColors.secondary, fontSize: 12)),
              )
            : null,
        onTap: granted && !alwaysShowButton ? null : onTap,
      ),
    );
  }
}
