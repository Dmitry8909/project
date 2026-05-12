<template>
  <div class="profile">
    <div v-if="loading" class="loading">Loading...</div>
    <template v-else-if="profile">
      <div class="profile-header">
        <div class="avatar-wrap">
          <div v-if="profile.avatar_url" class="avatar-img" :style="{ backgroundImage: `url(${resolveMedia(profile.avatar_url)})` }" @click="openAvatarLightbox"></div>
          <div v-else class="avatar">{{ (profile.display_name || profile.username)[0] }}</div>
        </div>
        <div class="profile-info">
          <h2>{{ profile.display_name || profile.username }}</h2>
          <p class="username">@{{ profile.username }}</p>
          <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>
          <div class="meta">
            <span v-if="profile.location" class="meta-item">📍 {{ profile.location }}</span>
            <span v-if="profile.date_of_birth" class="meta-item">🎂 {{ profile.date_of_birth }}</span>
            <span class="meta-item">📅 Joined {{ joinedDate }}</span>
          </div>
          <div class="stats">
            <button class="stat-link" @click="showFollowers = true">
              <strong>{{ profile.followers_count }}</strong> Followers
            </button>
            <button class="stat-link" @click="showFollowing = true">
              <strong>{{ profile.following_count }}</strong> Following
            </button>
          </div>
        </div>
        <div class="profile-actions">
          <button
            v-if="isOwnProfile"
            class="edit-btn"
            @click="showEditModal = true"
          >
            Edit profile
          </button>
          <button
            v-else
            @click="toggleFollow"
            class="follow-btn"
            :class="{ following: isFollowing }"
          >
            {{ isFollowing ? "Unfollow" : "Follow" }}
          </button>
        </div>
      </div>

      <div class="profile-tabs">
        <button
          :class="{ active: activeTab === 'posts' }"
          @click="activeTab = 'posts'"
        >Posts</button>
        <button
          :class="{ active: activeTab === 'media' }"
          @click="activeTab = 'media'"
        >Media</button>
        <button
          v-if="canViewLikes"
          :class="{ active: activeTab === 'likes' }"
          @click="activeTab = 'likes'; fetchLikedPosts()"
        >Likes</button>
      </div>

      <div v-if="activeTab === 'posts'" class="tab-content">
        <div v-for="post in posts" :key="post.id" class="post-card" @click="openPost(post.id)">
          <div class="post-header">
            <NuxtLink :to="`/profile/${post.author_name}`" class="author" @click.stop>
              <div class="post-avatar">
                <img v-if="post.author_avatar" :src="resolveMedia(post.author_avatar)" alt="" />
                <span v-else>{{ (post.author_name || '?')[0] }}</span>
              </div>
              <span>{{ post.author_name }}</span>
            </NuxtLink>
            <span class="time">{{ formatDate(post.created_at) }}</span>
          </div>
          <p class="post-content">{{ post.content }}</p>
          <ImageGallery v-if="post.media?.length" :images="post.media" />
          <div class="post-actions-bar" @click.stop>
            <NuxtLink :to="`/post/${post.id}`" class="action-btn">
              💬 {{ post.comments_count || "" }}
            </NuxtLink>
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
        <p v-if="!posts.length" class="empty">No posts yet.</p>
      </div>

      <div v-if="activeTab === 'media'" class="tab-content">
        <MediaPreview :mediaItems="mediaItems" />
      </div>

      <div v-if="activeTab === 'likes'" class="tab-content">
        <div v-for="post in likedPosts" :key="post.id" class="post-card" @click="openPost(post.id)">
          <div class="post-header">
            <NuxtLink :to="`/profile/${post.author_name}`" class="author" @click.stop>
              <div class="post-avatar">
                <img v-if="post.author_avatar" :src="resolveMedia(post.author_avatar)" alt="" />
                <span v-else>{{ (post.author_name || '?')[0] }}</span>
              </div>
              <span>{{ post.author_name }}</span>
            </NuxtLink>
            <span class="time">{{ formatDate(post.created_at) }}</span>
          </div>
          <p class="post-content">{{ post.content }}</p>
          <ImageGallery v-if="post.media?.length" :images="post.media" />
          <div class="post-actions-bar" @click.stop>
            <NuxtLink :to="`/post/${post.id}`" class="action-btn">
              💬 {{ post.comments_count || "" }}
            </NuxtLink>
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
        <p v-if="!likedPosts.length" class="empty">No liked posts</p>
      </div>
    </template>
    <p v-else class="error">User not found</p>

    <Teleport to="body">
      <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
        <div class="modal edit-modal">
          <div class="modal-header">
            <h3>Edit profile</h3>
            <button class="close-btn" @click="showEditModal = false">✕</button>
          </div>
          <div class="modal-body">
            <label>Photo</label>
            <div class="avatar-edit">
              <div v-if="avatarPreview || profile.avatar_url" class="avatar-edit-preview">
                <img :src="avatarPreview || resolveMedia(profile.avatar_url)" />
              </div>
              <div v-else class="avatar-edit-placeholder">{{ (profile.display_name || profile.username)[0] }}</div>
              <label class="avatar-upload-btn">
                {{ avatarPreview ? "Change" : "Upload" }}
                <input type="file" accept="image/*" @change="handleAvatarFile" hidden />
              </label>
              <button v-if="avatarPreview" class="avatar-cancel-btn" @click="cancelAvatar">Cancel</button>
            </div>
            <label>Display name</label>
            <input v-model="editForm.display_name" placeholder="Display name" maxlength="100" />
            <label>Bio</label>
            <textarea v-model="editForm.bio" placeholder="Bio" maxlength="200" rows="3"></textarea>
            <span class="char-count">{{ (editForm.bio || '').length }}/200</span>
            <label>Location</label>
            <input v-model="editForm.location" placeholder="Location" maxlength="100" />
            <label>Date of birth</label>
            <div class="date-input-wrap">
              <input v-model="editForm.date_of_birth" type="date" />
              <span class="date-icon">📅</span>
            </div>
            <label class="checkbox-label">
              <input v-model="editForm.show_dob" type="checkbox" />
              Show date of birth on profile
            </label>
            <label class="checkbox-label">
              <input v-model="editForm.likes_public" type="checkbox" />
              Make my likes visible to everyone
            </label>
            <div class="section-label">Notifications</div>
            <label class="checkbox-label">
              <input v-model="editForm.receive_new_post_notifications" type="checkbox" />
              New posts from people I follow
            </label>
            <label class="checkbox-label">
              <input v-model="editForm.receive_like_notifications" type="checkbox" />
              Likes on my posts
            </label>
            <label class="checkbox-label">
              <input v-model="editForm.receive_follow_notifications" type="checkbox" />
              New followers
            </label>
            <label class="checkbox-label">
              <input v-model="editForm.receive_new_message_notifications" type="checkbox" />
              New messages
            </label>
            <label class="checkbox-label">
              <input v-model="editForm.receive_comment_mention_notifications" type="checkbox" />
              Mentions in comments
            </label>
            <button class="save-btn" @click="saveProfile" :disabled="saving">
              {{ saving ? "Saving..." : "Save" }}
            </button>
            <p v-if="editError" class="error-text">{{ editError }}</p>
          </div>
        </div>
      </div>

      <div v-if="showFollowers" class="modal-overlay" @click.self="showFollowers = false">
        <div class="modal">
          <div class="modal-header">
            <h3>Followers</h3>
            <button class="close-btn" @click="showFollowers = false">✕</button>
          </div>
          <div class="modal-body">
            <div v-if="followersLoading" class="loading-sm">Loading...</div>
            <div v-else-if="!followersList.length" class="empty-sm">No followers</div>
            <div v-else>
              <div v-for="u in followersList" :key="u.id" class="user-row">
                <NuxtLink :to="`/profile/${u.username}`" class="user-info" @click="showFollowers = false">
                  <div class="user-avatar">
                    <img v-if="u.avatar_url" :src="resolveMedia(u.avatar_url)" alt="" />
                    <span v-else>{{ (u.display_name || u.username)[0] }}</span>
                  </div>
                  <div>
                    <div class="user-name">{{ u.display_name || u.username }}</div>
                    <div class="user-username">@{{ u.username }}</div>
                  </div>
                </NuxtLink>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="showFollowing" class="modal-overlay" @click.self="showFollowing = false">
        <div class="modal">
          <div class="modal-header">
            <h3>Following</h3>
            <button class="close-btn" @click="showFollowing = false">✕</button>
          </div>
          <div class="modal-body">
            <div v-if="followingLoading" class="loading-sm">Loading...</div>
            <div v-else-if="!followingList.length" class="empty-sm">Not following anyone</div>
            <div v-else>
              <div v-for="u in followingList" :key="u.id" class="user-row">
                <NuxtLink :to="`/profile/${u.username}`" class="user-info" @click="showFollowing = false">
                  <div class="user-avatar">
                    <img v-if="u.avatar_url" :src="resolveMedia(u.avatar_url)" alt="" />
                    <span v-else>{{ (u.display_name || u.username)[0] }}</span>
                  </div>
                  <div>
                    <div class="user-name">{{ u.display_name || u.username }}</div>
                    <div class="user-username">@{{ u.username }}</div>
                  </div>
                </NuxtLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showAvatarLightbox" class="modal-overlay" @click.self="showAvatarLightbox = false">
        <img :src="resolveMedia(profile.avatar_url)" class="avatar-lightbox-img" @click.stop />
        <button class="close-btn lightbox-close" @click="showAvatarLightbox = false">✕</button>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showCropModal" class="modal-overlay" @click.self="onCropOverlayClick">
        <div class="crop-modal">
          <div class="modal-header">
            <h3>Crop Avatar</h3>
            <button class="close-btn" @click="cancelCrop">✕</button>
          </div>
          <div
            class="crop-container"
            @mousedown="startDrag"
            @touchstart.prevent="startTouchDrag"
          >
            <div class="crop-circle"></div>
            <img
              :src="cropImageUrl"
              class="crop-image"
              :style="{
                transform: `translate(${cropTranslateX}px, ${cropTranslateY}px) scale(${cropZoom})`
              }"
              ref="cropImageRef"
              draggable="false"
            />
          </div>
          <div class="crop-controls">
            <span class="zoom-icon">🔍</span>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.01"
              v-model.number="cropZoom"
              class="crop-slider"
            />
            <span>{{ Math.round(cropZoom * 100) }}%</span>
          </div>
          <div class="modal-header" style="justify-content: flex-end; gap: 8px; border: none;">
            <button class="cancel-btn" @click="cancelCrop">Cancel</button>
            <button class="apply-btn" @click="applyCrop">Apply</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import ImageGallery from "~/components/ImageGallery.vue";
