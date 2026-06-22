<template>
  <div id="kt-app">
    <header class="app-header">
      <router-link to="/" style="text-decoration:none;display:flex;align-items:center;gap:.75rem;">
        <h1>🧠 Knowledge Tester</h1>
      </router-link>
      <span class="subtitle">多智能体在线出题</span>
      <nav style="margin-left:auto;display:flex;gap:.5rem;">
        <router-link to="/generate" class="btn btn-sm btn-secondary">生成试卷</router-link>
      </nav>
    </header>
    <router-view />
  </div>
</template>
