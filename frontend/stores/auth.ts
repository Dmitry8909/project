export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(null);
  const user = ref<any | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  function setToken(t: string) {
    token.value = t;
    if (process.client) {
      localStorage.setItem("token", t);
    }
    const authCookie = useCookie("auth_token", { sameSite: "lax", path: "/" });
    authCookie.value = t;
  }

  function setUser(u: any) {
    user.value = u;
  }

  async function fetchUser() {
    try {
      const data = await $fetch("/api/v1/users/me", {
        baseURL: useRuntimeConfig().public.apiBase,
        headers: { Authorization: `Bearer ${token.value}` },
      });
      user.value = data;
    } catch {
      logout();
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
    if (process.client) {
      localStorage.removeItem("token");
    }
    const authCookie = useCookie("auth_token", { path: "/" });
    authCookie.value = null;
  }

  function init() {
    if (process.client) {
      const saved = localStorage.getItem("token");
      if (saved) {
        token.value = saved;
        fetchUser();
      }
    }
  }

  return { token, user, isAuthenticated, setToken, setUser, fetchUser, logout, init };
});
