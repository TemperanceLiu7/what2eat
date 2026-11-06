<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { state } from '@/data/db'

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
          <el-menu-item index="/">随机推荐</el-menu-item>
          <el-menu-item index="/checkin">备餐打卡</el-menu-item>
          <el-menu-item index="/vote">吃不吃投票</el-menu-item>
          <el-menu-item index="/me">我的</el-menu-item>
        </el-menu>

        <router-link to="/me" class="pc-user">
          <el-tag v-if="state.user.verified" type="success" effect="light" round>
            已认证 · {{ state.user.studentId }}
          </el-tag>
          <el-tag v-else type="warning" effect="light" round>未认证 · 去绑定</el-tag>
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
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
}

.pc-header-inner {
  width: min(var(--page-w), 100% - 48px);
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.brand-emoji {
  font-size: 22px;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.brand-tag {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #fff1ea;
  color: var(--brand);
  font-weight: 600;
}

.pc-menu {
  flex: 1;
  border-bottom: none !important;
  background: transparent;
}

.pc-menu :deep(.el-menu-item) {
  font-size: 15px;
  border-bottom: 2px solid transparent !important;
}

.pc-menu :deep(.el-menu-item.is-active) {
  border-bottom-color: var(--brand) !important;
  font-weight: 600;
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
  color: var(--muted);
}
</style>
