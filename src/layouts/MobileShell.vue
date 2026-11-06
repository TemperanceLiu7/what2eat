<script setup>
import { state } from '@/data/db'
</script>

<template>
  <div class="shell mobile">
    <header class="m-header">
      <router-link to="/" class="m-brand">🍜 今天吃什么</router-link>
      <router-link to="/me" class="m-user">
        <van-tag v-if="state.user.verified" type="success" round>已认证</van-tag>
        <van-tag v-else round color="#fff1ea" text-color="#ff7a45">未认证</van-tag>
      </router-link>
    </header>

    <main class="m-main">
      <router-view />
    </main>

    <van-tabbar route :border="false" active-color="#ff7a45" inactive-color="#9aa0a6" safe-area-inset-bottom>
      <van-tabbar-item replace to="/" icon="fire-o">推荐</van-tabbar-item>
      <van-tabbar-item replace to="/checkin" icon="photo-o">打卡</van-tabbar-item>
      <van-tabbar-item replace to="/vote" icon="chart-trending-o">投票</van-tabbar-item>
      <van-tabbar-item replace to="/me" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
}

.m-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 48px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line);
  padding-top: env(safe-area-inset-top);
}

.m-brand {
  font-size: 16px;
  font-weight: 700;
}

.m-user {
  display: flex;
  align-items: center;
}

.m-main {
  padding-bottom: 64px;
}
</style>
