<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { isLoggedIn, isVerified, ui } from '@/stores/app'

const route = useRoute()
const active = computed(() => route.path)
</script>

<template>
  <div class="shell pc">
    <header class="pc-header">
      <div class="pc-header-inner">
        <router-link to="/" class="brand">
          <span class="brand-mark">吃</span>
          <span class="brand-name">今天吃什么</span>
          <span class="brand-tag">校园版</span>
        </router-link>

        <el-menu :default-active="active" mode="horizontal" router :ellipsis="false" class="pc-menu">
          <el-menu-item index="/personal">个人</el-menu-item>
          <el-menu-item index="/community">社区</el-menu-item>
          <el-menu-item index="/me">我的</el-menu-item>
        </el-menu>

        <router-link :to="isLoggedIn ? '/me' : '/login'" class="pc-user">
          <el-tag v-if="isVerified" type="success" effect="plain" size="small">
            已认证 · {{ ui.user.studentId }}
          </el-tag>
          <el-tag v-else-if="isLoggedIn" type="warning" effect="plain" size="small">
            未核验 · 去核验
          </el-tag>
          <el-tag v-else effect="plain" size="small">登录 / 注册</el-tag>
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
  background: var(--bg);
  border-bottom: 1px solid var(--line);
}

.pc-header-inner {
  width: min(var(--page-w), 100% - 48px);
  margin: 0 auto;
  height: 58px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-shrink: 0;
}

/* 方章式图标：朱红实底 + 白字，替代原来的 emoji */
.brand-mark {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand);
  color: #fff;
  border-radius: 2px;
  font-family: var(--font-serif);
  font-size: 14px;
  line-height: 1;
}

.brand-name {
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.brand-tag {
  font-size: 11px;
  padding: 2px 6px;
  border: 1px solid var(--brand-line);
  border-radius: 2px;
  color: var(--brand);
  line-height: 1.4;
}

.pc-menu {
  flex: 1;
  border-bottom: none !important;
  background: transparent;
}

.pc-menu :deep(.el-menu-item) {
  font-size: 14px;
  color: var(--ink-soft);
  border-bottom: 2px solid transparent !important;
}

.pc-menu :deep(.el-menu-item:hover) {
  background: transparent !important;
  color: var(--ink);
}

.pc-menu :deep(.el-menu-item.is-active) {
  border-bottom-color: var(--ink) !important;
  color: var(--ink);
  font-weight: 600;
}

.pc-user {
  flex-shrink: 0;
}

.pc-user :deep(.el-tag) {
  border-radius: 2px;
  font-size: 12px;
}

.pc-main {
  flex: 1;
}

.pc-footer {
  padding: 18px 0 26px;
  text-align: center;
  font-size: 12px;
  color: var(--muted);
  border-top: 1px solid var(--line);
  margin-top: 24px;
}
</style>