import MediaPreview from "~/components/MediaPreview.vue";

const router = useRouter();
const route = useRoute();
const config = useRuntimeConfig();
const authStore = useAuthStore();
const api = useApi();

const profile = ref<any>(null);
const posts = ref<any[]>([]);
const likedPosts = ref<any[]>([]);
const loading = ref(true);
const isFollowing = ref(false);
const activeTab = ref("posts");

const showFollowers = ref(false);
const showFollowing = ref(false);
const followersList = ref<any[]>([]);
const followingList = ref<any[]>([]);
const followersLoading = ref(false);
const followingLoading = ref(false);

const showEditModal = ref(false);
const editForm = ref({
  display_name: "",
  bio: "",
  location: "",
  date_of_birth: "",
  show_dob: true,
  likes_public: false,
  receive_new_post_notifications: true,
  receive_like_notifications: true,
  receive_follow_notifications: true,
  receive_new_message_notifications: true,
  receive_comment_mention_notifications: true,
});
const saving = ref(false);
const editError = ref("");
const avatarPreview = ref<string | null>(null);
const newAvatarFile = ref<File | null>(null);
const showAvatarLightbox = ref(false);

const showCropModal = ref(false);
const cropFile = ref<File | null>(null);
const cropImageUrl = ref<string>("");
const cropTranslateX = ref(0);
const cropTranslateY = ref(0);
const cropZoom = ref(1);
const cropSource = ref<"header" | "edit">("header");

