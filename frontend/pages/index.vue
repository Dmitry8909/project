<template>
  <div class="home">
    <div class="create-post">
      <textarea v-model="newPostContent" placeholder="What's happening?" rows="3"></textarea>
      <div class="post-actions">
        <label class="file-label">
          📷
          <input type="file" accept="image/*" multiple @change="handleFiles" hidden />
        </label>
        <div v-if="selectedFiles.length" class="file-previews">
          <div v-for="(f, i) in selectedFiles" :key="i" class="file-preview">
            <img :src="f.preview" alt="" />
            <button class="file-remove" @click="removeFile(i)">✕</button>
          </div>
        </div>
        <button @click="createPost" :disabled="(!newPostContent.trim() && !selectedFiles.length) || posting">
          {{ posting ? "Posting..." : "Post" }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

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
          <button class="action-btn" @click.stop="openComments(post)">
            💬 {{ post.comments_count || "" }}
          </button>
          <button class="action-btn" @click.stop="repost(post)">
            🔄 {{ post.reposts_count || "" }}
          </button>
          <button
            class="action-btn"
            :class="{ liked: post.is_liked }"
            @click.stop="toggleLike(post)"
          >
            {{ post.is_liked ? "❤️" : "🤍" }} {{ post.likes_count || "" }}
          </button>
          <button
            class="action-btn"
            :class="{ active: post.is_bookmarked }"
            @click.stop="toggleBookmark(post)"
          >
            {{ post.is_bookmarked ? "🔖" : "🔖" }}
          </button>
        </div>
      </div>
      <p v-if="!posts.length" class="empty">No posts yet. Follow some users to see their posts!</p>
    </div>

    <Teleport to="body">
      <div v-if="commentPost" class="modal-overlay" @click.self="commentPost = null">
        <div class="modal">
          <div class="modal-header">
            <h3>Comments</h3>
            <button class="close-btn" @click="commentPost = null">✕</button>
          </div>
          <div class="modal-body">
            <div v-for="c in comments" :key="c.id" class="comment">
              <strong>{{ c.author_name }}</strong>
              <p>{{ c.content }}</p>
              <span class="comment-time">{{ formatDate(c.created_at) }}</span>
            </div>
            <div class="comment-input">
              <input v-model="newComment" placeholder="Write a comment..." @keyup.enter="addComment" />
              <button @click="addComment" :disabled="!newComment.trim()">Send</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
const router = useRouter();
const authStore = useAuthStore();
const config = useRuntimeConfig();
const api = useApi();

const { refreshAll } = useNotificationBadge();

const newPostContent = ref("");
const selectedFiles = ref<{ file: File; preview: string }[]>([]);
const posts = ref<any[]>([]);
const loading = ref(true);
const posting = ref(false);

const commentPost = ref<any>(null);
const comments = ref<any[]>([]);
const newComment = ref("");



import ImageGallery from "~/components/ImageGallery.vue";

const apiBase = config.public.apiBase;
const media = useMediaUrl();
const resolveMedia = (url: string) => media.resolve(url);

function handleFiles(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files) {
    for (const file of Array.from(input.files)) {
      const preview = URL.createObjectURL(file);
      selectedFiles.value.push({ file, preview });
    }
  }
  input.value = "";
}

function removeFile(i: number) {
  URL.revokeObjectURL(selectedFiles.value[i].preview);
  selectedFiles.value.splice(i, 1);
}

