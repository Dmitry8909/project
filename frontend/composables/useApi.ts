export function useApi() {
  const config = useRuntimeConfig();
  const authStore = useAuthStore();

  async function request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (authStore.token) {
      headers["Authorization"] = `Bearer ${authStore.token}`;
    }

    const res = await fetch(`${config.public.apiBase}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }

    return res.json();
  }

  async function toggleLike(postId: string): Promise<{ liked: boolean }> {
    return request(`/api/v1/posts/${postId}/like`, { method: "POST" });
  }

  return { request, toggleLike };
}
