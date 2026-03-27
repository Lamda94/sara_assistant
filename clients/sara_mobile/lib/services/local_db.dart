import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class PendingMessage {
  final String localId;
  final String content;
  final DateTime createdAt;
  final bool synced;
  final String? response;

  PendingMessage({
    required this.localId,
    required this.content,
    required this.createdAt,
    this.synced = false,
    this.response,
  });

  Map<String, dynamic> toMap() => {
    'local_id': localId,
    'content': content,
    'created_at': createdAt.millisecondsSinceEpoch,
    'synced': synced ? 1 : 0,
    'response': response,
  };

  factory PendingMessage.fromMap(Map<String, dynamic> m) => PendingMessage(
    localId: m['local_id'] as String,
    content: m['content'] as String,
    createdAt: DateTime.fromMillisecondsSinceEpoch(m['created_at'] as int),
    synced: (m['synced'] as int) == 1,
    response: m['response'] as String?,
  );
}

class LocalDb {
  static Database? _db;

  static Future<Database> get db async {
    _db ??= await _open();
    return _db!;
  }

  static Future<Database> _open() async {
    final dbPath = join(await getDatabasesPath(), 'sara_offline.db');
    return openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, _) => db.execute('''
        CREATE TABLE pending_messages (
          id       INTEGER PRIMARY KEY AUTOINCREMENT,
          local_id TEXT    UNIQUE,
          content  TEXT,
          created_at INTEGER,
          synced   INTEGER DEFAULT 0,
          response TEXT
        )
      '''),
    );
  }

  static Future<void> insertPending(PendingMessage msg) async {
    final d = await db;
    await d.insert(
      'pending_messages',
      msg.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<List<PendingMessage>> getPending() async {
    final d = await db;
    final rows = await d.query(
      'pending_messages',
      where: 'synced = 0',
      orderBy: 'created_at ASC',
    );
    return rows.map(PendingMessage.fromMap).toList();
  }

  static Future<void> markSynced(String localId, String response) async {
    final d = await db;
    await d.update(
      'pending_messages',
      {'synced': 1, 'response': response},
      where: 'local_id = ?',
      whereArgs: [localId],
    );
  }

  static Future<void> deleteSynced() async {
    final d = await db;
    await d.delete('pending_messages', where: 'synced = 1');
  }
}
