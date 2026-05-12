<template>
  <div class="messages-page">
    <div class="sidebar">
      <h3>Conversations</h3>
      <div class="search-box">
        <input
          v-model="searchQuery"
          placeholder="Search users..."
          @input="debouncedSearch"
        />
      </div>

      <div v-if="searchResults.length" class="search-results">
        <div
          v-for="u in searchResults"
          :key="u.id"
          class="user-row"
          @click="startConversation(u)"
        >
          <div class="conv-avatar">{{ (u.display_name || u.username)[0] }}</div>
          <div class="conv-info">
            <span class="conv-user">{{ u.display_name || u.username }}</span>
            <span class="conv-preview">@{{ u.username }}</span>
          </div>
        </div>
      </div>

      <div v-if="!searchQuery && conversations.length === 0" class="empty">No conversations</div>
      <div
        v-for="conv in conversations"
        :key="conv.user_id"
        class="conv-item"
        :class="{ active: selectedUserId === conv.user_id }"
        @click="selectConversation(conv)"
      >
        <div class="conv-avatar">{{ (conv.display_name || conv.username)[0] }}</div>
        <div class="conv-info">
          <span class="conv-user">{{ conv.display_name || conv.username }}</span>
          <span class="conv-preview">{{ conv.last_message }}</span>
        </div>
        <span v-if="conv.unread_count" class="unread-badge">{{ conv.unread_count }}</span>
      </div>
    </div>

    <div class="chat">
      <div v-if="!selectedUserId" class="no-chat">
        <p>Search for a user to start messaging</p>
      </div>
      <template v-else>
        <div class="chat-header">
          <div class="conv-avatar">{{ chatUserName[0] }}</div>
          <span class="chat-user-name">{{ chatUserName }}</span>
        </div>
        <div class="messages-list" ref="messagesRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="msg"
            :class="{ mine: msg.sender_id === authStore.user?.id }"
          >
            <div v-if="msg.content" class="msg-content">{{ msg.content }}</div>
            <div v-if="msg.media?.length" class="msg-media">
              <img
                v-for="m in msg.media"
                :key="m.id"
                :src="mediaResolve(m.file_url)"
                class="msg-img"
                alt=""
              />
            </div>
            <div class="msg-meta">
              <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
              <span v-if="msg.sender_id === authStore.user?.id" class="msg-status">
                <span v-if="msg.is_read" class="read">✓✓</span>
                <span v-else class="delivered">✓</span>
              </span>
            </div>
          </div>
        </div>
        <div class="send-area">
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
          <input
            v-model="newMessage"
            placeholder="Type a message..."
            @keyup.enter="sendMessage"
          />
          <button @click="sendMessage" :disabled="!canSend">Send</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const api = useApi();
const config = useRuntimeConfig();
const { unreadMessages, refreshAll } = useNotificationBadge();

let refreshTimer: ReturnType<typeof setInterval> | null = null;

let loadingConversations = false;

async function safeFetchConversations() {
  if (loadingConversations) return;
  loadingConversations = true;
  await fetchConversations();
  loadingConversations = false;
}

function startRefreshTimer() {
  stopRefreshTimer();
  refreshTimer = setInterval(() => {
    if (selectedUserId.value && !loadingMessages && !loadingConversations) {
      loadMessages().then(() => safeFetchConversations());
    }
  }, 3000);
}

function stopRefreshTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

const conversations = ref<any[]>([]);
const selectedUserId = ref<string | null>(null);
const selectedUser = ref<any>(null);
const messages = ref<any[]>([]);
const newMessage = ref("");
const messagesRef = ref<HTMLElement | null>(null);

const searchQuery = ref("");
const searchResults = ref<any[]>([]);

const selectedFiles = ref<{ file: File; preview: string }[]>([]);



const apiBase = config.public.apiBase;
const mediaUrl = useMediaUrl();
const mediaResolve = (url: string) => mediaUrl.resolve(url);

const chatUserName = computed(() => {
  if (!selectedUser.value) return "";
  return selectedUser.value.display_name || selectedUser.value.username;
});

const canSend = computed(() => {
  return newMessage.value.trim() || selectedFiles.value.length > 0;
});

let debounceTimer: ReturnType<typeof setTimeout>;
function debouncedSearch() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 300);
}

async function doSearch() {
  const q = searchQuery.value.trim();
  if (!q) {
    searchResults.value = [];
    return;
  }
  try {
    searchResults.value = await api.request(`/api/v1/users/search?q=${encodeURIComponent(q)}`);
  } catch {
    searchResults.value = [];
  }
}

async function startConversation(user: any) {
  searchQuery.value = "";
  searchResults.value = [];
  selectedUser.value = user;
  selectedUserId.value = user.id;
  await loadMessages();
  await fetchConversations();
  startRefreshTimer();
}

async function selectConversation(conv: any) {
  selectedUserId.value = conv.user_id;
  selectedUser.value = {
    id: conv.user_id,
    username: conv.username,
    display_name: conv.display_name,
  };
  searchQuery.value = "";
  searchResults.value = [];
  await loadMessages();
  await fetchConversations();
  startRefreshTimer();
}

