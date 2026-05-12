export function useMediaUrl() {
  const config = useRuntimeConfig();
  const authStore = useAuthStore();
  const apiBase = config.public.apiBase;

  function resolve(url: string): string {
    if (!url) return "";
    if (url.startsWith("http")) return url;
    const token = authStore.token;
    if (!token) return `${apiBase}${url}`;
    const sep = url.includes("?") ? "&" : "?";
    return `${apiBase}${url}${sep}token=${encodeURIComponent(token)}`;
  }

  return { resolve };
}
