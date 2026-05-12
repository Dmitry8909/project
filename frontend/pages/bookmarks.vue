<template>
  <div class="bookmarks">
    <div class="page-header">
      <h2>Bookmarks</h2>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="!posts.length" class="empty">No bookmarked posts yet</div>
    <div v-else class="feed">
      <div v-for="post in posts" :key="post.id" class="post-card" @click="openPost(post.id)">
        <div class="post-header">
          <NuxtLink :to="`/profile/${post.author_name}`" class="author" @click.stop>
            <div class="post-avatar">
              <img v-if="post.author_avatar" :src="resolveMedia(post.author_avatar)" alt="" />
              <span v-else>{{ post.author_name[0] }}</span>
            </div>
            <span>{{ post.author_name }}</span>
          </NuxtLink>
          <span class="time">{{ formatDate(post.created_at) }}</span>
        </div>
        <p class="post-content">{{ post.content }}</p>
        <ImageGallery v-if="post.media?.length" :images="post.media" />
        <div class="post-actions-bar" @click.stop>
          <button
            class="action-btn"
            :class="{ liked: post.is_liked }"
            @click.stop="toggleLike(post)"
          >
            {{ post.is_liked ? "❤️" : "🤍" }} {{ post.likes_count || "" }}
          </button>
          <button class="remove-btn" @click.stop="removeBookmark(post)">
            Remove bookmark
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ImageGallery from "~/components/ImageGallery.vue";

const router = useRouter();
const authStore = useAuthStore();
const api = useApi();
const media = useMediaUrl();
const resolveMedia = (url: string) => media.resolve(url);

const posts = ref<any[]>([]);
const loading = ref(true);



async function fetchBookmarks() {
  try {
    posts.value = await api.request("/api/v1/posts/bookmarks/all?limit=50");
  } catch {
    posts.value = [];
  } finally {
    loading.value = false;
  }
}

async function removeBookmark(post: any) {
  try {
    const res = await api.request(`/api/v1/posts/${post.id}/bookmark`, { method: "POST" });
    if (!res.bookmarked) {
      posts.value = posts.value.filter((p) => p.id !== post.id);
    }
  } catch (e: any) {
    alert(e.message);
  }
}

async function toggleLike(post: any) {
  const wasLiked = post.is_liked;
  post.is_liked = !wasLiked;
  post.likes_count += post.is_liked ? 1 : -1;
  try {
    const res = await api.toggleLike(post.id);
    if (res.liked !== post.is_liked) {
      post.is_liked = res.liked;
      post.likes_count += res.liked ? 1 : -1;
    }
  } catch {
    post.is_liked = wasLiked;
    post.likes_count += wasLiked ? 1 : -1;
  }
}

function openPost(id: string) {
  router.push(`/post/${id}`);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString();
}

onMounted(fetchBookmarks);
</script>

<style scoped>
.page-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
}

h2 { font-size: 1.3rem; }

.post-card {
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
  cursor: pointer;
  transition: background 0.15s;
}

.post-card:hover { background: #fafbfc; }

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.author {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  text-decoration: none;
  color: #0f1419;
  font-size: 0.95rem;
}

.author:hover { color: #1d9bf0; }

.post-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  flex-shrink: 0;
  overflow: hidden;
}

.post-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.time { font-size: 0.8rem; color: #536471; }

.post-content { line-height: 1.5; margin-bottom: 8px; }

.post-actions-bar {
  display: flex;
  gap: 24px;
  align-items: center;
  margin-top: 8px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #536471;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 4px;
  transition: color 0.15s;
}

.action-btn:hover { color: #1d9bf0; }
.action-btn.liked { color: #e0245e; }

.remove-btn {
  background: none;
  border: 1px solid #cfd9de;
  padding: 4px 14px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #e0245e;
}

.remove-btn:hover { background: #fef2f2; }

.loading, .empty {
  text-align: center;
  color: #536471;
  padding: 48px 20px;
}
</style>
