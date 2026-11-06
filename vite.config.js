import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver, VantResolver } from 'unplugin-vue-components/resolvers'

// 同一份代码，PC 走 Element Plus，手机走 Vant。
// 两套组件库都按需引入：谁被渲染，谁的样式和代码才会进包。
// 部署在根路径（Cloudflare Pages / Vercel 都是根路径），不需要配 base。
export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [ElementPlusResolver(), VantResolver()],
      dts: false,
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { host: true, port: 5180 },
  preview: { host: true, port: 5180 },
})
