<template>
  <div class="media-grid">
    <div
      v-for="item in mediaItems"
      :key="item.media.id"
      class="media-thumb-wrap"
      @click="open(item.media, item.post)"
    >
      <img :src="resolveUrl(item.media.file_url)" class="media-thumb" />
    </div>
    <p v-if="!mediaItems.length" class="empty">No media</p>
  </div>

  <Teleport to="body">
    <div v-if="activeMedia" class="preview-overlay" @click.self="close">
      <div class="preview-layout">
        <div class="preview-gallery">
          <img :src="resolveUrl(activeMedia.file_url)" class="preview-img" />
          <div v-if="gallery.length > 1" class="gallery-nav-btns">
            <button class="nav-btn" @click="prevMedia">‹</button>
            <span class="counter">{{ currentIdx + 1 }} / {{ gallery.length }}</span>
            <button class="nav-btn" @click="nextMedia">›</button>
          </div>
        </div>
        <div class="preview-sidebar">
          <div class="sidebar-header">
            <NuxtLink
              :to="`/profile/${activePost.author_name}`"
              class="sidebar-author"
              @click="close"
            >
              <div class="author-avatar">{{ (activePost.author_name || '?')[0] }}</div>
              <span>{{ activePost.author_name }}</span>
            </NuxtLink>
            <button class="close-btn" @click="close">✕</button>
          </div>

          <div class="sidebar-content">
            <p class="post-text">{{ activePost.content }}</p>
            <div class="post-actions">
              <button
                class="action-btn"
                :class="{ liked: activePost.is_liked }"
                @click="toggleLike"
              >
                {{ activePost.is_liked ? "❤️" : "🤍" }} {{ activePost.likes_count || "" }}
              </button>
              <button
                class="action-btn"
                :class="{ active: activePost.is_bookmarked }"
                @click="toggleBookmark"
              >
                {{ activePost.is_bookmarked ? "🔖" : "🔖" }}
              </button>
            </div>
          </div>

          <div class="sidebar-comments">
            <div class="comments-list">
              <div v-for="c in comments" :key="c.id" class="comment">
                <NuxtLink :to="`/profile/${c.author_username}`" class="comment-author">
                  <strong>{{ c.author_name }}</strong>
                </NuxtLink>
                <p>{{ c.content }}</p>
              </div>
              <p v-if="!comments.length" class="empty-comments">No comments yet</p>
            </div>
            <div class="comment-input">
              <input v-model="newComment" placeholder="Write a comment..." @keyup.enter="addComment" />
              <button @click="addComment" :disabled="!newComment.trim()">Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const api = useApi();
const mediaUrl = useMediaUrl();
const resolveUrl = (url: string) => mediaUrl.resolve(url);

export interface MediaItem {
  media: { id: string; file_url: string; file_type: string; order: number };
  post: any;
}

const props = defineProps<{ mediaItems: MediaItem[] }>();

const activeMedia = ref<any>(null);
const activePost = ref<any>(null);
const currentIdx = ref(0);
const comments = ref<any[]>([]);
const newComment = ref("");

const gallery = computed(() => props.mediaItems.map((m) => m.media));

function open(media: any, post: any) {
  activeMedia.value = media;
  activePost.value = reactive(post);
  currentIdx.value = gallery.value.findIndex((m) => m.id === media.id);
  fetchComments();
}

function close() {
  activeMedia.value = null;
  activePost.value = null;
  comments.value = [];
  newComment.value = "";
}

function prevMedia() {
  if (currentIdx.value > 0) {
    currentIdx.value--;
    const item = props.mediaItems[currentIdx.value];
    activeMedia.value = item.media;
    activePost.value = reactive(item.post);
    fetchComments();
  }
}

function nextMedia() {
  if (currentIdx.value < props.mediaItems.length - 1) {
    currentIdx.value++;
    const item = props.mediaItems[currentIdx.value];
    activeMedia.value = item.media;
    activePost.value = reactive(item.post);
    fetchComments();
  }
}

