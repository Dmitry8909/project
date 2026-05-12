<template>
  <div class="post-page">
    <div v-if="loading" class="loading">Loading...</div>
    <template v-else-if="post">
      <div class="post-detail">
        <div class="post-header">
          <NuxtLink :to="`/profile/${post.author_name}`" class="author">
            <div class="avatar">
              <img v-if="post.author_avatar" :src="resolveMedia(post.author_avatar)" alt="" />
              <span v-else>{{ post.author_name[0] }}</span>
            </div>
            <div>
              <div class="author-name">{{ post.author_name }}</div>
              <div class="time">{{ formatDate(post.created_at) }}</div>
            </div>
          </NuxtLink>
        </div>
        <p class="post-content">{{ post.content }}</p>
        <ImageGallery v-if="post.media?.length" :images="post.media" />
        <div class="post-stats">
          <span>{{ post.comments_count }} comments</span>
          <span>{{ post.likes_count }} likes</span>
          <span>{{ post.bookmarks_count }} bookmarks</span>
        </div>
        <div class="post-actions-bar">
          <button class="action-btn" @click="showComments = !showComments">
            💬 Comment
          </button>
          <button class="action-btn" @click="repost">🔄 Repost</button>
          <button
            class="action-btn"
            :class="{ liked: post.is_liked }"
            @click="toggleLike"
          >
            {{ post.is_liked ? "❤️" : "🤍" }} {{ post.likes_count || "" }}
          </button>
          <button
            class="action-btn"
            :class="{ active: post.is_bookmarked }"
            @click="toggleBookmark"
          >
            {{ post.is_bookmarked ? "🔖 Bookmarked" : "🔖 Bookmark" }}
          </button>
        </div>
      </div>

      <div class="comments-section">
        <h3>Comments</h3>
        <div class="comment-input">
          <input v-model="newComment" placeholder="Write a comment..." @keyup.enter="addComment" />
          <button @click="addComment" :disabled="!newComment.trim()">Send</button>
        </div>
        <div v-for="c in comments" :key="c.id" class="comment">
          <NuxtLink :to="`/profile/${c.author_username}`" class="comment-author">
            <strong>{{ c.author_name }}</strong>
          </NuxtLink>
          <p>{{ c.content }}</p>
          <span class="comment-time">{{ formatDate(c.created_at) }}</span>
        </div>
        <p v-if="!comments.length" class="empty">No comments yet</p>
      </div>
    </template>
    <p v-else class="error">Post not found</p>
  </div>
</template>

<script setup lang="ts">
import ImageGallery from "~/components/ImageGallery.vue";

const route = useRoute();
const api = useApi();
const media = useMediaUrl();
const resolveMedia = (url: string) => media.resolve(url);

const post = ref<any>(null);
const comments = ref<any[]>([]);
const loading = ref(true);
const showComments = ref(false);
const newComment = ref("");



async function fetchPost() {
  try {
    post.value = await api.request(`/api/v1/posts/${route.params.id}`);
    comments.value = await api.request(`/api/v1/posts/${route.params.id}/comments`);
  } catch {
    post.value = null;
  } finally {
    loading.value = false;
  }
}

async function addComment() {
  if (!newComment.value.trim()) return;
  try {
    await api.request(`/api/v1/posts/${route.params.id}/comment`, {
      method: "POST",
      body: JSON.stringify({ content: newComment.value }),
    });
    newComment.value = "";
    comments.value = await api.request(`/api/v1/posts/${route.params.id}/comments`);
    post.value.comments_count = comments.value.length;
  } catch (e: any) {
    alert(e.message);
  }
}

async function toggleLike() {
  const wasLiked = post.value.is_liked;
  post.value.is_liked = !wasLiked;
  post.value.likes_count += post.value.is_liked ? 1 : -1;
  try {
    const res = await api.toggleLike(route.params.id as string);
    if (res.liked !== post.value.is_liked) {
      post.value.is_liked = res.liked;
      post.value.likes_count += res.liked ? 1 : -1;
    }
  } catch {
    post.value.is_liked = wasLiked;
    post.value.likes_count += wasLiked ? 1 : -1;
  }
}

async function toggleBookmark() {
  try {
    const res = await api.request(`/api/v1/posts/${route.params.id}/bookmark`, { method: "POST" });
    post.value.is_bookmarked = res.bookmarked;
  } catch (e: any) {
    alert(e.message);
  }
}

async function repost() {
  try {
    await api.request(`/api/v1/posts/${route.params.id}/repost`, { method: "POST" });
    alert("Reposted!");
  } catch (e: any) {
    alert(e.message);
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString();
}

onMounted(fetchPost);
</script>

<style scoped>
.post-detail {
  padding: 20px;
  border-bottom: 1px solid #eff3f4;
}

.post-header {
  margin-bottom: 12px;
}

.author {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: #0f1419;
}

.author:hover .author-name { color: #1d9bf0; }

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-name { font-weight: 600; }

.time { font-size: 0.85rem; color: #536471; }

.post-content {
  font-size: 1.05rem;
  line-height: 1.6;
  margin-bottom: 12px;
}

.post-stats {
  display: flex;
  gap: 20px;
  font-size: 0.85rem;
  color: #536471;
  padding: 12px 0;
  border-top: 1px solid #eff3f4;
  border-bottom: 1px solid #eff3f4;
  margin-bottom: 12px;
}

.post-actions-bar {
  display: flex;
  gap: 24px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #536471;
  font-size: 0.9rem;
  padding: 8px;
  border-radius: 9999px;
  transition: color 0.15s, background 0.15s;
}

.action-btn:hover { color: #1d9bf0; background: #e8f5fe; }
.action-btn.active { color: #1d9bf0; }
.action-btn.liked { color: #e0245e; }

.comments-section {
  padding: 20px;
}

.comments-section h3 { margin-bottom: 12px; }

.comment-input {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.comment-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  outline: none;
  font-size: 0.9rem;
}

.comment-input button {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
}

.comment-input button:disabled { opacity: 0.5; }

.comment {
  padding: 12px 0;
  border-bottom: 1px solid #f7f9fa;
}

.comment-author {
  text-decoration: none;
  color: #0f1419;
}

.comment-author:hover { color: #1d9bf0; }

.comment-author strong { font-size: 0.9rem; }

.comment p { margin: 4px 0; font-size: 0.95rem; }
.comment-time { font-size: 0.75rem; color: #536471; }

.loading, .error, .empty {
  text-align: center;
  color: #536471;
  padding: 48px 20px;
}
</style>
