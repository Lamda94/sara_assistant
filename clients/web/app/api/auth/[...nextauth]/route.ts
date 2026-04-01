import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const CREATOR_EMAIL = "lamda94@gmail.com";
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

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
    }),
  ],

  callbacks: {
    async signIn({ user }) {
      if (isCreator(user.email!)) return true;
      // Registrar solicitud de acceso si es un usuario nuevo
      try {
        await fetch(`${BACKEND}/auth/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: user.email, name: user.name }),
        });
      } catch {}
      return true; // Siempre permitir login; el middleware filtra no aprobados
    },

    async jwt({ token, user }) {
      if (user) {
        // Primera vez que se crea el token
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