async function fetchComments() {
  if (!activePost.value) return;
  try {
    comments.value = await api.request(`/api/v1/posts/${activePost.value.id}/comments`);
  } catch {
    comments.value = [];
  }
}

async function addComment() {
  if (!newComment.value.trim() || !activePost.value) return;
  try {
    await api.request(`/api/v1/posts/${activePost.value.id}/comment`, {
      method: "POST",
      body: JSON.stringify({ content: newComment.value }),
    });
    newComment.value = "";
    await fetchComments();
    activePost.value.comments_count = comments.value.length;
  } catch (e: any) {
    alert(e.message);
  }
}

async function toggleLike() {
  if (!activePost.value) return;
  const wasLiked = activePost.value.is_liked;
  activePost.value.is_liked = !wasLiked;
  activePost.value.likes_count += activePost.value.is_liked ? 1 : -1;
  try {
    const res = await api.toggleLike(activePost.value.id);
    if (res.liked !== activePost.value.is_liked) {
      activePost.value.is_liked = res.liked;
      activePost.value.likes_count += res.liked ? 1 : -1;
    }
  } catch {
    activePost.value.is_liked = wasLiked;
    activePost.value.likes_count += wasLiked ? 1 : -1;
  }
}

async function toggleBookmark() {
  if (!activePost.value) return;
  try {
    const res = await api.request(`/api/v1/posts/${activePost.value.id}/bookmark`, { method: "POST" });
    activePost.value.is_bookmarked = res.bookmarked;
  } catch (e: any) {
    alert(e.message);
  }
}

function onKeydown(e: KeyboardEvent) {
  if (!activeMedia.value) return;
  if (e.key === "Escape") close();
  if (e.key === "ArrowLeft") prevMedia();
  if (e.key === "ArrowRight") nextMedia();
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>

<style scoped>
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 4px;
}

.media-thumb-wrap {
  cursor: pointer;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 8px;
}

.media-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity 0.15s;
}

.media-thumb:hover { opacity: 0.9; }

.preview-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.preview-layout {
  display: flex;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  max-width: 1100px;
  width: 100%;
  height: 85vh;
}

.preview-gallery {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #000;
  position: relative;
  min-width: 0;
}

.preview-img {
  max-width: 100%;
  max-height: calc(85vh - 60px);
  object-fit: contain;
}

.gallery-nav-btns {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px;
}

.nav-btn {
  background: rgba(255,255,255,0.15);
  color: #fff;
  border: none;
  font-size: 1.5rem;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
}

.nav-btn:hover { background: rgba(255,255,255,0.3); }

.counter { color: #fff; font-size: 0.85rem; }

.preview-sidebar {
  width: 360px;
  min-width: 360px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eff3f4;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #eff3f4;
}

.sidebar-author {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #0f1419;
  font-weight: 600;
  font-size: 0.95rem;
}

.author-avatar {
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
}

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

.sidebar-content {
  padding: 16px;
  border-bottom: 1px solid #eff3f4;
}

.post-text {
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 12px;
}

.post-actions {
  display: flex;
  gap: 24px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #536471;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 4px;
}

.action-btn:hover { color: #1d9bf0; }
.action-btn.liked { color: #e0245e; }
.action-btn.active { color: #1d9bf0; }

.sidebar-comments {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.comments-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.comment {
  margin-bottom: 12px;
}

.comment-author {
  text-decoration: none;
  color: #0f1419;
  font-size: 0.85rem;
}

.comment-author:hover { color: #1d9bf0; }

.comment p {
  font-size: 0.9rem;
  margin-top: 2px;
}

.empty-comments {
  color: #536471;
  font-size: 0.85rem;
  text-align: center;
  padding: 24px 0;
}

.comment-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #eff3f4;
}

.comment-input input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  outline: none;
  font-size: 0.85rem;
}

.comment-input button {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
}

.comment-input button:disabled { opacity: 0.5; }

.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #536471;
  padding: 32px;
}
</style>
