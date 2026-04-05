import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../api.dart';
import '../theme.dart';

class BettingScreen extends StatefulWidget {
  const BettingScreen({super.key});

  @override
  State<BettingScreen> createState() => _BettingScreenState();
}

class _BettingScreenState extends State<BettingScreen> {
  Map<String, dynamic>? _metrics;
  List<dynamic> _bets = [];
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
        http.get(Uri.parse('$kBaseUrl/betting/metrics'), headers: {'X-API-Key': kApiKey}),
        http.get(Uri.parse('$kBaseUrl/betting/history?limit=20'), headers: {'X-API-Key': kApiKey}),
      ]);
      if (results[0].statusCode == 200) {
        _metrics = jsonDecode(results[0].body);
      }
      if (results[1].statusCode == 200) {
        _bets = jsonDecode(results[1].body);
      }
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('SABE', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
            const SizedBox(width: 10),
            if (_metrics != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _metrics!['model_status'] == 'certified'
                      ? const Color(0xFF4CAF50).withOpacity(0.15)
                      : const Color(0xFFFF9800).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(5),
                ),
                child: Text(
                  _metrics!['model_status'] == 'certified' ? 'CERTIFICADO' : 'APRENDIZAJE',
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    color: _metrics!['model_status'] == 'certified'
                        ? const Color(0xFF4CAF50)
                        : const Color(0xFFFF9800),
                    letterSpacing: 0.5,
                  ),
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
                  // Metrics cards
                  if (_metrics != null) ...[
                    Row(
                      children: [
                        _metricCard('Win Rate\nUlt. 5', '${_metrics!['win_rate_last_5']}%',
                            _metrics!['win_rate_last_5'] >= 85
                                ? const Color(0xFF4CAF50)
                                : const Color(0xFFFF9800)),
                        const SizedBox(width: 10),
                        _metricCard('Balance', '${_metrics!['balance'].toStringAsFixed(0)}u',
                            _metrics!['roi'] >= 0 ? const Color(0xFF4CAF50) : const Color(0xFFEF5350)),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        _metricCard('Win Rate', '${_metrics!['win_rate']}%', SaraColors.tertiary),
                        const SizedBox(width: 10),
                        _metricCard('Apuestas',
                            '${_metrics!['wins']}W ${_metrics!['losses']}L ${_metrics!['pending']}P',
                            SaraColors.tertiary),
                      ],
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Header
                  const Text('HISTORIAL', style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w600, color: SaraColors.secondary,
                    letterSpacing: 1.0,
                  )),
                  const SizedBox(height: 12),

                  // Bets list
                  if (_bets.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 32),
                      child: Text('No hay apuestas registradas.',
                          style: TextStyle(color: SaraColors.dim, fontSize: 13)),
                    )
                  else
                    ..._bets.map((bet) => _betCard(bet)),

                  // Glosario
                  const SizedBox(height: 24),
                  const Text('GLOSARIO', style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w600, color: SaraColors.secondary,
                    letterSpacing: 1.0,
                  )),
                  const SizedBox(height: 12),
                  _glossaryItem('Cuota (@)', 'Multiplicador de ganancia. @2.50 significa que si apuestas 10u ganas 25u (15u de beneficio).'),
                  _glossaryItem('Edge', 'Ventaja detectada. Es la diferencia entre la probabilidad que SABE calcula y la que la casa de apuestas ofrece. A mayor edge, mayor valor.'),
                  _glossaryItem('Confianza', 'Nivel de seguridad de SABE en su prediccion (0-100%). Depende de la cantidad y calidad de datos disponibles.'),
                  _glossaryItem('Stake', 'Cantidad apostada en unidades. Se calcula con el Criterio de Kelly segun el edge y la cuota.'),
                  _glossaryItem('Prob. predicha', 'Probabilidad que SABE calcula para que ocurra el resultado seleccionado.'),
                  _glossaryItem('Prob. implicita', 'Probabilidad que la casa de apuestas asigna segun la cuota. Se calcula como 1/cuota.'),
                  _glossaryItem('H2H', 'Mercado de quien gana el partido (Head to Head). Incluye local, visitante y empate.'),
                  _glossaryItem('Totals', 'Mercado de Over/Under. Apuesta a si habra mas o menos de X goles/puntos en el partido.'),
                  _glossaryItem('Spreads', 'Mercado de handicap. Se le da ventaja o desventaja a un equipo (ej: -1.5 goles).'),
                  _glossaryItem('ROI', 'Retorno sobre la inversion. Porcentaje de ganancia o perdida sobre el capital inicial.'),
                  _glossaryItem('Win Rate', 'Porcentaje de apuestas ganadas. SABE necesita 85% en las ultimas 5 para certificarse.'),
                  _glossaryItem('Post-mortem', 'Analisis automatico de por que una apuesta perdio. SABE lo usa para ajustar su modelo.'),
                  const SizedBox(height: 24),
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

  Widget _betCard(Map<String, dynamic> bet) {
    final id = bet['id'] as String;
    final result = bet['result'] as String;
    final icon = result == 'win' ? '✅' : result == 'loss' ? '❌' : '⏳';
    final resultColor = result == 'win'
        ? const Color(0xFF4CAF50)
        : result == 'loss'
            ? const Color(0xFFEF5350)
            : const Color(0xFFFF9800);
    final pl = (bet['profit_loss'] as num).toDouble();
    final plStr = pl > 0 ? '+${pl.toStringAsFixed(1)}' : pl.toStringAsFixed(1);
    final isExpanded = _expanded.contains(id);

    return GestureDetector(
      onTap: () => setState(() {
        if (isExpanded) { _expanded.remove(id); } else { _expanded.add(id); }
      }),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: SaraColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: resultColor.withOpacity(0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  Row(
                    children: [
                      Text(icon, style: const TextStyle(fontSize: 14)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(bet['event_name'] ?? '', style: const TextStyle(
                          color: SaraColors.primary, fontSize: 13, fontWeight: FontWeight.w500,
                        )),
                      ),
                      Text('@${(bet['odds'] as num).toStringAsFixed(2)}',
                          style: const TextStyle(color: SaraColors.primary, fontSize: 13, fontWeight: FontWeight.w500)),
                      const SizedBox(width: 6),
                      Icon(isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                          size: 16, color: SaraColors.secondary),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${bet['league'] ?? bet['sport']} — ${(bet['market'] as String).toUpperCase()} — ${bet['selection']}'
                          '${bet['event_date'] != null ? ' · ${_formatDate(bet['event_date'])}' : ''}',
                          style: const TextStyle(color: SaraColors.secondary, fontSize: 11),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        result != 'pending' ? '${plStr}u' : 'pendiente',
                        style: TextStyle(color: resultColor, fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      _tag('Edge ${((bet['edge'] as num) * 100).toStringAsFixed(1)}%', resultColor),
                      const SizedBox(width: 6),
                      _tag('Conf ${bet['confidence']}%', SaraColors.tertiary),
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
                    // Stats grid
                    Row(
                      children: [
                        _miniStat('Prob. predicha', '${((bet['predicted_prob'] as num) * 100).toStringAsFixed(0)}%'),
                        _miniStat('Prob. implícita', '${((bet['implied_prob'] as num) * 100).toStringAsFixed(0)}%'),
                        _miniStat('Stake', '${(bet['stake_units'] as num).toStringAsFixed(1)}u'),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        _miniStat('Resultado', result.toUpperCase()),
                        _miniStat('Fecha evento', bet['event_date'] != null ? _formatDate(bet['event_date']) : '—'),
                        _miniStat('Deporte', bet['sport'] ?? '—'),
                      ],
                    ),

                    // Analysis
                    if (bet['analysis_summary'] != null && (bet['analysis_summary'] as String).isNotEmpty) ...[
                      const SizedBox(height: 14),
                      const Text('ANÁLISIS', style: TextStyle(
                        fontSize: 10, color: SaraColors.secondary, letterSpacing: 0.8, fontWeight: FontWeight.w600,
                      )),
                      const SizedBox(height: 4),
                      Text(bet['analysis_summary'], style: const TextStyle(
                        color: SaraColors.tertiary, fontSize: 12, height: 1.5,
                      )),
                    ],

                    // Post-mortem
                    if (bet['post_mortem'] != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF5350).withOpacity(0.08),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('POST-MORTEM', style: TextStyle(
                              fontSize: 10, color: Color(0xFFEF5350), letterSpacing: 0.8, fontWeight: FontWeight.w600,
                            )),
                            const SizedBox(height: 4),
                            Text(bet['post_mortem'], style: const TextStyle(
                              color: Color(0xFFEF9A9A), fontSize: 11, height: 1.4,
                            )),
                          ],
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
          Text(label, style: const TextStyle(
            fontSize: 9, color: SaraColors.dim, letterSpacing: 0.5,
          )),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(
            fontSize: 12, color: SaraColors.primary, fontWeight: FontWeight.w500,
          )),
        ],
      ),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
      return '${dt.day} ${months[dt.month - 1]} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso.substring(0, 10);
    }
  }

  Widget _glossaryItem(String term, String definition) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 95,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
            decoration: BoxDecoration(
              color: SaraColors.surface,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(term, style: const TextStyle(
              fontSize: 11, color: SaraColors.tertiary, fontWeight: FontWeight.w600,
            )),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(definition, style: const TextStyle(
              fontSize: 11, color: SaraColors.secondary, height: 1.4,
            )),
          ),
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
}
