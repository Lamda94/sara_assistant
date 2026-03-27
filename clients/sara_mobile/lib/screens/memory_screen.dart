import 'package:flutter/material.dart';
import '../api.dart';
import '../theme.dart';

class MemoryScreen extends StatefulWidget {
  const MemoryScreen({super.key});

  @override
  State<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  List<Memory> _memories = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final mems = await getMemories();
      setState(() {
        _memories = mems;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Error al cargar memoria';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SaraColors.neutral,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141618),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 16),
          color: SaraColors.secondary,
          onPressed: () => Navigator.pop(context),
        ),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'MEMORIA',
              style: TextStyle(
                color: SaraColors.primary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
                letterSpacing: 2,
              ),
            ),
            Text(
              'Conocimiento persistente',
              style: TextStyle(
                color: SaraColors.secondary,
                fontSize: 9,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: const Color(0x0DFFFFFF)),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 18),
            color: SaraColors.secondary,
            onPressed: () {
              setState(() {
                _loading = true;
                _error = null;
              });
              _load();
            },
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(
                color: SaraColors.secondary,
                strokeWidth: 1.5,
              ),
            )
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.error_outline,
                          color: SaraColors.dim, size: 32),
                      const SizedBox(height: 12),
                      Text(
                        _error!,
                        style: const TextStyle(
                            color: SaraColors.secondary, fontSize: 13),
                      ),
                    ],
                  ),
                )
              : _memories.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.psychology_outlined,
                              color: SaraColors.dim, size: 40),
                          SizedBox(height: 16),
                          Text(
                            'Sin memorias aún',
                            style: TextStyle(
                                color: SaraColors.secondary, fontSize: 13),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Inicia una conversación para crear recuerdos',
                            style: TextStyle(
                                color: SaraColors.dim, fontSize: 11),
                          ),
                        ],
                      ),
                    )
                  : Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                          child: Row(
                            children: [
                              Text(
                                '${_memories.length} HECHOS',
                                style: const TextStyle(
                                  color: SaraColors.dim,
                                  fontSize: 9,
                                  letterSpacing: 1.5,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: SaraColors.surface,
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(
                                      color: const Color(0x0AFFFFFF)),
                                ),
                                child: const Text(
                                  'CONCIENCIA ÚNICA',
                                  style: TextStyle(
                                    color: SaraColors.tertiary,
                                    fontSize: 8,
                                    letterSpacing: 1.2,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: ListView.builder(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            itemCount: _memories.length,
                            itemBuilder: (ctx, i) =>
                                _MemoryCard(memory: _memories[i]),
                          ),
                        ),
                      ],
                    ),
    );
  }
}

class _MemoryCard extends StatelessWidget {
  final Memory memory;
  const _MemoryCard({required this.memory});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: SaraColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x0AFFFFFF)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(Icons.circle, size: 5, color: SaraColors.tertiary),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              memory.content,
              style: const TextStyle(
                color: SaraColors.primary,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