const cropImageRef = ref<HTMLImageElement | null>(null);
const isDragging = ref(false);
const cropDragEnded = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragOrigX = ref(0);
const dragOrigY = ref(0);

const CROP_CIRCLE_SIZE = 260;



const isOwnProfile = computed(() => {
  return authStore.user?.username === route.params.username;
});

const canViewLikes = computed(() => {
  if (isOwnProfile.value) return true;
  return profile.value?.likes_public === true;
});

const joinedDate = computed(() => {
  if (!profile.value?.created_at) return "";
  const d = new Date(profile.value.created_at);
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
});

const mediaUrl = useMediaUrl();
const resolveMedia = (url: string) => mediaUrl.resolve(url);

const mediaItems = computed(() => {
  const items: { media: any; post: any }[] = [];
  for (const post of posts.value) {
    if (post.media?.length) {
      for (const m of post.media) {
        items.push({ media: m, post });
      }
    }
  }
  return items;
});

async function fetchProfile() {
  try {
    profile.value = await api.request(`/api/v1/users/by-username/${route.params.username}`);
    const following: any[] = await api.request("/api/v1/subscriptions/following");
    isFollowing.value = following.some((f: any) => f.user_id === profile.value.id);
    posts.value = await api.request(`/api/v1/posts/user/${profile.value.id}?limit=50`);
  } catch {
    profile.value = null;
  } finally {
    loading.value = false;
  }
}

