<template>
  <div id="kt-app">
    <header class="app-header">
      <router-link to="/" class="brand" style="text-decoration:none;">
        <span class="brand-logo">K</span>
        <span>Knowledge Tester</span>
        <span class="brand-sub">多智能体出题</span>
      </router-link>
      <nav>
        <router-link to="/generate" class="btn btn-sm btn-secondary">生成试卷</router-link>
      </nav>
    </header>
    <router-view />
  </div>
</template>
