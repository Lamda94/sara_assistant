import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kServerClientId =
    '493494399792-qv888sn2thclkejp4l7ks7tiuo3iv3p9.apps.googleusercontent.com';

final _googleSignIn = GoogleSignIn(
  serverClientId: _kServerClientId,
  scopes: [
    'email',
    'profile',
    'https://www.googleapis.com/auth/calendar',
  ],
);

class AuthService {
  static final AuthService _instance = AuthService._();
  factory AuthService() => _instance;
  AuthService._();

  GoogleSignInAccount? _user;
  String? _accessToken;

  GoogleSignInAccount? get user => _user;
  String? get accessToken => _accessToken;
  bool get isSignedIn => _user != null;

  Future<bool> tryAutoSignIn() async {
    try {
      _user = await _googleSignIn.signInSilently();
      if (_user != null) {
        final auth = await _user!.authentication;
        _accessToken = auth.accessToken;
      }
      return _user != null;
    } catch (_) {
      return false;
    }
  }

  Future<bool> signIn() async {
    try {
      _user = await _googleSignIn.signIn();
      if (_user == null) return false;
      final auth = await _user!.authentication;
      _accessToken = auth.accessToken;
      // Guardar email para mostrar en UI
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('user_email', _user!.email);
      await prefs.setString('user_name', _user!.displayName ?? '');
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    _user = null;
    _accessToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('user_email');
    await prefs.remove('user_name');
  }

  /// Refresca el access token si expiró
  Future<String?> getValidToken() async {
    if (_user == null) return null;
    try {
      final auth = await _user!.authentication;
      _accessToken = auth.accessToken;
      return _accessToken;
    } catch (_) {
      return null;
    }
  }
}
