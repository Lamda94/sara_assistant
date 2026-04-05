import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import type { JWT } from "next-auth/jwt";

const CREATOR_EMAIL = "lamda94@gmail.com";
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

async function refreshGoogleToken(token: JWT): Promise<JWT> {
  try {
    const res = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID!,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        grant_type: "refresh_token",
        refresh_token: token.googleRefreshToken as string,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? "refresh failed");
    return {
      ...token,
      googleAccessToken: data.access_token,
      googleTokenExpiry: Date.now() + data.expires_in * 1000,
    };
  } catch {
    // Si falla el refresh, limpiar token para forzar re-login
    return { ...token, googleAccessToken: undefined, googleTokenExpiry: 0 };
  }
}

// Gmail ignora los puntos en el nombre de usuario
function normalizeEmail(email: string): string {
  const [local, domain] = email.toLowerCase().split("@");
  if (domain === "gmail.com") return local.replace(/\./g, "") + "@" + domain;
  return email.toLowerCase();
}

function isCreator(email: string): boolean {
  return normalizeEmail(email) === normalizeEmail(CREATOR_EMAIL);
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "openid email profile https://www.googleapis.com/auth/calendar",
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],

  callbacks: {
    async signIn({ user }) {
      if (isCreator(user.email!)) return true;
      try {
        await fetch(`${BACKEND}/auth/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: user.email, name: user.name }),
        });
      } catch {}
      return true;
    },

    async jwt({ token, user, account }) {
      // Guardar tokens de Google en el JWT al login
      if (account) {
        token.googleAccessToken = account.access_token;
        token.googleRefreshToken = account.refresh_token;
        token.googleTokenExpiry = account.expires_at
          ? account.expires_at * 1000
          : Date.now() + 3600 * 1000;
      }

      // Refrescar access_token si expiró
      if (
        token.googleRefreshToken &&
        typeof token.googleTokenExpiry === "number" &&
        Date.now() > token.googleTokenExpiry - 60_000 // 1 min antes de expirar
      ) {
        token = await refreshGoogleToken(token);
      }

      if (user) {
        if (isCreator(token.email!)) {
          token.approved = true;
          token.isCreator = true;
        } else {
          try {
            const res = await fetch(`${BACKEND}/auth/check?email=${token.email}`);
            const data = await res.json();
            token.approved = data.approved ?? false;
            token.isCreator = false;
          } catch {
            token.approved = false;
          }
        }
      }
      return token;
    },

    async session({ session, token }) {
      if (session.user) {
        (session.user as any).approved = token.approved;
        (session.user as any).isCreator = token.isCreator;
        (session.user as any).googleAccessToken = token.googleAccessToken;
      }
      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  session: { strategy: "jwt" },
});

export { handler as GET, handler as POST };
