<template>
  <NConfigProvider>
    <NMessageProvider>
      <NDialogProvider>
        <NLoadingBarProvider>
          <RouterView />
        </NLoadingBarProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { NConfigProvider, NDialogProvider, NLoadingBarProvider, NMessageProvider } from 'naive-ui'
</script>