async function uploadFiles(): Promise<{ file_url: string; file_type: string }[]> {
  const results: { file_url: string; file_type: string }[] = [];
  for (const { file } of selectedFiles.value) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${apiBase}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authStore.token}` },
      body: form,
    });
    if (res.ok) {
      const data = await res.json();
      results.push({ file_url: data.file_url, file_type: data.file_type });
    }
  }
  return results;
}

async function createPost() {
  if (!newPostContent.value.trim() && !selectedFiles.value.length) return;
  posting.value = true;
  try {
    const media = await uploadFiles();
    const newPost = await api.request("/api/v1/posts", {
      method: "POST",
      body: JSON.stringify({ content: newPostContent.value, media }),
    });
    newPostContent.value = "";
    for (const f of selectedFiles.value) URL.revokeObjectURL(f.preview);
    selectedFiles.value = [];
    posts.value.unshift(newPost);
    await refreshAll();
  } catch (e: any) {
    alert(e.message);
  } finally {
    posting.value = false;
  }
}

function openPost(id: string) {
  router.push(`/post/${id}`);
}

async function fetchFeed() {
  try {
    posts.value = await api.request("/api/v1/feed?limit=50");
  } catch {
    posts.value = [];
  } finally {
    loading.value = false;
  }
}

async function openComments(post: any) {
  commentPost.value = post;
  try {
    comments.value = await api.request(`/api/v1/posts/${post.id}/comments`);
  } catch {
    comments.value = [];
  }
}

async function addComment() {
  if (!newComment.value.trim() || !commentPost.value) return;
  try {
    await api.request(`/api/v1/posts/${commentPost.value.id}/comment`, {
      method: "POST",
      body: JSON.stringify({ content: newComment.value }),
    });
    newComment.value = "";
    const c = await api.request(`/api/v1/posts/${commentPost.value.id}/comments`);
    comments.value = c;
    commentPost.value.comments_count = c.length;
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

async function toggleBookmark(post: any) {
  try {
    const res = await api.request(`/api/v1/posts/${post.id}/bookmark`, { method: "POST" });
    post.is_bookmarked = res.bookmarked;
    post.bookmarks_count += res.bookmarked ? 1 : -1;
  } catch (e: any) {
    alert(e.message);
  }
}

async function repost(post: any) {
  try {
    await api.request(`/api/v1/posts/${post.id}/repost`, { method: "POST" });
    alert("Reposted!");
  } catch (e: any) {
    alert(e.message);
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString();
}

onMounted(() => {
  if (authStore.isAuthenticated) fetchFeed();
  setNewPostHandler(async (data) => {
    try {
      const post = await api.request(`/api/v1/posts/${data.post_id}`);
      posts.value.unshift(post);
      return true;
    } catch {
      return false;
    }
  });
});

onUnmounted(() => {
  setNewPostHandler(null);
});
</script>

<style scoped>
.create-post {
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
}

textarea {
  width: 100%;
  border: none;
  resize: none;
  font-size: 1rem;
  font-family: inherit;
  outline: none;
  min-height: 60px;
}

.post-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.file-label {
  cursor: pointer;
  font-size: 1.3rem;
  line-height: 1;
}

.file-previews {
  display: flex;
  gap: 6px;
  width: 100%;
  overflow-x: auto;
  padding: 4px 0;
}

.file-preview {
  position: relative;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}

.file-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.file-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  border: none;
  font-size: 0.7rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.post-actions button {
  margin-left: auto;
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
}

.post-actions button:disabled { opacity: 0.5; }

.feed { display: flex; flex-direction: column; }

.post-card {
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
  transition: background 0.15s;
  cursor: pointer;
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
  gap: 40px;
  margin-top: 10px;
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
.action-btn.active { color: #1d9bf0; }
.action-btn.liked { color: #e0245e; }

.loading, .empty {
  text-align: center;
  color: #536471;
  padding: 48px 20px;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 16px;
  width: 450px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
}

.modal-header h3 { font-size: 1.1rem; }

.close-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #536471;
  padding: 4px 8px;
  border-radius: 50%;
}

.close-btn:hover { background: #f7f9fa; }

.modal-body {
  overflow-y: auto;
  padding: 12px 20px;
  flex: 1;
}

.comment {
  padding: 10px 0;
  border-bottom: 1px solid #f7f9fa;
}

.comment strong { font-size: 0.9rem; }
.comment p { margin: 4px 0; font-size: 0.9rem; }
.comment-time { font-size: 0.75rem; color: #536471; }

.comment-input {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #eff3f4;
}

.comment-input input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  outline: none;
  font-size: 0.9rem;
}

.comment-input button {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
}

.comment-input button:disabled { opacity: 0.5; }
</style>
