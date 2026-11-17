<script setup>
import { THEMES, THEME_META, ui, setTheme } from '@/stores/app'
</script>

<template>
  <div class="theme-switcher" role="group" aria-label="选择界面主题">
    <button
      v-for="t in THEMES"
      :key="t"
      type="button"
      class="theme-option"
      :class="{ active: ui.theme === t }"
      @click="setTheme(t)"
    >
      <span class="theme-emoji" aria-hidden="true">{{ THEME_META[t].emoji }}</span>
      <span class="theme-name">{{ THEME_META[t].name }}</span>
    </button>
  </div>
</template>

<style scoped>
.theme-switcher {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.theme-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--cream);
  color: var(--ink-soft);
  font-family: var(--font-hand);
  font-size: 13px;
  line-height: 1.2;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.theme-option:hover {
  transform: translateY(-1px);
}

.theme-option.active {
  background: var(--brand-grad);
  border-color: transparent;
  color: #fff;
  box-shadow: var(--shadow-brand);
}

.theme-emoji {
  font-size: 15px;
}
</style>
