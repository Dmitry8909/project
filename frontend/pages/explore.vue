<template>
  <div class="explore">
    <div class="explore-header">
      <h2>Explore</h2>
      <div class="search-bar">
        <input
          v-model="query"
          placeholder="Search users..."
          @input="onInput"
        />
      </div>
    </div>

    <div v-if="loading" class="loading">Searching...</div>
    <div v-else-if="query && !results.length" class="empty">No users found</div>
    <div v-else-if="!query" class="empty">Type to search users</div>
    <div v-else class="results">
      <div v-for="u in results" :key="u.id" class="user-row">
        <NuxtLink :to="`/profile/${u.username}`" class="user-info">
          <div class="user-avatar">
            <img v-if="u.avatar_url" :src="media.resolve(u.avatar_url)" alt="" />
            <span v-else>{{ (u.display_name || u.username)[0] }}</span>
          </div>
          <div>
            <div class="user-name">{{ u.display_name || u.username }}</div>
            <div class="user-username">@{{ u.username }}</div>
          </div>
        </NuxtLink>
        <button
          v-if="u.id !== authStore.user?.id"
          class="follow-btn"
          :class="{ following: u.is_following }"
          @click="toggleFollow(u)"
        >
          {{ u.is_following ? "Following" : "Follow" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const api = useApi();
const media = useMediaUrl();

const query = ref("");
const results = ref<any[]>([]);
const loading = ref(false);
let timer: ReturnType<typeof setTimeout>;



function onInput() {
  clearTimeout(timer);
  if (!query.value.trim()) {
    results.value = [];
    return;
  }
  loading.value = true;
  timer = setTimeout(async () => {
    try {
      results.value = await api.request(
        `/api/v1/users/search?q=${encodeURIComponent(query.value)}`
      );
    } catch {
      results.value = [];
    } finally {
      loading.value = false;
    }
  }, 300);
}

async function toggleFollow(u: any) {
  try {
    if (u.is_following) {
      await api.request(`/api/v1/subscriptions/unfollow/${u.id}`, { method: "DELETE" });
      u.is_following = false;
    } else {
      await api.request(`/api/v1/subscriptions/follow/${u.id}`, { method: "POST" });
      u.is_following = true;
    }
  } catch (e: any) {
    alert(e.message);
  }
}
</script>

<style scoped>
.explore-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
}

h2 {
  font-size: 1.3rem;
  margin-bottom: 12px;
}

.search-bar input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  font-size: 0.95rem;
  outline: none;
  background: #eff3f4;
  transition: background 0.15s, border-color 0.15s;
}

.search-bar input:focus {
  background: #fff;
  border-color: #1d9bf0;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #eff3f4;
  transition: background 0.15s;
}

.user-row:hover {
  background: #f7f9fa;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  text-decoration: none;
  color: #0f1419;
  min-width: 0;
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
  overflow: hidden;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.user-username {
  font-size: 0.85rem;
  color: #536471;
}

.follow-btn {
  background: #0f1419;
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.follow-btn:hover {
  opacity: 0.85;
}

.follow-btn.following {
  background: #fff;
  color: #0f1419;
  border: 1px solid #cfd9de;
}

.loading, .empty {
  text-align: center;
  color: #536471;
  padding: 48px 20px;
  font-size: 0.95rem;
}
</style>