async function fetchLikedPosts() {
  if (likedPosts.value.length) return;
  try {
    likedPosts.value = await api.request(`/api/v1/posts/liked?author_id=${profile.value.id}&limit=50`);
  } catch {
    likedPosts.value = [];
  }
}

async function toggleFollow() {
  try {
    if (isFollowing.value) {
      await api.request(`/api/v1/subscriptions/unfollow/${profile.value.id}`, { method: "DELETE" });
      isFollowing.value = false;
      profile.value.followers_count--;
    } else {
      await api.request(`/api/v1/subscriptions/follow/${profile.value.id}`, { method: "POST" });
      isFollowing.value = true;
      profile.value.followers_count++;
    }
  } catch (e: any) {
    alert(e.message);
  }
}

function openEditModal() {
  editForm.value = {
    display_name: profile.value.display_name || "",
    bio: profile.value.bio || "",
    location: profile.value.location || "",
    date_of_birth: profile.value.date_of_birth || "",
    show_dob: profile.value.show_dob ?? true,
    likes_public: profile.value.likes_public ?? false,
    receive_new_post_notifications: profile.value.receive_new_post_notifications ?? true,
    receive_like_notifications: profile.value.receive_like_notifications ?? true,
    receive_follow_notifications: profile.value.receive_follow_notifications ?? true,
    receive_new_message_notifications: profile.value.receive_new_message_notifications ?? true,
    receive_comment_mention_notifications: profile.value.receive_comment_mention_notifications ?? true,
  };
  avatarPreview.value = null;
  newAvatarFile.value = null;
  editError.value = "";
  showEditModal.value = true;
}

watch(showEditModal, (v) => {
  if (v) openEditModal();
});

function openAvatarLightbox() {
  showAvatarLightbox.value = true;
}

function handleAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement;
  if (!input.files?.length) return;
  openAvatarCrop(input.files[0], "edit");
  input.value = "";
}

function cancelAvatar() {
  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value);
  avatarPreview.value = null;
  newAvatarFile.value = null;
}

async function saveProfile() {
  saving.value = true;
  editError.value = "";
  try {
    let avatarUrl = profile.value.avatar_url;
    if (newAvatarFile.value) {
      const form = new FormData();
      form.append("file", newAvatarFile.value);
      const uploadRes = await fetch(`${config.public.apiBase}/api/v1/media/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${authStore.token}` },
        body: form,
      });
      if (uploadRes.ok) {
        const data = await uploadRes.json();
        avatarUrl = data.file_url;
      }
    }
    const body: any = { avatar_url: avatarUrl };
    if (editForm.value.display_name !== (profile.value.display_name || "")) {
      body.display_name = editForm.value.display_name || null;
    }
    if (editForm.value.bio !== (profile.value.bio || "")) {
      body.bio = editForm.value.bio || null;
    }
    if (editForm.value.location !== (profile.value.location || "")) {
      body.location = editForm.value.location || null;
    }
    if (editForm.value.date_of_birth !== (profile.value.date_of_birth || "")) {
      body.date_of_birth = editForm.value.date_of_birth || null;
    }
    if (editForm.value.show_dob !== profile.value.show_dob) {
      body.show_dob = editForm.value.show_dob;
    }
    if (editForm.value.likes_public !== profile.value.likes_public) {
      body.likes_public = editForm.value.likes_public;
    }
    if (editForm.value.receive_new_post_notifications !== profile.value.receive_new_post_notifications) {
      body.receive_new_post_notifications = editForm.value.receive_new_post_notifications;
    }
    if (editForm.value.receive_like_notifications !== profile.value.receive_like_notifications) {
      body.receive_like_notifications = editForm.value.receive_like_notifications;
    }
    if (editForm.value.receive_follow_notifications !== profile.value.receive_follow_notifications) {
      body.receive_follow_notifications = editForm.value.receive_follow_notifications;
    }
    if (editForm.value.receive_new_message_notifications !== profile.value.receive_new_message_notifications) {
      body.receive_new_message_notifications = editForm.value.receive_new_message_notifications;
    }
    if (editForm.value.receive_comment_mention_notifications !== profile.value.receive_comment_mention_notifications) {
      body.receive_comment_mention_notifications = editForm.value.receive_comment_mention_notifications;
    }
    const updated = await api.request("/api/v1/users/me", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    Object.assign(profile.value, updated);
    showEditModal.value = false;
  } catch (e: any) {
    editError.value = e.message;
  } finally {
    saving.value = false;
  }
}

