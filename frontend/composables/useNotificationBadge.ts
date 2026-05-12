let wsInstance: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let activeInstances = 0

type MessageHandler = (data: any) => boolean | Promise<boolean>
let newMessageHandler: MessageHandler | null = null
let readReceiptHandler: ((data: any) => Promise<void> | void) | null = null
let newPostHandler: MessageHandler | null = null

export function setNewMessageHandler(handler: MessageHandler | null) {
  newMessageHandler = handler
}

export function setReadReceiptHandler(handler: ((data: any) => Promise<void> | void) | null) {
  readReceiptHandler = handler
}

export function setNewPostHandler(handler: MessageHandler | null) {
  newPostHandler = handler
}

async function callMessageHandler(data: any): Promise<boolean> {
  if (!newMessageHandler) return false
  const result = newMessageHandler(data)
  if (result instanceof Promise) return await result
  return result
}

async function callNewPostHandler(data: any): Promise<boolean> {
  if (!newPostHandler) return false
  const result = newPostHandler(data)
  if (result instanceof Promise) return await result
  return result
}

export function useNotificationBadge() {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const api = useApi()

  const unreadNotifications = useState<number>('notif-badge-notifications', () => 0)
  const unreadMessages = useState<number>('notif-badge-messages', () => 0)

  async function fetchUnreadNotifications() {
    try {
      const res = await api.request<{ count: number }>('/api/v1/notifications/unread-count')
      unreadNotifications.value = res.count
    } catch {}
  }

  async function fetchUnreadMessages() {
    try {
      const res = await api.request<{ count: number }>('/api/v1/messages/unread-count')
      unreadMessages.value = res.count
    } catch {}
  }

  async function refreshAll() {
    await Promise.all([fetchUnreadNotifications(), fetchUnreadMessages()])
  }

  function getNotificationUrl(data: any): string {
    if (data.post_id) return `/post/${data.post_id}`
    if (data.type === 'new_message') return '/messages'
    return '/notifications'
  }

  function showBrowserNotification(data: any) {
    if (Notification.permission !== 'granted') return
    const titles: Record<string, string> = {
      like: `${data.actor_name || 'Someone'} liked your post`,
      follow: `${data.actor_name || 'Someone'} started following you`,
      new_post: `${data.actor_name || 'Someone'} created a new post`,
      comment_mention: `${data.actor_name || 'Someone'} mentioned you in a comment`,
    }
    const title = titles[data.type] || 'New notification'
    const url = getNotificationUrl(data)
    const n = new Notification(title, { body: data.content_preview || '' })
    setTimeout(() => n.close(), 5000)
    n.onclick = () => {
      window.focus()
      window.location.href = url
    }
  }

  function connectWs() {
    if (wsInstance) return
    const token = authStore.token
    if (!token) return
    wsInstance = new WebSocket(`${config.public.wsBase}/ws?token=${encodeURIComponent(token)}`)
    wsInstance.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'new_message') {
          const handled = await callMessageHandler(data)
          if (!handled) {
            unreadMessages.value++
          }
          await refreshAll()
        } else if (data.type === 'read_receipt') {
          if (readReceiptHandler) {
            await readReceiptHandler(data)
          }
          await refreshAll()
        } else if (data.type === 'new_post') {
          const handled = await callNewPostHandler(data)
          if (!handled) {
            unreadNotifications.value++
            showBrowserNotification(data)
          }
          await refreshAll()
        } else {
          unreadNotifications.value++
          showBrowserNotification(data)
        }
      } catch {}
    }
    wsInstance.onclose = () => {
      wsInstance = null
      reconnectTimer = setTimeout(connectWs, 5000)
    }
    wsInstance.onerror = () => {
      wsInstance?.close()
    }
  }

  function disconnectWs() {
    if (wsInstance) {
      wsInstance.close()
      wsInstance = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  watch(() => authStore.isAuthenticated, (val) => {
    if (!val) {
      unreadNotifications.value = 0
      unreadMessages.value = 0
      disconnectWs()
    } else if (activeInstances > 0) {
      refreshAll()
      connectWs()
    }
  })

  onMounted(() => {
    activeInstances++
    if (activeInstances === 1) {
      if (authStore.isAuthenticated) {
        refreshAll()
        connectWs()
      }
      if (Notification.permission === 'default') {
        Notification.requestPermission()
      }
    }
  })

  onUnmounted(() => {
    activeInstances--
    if (activeInstances === 0) {
      disconnectWs()
    }
  })

  return {
    unreadNotifications,
    unreadMessages,
    refreshAll,
  }
}