async function fetchConversations() {
  try {
    conversations.value = await api.request("/api/v1/messages/conversations");
  } catch {
    conversations.value = [];
  }
  await refreshAll();
}

let loadingMessages = false;
let pendingLoad = false;

async function loadMessages() {
  if (!selectedUserId.value) return;
  if (loadingMessages) {
    pendingLoad = true;
    return;
  }
  loadingMessages = true;
  pendingLoad = false;
  try {
    messages.value = await api.request(`/api/v1/messages/conversation/${selectedUserId.value}?limit=50`);
    nextTick(() => {
      if (messagesRef.value) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
      }
    });
  } catch {
    messages.value = [];
  }
  loadingMessages = false;
  await refreshAll();
  if (pendingLoad) {
    pendingLoad = false;
    await loadMessages();
  }
}

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
    try {
      const res = await fetch(`${apiBase}/api/v1/media/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${authStore.token}` },
        body: form,
      });
      if (res.ok) {
        const data = await res.json();
        results.push({ file_url: data.file_url, file_type: data.file_type });
      }
    } catch {}
  }
  return results;
}

async function sendMessage() {
  if (!canSend.value || !selectedUserId.value) return;
  try {
    const media = await uploadFiles();
    const msg = await api.request("/api/v1/messages", {
      method: "POST",
      body: JSON.stringify({
        receiver_id: selectedUserId.value,
        content: newMessage.value,
        media,
      }),
    });
    messages.value.push(msg);
    newMessage.value = "";
    for (const f of selectedFiles.value) {
      URL.revokeObjectURL(f.preview);
    }
    selectedFiles.value = [];
    nextTick(() => {
      if (messagesRef.value) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
      }
    });
    await fetchConversations();
  } catch (e: any) {
    alert(e.message);
  }
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

onMounted(() => {
  fetchConversations();
  setNewMessageHandler(async (data) => {
    if (data.sender_id === selectedUserId.value) {
      await loadMessages();
      await fetchConversations();
      return true;
    }
    await fetchConversations();
    return false;
  });
  setReadReceiptHandler(async (data) => {
    if (data.conversation_with === selectedUserId.value) {
      await loadMessages();
      await fetchConversations();
    }
  });
});

onUnmounted(() => {
  setNewMessageHandler(null);
  setReadReceiptHandler(null);
  stopRefreshTimer();
});
</script>

<style scoped>
.messages-page {
  display: flex;
  height: 100vh;
  background: #fff;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  min-width: 280px;
  border-right: 1px solid #eff3f4;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar h3 {
  padding: 16px 16px 8px;
  font-size: 1.1rem;
}

.search-box {
  padding: 0 16px 8px;
}

.search-box input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cfd9de;
  border-radius: 9999px;
  font-size: 0.85rem;
  outline: none;
}

.search-box input:focus {
  border-color: #1d9bf0;
}

.search-results {
  border-bottom: 1px solid #eff3f4;
  max-height: 200px;
  overflow-y: auto;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.user-row:hover {
  background: #f7f9fa;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.conv-item:hover, .conv-item.active {
  background: #f7f9fa;
}

.conv-avatar {
  width: 40px;
  height: 40px;
  min-width: 40px;
  border-radius: 50%;
  background: #1d9bf0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.conv-info {
  flex: 1;
  overflow: hidden;
}

.conv-user {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
}

.conv-preview {
  display: block;
  font-size: 0.8rem;
  color: #536471;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unread-badge {
  background: #1d9bf0;
  color: #fff;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #eff3f4;
  font-weight: 600;
}

.chat-user-name {
  font-size: 1rem;
}

.no-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #536471;
  font-size: 0.95rem;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.msg {
  margin-bottom: 12px;
  max-width: 75%;
}

.msg.mine {
  margin-left: auto;
}

.msg-content {
  background: #f0f0f0;
  padding: 10px 14px;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
  word-wrap: break-word;
}

.msg.mine .msg-content {
  background: #1d9bf0;
  color: #fff;
  border-radius: 16px;
  border-bottom-right-radius: 4px;
}

.msg-media {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.msg-img {
  max-width: 200px;
  max-height: 200px;
  border-radius: 12px;
  object-fit: cover;
  cursor: pointer;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  padding: 0 4px;
}

.msg-time {
  font-size: 0.75rem;
  color: #536471;
}

.msg-status {
  font-size: 0.75rem;
}

.msg-status .delivered {
  color: #536471;
}

.msg-status .read {
  color: #1d9bf0;
}

.msg.mine .msg-meta {
  justify-content: flex-end;
}

.send-area {
  padding: 12px 20px;
  border-top: 1px solid #eff3f4;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
  padding-bottom: 4px;
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

.send-area input {
  flex: 1;
  min-width: 100px;
  padding: 10px 14px;
  border: 1px solid #cfd9de;
  border-radius: 24px;
  font-size: 0.95rem;
  outline: none;
}

.send-area input:focus {
  border-color: #1d9bf0;
}

.send-area button {
  background: #1d9bf0;
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 24px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.send-area button:hover {
  background: #1a8cd8;
}

.send-area button:disabled {
  opacity: 0.5;
}

.empty {
  padding: 32px 16px;
  text-align: center;
  color: #536471;
  font-size: 0.9rem;
}
</style>
