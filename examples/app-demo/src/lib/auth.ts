const AUTH_KEY = "app_demo_session";
const AUTH_COOKIE = "app_demo_auth";

export interface SessionUser {
  email: string;
  name: string;
  role: string;
}

export function getSession(): SessionUser | null {
  try {
    const raw = window.localStorage.getItem(AUTH_KEY);
    if (raw) {
      return JSON.parse(raw) as SessionUser;
    }
  } catch {
    // ignore storage errors
  }
  if (document.cookie.includes(`${AUTH_COOKIE}=1`)) {
    return {
      email: "cagla.inanc@kovan.io",
      name: "Çağla İnanç",
      role: "Senior Product Designer",
    };
  }
  return null;
}

export function setSession(email: string): SessionUser {
  const user: SessionUser = {
    email,
    name: email.startsWith("cagla") ? "Çağla İnanç" : "Kovan Kullanıcısı",
    role: "Yetenek Değerlendirme Uzmanı",
  };
  try {
    window.localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  } catch {
    // ignore storage errors
  }
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=86400; SameSite=Lax`;
  return user;
}

export function clearSession(): void {
  try {
    window.localStorage.removeItem(AUTH_KEY);
  } catch {
    // ignore
  }
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}
