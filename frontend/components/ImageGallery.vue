<template>
  <div v-if="images.length" class="gallery-grid">
    <img
      v-for="(img, i) in images"
      :key="img.id"
      :src="media.resolve(img.file_url)"
      class="gallery-thumb"
      @click.stop="open(i)"
    />
  </div>

  <Teleport to="body">
    <div v-if="activeIndex !== null" class="gallery-overlay" @click.self="close">
      <button class="gallery-nav gallery-prev" @click="prev">‹</button>
      <img :src="media.resolve(images[activeIndex].file_url)" class="gallery-full" />
      <button class="gallery-nav gallery-next" @click="next">›</button>
      <div class="gallery-counter">{{ activeIndex + 1 }} / {{ images.length }}</div>
      <button class="gallery-close" @click="close">✕</button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const media = useMediaUrl();

const props = defineProps<{ images: any[] }>();
const activeIndex = ref<number | null>(null);

function open(i: number) {
  activeIndex.value = i;
}

function close() {
  activeIndex.value = null;
}

function prev() {
  if (activeIndex.value !== null && activeIndex.value > 0) {
    activeIndex.value--;
  }
}

function next() {
  if (activeIndex.value !== null && activeIndex.value < props.images.length - 1) {
    activeIndex.value++;
  }
}

function onKeydown(e: KeyboardEvent) {
  if (activeIndex.value === null) return;
  if (e.key === "Escape") close();
  if (e.key === "ArrowLeft") prev();
  if (e.key === "ArrowRight") next();
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>

<style scoped>
.gallery-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.gallery-thumb {
  max-width: 200px;
  max-height: 200px;
  border-radius: 12px;
  object-fit: cover;
  cursor: pointer;
  transition: opacity 0.15s;
}

.gallery-thumb:hover {
  opacity: 0.9;
}

.gallery-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.gallery-full {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
}

.gallery-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,0.15);
  color: #fff;
  border: none;
  font-size: 2.5rem;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.gallery-nav:hover { background: rgba(255,255,255,0.3); }
.gallery-prev { left: 20px; }
.gallery-next { right: 20px; }

.gallery-counter {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  color: #fff;
  font-size: 0.9rem;
  background: rgba(0,0,0,0.5);
  padding: 6px 16px;
  border-radius: 9999px;
}

.gallery-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255,255,255,0.15);
  color: #fff;
  border: none;
  font-size: 1.2rem;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