function openAvatarCrop(file: File, source: "header" | "edit") {
  cropFile.value = file;
  cropSource.value = source;
  cropImageUrl.value = URL.createObjectURL(file);
  cropTranslateX.value = 0;
  cropTranslateY.value = 0;
  cropZoom.value = 1;
  showCropModal.value = true;
}

function cancelCrop() {
  if (cropImageUrl.value) URL.revokeObjectURL(cropImageUrl.value);
  cropFile.value = null;
  cropImageUrl.value = "";
  showCropModal.value = false;
  stopDrag();
  stopTouchDrag();
}

function onCropOverlayClick() {
  if (!cropDragEnded.value) cancelCrop();
}

async function applyCrop() {
  if (!cropFile.value || !cropImageRef.value) return;
  const img = cropImageRef.value;
  const nw = img.naturalWidth;
  const nh = img.naturalHeight;
  const zoom = cropZoom.value;
  const ox = cropTranslateX.value;
  const oy = cropTranslateY.value;

  const cropSize = CROP_CIRCLE_SIZE / zoom;
  const cropLeft = nw / 2 - CROP_CIRCLE_SIZE / 2 / zoom - ox / zoom;
  const cropTop = nh / 2 - CROP_CIRCLE_SIZE / 2 / zoom - oy / zoom;
  const clampedLeft = Math.max(0, Math.min(nw - cropSize, cropLeft));
  const clampedTop = Math.max(0, Math.min(nh - cropSize, cropTop));
  const clampedSize = Math.min(cropSize, nw - clampedLeft, nh - clampedTop);

  const canvas = document.createElement("canvas");
  const outputSize = 400;
  canvas.width = outputSize;
  canvas.height = outputSize;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(img, clampedLeft, clampedTop, clampedSize, clampedSize, 0, 0, outputSize, outputSize);

  canvas.toBlob(async (blob) => {
    if (!blob) return;
    if (cropImageUrl.value) URL.revokeObjectURL(cropImageUrl.value);
    showCropModal.value = false;

    if (cropSource.value === "header") {
      const form = new FormData();
      form.append("file", blob, "avatar.png");
      try {
        const res = await fetch(`${config.public.apiBase}/api/v1/media/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${authStore.token}` },
          body: form,
        });
        if (res.ok) {
          const data = await res.json();
          const updated = await api.request("/api/v1/users/me", {
            method: "PATCH",
            body: JSON.stringify({ avatar_url: data.file_url }),
          });
          Object.assign(profile.value, updated);
        }
      } catch {}
    } else {
      const url = URL.createObjectURL(blob);
      avatarPreview.value = url;
      newAvatarFile.value = new File([blob], "avatar.png", { type: "image/png" });
    }
    cropFile.value = null;
    stopDrag();
    stopTouchDrag();
  }, "image/png");
}

function startDrag(e: MouseEvent) {
  isDragging.value = true;
  dragStartX.value = e.clientX;
  dragStartY.value = e.clientY;
  dragOrigX.value = cropTranslateX.value;
  dragOrigY.value = cropTranslateY.value;
  document.addEventListener("mousemove", doDrag);
  document.addEventListener("mouseup", stopDrag);
}

