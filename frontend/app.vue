<template>
  <div class="layout">
    <aside v-if="authStore.isAuthenticated" class="sidebar">
      <div class="sidebar-header">
        <NuxtLink to="/" class="logo">MicroBlog</NuxtLink>
      </div>

      <nav class="nav">
        <a href="/" class="nav-item" @click.prevent="navigate('/')">
          <span class="nav-icon">🏠</span>
          <span>Home</span>
        </a>
        <a href="/explore" class="nav-item" @click.prevent="navigate('/explore')">
          <span class="nav-icon">🔍</span>
          <span>Explore</span>
        </a>
        <a href="/messages" class="nav-item" @click.prevent="navigate('/messages')">
          <span class="nav-icon">✉️</span>
          <span>Chat</span>
          <span v-if="badge.unreadMessages.value" class="badge">{{ badge.unreadMessages.value }}</span>
        </a>
        <a href="/bookmarks" class="nav-item" @click.prevent="navigate('/bookmarks')">
          <span class="nav-icon">🔖</span>
          <span>Bookmarks</span>
        </a>
        <a href="/notifications" class="nav-item" @click.prevent="navigate('/notifications')">
          <span class="nav-icon">🔔</span>
          <span>Notifications</span>
          <span v-if="badge.unreadNotifications.value" class="badge">{{ badge.unreadNotifications.value }}</span>
        </a>
        <a :href="`/profile/${authStore.user?.username}`" class="nav-item" @click.prevent="navigate(`/profile/${authStore.user?.username}`)">
          <span class="nav-icon">👤</span>
          <span>Profile</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <button @click="handleLogout" class="logout-btn">Logout</button>
      </div>
    </aside>

    <main>
      <NuxtPage />
    </main>
  </div>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const router = useRouter();
const badge = useNotificationBadge();

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

function navigate(path: string) {
  if (useRoute().path === path) {
    window.location.href = path;
  } else {
    router.push(path);
  }
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #fff;
  color: #0f1419;
}

.layout {
  display: flex;
  max-width: 1000px;
  min-height: 100vh;
  margin: 0 auto;
  background: #fff;
}

.sidebar {
  width: 240px;
  min-width: 240px;
  padding: 20px 12px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: sticky;
  top: 0;
  border-right: 1px solid #eff3f4;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.sidebar-header {
  margin-bottom: 20px;
  padding: 0 8px;
}

.logo {
  font-size: 1.3rem;
  font-weight: 800;
  color: #1d9bf0;
  text-decoration: none;
  letter-spacing: -0.5px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 20px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 9999px;
  text-decoration: none;
  color: #0f1419;
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.15s;
  position: relative;
}

.nav-item:hover {
  background: #e8f5fe;
  color: #1d9bf0;
}

.nav-icon {
  font-size: 1.2rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.badge {
  background: #1d9bf0;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  left: 48px;
  top: 8px;
}

.sidebar-footer {
  margin-top: auto;
  padding: 12px 4px 0;
}

.logout-btn {
  width: 100%;
  padding: 10px;
  background: none;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.85rem;
  color: #e0245e;
  font-weight: 600;
  transition: background 0.15s;
}

.logout-btn:hover {
  background: #fef2f2;
}

main {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1100px) {
  .layout { max-width: 100%; margin: 0 8px; }
}

@media (max-width: 768px) {
  .sidebar { width: 200px; min-width: 200px; padding: 16px 8px; }
  .nav-item { padding: 10px 12px; font-size: 0.9rem; gap: 12px; }
}

@media (max-width: 600px) {
  .sidebar { width: 64px; min-width: 64px; }
  .nav-item span:not(.nav-icon) { display: none; }
  .nav-item { justify-content: center; padding: 12px 0; }
  .sidebar-header { display: none; }
  .logout-btn { font-size: 0; }
  .logout-btn::before { content: "⏻"; font-size: 1.2rem; }
}

a { color: #1d9bf0; text-decoration: none; }
button { font-family: inherit; }

/* Auth pages - global styles (loaded from initial bundle, no lazy loading) */
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100%;
}

.auth-card {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
}

.auth-card h1 {
  margin-bottom: 20px;
}

.auth-card input {
  width: 100%;
  padding: 10px 14px;
  margin-bottom: 12px;
  border: 1px solid #cfd9de;
  border-radius: 8px;
  font-size: 1rem;
  outline: none;
  box-sizing: border-box;
}

.auth-card input:focus {
  border-color: #1d9bf0;
  box-shadow: 0 0 0 2px rgba(29,155,240,0.15);
}

.auth-card button {
  width: 100%;
  padding: 10px;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  font-family: inherit;
  font-weight: 600;
}

.auth-card button:hover {
  background: #1a8cd8;
}

.auth-card button:disabled {
  opacity: 0.6;
}

.auth-card .error {
  color: #e0245e;
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.auth-card .switch {
  margin-top: 16px;
  text-align: center;
  font-size: 0.9rem;
}
</style>
