import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../theme.dart';
import 'monitoring_channel.dart';
import '../api.dart';

class MonitoringSetupScreen extends StatefulWidget {
  const MonitoringSetupScreen({super.key});
  @override
  State<MonitoringSetupScreen> createState() => _MonitoringSetupScreenState();
}

class _MonitoringSetupScreenState extends State<MonitoringSetupScreen> {
  Map<String, bool> _perms = {};
  bool _monitoring = false;
  bool _loading = false;
  final _childIdCtrl = TextEditingController(text: 'hija1-mobile');

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

  Future<void> _startMonitoring() async {
    await MonitoringChannel.startMonitoring(_childIdCtrl.text.trim());
    // Registrar el dispositivo hijo en el backend
    try {
      await http.post(
        Uri.parse('$kBaseUrl/monitoring/register-child'),
        headers: {'Content-Type': 'application/json'},
        body: '{"child_session_id":"${_childIdCtrl.text.trim()}","parent_session_id":"$kSessionId","device_label":"Dispositivo de hija"}',
      );
    } catch (_) {}
    setState(() => _monitoring = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Monitoreo activo')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final allGranted = (_perms['usageStats'] ?? false) &&
        (_perms['notificationListener'] ?? false) &&
        (_perms['accessibility'] ?? false);

    return Scaffold(
      backgroundColor: SaraColors.bg,
      appBar: AppBar(
        backgroundColor: SaraColors.surface,
        title: Text('Control Parental', style: TextStyle(color: SaraColors.fg, fontSize: 15)),
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
                _section('ID del dispositivo hijo'),
                const SizedBox(height: 8),
                TextField(
                  controller: _childIdCtrl,
                  style: TextStyle(color: SaraColors.fg, fontSize: 13),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: SaraColors.surface,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                    hintText: 'ej: hija1-mobile',
                    hintStyle: TextStyle(color: SaraColors.dim),
                  ),
                ),
                const SizedBox(height: 20),
                _section('Permisos requeridos'),
                const SizedBox(height: 8),
                _permTile(
                  'Uso de aplicaciones',
                  'Tiempo en cada app, lanzamientos',
                  _perms['usageStats'] ?? false,
                  MonitoringChannel.openUsageAccessSettings,
                ),
                _permTile(
                  'Acceso a notificaciones',
                  'WhatsApp, Telegram, Instagram, TikTok',
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
                  'Batería sin restricciones',
                  'Mantiene el monitoreo activo siempre',
                  true,  // No se puede verificar sin root, asumimos que el padre lo activa
                  MonitoringChannel.openBatterySettings,
                ),
                const SizedBox(height: 24),
                if (!allGranted)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(
                      '⚠ Activa todos los permisos para un monitoreo completo.',
                      style: TextStyle(color: Colors.amber[700], fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _monitoring ? Colors.red[700] : SaraColors.secondary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: _monitoring
                      ? () async {
                          await MonitoringChannel.stopMonitoring();
                          setState(() => _monitoring = false);
                        }
                      : _startMonitoring,
                  child: Text(
                    _monitoring ? 'Detener monitoreo' : 'Activar monitoreo',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'El padre puede preguntar a SARA:\n"¿Qué hizo mi hija hoy en el móvil?"',
                  style: TextStyle(color: SaraColors.dim, fontSize: 11),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
    );
  }

  Widget _section(String title) => Text(
    title,
    style: TextStyle(color: SaraColors.secondary, fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 0.5),
  );

  Widget _permTile(String title, String subtitle, bool granted, VoidCallback onTap) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: SaraColors.surface,
        borderRadius: BorderRadius.circular(10),
      ),
      child: ListTile(
        leading: Icon(
          granted ? Icons.check_circle : Icons.radio_button_unchecked,
          color: granted ? Colors.greenAccent : SaraColors.dim,
          size: 20,
        ),
        title: Text(title, style: TextStyle(color: SaraColors.fg, fontSize: 13)),
        subtitle: Text(subtitle, style: TextStyle(color: SaraColors.dim, fontSize: 11)),
        trailing: granted
            ? null
            : TextButton(
                onPressed: onTap,
                child: Text('Activar', style: TextStyle(color: SaraColors.secondary, fontSize: 12)),
              ),
        onTap: granted ? null : onTap,
      ),
    );
  }
}
