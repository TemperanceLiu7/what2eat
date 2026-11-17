<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { isLoggedIn, isVerified, ui } from '@/stores/app'
import ThemeSwitcher from '@/ui/ThemeSwitcher.vue'

const route = useRoute()
const active = computed(() => route.path)
</script>

<template>
  <div class="shell pc">
    <header class="pc-header">
      <div class="pc-header-inner">
        <router-link to="/" class="brand">
          <span class="brand-emoji">🍜</span>
          <span class="brand-name">今天吃什么</span>
          <span class="brand-tag">校园版</span>
        </router-link>

        <el-menu :default-active="active" mode="horizontal" router :ellipsis="false" class="pc-menu">
          <el-menu-item index="/personal">个人</el-menu-item>
          <el-menu-item index="/community">社区</el-menu-item>
          <el-menu-item index="/me">我的</el-menu-item>
        </el-menu>

        <ThemeSwitcher class="pc-theme" />

        <router-link :to="isLoggedIn ? '/me' : '/login'" class="pc-user">
          <el-tag v-if="isVerified" type="success" effect="light" round>
            已认证 · {{ ui.user.studentId }}
          </el-tag>
          <el-tag v-else-if="isLoggedIn" type="warning" effect="light" round>未核验 · 去核验</el-tag>
          <el-tag v-else effect="plain" round>登录 / 注册</el-tag>
        </router-link>
      </div>
    </header>

    <main class="pc-main">
      <router-view />
    </main>

    <footer class="pc-footer">
      课程设计演示 · 同一网址自动适配电脑与手机 · 数据保存在浏览器本地
    </footer>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.pc-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px dashed var(--brand-line-soft);
}

.pc-header-inner {
  width: min(var(--page-w), 100% - 48px);
  margin: 0 auto;
  height: 68px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.brand-emoji {
  font-size: 24px;
}

.brand-name {
  font-family: var(--font-hand);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--kraft-deep);
}

.brand-tag {
  font-family: var(--font-hand);
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--cream);
  color: var(--brand);
  transform: rotate(-2deg);
  box-shadow: var(--shadow-sm);
}

.pc-menu {
  flex: 1;
  border-bottom: none !important;
  background: transparent;
}

.pc-menu :deep(.el-menu-item) {
  font-family: var(--font-hand);
  font-size: 15px;
  color: var(--ink-soft);
  border-radius: 10px;
  margin: 0 4px;
  border-bottom: none !important;
}

.pc-menu :deep(.el-menu-item:hover) {
  background: rgba(244, 237, 217, 0.55) !important;
}

.pc-menu :deep(.el-menu-item.is-active) {
  background: var(--kraft) !important;
  color: var(--cream) !important;
  font-weight: 700;
}

.pc-theme {
  flex-shrink: 0;
}

.pc-user {
  flex-shrink: 0;
}

.pc-main {
  flex: 1;
}

.pc-footer {
  padding: 18px 0 28px;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 250, 238, 0.85);
}
</style>
