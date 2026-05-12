<template>
  <div class="notifications-page">
    <div class="page-header">
      <h2>Notifications</h2>
      <button v-if="notifications.length" class="read-all-btn" @click="markAllRead">
        Mark all as read
      </button>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="!notifications.length" class="empty">No notifications yet</div>
    <div v-else class="notif-list">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="notif-item"
        :class="{ unread: !n.is_read }"
        @click="handleClick(n)"
      >
        <div class="notif-dot" v-if="!n.is_read"></div>
        <div class="notif-body">
          <p class="notif-title">{{ n.title }}</p>
          <p v-if="n.content" class="notif-content">{{ n.content }}</p>
          <span class="notif-time">{{ formatDate(n.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi();
const { unreadNotifications } = useNotificationBadge();

const notifications = ref<any[]>([]);
const loading = ref(true);



async function fetchNotifications() {
  try {
    notifications.value = await api.request("/api/v1/notifications?limit=50");
  } catch {
    notifications.value = [];
  } finally {
    loading.value = false;
  }
}

const titleMap: Record<string, string> = {
  like: "liked your post",
  follow: "started following you",
  new_message: "sent you a message",
  new_post: "created a new post",
  comment_mention: "mentioned you in a comment",
};

onMounted(fetchNotifications);

async function handleClick(n: any) {
  if (!n.is_read) {
    try {
      await api.request(`/api/v1/notifications/${n.id}/read`, { method: "PATCH" });
      n.is_read = true;
      unreadNotifications.value = Math.max(0, unreadNotifications.value - 1);
    } catch {}
  }
  if (n.reference_id) {
    navigateTo(`/post/${n.reference_id}`);
  }
}

async function markAllRead() {
  try {
    await api.request("/api/v1/notifications/read-all", { method: "POST" });
    const count = notifications.value.filter((n) => !n.is_read).length;
    notifications.value.forEach((n) => (n.is_read = true));
    unreadNotifications.value = Math.max(0, unreadNotifications.value - count);
  } catch (e: any) {
    alert(e.message);
  }
}

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
}

.page-header h2 { font-size: 1.3rem; }

.read-all-btn {
  background: none;
  border: 1px solid #cfd9de;
  padding: 6px 14px;
  border-radius: 9999px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #1d9bf0;
  font-weight: 600;
  transition: background 0.15s;
}

.read-all-btn:hover { background: #e8f5fe; }

.notif-list { display: flex; flex-direction: column; }

.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #eff3f4;
  cursor: pointer;
  transition: background 0.15s;
}

.notif-item:hover { background: #f7f9fa; }

.notif-item.unread { background: #f0f7fe; }
.notif-item.unread:hover { background: #e8f5fe; }

.notif-dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
  background: #1d9bf0;
  margin-top: 6px;
}

.notif-body { flex: 1; min-width: 0; }

.notif-title {
  font-size: 0.95rem;
  color: #0f1419;
  line-height: 1.4;
}

.notif-content {
  font-size: 0.85rem;
  color: #536471;
  margin-top: 2px;
}

.notif-time {
  font-size: 0.75rem;
  color: #536471;
  margin-top: 4px;
  display: block;
}

.loading, .empty {
  text-align: center;
  color: #536471;
  padding: 48px 20px;
}
</style>
