<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Sign In</h1>
      <form @submit.prevent="handleLogin">
        <input v-model="username" placeholder="Username" required />
        <input v-model="password" type="password" placeholder="Password" required />
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? "Loading..." : "Sign In" }}</button>
      </form>
      <p class="switch">Don't have an account? <NuxtLink to="/register">Sign up</NuxtLink></p>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter();
const authStore = useAuthStore();
const config = useRuntimeConfig();

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function handleLogin() {
  error.value = "";
  loading.value = true;
  try {
    const data: any = await $fetch("/api/v1/auth/login", {
      baseURL: config.public.apiBase,
      method: "POST",
      body: { username: username.value, password: password.value },
    });
    authStore.setToken(data.access_token);
    await authStore.fetchUser();
    router.push("/");
  } catch (e: any) {
    error.value = e.data?.detail || e.message || "Login failed";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
.auth-card {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
}
h1 { margin-bottom: 20px; }
input {
  width: 100%;
  padding: 10px 14px;
  margin-bottom: 12px;
  border: 1px solid #cfd9de;
  border-radius: 8px;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}
input:focus {
  border-color: #1d9bf0;
  box-shadow: 0 0 0 2px rgba(29,155,240,0.15);
}
button {
  width: 100%;
  padding: 10px;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}
button:hover {
  background: #1a8cd8;
}
button:disabled { opacity: 0.6; }
.error { color: #e0245e; margin-bottom: 12px; }
.switch { margin-top: 16px; text-align: center; font-size: 0.9rem; }
</style>
