<script setup>
import { isLoggedIn, isVerified } from '@/stores/app'
</script>

<template>
  <div class="shell mobile">
    <header class="m-header">
      <router-link to="/" class="m-brand">🍜 今天吃什么</router-link>
      <router-link :to="isLoggedIn ? '/me' : '/login'" class="m-user">
        <van-tag v-if="isVerified" type="success" round>已认证</van-tag>
        <van-tag v-else-if="isLoggedIn" round color="#fff1ea" text-color="#ff7a45">未核验</van-tag>
        <van-tag v-else round color="#f2f3f5" text-color="#646b73">登录</van-tag>
      </router-link>
    </header>

    <main class="m-main">
      <router-view />
    </main>

    <van-tabbar route :border="false" active-color="#ff7a45" inactive-color="#9aa0a6" safe-area-inset-bottom>
      <van-tabbar-item replace to="/personal" icon="home-o">个人</van-tabbar-item>
      <van-tabbar-item replace to="/community" icon="friends-o">社区</van-tabbar-item>
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
