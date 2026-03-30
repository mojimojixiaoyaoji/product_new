<template>
  <div class="theme-toggle">
    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'system' }"
      title="跟随系统"
      @click="themeStore.setMode('system')"
    >
      <span class="icon">🖥️</span>
    </button>
    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'dark' }"
      title="深色模式"
      @click="themeStore.setMode('dark')"
    >
      <span class="icon">🌙</span>
    </button>
    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'light' }"
      title="浅色模式"
      @click="themeStore.setMode('light')"
    >
      <span class="icon">☀️</span>
    </button>
  </div>
</template>

<script lang="ts" setup>
import { useThemeStore } from '@/store/theme'

const themeStore = useThemeStore()
</script>

<style lang="scss" scoped>
.theme-toggle {
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px;
  border-radius: 8px;

  .theme-btn {
    background: transparent;
    border: none;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
    opacity: 0.5;
    transition: all 0.3s;

    .icon {
      font-size: 14px;
    }

    &:hover {
      opacity: 0.8;
      background: rgba(255, 255, 255, 0.1);
    }

    &.active {
      opacity: 1;
      background: rgba(215, 0, 15, 0.3);
    }
  }
}

// Light theme overrides
[data-theme="light"] .theme-toggle {
  background: rgba(0, 0, 0, 0.08);

  .theme-btn {
    &:hover {
      background: rgba(0, 0, 0, 0.08);
    }

    &.active {
      background: rgba(215, 0, 15, 0.2);
    }
  }
}
</style>
