<template>
  <main class="app-shell">
    <header class="app-header">
      <div>
        <p class="eyebrow">TPMS-FORGE</p>
        <h1>TPMS 结构生成与打印路径规划平台</h1>
      </div>
      <nav>
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/dev/health">健康检查</RouterLink>
      </nav>
    </header>
    <RouterView />
  </main>
</template>