function startTouchDrag(e: TouchEvent) {
  const t = e.touches[0];
  isDragging.value = true;
  dragStartX.value = t.clientX;
  dragStartY.value = t.clientY;
  dragOrigX.value = cropTranslateX.value;
  dragOrigY.value = cropTranslateY.value;
  document.addEventListener("touchmove", doTouchDrag);
  document.addEventListener("touchend", stopTouchDrag);
}

function doDrag(e: MouseEvent) {
  if (!isDragging.value) return;
  cropTranslateX.value = dragOrigX.value + (e.clientX - dragStartX.value);
  cropTranslateY.value = dragOrigY.value + (e.clientY - dragStartY.value);
}

function doTouchDrag(e: TouchEvent) {
  if (!isDragging.value) return;
  const t = e.touches[0];
  cropTranslateX.value = dragOrigX.value + (t.clientX - dragStartX.value);
  cropTranslateY.value = dragOrigY.value + (t.clientY - dragStartY.value);
}

function stopDrag() {
  isDragging.value = false;
  cropDragEnded.value = true;
  setTimeout(() => { cropDragEnded.value = false; }, 0);
  document.removeEventListener("mousemove", doDrag);
  document.removeEventListener("mouseup", stopDrag);
}

function stopTouchDrag() {
  isDragging.value = false;
  cropDragEnded.value = true;
  setTimeout(() => { cropDragEnded.value = false; }, 0);
  document.removeEventListener("touchmove", doTouchDrag);
  document.removeEventListener("touchend", stopTouchDrag);
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

function openPost(id: string) {
  router.push(`/post/${id}`);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString();
}

watch(showFollowers, async (v) => {
  if (v && !followersList.value.length) {
    followersLoading.value = true;
    try {
      followersList.value = await api.request("/api/v1/subscriptions/followers");
    } catch { }
    followersLoading.value = false;
  }
});

watch(showFollowing, async (v) => {
  if (v && !followingList.value.length) {
    followingLoading.value = true;
    try {
      followingList.value = await api.request("/api/v1/subscriptions/following");
    } catch { }
    followingLoading.value = false;
  }
});

onMounted(fetchProfile);

function cleanupCropListeners() {
  document.removeEventListener("mousemove", doDrag);
  document.removeEventListener("mouseup", stopDrag);
  document.removeEventListener("touchmove", doTouchDrag);
  document.removeEventListener("touchend", stopTouchDrag);
}

onUnmounted(cleanupCropListeners);
</script>

<style scoped>
.profile-header {
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
  border-bottom: 1px solid #eff3f4;
}

.avatar-wrap {
  position: relative;
  width: 64px;
  height: 64px;
  min-width: 64px;
  flex-shrink: 0;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
}

.avatar-img {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-size: cover;
  background-position: center;
}

.avatar-lightbox-img {
  width: 400px;
  height: 400px;
  max-width: 80vw;
  max-height: 80vw;
  border-radius: 50%;
  object-fit: cover;
}

.lightbox-close {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1001;
  font-size: 1.5rem;
  background: rgba(0,0,0,0.5);
  color: #fff;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
}

.avatar-edit {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.avatar-edit-preview {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
}

.avatar-edit-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-edit-placeholder {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 700;
}

.avatar-upload-btn {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}

.avatar-cancel-btn {
  background: none;
  border: 1px solid #cfd9de;
  padding: 6px 14px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #536471;
}

.profile-info { flex: 1; }

h2 { font-size: 1.2rem; margin-bottom: 2px; }
.username { color: #536471; font-size: 0.9rem; margin-bottom: 8px; }
.bio { margin-bottom: 8px; font-size: 0.95rem; white-space: pre-wrap; }

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
}

.meta-item {
  font-size: 0.85rem;
  color: #536471;
}

.stats {
  display: flex;
  gap: 20px;
}

.stat-link {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  color: #536471;
  padding: 0;
  font-family: inherit;
}

.stat-link:hover { color: #1d9bf0; }
.stat-link strong { color: #0f1419; }

.profile-actions {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
}

.edit-btn {
  background: #fff;
  color: #0f1419;
  border: 1px solid #cfd9de;
  padding: 8px 20px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
}

.edit-btn:hover { background: #f7f9fa; }

.follow-btn {
  background: #0f1419;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 700;
  flex-shrink: 0;
}

.follow-btn.following {
  background: #fff;
  color: #0f1419;
  border: 1px solid #cfd9de;
}

.profile-tabs {
  display: flex;
  border-bottom: 1px solid #eff3f4;
}

.profile-tabs button {
  flex: 1;
  padding: 14px 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: #536471;
  position: relative;
  font-family: inherit;
}

.profile-tabs button:hover { color: #0f1419; }

.profile-tabs button.active {
  color: #0f1419;
  font-weight: 600;
}

.profile-tabs button.active::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 56px;
  height: 3px;
  background: #1d9bf0;
  border-radius: 9999px;
}

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
  text-decoration: none;
  font-family: inherit;
}

.action-btn:hover { color: #1d9bf0; }
.action-btn.active { color: #1d9bf0; }
.action-btn.liked { color: #e0245e; }

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
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.edit-modal { width: 500px; }

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
  padding: 20px;
  flex: 1;
}

.modal-body label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #0f1419;
  margin-bottom: 4px;
  margin-top: 12px;
}

.modal-body label:first-child { margin-top: 0; }

.modal-body :where(input, textarea) {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #cfd9de;
  font-size: 0.9rem;
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}

.modal-body input:not([type="checkbox"]):not([type="file"]) {
  border-radius: 9999px;
}

.modal-body input[type="date"] {
  appearance: none;
  -webkit-appearance: none;
  background: #fff;
  color-scheme: light;
  min-height: 44px;
}

.date-input-wrap {
  position: relative;
}

.date-input-wrap input[type="date"] {
  padding-right: 40px;
}

.date-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  font-size: 1.1rem;
  opacity: 0.6;
}

.modal-body textarea {
  border-radius: 16px;
  resize: vertical;
}

.modal-body input:focus,
.modal-body textarea:focus {
  border-color: #1d9bf0;
  box-shadow: 0 0 0 2px rgba(29,155,240,0.15);
}

.char-count {
  display: block;
  text-align: right;
  font-size: 0.75rem;
  color: #536471;
  margin-top: 2px;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 400 !important;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.section-label {
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f1419;
  margin-top: 20px;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #eff3f4;
}

.save-btn {
  width: 100%;
  padding: 12px;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 9999px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 600;
  margin-top: 16px;
}

.save-btn:hover { background: #1a8cd8; }
.save-btn:disabled { opacity: 0.6; }

.error-text {
  color: #e0245e;
  font-size: 0.85rem;
  margin-top: 8px;
  text-align: center;
}

.user-row {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #f7f9fa;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: #0f1419;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
  flex-shrink: 0;
  overflow: hidden;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-name { font-weight: 600; font-size: 0.9rem; }
.user-username { font-size: 0.8rem; color: #536471; }

.crop-modal {
  background: #fff;
  border-radius: 16px;
  width: 340px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  overflow: hidden;
}

.crop-container {
  position: relative;
  width: 280px;
  height: 280px;
  margin: 16px auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  overflow: hidden;
  user-select: none;
}

.crop-container:active { cursor: grabbing; }

.crop-circle {
  position: absolute;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  border: 2px solid #1d9bf0;
  box-shadow: 0 0 0 9999px rgba(0,0,0,0.5);
  pointer-events: none;
  z-index: 2;
}

.crop-image {
  max-width: none;
  pointer-events: none;
  user-select: none;
}

.crop-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 12px;
  font-size: 0.85rem;
  color: #536471;
}

.crop-slider {
  flex: 1;
  accent-color: #1d9bf0;
  cursor: pointer;
}

.zoom-icon { font-size: 1rem; }

.cancel-btn {
  background: none;
  border: 1px solid #cfd9de;
  padding: 6px 16px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.85rem;
  font-family: inherit;
  color: #0f1419;
}

.apply-btn {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 6px 16px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  font-family: inherit;
}

.loading, .error { text-align: center; color: #536471; padding: 48px 20px; }
.loading-sm, .empty-sm { text-align: center; color: #536471; padding: 32px; font-size: 0.9rem; }
.empty { color: #536471; padding: 32px 0; text-align: center; }
</style>
