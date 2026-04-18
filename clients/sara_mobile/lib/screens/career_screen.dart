import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../api.dart';
import '../theme.dart';

const _sessionId = 'lamda94-mobile';

class CareerScreen extends StatefulWidget {
  const CareerScreen({super.key});

  @override
  State<CareerScreen> createState() => _CareerScreenState();
}

class _CareerScreenState extends State<CareerScreen> {
  Map<String, dynamic>? _status;
  List<dynamic> _apps = [];
  bool _loading = true;
  final Set<String> _expanded = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        http.get(Uri.parse('$kBaseUrl/career/status?session_id=$_sessionId'),
            headers: {'X-API-Key': kApiKey}),
        http.get(Uri.parse('$kBaseUrl/career/applications?limit=20'),
            headers: {'X-API-Key': kApiKey}),
      ]);
      if (results[0].statusCode == 200) _status = jsonDecode(results[0].body);
      if (results[1].statusCode == 200) _apps = jsonDecode(results[1].body);
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final mode = _status?['career_mode'] == true;
    final byStatus = (_status?['by_status'] as Map<String, dynamic>?) ?? {};
    final lastScan = _status?['last_scan'];

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('CareerOps', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
            const SizedBox(width: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: (mode ? const Color(0xFF4CAF50) : SaraColors.tertiary).withOpacity(0.15),
                borderRadius: BorderRadius.circular(5),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.power_settings_new, size: 10,
                      color: mode ? const Color(0xFF4CAF50) : SaraColors.tertiary),
                  const SizedBox(width: 4),
                  Text(
                    mode ? 'ACTIVO' : 'INACTIVO',
                    style: TextStyle(
                      fontSize: 9, fontWeight: FontWeight.w600,
                      color: mode ? const Color(0xFF4CAF50) : SaraColors.tertiary,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            color: SaraColors.secondary,
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: SaraColors.tertiary))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Metrics
                  Row(
                    children: [
                      _metricCard('Evaluadas', '${_status?['total_applications'] ?? 0}', SaraColors.tertiary),
                      const SizedBox(width: 10),
                      _metricCard('CVs', '${byStatus['cv_generated'] ?? 0}', const Color(0xFF42A5F5)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _metricCard('Aplicadas', '${byStatus['applied'] ?? 0}', const Color(0xFF4CAF50)),
                      const SizedBox(width: 10),
                      _metricCard(
                        'Ultimo scan',
                        lastScan?['date'] != null
                            ? _formatDate(lastScan!['date'])
                            : '—',
                        const Color(0xFFFF9800),
                      ),
                    ],
                  ),

                  // Status tags
                  if (byStatus.entries.where((e) => (e.value as int) > 0).isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: byStatus.entries
                          .where((e) => (e.value as int) > 0)
                          .map((e) => _tag('${e.key}: ${e.value}', SaraColors.tertiary))
                          .toList(),
                    ),
                  ],

                  const SizedBox(height: 24),
                  const Text('EVALUACIONES', style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w600, color: SaraColors.secondary,
                    letterSpacing: 1.0,
                  )),
                  const SizedBox(height: 12),

                  if (_apps.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 32),
                      child: Text(
                        'No hay evaluaciones. Dile a SARA:\n"evalua esta oferta: [url]"',
                        style: TextStyle(color: SaraColors.dim, fontSize: 13),
                      ),
                    )
                  else
                    ..._apps.map((app) => _appCard(app)),
                ],
              ),
            ),
    );
  }

  Widget _metricCard(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: SaraColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: SaraColors.secondary, height: 1.3)),
            const SizedBox(height: 6),
            Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: color)),
          ],
        ),
      ),
    );
  }

  Widget _appCard(Map<String, dynamic> app) {
    final id = app['id'] as String;
    final score = (app['score'] as num?)?.toDouble() ?? 0;
    final compat = app['compatibility_pct'] as int?;
    final status = app['status'] as String;
    final isExpanded = _expanded.contains(id);

    final scoreColor = score >= 4.5
        ? const Color(0xFF4CAF50)
        : score >= 4.0
            ? const Color(0xFF8BC34A)
            : score >= 3.5
                ? const Color(0xFFFF9800)
                : const Color(0xFFEF5350);

    final statusIcons = {
      'evaluated': '📋', 'cv_generated': '📄', 'applied': '✅',
      'interview': '🎯', 'offer': '🏆', 'rejected': '❌', 'discarded': '🚫',
    };

    return GestureDetector(
      onTap: () => setState(() {
        if (isExpanded) { _expanded.remove(id); } else { _expanded.add(id); }
      }),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: SaraColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  Row(
                    children: [
                      Text(statusIcons[status] ?? '📋', style: const TextStyle(fontSize: 14)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${app['company']}', style: const TextStyle(
                              color: SaraColors.primary, fontSize: 13, fontWeight: FontWeight.w600,
                            )),
                            Text('${app['role']}', style: const TextStyle(
                              color: SaraColors.secondary, fontSize: 11,
                            )),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            score > 0 ? score.toStringAsFixed(1) : '—',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: scoreColor),
                          ),
                          if (compat != null)
                            Text('$compat% match', style: const TextStyle(fontSize: 10, color: SaraColors.secondary)),
                        ],
                      ),
                      const SizedBox(width: 8),
                      Icon(isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                          size: 16, color: SaraColors.secondary),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _tag(status.replaceAll('_', ' ').toUpperCase(), SaraColors.tertiary),
                      const SizedBox(width: 6),
                      if (app['archetype'] != null)
                        _tag(app['archetype'], SaraColors.secondary),
                      const Spacer(),
                      if (app['created_at'] != null)
                        Text(_formatDate(app['created_at']),
                            style: const TextStyle(fontSize: 10, color: SaraColors.dim)),
                    ],
                  ),
                ],
              ),
            ),

            // Expanded detail
            if (isExpanded) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: Color(0x0AFFFFFF))),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _miniStat('Score', score > 0 ? '${score.toStringAsFixed(1)}/5' : '—'),
                        _miniStat('Compatibilidad', compat != null ? '$compat%' : '—'),
                        _miniStat('Legitimidad', app['legitimacy'] ?? '—'),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        _miniStat('Arquetipo', app['archetype'] ?? '—'),
                        _miniStat('CV', app['cv_path'] != null ? 'Generado' : 'No'),
                        _miniStat('Portal', app['portal_source'] ?? '—'),
                      ],
                    ),

                    if (app['evaluation_summary'] != null) ...[
                      const SizedBox(height: 14),
                      const Text('RESUMEN', style: TextStyle(
                        fontSize: 10, color: SaraColors.secondary, letterSpacing: 0.8, fontWeight: FontWeight.w600,
                      )),
                      const SizedBox(height: 4),
                      Text(app['evaluation_summary'], style: const TextStyle(
                        color: SaraColors.tertiary, fontSize: 12, height: 1.5,
                      )),
                    ],

                    if (app['evaluation_blocks'] != null) ...[
                      const SizedBox(height: 12),
                      const Text('BLOQUES', style: TextStyle(
                        fontSize: 10, color: SaraColors.secondary, letterSpacing: 0.8, fontWeight: FontWeight.w600,
                      )),
                      const SizedBox(height: 4),
                      ...(app['evaluation_blocks'] as Map<String, dynamic>).entries.map((e) =>
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.03),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Bloque ${e.key.toUpperCase()}', style: const TextStyle(
                                  fontSize: 10, color: SaraColors.tertiary, fontWeight: FontWeight.w600,
                                )),
                                const SizedBox(height: 2),
                                Text(
                                  e.value.toString().length > 200
                                      ? '${e.value.toString().substring(0, 200)}...'
                                      : e.value.toString(),
                                  style: const TextStyle(fontSize: 11, color: SaraColors.secondary, height: 1.4),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _miniStat(String label, String value) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 9, color: SaraColors.dim, letterSpacing: 0.5)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 12, color: SaraColors.primary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _tag(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(text, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w500)),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
      return '${dt.day} ${months[dt.month - 1]}';
    } catch (_) {
      return iso.substring(0, 10);
    }
  }
}
