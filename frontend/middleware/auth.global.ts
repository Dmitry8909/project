export default defineNuxtRouteMiddleware((to, from) => {
  const authStore = useAuthStore();
  const publicRoutes = ["/login", "/register"];

  if (process.server) {
    const tokenCookie = useCookie("auth_token");
    const hasToken = !!tokenCookie.value;

    if (publicRoutes.includes(to.path) && hasToken) {
      return navigateTo("/");
    }

    if (!publicRoutes.includes(to.path) && !hasToken) {
      return navigateTo("/login");
    }
  } else {
    authStore.init();

    if (publicRoutes.includes(to.path) && authStore.isAuthenticated) {
      return navigateTo("/");
    }

    if (!publicRoutes.includes(to.path) && !authStore.isAuthenticated) {
      return navigateTo("/login");
    }
  }
});
