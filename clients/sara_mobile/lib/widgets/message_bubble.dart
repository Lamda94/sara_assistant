import 'package:flutter/material.dart';
import '../api.dart';
import '../theme.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const MessageBubble({super.key, required this.message});

  bool get _isUser => message.role == 'user';

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment:
            _isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!_isUser) _Avatar(),
          if (!_isUser) const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment:
                  _isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: _isUser
                        ? SaraColors.surface3
                        : SaraColors.surface,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: _isUser
                          ? const Radius.circular(16)
                          : const Radius.circular(4),
                      bottomRight: _isUser
                          ? const Radius.circular(4)
                          : const Radius.circular(16),
                    ),
                    border: Border.all(
                      color: _isUser
                          ? const Color(0x14FFFFFF)
                          : const Color(0x0AFFFFFF),
                    ),
                  ),
                  child: Text(
                    message.content,
                    style: const TextStyle(
                      color: SaraColors.primary,
                      fontSize: 14,
                      height: 1.5,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _timeLabel(),
                  style: const TextStyle(
                    color: SaraColors.dim,
                    fontSize: 9,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          if (_isUser) const SizedBox(width: 8),
          if (_isUser) _UserDot(),
        ],
      ),
    );
  }

  String _timeLabel() {
    final h = message.time.hour.toString().padLeft(2, '0');
    final m = message.time.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

class _Avatar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: SaraColors.surface,
        shape: BoxShape.circle,
        border: Border.all(color: SaraColors.secondary, width: 1),
      ),
      child: const Center(
        child: Text(
          'S',
          style: TextStyle(
            color: SaraColors.tertiary,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}

class _UserDot extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: SaraColors.surface3,
        shape: BoxShape.circle,
        border: Border.all(color: const Color(0x14FFFFFF), width: 1),
      ),
      child: const Center(
        child: Text(
          'L',
          style: TextStyle(
            color: SaraColors.secondary,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
